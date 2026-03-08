'use client';

import { HighlightCard } from '@/components/molecules/HighlightCard';
import type { Highlight } from '@/types';

interface HighlightGridProps {
  highlights: Highlight[];
  onPlay: (highlight: Highlight) => void;
  onExport: (highlight: Highlight, layout: 'original' | 'shortform') => void;
  exportingHighlightId?: number | null;
}

export function HighlightGrid({ highlights, onPlay, onExport, exportingHighlightId }: HighlightGridProps) {
  if (highlights.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">
          {/* 영상을 업로드하면 AI가 하이라이트 구간을 자동으로 추출해요 */}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">
          추출된 하이라이트
          <span className="ml-2 text-lg text-muted-foreground font-normal">
            ({highlights.length}개)
          </span>
        </h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {highlights.map((highlight) => (
          <HighlightCard
            key={highlight.id}
            highlight={highlight}
            onPlay={onPlay}
            onExport={onExport}
            isExporting={exportingHighlightId === highlight.id}
          />
        ))}
      </div>
    </div>
  );
}
