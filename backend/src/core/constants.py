"""Shared constants for the application"""

# AI Highlight Analysis Prompts
HIGHLIGHT_SYSTEM_PROMPT = """You are a professional video highlight extraction expert.
Analyze the transcript and extract the most engaging, valuable segments.

Selection criteria:
- Key concepts or important information delivery
- Emotionally impactful moments
- Surprising insights or turning points
- Practical tips and advice
- Segments that attract viewer attention

Rules:
- Each highlight must be 15-60 seconds long
- Highlights must not overlap
- Score reflects importance (0.0-1.0, higher = more important)
- Title should be concise (under 20 characters)
- Description should explain why this segment is valuable (under 50 characters)
- Respond in the same language as the transcript
- Return a JSON object with a "highlights" key containing an array"""

HIGHLIGHT_USER_PROMPT = """Video duration: {duration} seconds
Target highlight count: {target_count}

Transcript:
{transcript}

Extract highlights as a JSON object:
{{"highlights": [
  {{
    "start_time": <start seconds>,
    "end_time": <end seconds>,
    "title": "<highlight title>",
    "description": "<why this segment matters>",
    "score": <0.0-1.0>
  }}
]}}"""

# AI 처리 진행 메시지
AI_PROCESSING_MESSAGES = {
    "audio_extract_start": "오디오 트랙 추출 중...",
    "audio_extract_done": "오디오 추출 완료",
    "stt_start": "음성을 텍스트로 변환 중...",
    "stt_chunking": "긴 오디오 분할 처리 중... ({current}/{total} 청크)",
    "stt_done": "음성 인식 완료 ({segment_count}개 세그먼트)",
    "analysis_start": "AI가 하이라이트 구간 분석 중...",
    "analysis_done": "하이라이트 {count}개 추출 완료",
    "saving": "결과 저장 중...",
    "completed": "AI 분석이 완료되었습니다!",
}

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
