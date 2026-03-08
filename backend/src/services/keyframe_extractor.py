"""FFmpeg keyframe extraction for multimodal analysis"""
import asyncio
import base64
import os
from dataclasses import dataclass
from pathlib import Path

from core.config import get_settings


@dataclass
class KeyframeInfo:
    timestamp: float
    base64: str


class KeyframeExtractor:
    """Extract keyframes from video at regular intervals"""

    async def extract(
        self,
        video_path: str,
        output_dir: str,
        duration: float = 0,
    ) -> list[KeyframeInfo]:
        settings = get_settings()
        interval = settings.keyframe_interval
        max_count = settings.keyframe_max_count
        width = settings.keyframe_width

        # Adjust interval if too many frames
        if duration > 0 and duration / interval > max_count:
            interval = int(duration / max_count) + 1

        os.makedirs(output_dir, exist_ok=True)
        pattern = os.path.join(output_dir, "frame_%04d.jpg")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"fps=1/{interval},scale={width}:-1",
            "-q:v", "5",
            pattern,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

        # Read generated frames and encode to base64
        keyframes: list[KeyframeInfo] = []
        frame_files = sorted(Path(output_dir).glob("frame_*.jpg"))

        for i, frame_path in enumerate(frame_files[:max_count]):
            timestamp = i * interval
            with open(frame_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            keyframes.append(KeyframeInfo(timestamp=timestamp, base64=b64))

        return keyframes

    async def extract_smart(
        self,
        video_path: str,
        output_dir: str,
        duration: float,
        scene_changes: list[float],
        audio_hotspot_timestamps: list[float],
    ) -> list[KeyframeInfo]:
        """이벤트 기반 키프레임 추출: 장면전환 + 오디오핫스팟 + 균등보간"""
        settings = get_settings()
        max_count = settings.keyframe_max_count
        width = settings.keyframe_width
        interval = settings.keyframe_interval

        # 1) 이벤트 시점 수집
        event_times: set[float] = set()
        for t in scene_changes:
            event_times.add(round(t, 1))
        for t in audio_hotspot_timestamps:
            event_times.add(round(t, 1))

        # 2) 균등 간격 보간 (빈 구간 커버)
        for t in range(0, int(duration), interval):
            event_times.add(float(t))

        # 3) 정렬 + 근접 중복 제거 (2초 이내)
        sorted_times = sorted(event_times)
        if not sorted_times:
            return await self.extract(video_path, output_dir, duration)

        filtered = [sorted_times[0]]
        for t in sorted_times[1:]:
            if t - filtered[-1] >= 2.0:
                filtered.append(t)

        targets = filtered[:max_count]

        # 4) 타임스탬프 기반 프레임 추출
        return await self._extract_at_timestamps(video_path, output_dir, targets, width)

    async def _extract_at_timestamps(
        self,
        video_path: str,
        output_dir: str,
        timestamps: list[float],
        width: int,
    ) -> list[KeyframeInfo]:
        """지정된 타임스탬프에서 프레임 추출"""
        os.makedirs(output_dir, exist_ok=True)
        keyframes: list[KeyframeInfo] = []

        for i, ts in enumerate(timestamps):
            frame_path = os.path.join(output_dir, f"frame_{i:04d}.jpg")
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(ts),
                "-i", video_path,
                "-vframes", "1",
                "-vf", f"scale={width}:-1",
                "-q:v", "5",
                frame_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            if os.path.exists(frame_path):
                with open(frame_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                keyframes.append(KeyframeInfo(timestamp=ts, base64=b64))

        return keyframes

    def cleanup(self, output_dir: str):
        """Remove temporary keyframe files"""
        if os.path.exists(output_dir):
            for f in Path(output_dir).glob("frame_*.jpg"):
                f.unlink()
            try:
                os.rmdir(output_dir)
            except OSError:
                pass
