# Design: video-history

> Feature: 영상 히스토리 & 관리 — 과거 분석된 영상 목록 조회, 재열기, 삭제
> Plan: `docs/01-plan/features/video-history.plan.md`
> Created: 2026-02-09

## 1. 구현 순서

```
1. [FE] components/molecules/VideoHistoryCard.tsx  - (신규) 영상 히스토리 카드
2. [FE] app/history/page.tsx                       - (신규) 히스토리 페이지
3. [FE] components/organisms/Header.tsx            - 히스토리 Link 연동
4. [FE] app/page.tsx                               - ?videoId 쿼리 파라미터 지원
```

## 2. 아키텍처 개요

```
Header (organism)
    │
    ├── [히스토리] Link → /history
    │
    ▼
/history (page)
    │
    ├── useEffect → videoApi.getAll()
    ├── VideoHistoryCard 그리드
    │     ├── 제목, 소스, 상태 배지, 하이라이트 수
    │     ├── [열기] → router.push(/?videoId={id})
    │     └── [삭제] → confirm → videoApi.delete()
    │
    ▼
/ (page) ← ?videoId=N
    │
    ├── useSearchParams → videoId 추출
    ├── videoApi.getById(videoId)
    ├── setCurrentVideoId, setHighlights, setStatus
    │
    ▼
기존 HighlightGrid + VideoPlayer 동작
```

**설계 원칙**:
- 백엔드 변경 **없음** — 기존 API 100% 재사용
- 프론트엔드만 4개 파일 변경
- Next.js App Router의 디렉토리 기반 라우팅 활용
- URL 쿼리 파라미터로 상태 복원 (새로고침해도 유지)

## 3. Backend 설계

**변경 없음** — 기존 API로 충분:

| 엔드포인트 | 위치 | 용도 |
|-----------|------|------|
| `GET /api/videos/` | videos.py:150 | 전체 영상 목록 (created_at DESC, highlights 포함) |
| `GET /api/videos/{id}` | videos.py:131 | 영상 상세 + 하이라이트 |
| `DELETE /api/videos/{id}` | videos.py:158 | 영상 삭제 (cascade highlights) |

## 4. Frontend 설계

### 4.1 VideoHistoryCard 컴포넌트

**파일**: `frontend/src/components/molecules/VideoHistoryCard.tsx` (신규)

```typescript
'use client';

import { Clock, Film, Youtube, Trash2, Play, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { VideoResponse } from '@/services/api';

interface VideoHistoryCardProps {
  video: VideoResponse;
  onOpen: (videoId: number) => void;
  onDelete: (videoId: number) => void;
}

export function VideoHistoryCard({ video, onOpen, onDelete }: VideoHistoryCardProps) {
  const statusConfig: Record<string, { label: string; className: string }> = {
    completed: { label: '완료', className: 'bg-green-500/20 text-green-400' },
    processing: { label: '처리중', className: 'bg-yellow-500/20 text-yellow-400' },
    uploading: { label: '업로드중', className: 'bg-blue-500/20 text-blue-400' },
    error: { label: '오류', className: 'bg-red-500/20 text-red-400' },
    idle: { label: '대기', className: 'bg-gray-500/20 text-gray-400' },
  };

  const statusInfo = statusConfig[video.status] || statusConfig.idle;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '--:--';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`"${video.title}" 영상을 삭제하시겠습니까?`)) {
      onDelete(video.id);
    }
  };

  return (
    <div
      className="group bg-card/50 border border-border/50 rounded-xl p-4 hover:border-violet-500/50 transition-colors cursor-pointer"
      onClick={() => video.status === 'completed' && onOpen(video.id)}
    >
      {/* 상단: 소스 아이콘 + 상태 배지 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-muted-foreground">
          {video.source.type === 'youtube' ? (
            <Youtube className="h-4 w-4 text-red-400" />
          ) : (
            <Film className="h-4 w-4" />
          )}
          <span className="text-xs">
            {video.source.type === 'youtube' ? 'YouTube' : '파일 업로드'}
          </span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full ${statusInfo.className}`}>
          {statusInfo.label}
        </span>
      </div>

      {/* 제목 */}
      <h3 className="font-medium text-sm line-clamp-2 mb-3">{video.title}</h3>

      {/* 메타 정보 */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatDuration(video.duration)}
        </span>
        <span className="flex items-center gap-1">
          <Play className="h-3 w-3" />
          하이라이트 {video.highlights.length}개
        </span>
      </div>

      {/* 하단: 생성일시 + 액션 */}
      <div className="flex items-center justify-between pt-3 border-t border-border/30">
        <span className="text-xs text-muted-foreground">
          {formatDate(video.created_at)}
        </span>
        <div className="flex items-center gap-1">
          {video.status === 'completed' && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                onOpen(video.id);
              }}
            >
              열기
            </Button>
          )}
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7 text-muted-foreground hover:text-red-400"
            onClick={handleDelete}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
```

**표시 항목**:

| 요소 | 내용 |
|------|------|
| 소스 아이콘 | YouTube → 빨간 Youtube 아이콘, 파일 → Film 아이콘 |
| 상태 배지 | completed: 녹색, processing: 노란색, error: 빨간색 |
| 제목 | 2줄 제한 (line-clamp-2) |
| duration | MM:SS 형식 |
| 하이라이트 수 | `highlights.length` |
| 생성일시 | 한국어 날짜 형식 |
| 열기 버튼 | completed 상태만 표시 |
| 삭제 버튼 | confirm 다이얼로그 후 삭제 |

### 4.2 히스토리 페이지

**파일**: `frontend/src/app/history/page.tsx` (신규)

```typescript
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { VideoHistoryCard } from '@/components/molecules/VideoHistoryCard';
import { videoApi, VideoResponse } from '@/services/api';

export default function HistoryPage() {
  const router = useRouter();
  const [videos, setVideos] = useState<VideoResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadVideos();
  }, []);

  const loadVideos = async () => {
    try {
      const data = await videoApi.getAll();
      setVideos(data);
    } catch {
      // 조용히 실패 — 빈 목록 표시
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpen = (videoId: number) => {
    router.push(`/?videoId=${videoId}`);
  };

  const handleDelete = async (videoId: number) => {
    try {
      await videoApi.delete(videoId);
      setVideos((prev) => prev.filter((v) => v.id !== videoId));
    } catch {
      alert('삭제에 실패했습니다');
    }
  };

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">영상 히스토리</h1>
            <p className="text-muted-foreground mt-1">
              이전에 분석한 영상들을 다시 확인할 수 있어요
            </p>
          </div>
          <span className="text-sm text-muted-foreground">
            총 {videos.length}개
          </span>
        </div>

        {/* 로딩 */}
        {isLoading && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">불러오는 중...</p>
          </div>
        )}

        {/* 빈 상태 */}
        {!isLoading && videos.length === 0 && (
          <div className="text-center py-16 space-y-4">
            <p className="text-muted-foreground text-lg">
              아직 분석한 영상이 없어요
            </p>
            <p className="text-muted-foreground text-sm">
              메인 페이지에서 영상을 업로드하면 여기에 표시됩니다
            </p>
          </div>
        )}

        {/* 영상 그리드 */}
        {!isLoading && videos.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {videos.map((video) => (
              <VideoHistoryCard
                key={video.id}
                video={video}
                onOpen={handleOpen}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
```

**페이지 구조**:

| 상태 | 표시 |
|------|------|
| isLoading=true | "불러오는 중..." |
| videos.length === 0 | "아직 분석한 영상이 없어요" |
| videos.length > 0 | VideoHistoryCard 그리드 (3열) |

### 4.3 Header.tsx 수정

**파일**: `frontend/src/components/organisms/Header.tsx`

**변경 사항**:

```typescript
// 추가 import
import Link from 'next/link';
import { History } from 'lucide-react';

// 히스토리 버튼 변경 (기존 Button → Link + Button asChild)
<Button variant="ghost" size="sm" asChild>
  <Link href="/history">
    <History className="h-4 w-4 mr-1" />
    히스토리
  </Link>
</Button>
```

**변경 범위**: import 추가 + 기존 `<Button>히스토리</Button>`를 Link 래핑으로 교체

### 4.4 page.tsx 수정

**파일**: `frontend/src/app/page.tsx`

**변경 사항**:

```typescript
// 추가 import
import { useSearchParams } from 'next/navigation';
import { useEffect } from 'react';
import { Suspense } from 'react';

// Home 컴포넌트 내부에 추가:
const searchParams = useSearchParams();

// useEffect: URL의 videoId로 영상 로드
useEffect(() => {
  const videoIdParam = searchParams.get('videoId');
  if (videoIdParam) {
    const videoId = parseInt(videoIdParam, 10);
    if (!isNaN(videoId)) {
      loadVideoFromHistory(videoId);
    }
  }
}, [searchParams]);

// 새로운 함수 추가:
const loadVideoFromHistory = async (videoId: number) => {
  try {
    const data = await videoApi.getById(videoId);
    if (data.status === 'completed') {
      setCurrentVideoId(videoId);
      setStatus({
        status: data.status,
        progress: data.progress,
        message: data.message,
      });
      setHighlights(data.highlights.map((h) => ({
        id: h.id,
        startTime: h.start_time,
        endTime: h.end_time,
        title: h.title,
        description: h.description || '',
        score: h.score,
        thumbnailUrl: h.thumbnail_url || undefined,
      })));
    }
  } catch {
    // 영상 없음 — 무시
  }
};

// default export를 Suspense로 감싸기 (useSearchParams 필수)
function HomeContent() {
  // 기존 Home 컴포넌트 내용 전체
}

export default function Home() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  );
}
```

**핵심 변경점**:
1. `useSearchParams()`로 `?videoId=N` 추출
2. `loadVideoFromHistory()` — API 호출 → 상태 세팅
3. `Suspense` 래핑 — Next.js App Router에서 `useSearchParams` 사용 시 필수
4. 기존 `Home` → `HomeContent`로 이름 변경, `Home`은 Suspense 래퍼

## 5. 상태 흐름 상세

```
[/history 페이지]
    │
    ├── videoApi.getAll() → VideoResponse[]
    │
    ├── VideoHistoryCard 클릭 (completed 영상)
    │     └── router.push('/?videoId=6')
    │
    ▼
[/ 페이지 로드]
    │
    ├── useSearchParams → videoId = '6'
    ├── loadVideoFromHistory(6)
    │     ├── videoApi.getById(6)
    │     ├── setCurrentVideoId(6)
    │     ├── setStatus({ status: 'completed', ... })
    │     └── setHighlights([...])
    │
    ▼
[HighlightGrid 표시 + Play 클릭 → VideoPlayer]
```

## 6. 변경 없는 파일 (확인)

| 파일 | 이유 |
|------|------|
| `backend/src/api/videos.py` | API 이미 완성 |
| `backend/src/infrastructure/repository.py` | list_all, delete 이미 존재 |
| `frontend/src/services/api.ts` | getAll, delete 이미 존재 |
| `frontend/src/store/videoStore.ts` | 기존 store 유지 |
| `frontend/src/components/organisms/VideoPlayer.tsx` | 변경 없음 |
| `frontend/src/components/organisms/HighlightGrid.tsx` | 변경 없음 |
| `frontend/src/components/molecules/HighlightCard.tsx` | 변경 없음 |
| `frontend/src/types/index.ts` | 타입 변경 불필요 |

## 7. 검증 항목

| ID | 검증 항목 | 방법 |
|----|----------|------|
| V-1 | Header 히스토리 버튼 클릭 시 /history로 이동하는지 | 브라우저에서 버튼 클릭 |
| V-2 | /history 페이지에 과거 영상 목록이 표시되는지 | 영상 업로드 후 /history 접근 |
| V-3 | 영상 카드에 제목, 소스 타입, 상태 배지, 하이라이트 수가 표시되는지 | 카드 내용 확인 |
| V-4 | completed 영상 카드 클릭 시 메인 페이지로 이동 + 하이라이트 로드되는지 | 카드 클릭 후 메인 페이지 확인 |
| V-5 | 메인 페이지에서 VideoPlayer Play 버튼이 정상 동작하는지 | 히스토리에서 열기 후 Play 클릭 |
| V-6 | 삭제 버튼 클릭 시 확인 다이얼로그 표시되는지 | 삭제 아이콘 클릭 |
| V-7 | 삭제 확인 후 목록에서 즉시 제거되는지 | 확인 클릭 후 목록 상태 |
| V-8 | 영상이 없을 때 빈 상태 메시지가 표시되는지 | 모든 영상 삭제 후 확인 |
| V-9 | 기존 업로드/YouTube 처리 기능이 정상 동작하는지 | 메인 페이지에서 새 영상 업로드 |
| V-10 | URL에 ?videoId 포함 시 새로고침해도 하이라이트가 유지되는지 | /?videoId=6에서 F5 |
