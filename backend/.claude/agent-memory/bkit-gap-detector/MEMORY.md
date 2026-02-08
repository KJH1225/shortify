# Gap Detector Memory - Shortify Backend

## Project Context
- **Project**: Shortify - YouTube video highlight extraction tool
- **Backend**: FastAPI + SQLAlchemy + OpenAI (Whisper + GPT-4o-mini)
- **Architecture**: Layered (core/domain, services/application, api/presentation, infrastructure)

## Key Patterns
- Python snake_case conventions throughout
- Services follow single-responsibility principle
- VideoProcessor is the orchestrator for audio_extractor, transcription_service, highlight_analyzer
- Mock fallback was intentionally removed (2026-02-08) - AI failures produce ERROR responses

## Analysis History
| Feature | Date | Match Rate | V-Items | Status |
|---------|------|-----------|---------|--------|
| real-ai-integration | 2026-02-08 | 97% | 12/12 PASS | PASS |

## Common Design Patterns in This Project
- `get_settings()` singleton via `@lru_cache`
- `async_session_maker()` for DB sessions in services
- `asyncio.create_subprocess_exec()` for FFmpeg
- Exponential backoff retry: `sleep(delay * 2^attempt)`
- `HighlightRepository.create_batch()` for bulk insert
- `finally` blocks for resource cleanup (temp audio files)

## Lessons Learned
- OpenAI `response_format: json_object` requires top-level JSON object, not array
  - Design may show array format but impl correctly wraps in {"highlights": [...]}
  - This is a valid technical improvement, not a gap
- When user explicitly requests removal of mock/fallback, treat as intentional change
- Helper methods (like _save_highlights) may be inlined - count as MINOR gap if functional equivalent
