'use client';

import { Clock, Film, Youtube, Trash2, Play } from 'lucide-react';
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
