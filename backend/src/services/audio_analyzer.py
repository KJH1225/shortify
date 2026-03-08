"""FFmpeg audio energy analysis for multimodal highlight detection"""
import asyncio
import re
from dataclasses import dataclass

from core.config import get_settings


@dataclass
class AudioHotspot:
    timestamp: float
    rms_level: float
    description: str  # "volume_spike" | "silence_to_voice" | "emotion_shift"


class AudioAnalyzer:
    """Analyze audio energy to detect hotspots (volume spikes, silence transitions, emotion shifts)"""

    async def analyze(self, audio_path: str) -> list[AudioHotspot]:
        settings = get_settings()
        top_n = settings.audio_hotspot_count

        rms_values = await self._extract_rms_levels(audio_path)
        if not rms_values:
            return []

        hotspots: list[AudioHotspot] = []

        # Existing detectors
        hotspots.extend(self._detect_volume_spikes(rms_values))
        hotspots.extend(self._detect_silence_transitions(rms_values))

        # New: loudness shift detection
        loudness_hotspots = await self._detect_loudness_shifts(audio_path)
        hotspots.extend(loudness_hotspots)

        # Deduplicate nearby hotspots (within 2 seconds)
        hotspots = self._deduplicate(hotspots, min_gap=2.0)

        hotspots.sort(key=lambda h: h.rms_level, reverse=True)
        return hotspots[:top_n]

    def _detect_volume_spikes(self, rms_values: list[tuple[float, float]]) -> list[AudioHotspot]:
        """Volume spike: current > avg of previous 5 seconds + 6dB"""
        hotspots = []
        for i, (ts, rms) in enumerate(rms_values):
            if i >= 5:
                prev_avg = sum(v for _, v in rms_values[i - 5:i]) / 5
                if rms > prev_avg + 6:
                    hotspots.append(AudioHotspot(
                        timestamp=ts, rms_level=rms,
                        description="volume_spike",
                    ))
        return hotspots

    def _detect_silence_transitions(self, rms_values: list[tuple[float, float]]) -> list[AudioHotspot]:
        """Silence to voice: previous < -50dB, current > -30dB"""
        hotspots = []
        for i, (ts, rms) in enumerate(rms_values):
            if i > 0:
                _, prev_rms = rms_values[i - 1]
                if prev_rms < -50 and rms > -30:
                    hotspots.append(AudioHotspot(
                        timestamp=ts, rms_level=rms,
                        description="silence_to_voice",
                    ))
        return hotspots

    async def _detect_loudness_shifts(self, audio_path: str) -> list[AudioHotspot]:
        """ebur128 Momentary Loudness 급변 감지 (감정 전환 포인트)"""
        cmd = [
            "ffmpeg", "-i", audio_path,
            "-af", "ebur128=metadata=1,ametadata=print:key=lavfi.r128.M",
            "-f", "null", "-",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            return []  # ebur128 not supported — fallback gracefully

        output = stderr.decode(errors="replace")
        pts_pattern = re.compile(r"pts_time:(\d+\.?\d*)")
        loudness_pattern = re.compile(r"lavfi\.r128\.M=(-?\d+\.?\d*)")

        values: list[tuple[float, float]] = []
        current_pts = 0.0
        for line in output.split("\n"):
            pts_match = pts_pattern.search(line)
            if pts_match:
                current_pts = float(pts_match.group(1))
            loudness_match = loudness_pattern.search(line)
            if loudness_match:
                val = float(loudness_match.group(1))
                if val > -70:
                    values.append((current_pts, val))

        settings = get_settings()
        threshold = settings.loudness_shift_threshold
        hotspots = []
        for i in range(1, len(values)):
            ts, lufs = values[i]
            _, prev_lufs = values[i - 1]
            delta = abs(lufs - prev_lufs)
            if delta >= threshold:
                hotspots.append(AudioHotspot(
                    timestamp=ts, rms_level=lufs,
                    description="emotion_shift",
                ))

        return hotspots

    def _deduplicate(self, hotspots: list[AudioHotspot], min_gap: float = 2.0) -> list[AudioHotspot]:
        """Remove nearby duplicates, keeping highest RMS"""
        hotspots.sort(key=lambda h: h.rms_level, reverse=True)
        result = []
        for h in hotspots:
            if not any(abs(h.timestamp - e.timestamp) < min_gap for e in result):
                result.append(h)
        return result

    async def _extract_rms_levels(self, audio_path: str) -> list[tuple[float, float]]:
        """Extract per-second RMS levels using FFmpeg astats"""
        cmd = [
            "ffmpeg", "-i", audio_path,
            "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
            "-f", "null", "-",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        output = stderr.decode(errors="replace")
        rms_values: list[tuple[float, float]] = []

        # Parse: frame:N ... pts_time:X.XXX
        #        lavfi.astats.Overall.RMS_level=-XX.XX
        pts_pattern = re.compile(r"pts_time:(\d+\.?\d*)")
        rms_pattern = re.compile(r"lavfi\.astats\.Overall\.RMS_level=(-?\d+\.?\d*)")

        current_pts = 0.0
        for line in output.split("\n"):
            pts_match = pts_pattern.search(line)
            if pts_match:
                current_pts = float(pts_match.group(1))

            rms_match = rms_pattern.search(line)
            if rms_match:
                rms_val = float(rms_match.group(1))
                if rms_val > -100:  # Filter out -inf values
                    rms_values.append((current_pts, rms_val))

        return rms_values
