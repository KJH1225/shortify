'use client';

import Image from 'next/image';
import { Play, Download, Clock, Star, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import type { Highlight } from '@/types';

// 허용된 이미지 도메인 검증
const ALLOWED_IMAGE_DOMAINS = ['localhost', 'i.ytimg.com', 'img.youtube.com'];

function isValidImageUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ALLOWED_IMAGE_DOMAINS.some(domain => parsed.hostname.includes(domain));
  } catch {
    return false;
  }
}

interface HighlightCardProps {
  highlight: Highlight;
  onPlay: (highlight: Highlight) => void;
  onExport: (highlight: Highlight, layout: 'original' | 'shortform') => void;
  isExporting?: boolean;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function HighlightCard({ highlight, onPlay, onExport, isExporting = false }: HighlightCardProps) {
  const duration = highlight.endTime - highlight.startTime;

  return (
    <Card className="group overflow-hidden border-border/50 bg-card/50 backdrop-blur hover:border-violet-500/50 transition-all">
      <CardContent className="p-0">
        <div className="relative aspect-video bg-muted">
          {highlight.thumbnailUrl && isValidImageUrl(highlight.thumbnailUrl) ? (
            <Image
              src={highlight.thumbnailUrl}
              alt={highlight.title}
              fill
              className="object-cover"
              unoptimized={highlight.thumbnailUrl.startsWith('http')}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20">
              <Play className="h-12 w-12 text-muted-foreground" />
            </div>
          )}
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <Button
              size="icon"
              variant="secondary"
              className="rounded-full"
              onClick={() => onPlay(highlight)}
            >
              <Play className="h-5 w-5" />
            </Button>
          </div>
          <div className="absolute bottom-2 right-2 px-2 py-1 rounded bg-black/70 text-xs text-white">
            {formatTime(duration)}
          </div>
        </div>

        <div className="p-4 space-y-2">
          <h3 className="font-semibold line-clamp-1">{highlight.title}</h3>
          <p className="text-sm text-muted-foreground line-clamp-2">
            {highlight.description}
          </p>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{formatTime(highlight.startTime)} - {formatTime(highlight.endTime)}</span>
            </div>
            <div className="flex items-center gap-1">
              <Star className="h-3 w-3 text-yellow-500" />
              <span>{Math.round(highlight.score * 100)}%</span>
            </div>
          </div>
          {highlight.clips && highlight.clips.length > 1 && (
            <div className="text-xs text-violet-400">
              {highlight.clips.length}개 클립 편집 ({formatTime(highlight.clips.reduce((sum, c) => sum + c.end - c.start, 0))})
            </div>
          )}
          <div className="flex gap-2 pt-2">
            <Button
              size="sm"
              variant="outline"
              className="flex-1 text-xs"
              onClick={() => onExport(highlight, 'original')}
              disabled={isExporting}
            >
              {isExporting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Download className="h-3 w-3 mr-1" />}
              원본
            </Button>
            <Button
              size="sm"
              className="flex-1 text-xs bg-violet-600 hover:bg-violet-700"
              onClick={() => onExport(highlight, 'shortform')}
              disabled={isExporting}
            >
              {isExporting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Download className="h-3 w-3 mr-1" />}
              숏폼 9:16
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
