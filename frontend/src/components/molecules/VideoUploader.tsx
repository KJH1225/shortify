'use client';

import { useState, useCallback } from 'react';
import { Upload, Link, FileVideo, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// 파일 검증 설정
const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'];
const ALLOWED_MIME_TYPES = [
  'video/mp4', 'video/quicktime', 'video/x-msvideo',
  'video/x-matroska', 'video/webm', 'video/x-m4v'
];
const MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024; // 2GB

// YouTube URL 검증
const YOUTUBE_URL_REGEX = /^https?:\/\/(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/|live\/)|youtu\.be\/)[a-zA-Z0-9_-]{11}/;

function validateFile(file: File): { valid: boolean; error?: string } {
  // 확장자 검증
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return { valid: false, error: `지원하지 않는 파일 형식입니다. (${ALLOWED_EXTENSIONS.join(', ')})` };
  }

  // MIME 타입 검증
  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    return { valid: false, error: '유효한 영상 파일이 아닙니다.' };
  }

  // 파일 크기 검증
  if (file.size > MAX_FILE_SIZE) {
    return { valid: false, error: '파일 크기가 2GB를 초과합니다.' };
  }

  return { valid: true };
}

function validateYouTubeUrl(url: string): boolean {
  return YOUTUBE_URL_REGEX.test(url);
}

interface VideoUploaderProps {
  onFileSelect: (file: File) => void;
  onUrlSubmit: (url: string) => void;
  isProcessing: boolean;
}

export function VideoUploader({ onFileSelect, onUrlSubmit, isProcessing }: VideoUploaderProps) {
  const [url, setUrl] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    setError(null);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const validation = validateFile(file);
      if (validation.valid) {
        onFileSelect(file);
      } else {
        setError(validation.error || '파일 검증에 실패했습니다.');
      }
    }
  }, [onFileSelect]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const validation = validateFile(file);
      if (validation.valid) {
        onFileSelect(file);
      } else {
        setError(validation.error || '파일 검증에 실패했습니다.');
      }
    }
  };

  const handleUrlSubmit = () => {
    setError(null);
    const trimmedUrl = url.trim();
    if (!trimmedUrl) return;

    if (!validateYouTubeUrl(trimmedUrl)) {
      setError('유효한 YouTube URL이 아닙니다.');
      return;
    }

    onUrlSubmit(trimmedUrl);
    setUrl('');
  };

  return (
    <Card className="w-full max-w-2xl mx-auto border-border/50 bg-card/50 backdrop-blur">
      <CardContent className="p-6">
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <Tabs defaultValue="upload" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="upload" className="gap-2">
              <Upload className="h-4 w-4" />
              파일 업로드
            </TabsTrigger>
            <TabsTrigger value="url" className="gap-2">
              <Link className="h-4 w-4" />
              YouTube URL
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload">
            <div
              className={`
                relative border-2 border-dashed rounded-xl p-12 text-center transition-all
                ${dragActive
                  ? 'border-violet-500 bg-violet-500/10'
                  : 'border-border hover:border-violet-500/50 hover:bg-muted/50'
                }
              `}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={isProcessing}
              />
              <FileVideo className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-lg font-medium mb-2">
                영상 파일을 드래그하거나 클릭하세요
              </p>
              <p className="text-sm text-muted-foreground">
                MP4, MOV, AVI, MKV 지원 (최대 2GB)
              </p>
            </div>
          </TabsContent>

          <TabsContent value="url">
            <div className="space-y-4">
              <div className="flex gap-3">
                <Input
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={isProcessing}
                  className="flex-1"
                />
                <Button
                  onClick={handleUrlSubmit}
                  disabled={!url.trim() || isProcessing}
                  className="bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:from-violet-600 hover:to-fuchsia-600"
                >
                  분석 시작
                </Button>
              </div>
              <p className="text-sm text-muted-foreground text-center">
                YouTube, Vimeo 등 주요 플랫폼 URL 지원
              </p>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
