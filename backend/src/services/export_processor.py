"""Export processor for highlight video generation using FFmpeg"""
import asyncio
import subprocess
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

from core.config import get_settings


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


# In-memory job storage (replace with Redis/DB in production)
_export_jobs: dict[str, ExportJob] = {}


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

        _export_jobs[export_id] = job
        return job

    async def process_export(self, job: ExportJob) -> ExportJob:
        """Process the export job using FFmpeg"""
        job.status = ExportStatus.PROCESSING

        # Check FFmpeg availability
        if not self._check_ffmpeg():
            job.status = ExportStatus.ERROR
            job.error_message = "FFmpeg is not installed or not in PATH"
            return job

        # Check if source video exists
        if not os.path.exists(job.video_path):
            job.status = ExportStatus.ERROR
            job.error_message = f"Source video not found: {job.video_path}"
            return job

        # Generate output filename
        duration = job.end_time - job.start_time
        output_filename = f"{job.highlight_id}_{int(job.start_time)}_{int(job.end_time)}.mp4"
        output_path = self.output_dir / output_filename

        try:
            # FFmpeg command for video clipping
            # -ss: start time (before -i for fast seeking)
            # -t: duration
            # -c:v libx264: H.264 video codec
            # -c:a aac: AAC audio codec
            # -preset fast: encoding speed/quality balance
            # -crf 23: quality (lower = better, 18-28 is reasonable)
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-ss", str(job.start_time),
                "-i", job.video_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                "-crf", "23",
                "-movflags", "+faststart",  # Enable streaming
                str(output_path),
            ]

            # Run FFmpeg asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                job.status = ExportStatus.COMPLETED
                job.output_path = str(output_path)
                job.completed_at = datetime.now()
            else:
                job.status = ExportStatus.ERROR
                job.error_message = stderr.decode()[:500]  # Limit error message

        except Exception as e:
            job.status = ExportStatus.ERROR
            job.error_message = str(e)

        return job

    def get_job(self, export_id: str) -> Optional[ExportJob]:
        """Get export job by ID"""
        return _export_jobs.get(export_id)

    def get_job_status(self, export_id: str) -> dict:
        """Get job status as dict"""
        job = self.get_job(export_id)
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
