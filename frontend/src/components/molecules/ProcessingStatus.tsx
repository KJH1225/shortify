'use client';

import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent } from '@/components/ui/card';
import type { ProcessingStatus as ProcessingStatusType } from '@/types';

interface ProcessingStatusProps {
  status: ProcessingStatusType;
}

export function ProcessingStatus({ status }: ProcessingStatusProps) {
  if (status.status === 'idle') return null;

  const statusConfig = {
    uploading: {
      icon: <Loader2 className="h-6 w-6 animate-spin text-violet-500" />,
      title: '업로드 중...',
      color: 'from-violet-500 to-fuchsia-500',
    },
    processing: {
      icon: <Loader2 className="h-6 w-6 animate-spin text-violet-500" />,
      title: 'AI가 분석 중...',
      color: 'from-violet-500 to-fuchsia-500',
    },
    completed: {
      icon: <CheckCircle2 className="h-6 w-6 text-green-500" />,
      title: '분석 완료!',
      color: 'from-green-500 to-emerald-500',
    },
    error: {
      icon: <XCircle className="h-6 w-6 text-red-500" />,
      title: '오류 발생',
      color: 'from-red-500 to-rose-500',
    },
  };

  const config = statusConfig[status.status];

  return (
    <Card className="w-full max-w-2xl mx-auto border-border/50 bg-card/50 backdrop-blur">
      <CardContent className="p-6">
        <div className="flex items-center gap-4 mb-4">
          {config.icon}
          <div className="flex-1">
            <h3 className="font-semibold">{config.title}</h3>
            <p className="text-sm text-muted-foreground">{status.message}</p>
          </div>
          <span className="text-lg font-bold">{status.progress}%</span>
        </div>
        <div className="relative">
          <Progress value={status.progress} className="h-2" />
          <div
            className={`absolute inset-0 h-2 rounded-full bg-gradient-to-r ${config.color} opacity-20`}
            style={{ width: `${status.progress}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
