'use client';

import { MainLayout } from '@/components/templates/MainLayout';
import { VideoUploader } from '@/components/molecules/VideoUploader';
import { ProcessingStatus } from '@/components/molecules/ProcessingStatus';
import { HighlightGrid } from '@/components/organisms/HighlightGrid';
import { useVideoStore } from '@/store/video-store';
import type { Highlight } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const { status, highlights, setStatus, setHighlights, reset } = useVideoStore();

  const isProcessing = status.status === 'uploading' || status.status === 'processing';

  const pollVideoStatus = async (videoId: string) => {
    const maxAttempts = 60;
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
        const response = await fetch(`${API_URL}/api/videos/${videoId}`);
        if (!response.ok) throw new Error('Failed to fetch video status');

        const data = await response.json();

        setStatus({
          status: data.status,
          progress: data.progress,
          message: data.message,
        });

        if (data.status === 'completed') {
          setHighlights(data.highlights.map((h: any) => ({
            id: h.id,
            startTime: h.start_time,
            endTime: h.end_time,
            title: h.title,
            description: h.description,
            score: h.score,
            thumbnailUrl: h.thumbnail_url,
          })));
        } else if (data.status === 'error') {
          return;
        } else {
          attempts++;
          setTimeout(poll, 2000);
        }
      } catch (error) {
        setStatus({
          status: 'error',
          progress: 0,
          message: error instanceof Error ? error.message : 'Unknown error',
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
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_URL}/api/videos/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      pollVideoStatus(data.id);
    } catch (error) {
      setStatus({
        status: 'error',
        progress: 0,
        message: error instanceof Error ? error.message : 'Upload failed',
      });
    }
  };

  const handleUrlSubmit = async (url: string) => {
    console.log('URL submitted:', url);

    reset();
    setStatus({ status: 'uploading', progress: 0, message: 'Processing YouTube URL...' });

    try {
      const response = await fetch(`${API_URL}/api/videos/youtube`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error('YouTube processing failed');
      }

      const data = await response.json();
      pollVideoStatus(data.id);
    } catch (error) {
      setStatus({
        status: 'error',
        progress: 0,
        message: error instanceof Error ? error.message : 'YouTube processing failed',
      });
    }
  };

  const handlePlay = (highlight: Highlight) => {
    console.log('Play highlight:', highlight.title, `${highlight.startTime}s - ${highlight.endTime}s`);
    // TODO: 영상 플레이어 연동
  };

  const handleExport = async (highlight: Highlight) => {
    console.log('Export highlight:', highlight.title);

    try {
      const response = await fetch(`${API_URL}/api/highlights/${highlight.id}/export`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const data = await response.json();
      console.log('Export started:', data);
      alert(`Export started! Job ID: ${data.export_id}`);
    } catch (error) {
      console.error('Export error:', error);
      alert('Export failed');
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

        {/* Highlights Grid */}
        <HighlightGrid
          highlights={highlights}
          onPlay={handlePlay}
          onExport={handleExport}
        />
      </div>
    </MainLayout>
  );
}
