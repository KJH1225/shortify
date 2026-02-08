'use client';

import type { Highlight } from '@/types';

interface HighlightTimelineProps {
  highlights: Highlight[];
  duration: number;
  currentTime: number;
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

      {/* 재생 헤드 */}
      <div
        className="absolute top-1.5 w-3 h-3 bg-white rounded-full shadow -translate-x-1/2"
        style={{ left: `${(currentTime / duration) * 100}%` }}
      />
    </div>
  );
}
