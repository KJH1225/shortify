'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { VideoUploader } from '@/components/molecules/VideoUploader';
import { ProcessingStatus } from '@/components/molecules/ProcessingStatus';
import { HighlightGrid } from '@/components/organisms/HighlightGrid';
import { VideoPlayer } from '@/components/organisms/VideoPlayer';
import { useVideoStore } from '@/store/videoStore';
import { videoApi, highlightApi, ApiRequestError } from '@/services/api';
import type { Highlight } from '@/types';

function HomeContent() {
  const searchParams = useSearchParams();
  const { status, highlights, setStatus, setHighlights, reset } = useVideoStore();
  const [exportingHighlightId, setExportingHighlightId] = useState<number | null>(null);
  const [currentVideoId, setCurrentVideoId] = useState<number | null>(null);
  const [activeHighlight, setActiveHighlight] = useState<Highlight | null>(null);
  const [showPlayer, setShowPlayer] = useState(false);

  const isProcessing = status.status === 'uploading' || status.status === 'processing';

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
          clips: h.clips || undefined,
        })));
      }
    } catch {
      // 영상 없음 — 무시
    }
  };

  useEffect(() => {
    const videoIdParam = searchParams.get('videoId');
    if (videoIdParam) {
      const videoId = parseInt(videoIdParam, 10);
      if (!isNaN(videoId)) {
        loadVideoFromHistory(videoId);
      }
    }
  }, [searchParams]);

  const pollVideoStatus = async (videoId: number) => {
    const maxAttempts = 180;
    let attempts = 0;

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setStatus({
          status: 'error',
          progress: 0,
          message: 'Processing timeout',
        });
        return;
      }

      try {
        const data = await videoApi.getById(videoId);

        setStatus({
          status: data.status,
          progress: data.progress,
          message: data.message,
        });

        if (data.status === 'completed') {
          setCurrentVideoId(videoId);
          setHighlights(data.highlights.map((h) => ({
            id: h.id,
            startTime: h.start_time,
            endTime: h.end_time,
            title: h.title,
            description: h.description || '',
            score: h.score,
            thumbnailUrl: h.thumbnail_url || undefined,
          })));
        } else if (data.status === 'error') {
          return;
        } else {
          attempts++;
          setTimeout(poll, 2000);
        }
      } catch (error) {
        const message = error instanceof ApiRequestError
          ? error.message
          : error instanceof Error
            ? error.message
            : 'Unknown error';
        setStatus({
          status: 'error',
          progress: 0,
          message,
        });
      }
    };

    poll();
  };

  const handleFileSelect = async (file: File) => {
    console.log('File selected:', file.name, file.size, file.type);

    reset();
    setStatus({ status: 'uploading', progress: 0, message: 'Uploading video...' });

    try {
      const data = await videoApi.upload(file);
      pollVideoStatus(data.id);
    } catch (error) {
      const message = error instanceof ApiRequestError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'Upload failed';
      setStatus({
        status: 'error',
        progress: 0,
        message,
      });
    }
  };

  const handleUrlSubmit = async (url: string) => {
    console.log('URL submitted:', url);

    reset();
    setStatus({ status: 'uploading', progress: 0, message: 'Processing YouTube URL...' });

    try {
      const data = await videoApi.processYouTube(url);
      pollVideoStatus(data.id);
    } catch (error) {
      const message = error instanceof ApiRequestError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'YouTube processing failed';
      setStatus({
        status: 'error',
        progress: 0,
        message,
      });
    }
  };

  const handlePlay = (highlight: Highlight) => {
    setActiveHighlight(highlight);
    setShowPlayer(true);
  };

  const handleClosePlayer = () => {
    setShowPlayer(false);
    setActiveHighlight(null);
  };

  const handleExport = async (highlight: Highlight, layout: 'original' | 'shortform' = 'original') => {
    if (exportingHighlightId) return;
    setExportingHighlightId(highlight.id);

    try {
      const response = await highlightApi.export(highlight.id, layout);
      const exportId = response.data.export_id;

      // Poll export status
      let attempts = 0;
      const maxAttempts = 60;

      const poll = async () => {
        if (attempts >= maxAttempts) {
          setExportingHighlightId(null);
          alert('Export timeout');
          return;
        }

        try {
          const statusRes = await highlightApi.getExportStatus(highlight.id, exportId);
          const exportStatus = statusRes.data.status;

          if (exportStatus === 'completed') {
            highlightApi.downloadExport(highlight.id, exportId);
            setExportingHighlightId(null);
          } else if (exportStatus === 'error') {
            setExportingHighlightId(null);
            alert(statusRes.data.error_message || 'Export failed');
          } else {
            attempts++;
            setTimeout(poll, 3000);
          }
        } catch {
          setExportingHighlightId(null);
          alert('Export status check failed');
        }
      };

      poll();
    } catch (error) {
      setExportingHighlightId(null);
      const message = error instanceof ApiRequestError ? error.message : 'Export failed';
      alert(message);
    }
  };

  return (
    <MainLayout>
      <div className="space-y-12">
        {/* Hero Section */}
        <section className="text-center space-y-4 py-8">
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-violet-400 via-fuchsia-400 to-pink-400 bg-clip-text text-transparent">
            영상의 하이라이트를
            <br />
            AI가 자동으로 추출해요
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            긴 영상에서 가장 흥미로운 순간들을 AI가 찾아내고,
            <br />
            숏폼 콘텐츠로 바로 변환할 수 있어요
          </p>
        </section>

        {/* Uploader */}
        <VideoUploader
          onFileSelect={handleFileSelect}
          onUrlSubmit={handleUrlSubmit}
          isProcessing={isProcessing}
        />

        {/* Processing Status */}
        {status.status !== 'idle' && (
          <ProcessingStatus status={status} />
        )}

        {/* Video Player */}
        {showPlayer && currentVideoId && (
          <VideoPlayer
            videoUrl={videoApi.getStreamUrl(currentVideoId)}
            highlights={highlights}
            activeHighlight={activeHighlight}
            onHighlightChange={setActiveHighlight}
            onClose={handleClosePlayer}
          />
        )}

        {/* Highlights Grid */}
        <HighlightGrid
          highlights={highlights}
          onPlay={handlePlay}
          onExport={handleExport}
          exportingHighlightId={exportingHighlightId}
        />
      </div>
    </MainLayout>
  );
}

export default function Home() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  );
}
