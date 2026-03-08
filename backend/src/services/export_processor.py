"""Export processor for highlight video generation using FFmpeg"""
from __future__ import annotations

import asyncio
import json
import subprocess
import os
import tempfile
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
        clips: list[dict] | None = None,
        title: str = "",
    ):
        self.export_id = export_id
        self.highlight_id = highlight_id
        self.video_path = video_path
        self.start_time = start_time
        self.end_time = end_time
        self.layout = layout
        self.clips = clips
        self.title = title
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
            "clips": json.dumps(self.clips) if self.clips else "",
            "title": self.title,
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
        job.title = data.get("title", "")
        clips_raw = data.get("clips", "")
        job.clips = json.loads(clips_raw) if clips_raw else None
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

    def _check_xfade_support(self) -> bool:
        """Check if FFmpeg supports xfade filter (4.3+)"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-filters"],
                capture_output=True, text=True,
            )
            return "xfade" in result.stdout
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
        clips: list[dict] | None = None,
        title: str = "",
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
            clips=clips,
            title=title,
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

        title_img_path = None
        try:
            # Generate title overlay image for shortform
            if job.layout == "shortform" and job.title:
                title_img_path = self._generate_title_image(job.title)

            has_multi_clips = job.clips and len(job.clips) > 1

            if has_multi_clips and job.layout == "shortform":
                src_w, src_h = await self._get_video_dimensions(job.video_path)
                cmd = self._build_shortform_concat_cmd(
                    job.video_path, str(output_path), job.clips,
                    src_w, src_h, title_img_path=title_img_path,
                )
            elif has_multi_clips:
                cmd = self._build_concat_cmd(
                    job.video_path, str(output_path), job.clips,
                )
            elif job.layout == "shortform":
                src_w, src_h = await self._get_video_dimensions(job.video_path)
                cmd = self._build_shortform_cmd(
                    job.video_path, str(output_path),
                    job.start_time, duration, src_w, src_h,
                    title_img_path=title_img_path,
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
        finally:
            if title_img_path and os.path.exists(title_img_path):
                os.unlink(title_img_path)

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

    def _generate_title_image(self, title: str) -> str | None:
        """Pillow로 제목 텍스트 투명 PNG 생성. title이 없으면 None 반환."""
        if not title:
            return None

        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return None

        from core.constants import (
            SHORTFORM_WIDTH, SHORTFORM_CONTENT_Y,
            SHORTFORM_TITLE_FONTSIZE, SHORTFORM_TITLE_Y,
            SHORTFORM_TITLE_FONT, SHORTFORM_TITLE_BORDERW,
            SHORTFORM_TITLE_SHADOWX, SHORTFORM_TITLE_SHADOWY,
        )

        W = SHORTFORM_WIDTH
        H = SHORTFORM_CONTENT_Y  # 288px (top safe zone)

        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(SHORTFORM_TITLE_FONT, SHORTFORM_TITLE_FONTSIZE)
        except (OSError, IOError):
            return None

        bbox = draw.textbbox((0, 0), title, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = (W - text_w) // 2
        text_y = SHORTFORM_TITLE_Y

        # Shadow
        draw.text(
            (text_x + SHORTFORM_TITLE_SHADOWX, text_y + SHORTFORM_TITLE_SHADOWY),
            title, font=font, fill=(0, 0, 0, 128),
        )
        # Main text with stroke
        draw.text(
            (text_x, text_y), title, font=font, fill="white",
            stroke_width=SHORTFORM_TITLE_BORDERW, stroke_fill="black",
        )

        tmp = tempfile.NamedTemporaryFile(
            suffix=".png", delete=False, dir=str(self.output_dir),
        )
        img.save(tmp.name, "PNG")
        tmp.close()
        return tmp.name

    def _build_shortform_cmd(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        duration: float,
        src_width: int,
        src_height: int,
        title_img_path: str | None = None,
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

        inputs = [
            "-ss", str(start_time),
            "-i", input_path,
            "-t", str(duration),
        ]
        if title_img_path:
            inputs.extend(["-i", title_img_path])

        if is_portrait:
            base = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1"
            if title_img_path:
                filter_complex = f"{base}[base];[base][1:v]overlay=0:0"
            else:
                filter_complex = base
            return [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "0:a",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                "-crf", "23",
                "-movflags", "+faststart",
                output_path,
            ]
        else:
            base = (
                f"[0:v]scale={W}:{H},boxblur={BLUR}:{BLUR}[bg];"
                f"[0:v]scale='if(gt(iw/ih,{W}/{CH}),{W},-2)'"
                f":'if(gt(iw/ih,{W}/{CH}),-2,{CH})'[fg];"
                f"[bg][fg]overlay=(W-w)/2:{CY}+({CH}-h)/2,setsar=1"
            )
            if title_img_path:
                filter_complex = f"{base}[base];[base][1:v]overlay=0:0"
            else:
                filter_complex = base
            return [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "0:a",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                "-crf", "23",
                "-movflags", "+faststart",
                output_path,
            ]

    def _build_concat_cmd(
        self,
        input_path: str,
        output_path: str,
        clips: list[dict],
    ) -> list[str]:
        """서브클립 concat FFmpeg 커맨드 빌드 (xfade 크로스페이드 + concat 폴백)"""
        n = len(clips)
        fade = get_settings().crossfade_duration
        use_xfade = fade > 0 and n > 1 and self._check_xfade_support()

        inputs: list[str] = []
        filter_parts: list[str] = []
        for i, clip in enumerate(clips):
            dur = clip["end"] - clip["start"]
            inputs.extend(["-ss", str(clip["start"]), "-t", str(dur), "-i", input_path])
            filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
            filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

        if use_xfade:
            durations = [clip["end"] - clip["start"] for clip in clips]

            # Video xfade chaining
            prev_v = "v0"
            accumulated = durations[0]
            for i in range(1, n):
                offset = accumulated - fade
                out_label = "outv" if i == n - 1 else f"xv{i}"
                filter_parts.append(
                    f"[{prev_v}][v{i}]xfade=transition=fade:duration={fade}:offset={offset}[{out_label}]"
                )
                accumulated += durations[i] - fade
                prev_v = out_label

            # Audio acrossfade chaining
            prev_a = "a0"
            for i in range(1, n):
                out_label = "outa" if i == n - 1 else f"xa{i}"
                filter_parts.append(
                    f"[{prev_a}][a{i}]acrossfade=d={fade}:c1=tri:c2=tri[{out_label}]"
                )
                prev_a = out_label
        else:
            streams = "".join(f"[v{i}][a{i}]" for i in range(n))
            filter_parts.append(f"{streams}concat=n={n}:v=1:a=1[outv][outa]")

        filter_complex = ";".join(filter_parts)

        return [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            "-crf", "23",
            "-movflags", "+faststart",
            output_path,
        ]

    def _build_shortform_concat_cmd(
        self,
        input_path: str,
        output_path: str,
        clips: list[dict],
        src_width: int,
        src_height: int,
        title_img_path: str | None = None,
    ) -> list[str]:
        """서브클립 concat + 9:16 숏폼 레이아웃 FFmpeg 커맨드 (xfade 크로스페이드 + 폴백)"""
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

        n = len(clips)
        fade = get_settings().crossfade_duration
        use_xfade = fade > 0 and n > 1 and self._check_xfade_support()
        is_portrait = src_height > src_width

        inputs: list[str] = []
        filter_parts: list[str] = []
        for i, clip in enumerate(clips):
            dur = clip["end"] - clip["start"]
            inputs.extend(["-ss", str(clip["start"]), "-t", str(dur), "-i", input_path])
            filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
            filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

        # Title image is the last input (index = n)
        if title_img_path:
            inputs.extend(["-i", title_img_path])
            title_idx = n

        if use_xfade:
            durations = [clip["end"] - clip["start"] for clip in clips]

            # Video xfade chaining -> [cv]
            prev_v = "v0"
            accumulated = durations[0]
            for i in range(1, n):
                offset = accumulated - fade
                out_label = "cv" if i == n - 1 else f"xv{i}"
                filter_parts.append(
                    f"[{prev_v}][v{i}]xfade=transition=fade:duration={fade}:offset={offset}[{out_label}]"
                )
                accumulated += durations[i] - fade
                prev_v = out_label

            # Audio acrossfade chaining -> [ca]
            prev_a = "a0"
            for i in range(1, n):
                out_label = "ca" if i == n - 1 else f"xa{i}"
                filter_parts.append(
                    f"[{prev_a}][a{i}]acrossfade=d={fade}:c1=tri:c2=tri[{out_label}]"
                )
                prev_a = out_label
        else:
            streams = "".join(f"[v{i}][a{i}]" for i in range(n))
            filter_parts.append(f"{streams}concat=n={n}:v=1:a=1[cv][ca]")

        # Shortform layout
        if is_portrait:
            base = (
                f"[cv]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1"
            )
            if title_img_path:
                filter_parts.append(f"{base}[sf_base];[sf_base][{title_idx}:v]overlay=0:0[outv]")
            else:
                filter_parts.append(f"{base}[outv]")
        else:
            filter_parts.append(f"[cv]split=2[cv_bg][cv_fg]")
            base = (
                f"[cv_bg]scale={W}:{H},boxblur={BLUR}:{BLUR}[bg];"
                f"[cv_fg]scale='if(gt(iw/ih,{W}/{CH}),{W},-2)'"
                f":'if(gt(iw/ih,{W}/{CH}),-2,{CH})'[fg];"
                f"[bg][fg]overlay=(W-w)/2:{CY}+({CH}-h)/2,setsar=1"
            )
            if title_img_path:
                filter_parts.append(f"{base}[sf_base];[sf_base][{title_idx}:v]overlay=0:0[outv]")
            else:
                filter_parts.append(f"{base}[outv]")

        filter_parts.append("[ca]anull[outa]")
        filter_complex = ";".join(filter_parts)

        return [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[outa]",
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
