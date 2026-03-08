"""Export processor for highlight video generation using FFmpeg"""
from __future__ import annotations

import asyncio
import subprocess
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

from core.config import get_settings
from infrastructure.redis_client import get_redis


class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ExportJob:
    """Represents an export job"""

    def __init__(
        self,
        export_id: str,
        highlight_id: int,
        video_path: str,
        start_time: float,
        end_time: float,
        layout: str = "original",
    ):
        self.export_id = export_id
        self.highlight_id = highlight_id
        self.video_path = video_path
        self.start_time = start_time
        self.end_time = end_time
        self.layout = layout
        self.status = ExportStatus.PENDING
        self.output_path: Optional[str] = None
        self.error_message: Optional[str] = None
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        data: dict = {
            "export_id": self.export_id,
            "highlight_id": self.highlight_id,
            "video_path": self.video_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "layout": self.layout,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }
        if self.output_path is not None:
            data["output_path"] = self.output_path
        if self.error_message is not None:
            data["error_message"] = self.error_message
        if self.completed_at is not None:
            data["completed_at"] = self.completed_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ExportJob":
        job = cls(
            export_id=data["export_id"],
            highlight_id=int(data["highlight_id"]),
            video_path=data["video_path"],
            start_time=float(data["start_time"]),
            end_time=float(data["end_time"]),
        )
        job.layout = data.get("layout", "original")
        job.status = ExportStatus(data["status"])
        job.output_path = data.get("output_path")
        job.error_message = data.get("error_message")
        job.created_at = datetime.fromisoformat(data["created_at"])
        completed_at = data.get("completed_at")
        job.completed_at = datetime.fromisoformat(completed_at) if completed_at else None
        return job


class ExportProcessor:
    """Handles video export/clipping using FFmpeg"""

    def __init__(self):
        self.output_dir = Path(get_settings().upload_dir) / "exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _job_key(self, export_id: str) -> str:
        return f"export_job:{export_id}"

    async def _save_job(self, job: ExportJob) -> None:
        redis = get_redis()
        ttl = get_settings().export_job_ttl_seconds
        await redis.hset(self._job_key(job.export_id), mapping=job.to_dict())
        await redis.expire(self._job_key(job.export_id), ttl)

    async def create_export_job(
        self,
        highlight_id: int,
        video_path: str,
        start_time: float,
        end_time: float,
        layout: str = "original",
    ) -> ExportJob:
        """Create a new export job"""
        export_id = f"export_{uuid.uuid4().hex[:8]}"

        job = ExportJob(
            export_id=export_id,
            highlight_id=highlight_id,
            video_path=video_path,
            start_time=start_time,
            end_time=end_time,
            layout=layout,
        )
        await self._save_job(job)
        return job

    async def process_export(self, job: ExportJob) -> ExportJob:
        """Process the export job using FFmpeg"""
        job.status = ExportStatus.PROCESSING
        await self._save_job(job)

        # Check FFmpeg availability
        if not self._check_ffmpeg():
            job.status = ExportStatus.ERROR
            job.error_message = "FFmpeg is not installed or not in PATH"
            await self._save_job(job)
            return job

        # Check if source video exists
        if not os.path.exists(job.video_path):
            job.status = ExportStatus.ERROR
            job.error_message = f"Source video not found: {job.video_path}"
            await self._save_job(job)
            return job

        # Generate output filename
        duration = job.end_time - job.start_time

        # 숏폼 모드: 최대 길이 제한
        if job.layout == "shortform":
            from core.constants import SHORTFORM_MAX_DURATION
            if duration > SHORTFORM_MAX_DURATION:
                job.status = ExportStatus.ERROR
                job.error_message = f"숏폼 모드는 최대 {SHORTFORM_MAX_DURATION}초까지 지원합니다 (현재: {int(duration)}초)"
                await self._save_job(job)
                return job

        suffix = "_sf" if job.layout == "shortform" else ""
        output_filename = f"{job.highlight_id}_{int(job.start_time)}_{int(job.end_time)}{suffix}.mp4"
        output_path = self.output_dir / output_filename

        try:
            if job.layout == "shortform":
                src_w, src_h = await self._get_video_dimensions(job.video_path)
                cmd = self._build_shortform_cmd(
                    job.video_path, str(output_path),
                    job.start_time, duration, src_w, src_h,
                )
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(job.start_time),
                    "-i", job.video_path,
                    "-t", str(duration),
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-preset", "fast",
                    "-crf", "23",
                    "-movflags", "+faststart",
                    str(output_path),
                ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await process.communicate()

            if process.returncode == 0:
                job.status = ExportStatus.COMPLETED
                job.output_path = str(output_path)
                job.completed_at = datetime.now()
            else:
                job.status = ExportStatus.ERROR
                job.error_message = stderr.decode()[:500]

        except Exception as e:
            job.status = ExportStatus.ERROR
            job.error_message = str(e)

        await self._save_job(job)
        return job

    async def _get_video_dimensions(self, video_path: str) -> tuple[int, int]:
        """ffprobe로 영상 width/height 조회"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            video_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        parts = stdout.decode().strip().split("x")
        return int(parts[0]), int(parts[1])

    def _build_shortform_cmd(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        duration: float,
        src_width: int,
        src_height: int,
    ) -> list[str]:
        """9:16 숏폼 레이아웃 FFmpeg 커맨드 빌드"""
        from core.constants import (
            SHORTFORM_WIDTH, SHORTFORM_HEIGHT,
            SHORTFORM_CONTENT_HEIGHT, SHORTFORM_CONTENT_Y,
            SHORTFORM_BLUR_STRENGTH,
        )

        W = SHORTFORM_WIDTH
        H = SHORTFORM_HEIGHT
        CY = SHORTFORM_CONTENT_Y
        CH = SHORTFORM_CONTENT_HEIGHT
        BLUR = SHORTFORM_BLUR_STRENGTH

        is_portrait = src_height > src_width

        if is_portrait:
            vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1"
            return [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", input_path,
                "-t", str(duration),
                "-vf", vf,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                "-crf", "23",
                "-movflags", "+faststart",
                output_path,
            ]
        else:
            filter_complex = (
                f"[0:v]scale={W}:{H},boxblur={BLUR}:{BLUR}[bg];"
                f"[0:v]scale='if(gt(iw/ih,{W}/{CH}),{W},-2)'"
                f":'if(gt(iw/ih,{W}/{CH}),-2,{CH})'[fg];"
                f"[bg][fg]overlay=(W-w)/2:{CY}+({CH}-h)/2,setsar=1"
            )
            return [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", input_path,
                "-t", str(duration),
                "-filter_complex", filter_complex,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                "-crf", "23",
                "-movflags", "+faststart",
                output_path,
            ]

    async def get_job(self, export_id: str) -> Optional[ExportJob]:
        """Get export job by ID"""
        redis = get_redis()
        data = await redis.hgetall(self._job_key(export_id))
        if not data:
            return None
        return ExportJob.from_dict(data)

    async def get_job_status(self, export_id: str) -> dict:
        """Get job status as dict"""
        job = await self.get_job(export_id)
        if not job:
            return {"error": "Job not found"}

        download_url = None
        if job.status == ExportStatus.COMPLETED:
            download_url = f"/api/highlights/{job.highlight_id}/export/{job.export_id}/download"

        return {
            "export_id": job.export_id,
            "highlight_id": job.highlight_id,
            "status": job.status.value,
            "download_url": download_url,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }


# Singleton instance
export_processor = ExportProcessor()
