'use client';

import { useState, useCallback } from 'react';
import { Upload, Link, FileVideo } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface VideoUploaderProps {
  onFileSelect: (file: File) => void;
  onUrlSubmit: (url: string) => void;
  isProcessing: boolean;
}

export function VideoUploader({ onFileSelect, onUrlSubmit, isProcessing }: VideoUploaderProps) {
  const [url, setUrl] = useState('');
  const [dragActive, setDragActive] = useState(false);

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

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('video/')) {
        onFileSelect(file);
      }
    }
  }, [onFileSelect]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
    }
  };

  const handleUrlSubmit = () => {
    if (url.trim()) {
      onUrlSubmit(url.trim());
      setUrl('');
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto border-border/50 bg-card/50 backdrop-blur">
      <CardContent className="p-6">
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
