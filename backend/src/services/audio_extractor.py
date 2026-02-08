"""FFmpeg 기반 오디오 추출 서비스"""
import asyncio
import subprocess
import os

from core.config import get_settings


class AudioExtractor:
    """영상 파일에서 오디오를 추출하는 서비스"""

    def _check_ffmpeg(self) -> bool:
        """FFmpeg 설치 여부 확인"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    async def extract(self, video_path: str, output_path: str) -> str:
        """
        영상에서 오디오를 WAV(16kHz, mono)로 추출

        Args:
            video_path: 입력 영상 파일 경로
            output_path: 출력 WAV 파일 경로

        Returns:
            출력 파일 경로

        Raises:
            RuntimeError: FFmpeg 미설치 또는 실행 실패
            FileNotFoundError: 영상 파일 없음
        """
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg가 설치되지 않았습니다")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        settings = get_settings()
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(settings.audio_sample_rate),
            "-ac", "1",
            output_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()[:500]
            raise RuntimeError(f"오디오 추출 실패: {error_msg}")

        if not os.path.exists(output_path):
            raise RuntimeError("오디오 추출 결과 파일이 생성되지 않았습니다")

        return output_path
