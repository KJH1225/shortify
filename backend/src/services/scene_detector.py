"""FFmpeg scene change detection"""
import asyncio
import re

from core.config import get_settings


class SceneDetector:
    """Detect scene changes in video using FFmpeg"""

    async def detect(self, video_path: str) -> list[float]:
        settings = get_settings()
        threshold = settings.scene_threshold

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null", "-",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        output = stderr.decode(errors="replace")
        timestamps: list[float] = []

        pts_pattern = re.compile(r"pts_time:(\d+\.?\d*)")
        for line in output.split("\n"):
            if "showinfo" in line:
                match = pts_pattern.search(line)
                if match:
                    timestamps.append(float(match.group(1)))

        return timestamps
