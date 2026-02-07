'use client';

import { MainLayout } from '@/components/templates/MainLayout';
import { VideoUploader } from '@/components/molecules/VideoUploader';
import { ProcessingStatus } from '@/components/molecules/ProcessingStatus';
import { HighlightGrid } from '@/components/organisms/HighlightGrid';
import { useVideoStore } from '@/store/video-store';
import type { Highlight } from '@/types';

export default function Home() {
  const { status, highlights, simulateProcessing } = useVideoStore();

  const isProcessing = status.status === 'uploading' || status.status === 'processing';

  const handleFileSelect = (file: File) => {
    console.log('File selected:', file.name, file.size, file.type);
    // TODO: 실제 API 연동 시 아래 코드로 교체
    // const formData = new FormData();
    // formData.append('file', file);
    // fetch('/api/videos/upload', { method: 'POST', body: formData });
    simulateProcessing();
  };

  const handleUrlSubmit = (url: string) => {
    console.log('URL submitted:', url);
    // TODO: 실제 API 연동 시 아래 코드로 교체
    // fetch('/api/videos/youtube', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ url })
    // });
    simulateProcessing();
  };

  const handlePlay = (highlight: Highlight) => {
    console.log('Play highlight:', highlight.title, `${highlight.startTime}s - ${highlight.endTime}s`);
    // TODO: 영상 플레이어 연동
  };

  const handleExport = (highlight: Highlight) => {
    console.log('Export highlight:', highlight.title);
    // TODO: 숏폼 내보내기 API 연동
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
