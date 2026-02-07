"""Shared constants for the application"""

# Mock highlight data (shared with frontend)
MOCK_HIGHLIGHTS_DATA = [
    {
        "start_time": 45.0,
        "end_time": 78.0,
        "title": "핵심 개념 설명",
        "description": "영상에서 가장 중요한 핵심 개념을 설명하는 구간입니다.",
        "score": 0.95,
    },
    {
        "start_time": 120.0,
        "end_time": 165.0,
        "title": "놀라운 반전",
        "description": "시청자들의 반응이 가장 뜨거웠던 반전 구간입니다.",
        "score": 0.92,
    },
    {
        "start_time": 210.0,
        "end_time": 245.0,
        "title": "실용적인 팁",
        "description": "바로 적용할 수 있는 실용적인 팁을 공유하는 구간입니다.",
        "score": 0.88,
    },
    {
        "start_time": 300.0,
        "end_time": 340.0,
        "title": "감동적인 순간",
        "description": "영상에서 가장 감동적인 순간이 담긴 구간입니다.",
        "score": 0.85,
    },
    {
        "start_time": 420.0,
        "end_time": 480.0,
        "title": "결론 및 요약",
        "description": "전체 내용을 깔끔하게 정리하는 마무리 구간입니다.",
        "score": 0.82,
    },
]

# Processing messages (shared with frontend)
PROCESSING_MESSAGES = [
    "오디오 트랙 추출 중...",
    "음성을 텍스트로 변환 중...",
    "감정 분석 진행 중...",
    "하이라이트 구간 탐지 중...",
    "최적의 클립 선택 중...",
]

# File validation constants
ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
ALLOWED_MIME_TYPES = {
    'video/mp4', 'video/quicktime', 'video/x-msvideo',
    'video/x-matroska', 'video/webm', 'video/x-m4v'
}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

# YouTube URL patterns
YOUTUBE_URL_PATTERNS = [
    r'^https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    r'^https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    r'^https?://(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
    r'^https?://youtu\.be/([a-zA-Z0-9_-]{11})',
    r'^https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
]
