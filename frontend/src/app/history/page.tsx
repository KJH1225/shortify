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
