# Design: video-player

> Feature: 인터랙티브 영상 플레이어 + 하이라이트 타임라인 프리뷰
> Plan: `docs/01-plan/features/video-player.plan.md`
> Created: 2026-02-08

## 1. 구현 순서

```
1. [BE] api/stream.py           - (신규) 영상 스트리밍 라우터 (Range Request)
2. [BE] main.py                 - stream 라우터 등록
3. [FE] services/api.ts         - getVideoStreamUrl() 헬퍼 추가
4. [FE] components/molecules/HighlightTimeline.tsx  - (신규) 하이라이트 마커 타임라인
5. [FE] components/organisms/VideoPlayer.tsx        - (신규) 영상 플레이어 + 컨트롤
6. [FE] app/page.tsx            - VideoPlayer 통합, handlePlay/상태 연동
```

## 2. 아키텍처 개요

```
page.tsx (메인 페이지)
    │
    ├── VideoPlayer (organism)
    │     ├── <video> (HTML5 native)
    │     ├── 커스텀 컨트롤 (Play/Pause, 볼륨, 시간)
    │     └── HighlightTimeline (molecule)
    │           └── 마커 (absolute positioned divs)
    │
    ├── HighlightGrid (organism)
    │     └── HighlightCard (molecule) → onPlay → VideoPlayer.seekTo()
    │
    └── <video src>  →  GET /api/videos/{id}/stream (Range Request)
```

**설계 원칙**:
- `<video>` native API 직접 사용 (외부 라이브러리 불필요)
- 플레이어와 하이라이트 카드는 `page.tsx`의 상태로 연동
- Range Request로 시크 및 부분 로딩 지원
- 하이라이트 구간 자동 재생/자동 정지

## 3. Backend 설계

### 3.1 스트리밍 엔드포인트

**파일**: `backend/src/api/stream.py` (신규)

```python
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pathlib import Path
import os
import mimetypes

from core.config import get_settings

router = APIRouter()


@router.get("/videos/{video_id}/stream")
async def stream_video(video_id: int, request: Request):
    """
    영상 파일 스트리밍 (Range Request 지원)

    Response:
        200: 전체 파일 (Range 헤더 없을 때)
        206: 부분 콘텐츠 (Range 헤더 있을 때)
        404: 영상 파일 없음
    """
    video_path = _find_video_path(video_id)
    if not video_path:
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다")

    file_size = os.path.getsize(video_path)
    content_type = mimetypes.guess_type(video_path)[0] or "video/mp4"

    range_header = request.headers.get("range")

    if range_header:
        # Range Request → 206 Partial Content
        start, end = _parse_range(range_header, file_size)
        content_length = end - start + 1

        return StreamingResponse(
            _file_iterator(video_path, start, end),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            },
        )

    # Range 없음 → 200 전체 파일
    return StreamingResponse(
        _file_iterator(video_path, 0, file_size - 1),
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
    )


def _find_video_path(video_id: int) -> str | None:
    """영상 파일 경로 탐색 (video_processor._get_video_path와 동일 로직)"""
    upload_dir = Path(get_settings().upload_dir)

    # YouTube: {video_id}.mp4
    mp4_path = upload_dir / f"{video_id}.mp4"
    if mp4_path.exists():
        return str(mp4_path)

    # File upload: {video_id}_{filename} 패턴
    for f in upload_dir.iterdir():
        if f.name.startswith(f"{video_id}_") and f.is_file():
            return str(f)

    return None


def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    """Range 헤더 파싱 → (start, end)"""
    range_spec = range_header.replace("bytes=", "")
    parts = range_spec.split("-")
    start = int(parts[0]) if parts[0] else 0
    end = int(parts[1]) if parts[1] else file_size - 1
    end = min(end, file_size - 1)
    return start, end


async def _file_iterator(path: str, start: int, end: int, chunk_size: int = 1024 * 1024):
    """파일을 청크 단위로 스트리밍 (1MB 기본)"""
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            remaining -= len(data)
            yield data
```

**Range Request 동작**:

| 요청 | 응답 |
|------|------|
| 헤더 없음 | 200 + 전체 파일 |
| `Range: bytes=0-1048575` | 206 + 처음 1MB |
| `Range: bytes=5242880-` | 206 + 5MB부터 끝까지 |

**청크 크기**: 1MB — 시크 응답성과 메모리 효율의 균형

### 3.2 main.py 수정

**파일**: `backend/src/main.py`

```python
# 추가
from api import stream

# 라우터 등록 (기존 videos, highlights 아래에 추가)
app.include_router(stream.router, prefix="/api", tags=["stream"])
```

**라우트 결과**: `GET /api/videos/{video_id}/stream`

## 4. Frontend 설계

### 4.1 API 클라이언트 확장

**파일**: `frontend/src/services/api.ts`

```typescript
// videoApi 객체에 추가
export const videoApi = {
  // ... 기존 메서드 유지

  /**
   * Get video stream URL for <video> src
   */
  getStreamUrl: (videoId: number): string => {
    return `${API_URL}/api/videos/${videoId}/stream`;
  },
};
```

**설계 결정**: `getStreamUrl()`은 URL 문자열만 반환 (fetch 호출 아님)
- `<video src={url}>` 에 직접 전달
- 브라우저가 Range Request를 자동으로 처리

### 4.2 HighlightTimeline 컴포넌트

**파일**: `frontend/src/components/molecules/HighlightTimeline.tsx` (신규)

```typescript
interface HighlightTimelineProps {
  highlights: Highlight[];
  duration: number;           // 영상 전체 길이 (초)
  currentTime: number;        // 현재 재생 시간
  activeHighlight: Highlight | null;
  onSeek: (time: number) => void;
  onHighlightClick: (highlight: Highlight) => void;
}

export function HighlightTimeline({
  highlights,
  duration,
  currentTime,
  activeHighlight,
  onSeek,
  onHighlightClick,
}: HighlightTimelineProps) {
  // 프로그레스바 클릭 → 시크
  const handleBarClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    onSeek(ratio * duration);
  };

  return (
    <div className="relative w-full h-8 cursor-pointer" onClick={handleBarClick}>
      {/* 배경 바 */}
      <div className="absolute inset-x-0 top-3 h-2 bg-white/20 rounded-full" />

      {/* 재생 진행 바 */}
      <div
        className="absolute top-3 left-0 h-2 bg-violet-500 rounded-full"
        style={{ width: `${(currentTime / duration) * 100}%` }}
      />

      {/* 하이라이트 마커들 */}
      {highlights.map((h) => {
        const left = (h.startTime / duration) * 100;
        const width = ((h.endTime - h.startTime) / duration) * 100;
        const isActive = activeHighlight?.id === h.id;

        return (
          <div
            key={h.id}
            className={`absolute top-2 h-4 rounded-sm cursor-pointer transition-colors ${
              isActive ? 'bg-fuchsia-500/80' : 'bg-violet-400/50 hover:bg-violet-400/70'
            }`}
            style={{ left: `${left}%`, width: `${Math.max(width, 0.5)}%` }}
            title={h.title}
            onClick={(e) => {
              e.stopPropagation();
              onHighlightClick(h);
            }}
          />
        );
      })}

      {/* 재생 헤드 (현재 위치 인디케이터) */}
      <div
        className="absolute top-1.5 w-3 h-3 bg-white rounded-full shadow -translate-x-1/2"
        style={{ left: `${(currentTime / duration) * 100}%` }}
      />
    </div>
  );
}
```

**마커 위치 계산**:
```
left = (highlight.startTime / duration) * 100  (%)
width = ((highlight.endTime - highlight.startTime) / duration) * 100  (%)
```

**스타일링**:
| 요소 | 색상 | 설명 |
|------|------|------|
| 배경 바 | `bg-white/20` | 반투명 흰색 |
| 재생 진행 | `bg-violet-500` | 보라색 (프로젝트 테마) |
| 마커 (기본) | `bg-violet-400/50` | 반투명 보라 |
| 마커 (active) | `bg-fuchsia-500/80` | 핑크 강조 |
| 재생 헤드 | `bg-white` | 흰색 원형 |

### 4.3 VideoPlayer 컴포넌트

**파일**: `frontend/src/components/organisms/VideoPlayer.tsx` (신규)

```typescript
'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { HighlightTimeline } from '@/components/molecules/HighlightTimeline';
import type { Highlight } from '@/types';

interface VideoPlayerProps {
  videoUrl: string;            // 스트리밍 URL
  highlights: Highlight[];
  activeHighlight: Highlight | null;
  onHighlightChange: (highlight: Highlight | null) => void;
  onClose: () => void;
}

export function VideoPlayer({
  videoUrl,
  highlights,
  activeHighlight,
  onHighlightChange,
  onClose,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);

  // 시간 포맷: MM:SS
  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // <video> 이벤트 핸들러
  const handleTimeUpdate = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    setCurrentTime(video.currentTime);

    // 하이라이트 종료 시 자동 일시정지 (FE-4)
    if (activeHighlight && video.currentTime >= activeHighlight.endTime) {
      video.pause();
      setIsPlaying(false);
      onHighlightChange(null);
    }
  }, [activeHighlight, onHighlightChange]);

  const handleLoadedMetadata = useCallback(() => {
    const video = videoRef.current;
    if (video) {
      setDuration(video.duration);
    }
  }, []);

  // 플레이어 제어
  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      video.play();
      setIsPlaying(true);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  };

  const toggleMute = () => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setIsMuted(video.muted);
  };

  const seekTo = useCallback((time: number) => {
    const video = videoRef.current;
    if (video) {
      video.currentTime = time;
      setCurrentTime(time);
    }
  }, []);

  // 하이라이트 클릭 → 시크 + 재생 (FE-3)
  const handleHighlightPlay = useCallback((highlight: Highlight) => {
    const video = videoRef.current;
    if (!video) return;

    video.currentTime = highlight.startTime;
    video.play();
    setIsPlaying(true);
    setCurrentTime(highlight.startTime);
    onHighlightChange(highlight);
  }, [onHighlightChange]);

  // 외부에서 activeHighlight 변경 시 시크 (HighlightCard Play 버튼)
  useEffect(() => {
    if (activeHighlight && videoRef.current) {
      videoRef.current.currentTime = activeHighlight.startTime;
      videoRef.current.play();
      setIsPlaying(true);
    }
  }, [activeHighlight]);

  return (
    <div className="bg-card/50 backdrop-blur border border-border/50 rounded-xl overflow-hidden">
      {/* 영상 영역 */}
      <div className="relative aspect-video bg-black">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          preload="metadata"
        />

        {/* 닫기 버튼 (UI-3) */}
        <Button
          size="icon"
          variant="ghost"
          className="absolute top-2 right-2 text-white/70 hover:text-white bg-black/40 rounded-full"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* 컨트롤 바 */}
      <div className="px-4 py-3 space-y-2">
        {/* 타임라인 + 하이라이트 마커 */}
        {duration > 0 && (
          <HighlightTimeline
            highlights={highlights}
            duration={duration}
            currentTime={currentTime}
            activeHighlight={activeHighlight}
            onSeek={seekTo}
            onHighlightClick={handleHighlightPlay}
          />
        )}

        {/* 버튼 + 시간 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button size="icon" variant="ghost" onClick={togglePlay}>
              {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
            </Button>
            <Button size="icon" variant="ghost" onClick={toggleMute}>
              {isMuted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
            </Button>
            <span className="text-sm text-muted-foreground">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**핵심 동작**:

| 기능 | 구현 방식 |
|------|----------|
| 재생/일시정지 | `videoRef.current.play()` / `.pause()` |
| 시크 | `videoRef.current.currentTime = time` |
| 시간 업데이트 | `onTimeUpdate` 이벤트 → `setCurrentTime()` |
| 자동 정지 | `currentTime >= activeHighlight.endTime` → `.pause()` |
| 하이라이트 시크 | `video.currentTime = highlight.startTime` + `.play()` |

**Ref 기반 제어가 필요한 이유**:
- `<video>` DOM API는 명령형 (`play()`, `pause()`, `currentTime =`)
- React의 선언형 패턴과 호환 위해 `useRef` 필수

### 4.4 page.tsx 통합

**파일**: `frontend/src/app/page.tsx`

**변경 사항**:

```typescript
// 추가 import
import { VideoPlayer } from '@/components/organisms/VideoPlayer';
import { videoApi } from '@/services/api';

// 새로운 상태
const [currentVideoId, setCurrentVideoId] = useState<number | null>(null);
const [activeHighlight, setActiveHighlight] = useState<Highlight | null>(null);
const [showPlayer, setShowPlayer] = useState(false);

// pollVideoStatus 완료 시 videoId 저장
// data.status === 'completed' 분기 내에:
setCurrentVideoId(videoId);

// handlePlay 구현 (기존 TODO 교체)
const handlePlay = (highlight: Highlight) => {
  setActiveHighlight(highlight);
  setShowPlayer(true);
};

// 플레이어 닫기
const handleClosePlayer = () => {
  setShowPlayer(false);
  setActiveHighlight(null);
};

// JSX에 VideoPlayer 추가 (HighlightGrid 위에)
{showPlayer && currentVideoId && (
  <VideoPlayer
    videoUrl={videoApi.getStreamUrl(currentVideoId)}
    highlights={highlights}
    activeHighlight={activeHighlight}
    onHighlightChange={setActiveHighlight}
    onClose={handleClosePlayer}
  />
)}
```

**상태 흐름**:
```
[VideoUploader] → upload/youtube → pollVideoStatus
    │                                    │
    │                          data.status === 'completed'
    │                                    │
    │                          setCurrentVideoId(videoId)
    │                                    │
    ▼                                    ▼
[HighlightCard Play 클릭]       [highlights 표시]
    │
    ├── setActiveHighlight(highlight)
    ├── setShowPlayer(true)
    │
    ▼
[VideoPlayer 표시]
    │
    ├── video.currentTime = highlight.startTime
    ├── video.play()
    │
    ├── onTimeUpdate → currentTime >= endTime → pause
    │
    └── onClose → setShowPlayer(false)
```

## 5. 데이터 흐름 상세

```
                    page.tsx
                      │
    ┌─────────────────┼──────────────────┐
    │                 │                  │
    ▼                 ▼                  ▼
VideoPlayer     HighlightGrid    ProcessingStatus
    │                 │
    │  Props:         │  Props:
    │  - videoUrl     │  - highlights[]
    │  - highlights[] │  - onPlay(h)
    │  - active       │  - onExport(h)
    │  - onChange(h)  │
    │  - onClose()    │
    │                 │
    │      ┌──────────┘
    │      │
    │   onPlay(highlight)
    │      │
    │      ▼
    │   page.tsx: setActiveHighlight(h), setShowPlayer(true)
    │      │
    │      ▼ (activeHighlight prop 변경)
    │
    └──── useEffect → video.currentTime = h.startTime → play()
```

## 6. page.tsx 상태 관리

| 상태 | 타입 | 용도 |
|------|------|------|
| `currentVideoId` | `number \| null` | 현재 분석 완료된 영상 ID |
| `activeHighlight` | `Highlight \| null` | 현재 재생 중인 하이라이트 |
| `showPlayer` | `boolean` | 플레이어 표시 여부 |
| `status` | `ProcessingStatus` | 기존 — 처리 상태 |
| `highlights` | `Highlight[]` | 기존 — 하이라이트 목록 |
| `exportingHighlightId` | `number \| null` | 기존 — 내보내기 중 ID |

## 7. 변경 없는 파일 (확인)

| 파일 | 이유 |
|------|------|
| `backend/src/api/videos.py` | 영상 CRUD 변경 없음 |
| `backend/src/api/highlights.py` | Export 변경 없음 |
| `backend/src/services/video_processor.py` | AI 파이프라인 변경 없음 |
| `backend/src/services/export_processor.py` | FFmpeg 클리핑 변경 없음 |
| `backend/src/infrastructure/*` | DB 모델/Repository 변경 없음 |
| `frontend/src/components/molecules/HighlightCard.tsx` | onPlay 인터페이스 유지 |
| `frontend/src/components/organisms/HighlightGrid.tsx` | 변경 없음 |
| `frontend/src/types/index.ts` | 타입 변경 불필요 |
| `frontend/src/store/videoStore.ts` | 기존 store 유지 |

## 8. 검증 항목

| ID | 검증 항목 | 방법 |
|----|----------|------|
| V-1 | `GET /api/videos/{id}/stream` 엔드포인트가 206 Partial Content를 반환하는지 | `curl -H "Range: bytes=0-1024" http://localhost:8000/api/videos/4/stream -I` |
| V-2 | 존재하지 않는 video_id에 404를 반환하는지 | `curl http://localhost:8000/api/videos/9999/stream` |
| V-3 | VideoPlayer에서 영상이 로드되고 재생되는지 | 브라우저에서 Play 버튼 클릭 |
| V-4 | HighlightCard Play 클릭 시 해당 구간으로 시크 + 재생 시작되는지 | 하이라이트 카드 Play 클릭 |
| V-5 | 하이라이트 종료 시간에 자동 일시정지되는지 | 재생 중 endTime 도달 관찰 |
| V-6 | HighlightTimeline 마커가 올바른 위치에 표시되는지 | 마커 위치와 실제 시간 비교 |
| V-7 | 타임라인 마커 클릭 시 해당 구간으로 점프하는지 | 마커 클릭 후 currentTime 확인 |
| V-8 | 프로그레스바 클릭으로 임의 위치 시크 가능한지 | 프로그레스바 중간 클릭 |
| V-9 | 현재 시간이 MM:SS 형식으로 실시간 업데이트되는지 | 재생 중 시간 표시 확인 |
| V-10 | 플레이어 닫기 버튼이 동작하는지 | X 버튼 클릭 후 플레이어 사라짐 |
| V-11 | 기존 Export/Download 기능이 정상 동작하는지 | 하이라이트 다운로드 버튼 클릭 |
| V-12 | 현재 재생 중인 하이라이트 마커가 강조 표시되는지 | active 마커 색상 확인 |
