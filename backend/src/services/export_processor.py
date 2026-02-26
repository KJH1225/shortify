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
    ):
        self.export_id = export_id
        self.highlight_id = highlight_id
        self.video_path = video_path
        self.start_time = start_time
        self.end_time = end_time
        self.status = ExportStatus.PENDING
        self.output_path: Optional[str] = None
        self.error_message: Optional[str] = None
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "export_id": self.export_id,
            "highlight_id": self.highlight_id,
            "video_path": self.video_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value,
            "output_path": self.output_path,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExportJob":
        job = cls(
            export_id=data["export_id"],
            highlight_id=int(data["highlight_id"]),
            video_path=data["video_path"],
            start_time=float(data["start_time"]),
            end_time=float(data["end_time"]),
        )
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
    ) -> ExportJob:
        """Create a new export job"""
        export_id = f"export_{uuid.uuid4().hex[:8]}"

        job = ExportJob(
            export_id=export_id,
            highlight_id=highlight_id,
            video_path=video_path,
            start_time=start_time,
            end_time=end_time,
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
        output_filename = f"{job.highlight_id}_{int(job.start_time)}_{int(job.end_time)}.mp4"
        output_path = self.output_dir / output_filename

        try:
            cmd = [
                "ffmpeg",
                "-y",
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
