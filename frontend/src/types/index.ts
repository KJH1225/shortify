export interface VideoSource {
  type: 'file' | 'youtube';
  file?: File;
  url?: string;
}

export interface Highlight {
  id: string;
  startTime: number;
  endTime: number;
  title: string;
  description: string;
  score: number;
  thumbnailUrl?: string;
}

export interface ProcessingStatus {
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
}

export interface VideoProject {
  id: string;
  title: string;
  source: VideoSource;
  duration: number;
  highlights: Highlight[];
  status: ProcessingStatus;
  createdAt: Date;
}
