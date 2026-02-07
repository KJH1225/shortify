'use client';

import { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { VideoUploader } from '@/components/molecules/VideoUploader';
import { ProcessingStatus } from '@/components/molecules/ProcessingStatus';
import { HighlightGrid } from '@/components/organisms/HighlightGrid';
import type { Highlight, ProcessingStatus as ProcessingStatusType } from '@/types';
import mockData from '../../mocks/highlights.json';

export default function Home() {
  const [status, setStatus] = useState<ProcessingStatusType>({
    status: 'idle',
    progress: 0,
    message: '',
  });
  const [highlights, setHighlights] = useState<Highlight[]>([]);

  const simulateProcessing = async () => {
    // 업로드 단계
    setStatus({ status: 'uploading', progress: 0, message: '영상 업로드 중...' });

    for (let i = 0; i <= 30; i += 10) {
      await new Promise(r => setTimeout(r, 200));
      setStatus({ status: 'uploading', progress: i, message: '영상 업로드 중...' });
    }

    // 분석 단계
    setStatus({ status: 'processing', progress: 30, message: 'AI가 영상을 분석하고 있어요...' });

    const messages = [
      '오디오 트랙 추출 중...',
      '음성을 텍스트로 변환 중...',
      '감정 분석 진행 중...',
      '하이라이트 구간 탐지 중...',
      '최적의 클립 선택 중...',
    ];

    for (let i = 30; i <= 90; i += 15) {
      await new Promise(r => setTimeout(r, 800));
      const msgIndex = Math.floor((i - 30) / 15);
      setStatus({
        status: 'processing',
        progress: i,
        message: messages[msgIndex] || messages[messages.length - 1]
      });
    }

    // 완료
    setStatus({ status: 'completed', progress: 100, message: '분석이 완료되었습니다!' });
    setHighlights(mockData.highlights as Highlight[]);
  };

  const handleFileSelect = (file: File) => {
    console.log('File selected:', file.name);
    simulateProcessing();
  };

  const handleUrlSubmit = (url: string) => {
    console.log('URL submitted:', url);
    simulateProcessing();
  };

  const handlePlay = (highlight: Highlight) => {
    console.log('Play highlight:', highlight.title);
  };

  const handleExport = (highlight: Highlight) => {
    console.log('Export highlight:', highlight.title);
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
          isProcessing={status.status === 'uploading' || status.status === 'processing'}
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
