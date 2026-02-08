'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { HighlightTimeline } from '@/components/molecules/HighlightTimeline';
import type { Highlight } from '@/types';

interface VideoPlayerProps {
  videoUrl: string;
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

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const handleTimeUpdate = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    setCurrentTime(video.currentTime);

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

  const handleHighlightPlay = useCallback((highlight: Highlight) => {
    const video = videoRef.current;
    if (!video) return;

    video.currentTime = highlight.startTime;
    video.play();
    setIsPlaying(true);
    setCurrentTime(highlight.startTime);
    onHighlightChange(highlight);
  }, [onHighlightChange]);

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

        {/* 닫기 버튼 */}
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
