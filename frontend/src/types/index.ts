export interface VideoSource {
  type: 'file' | 'youtube';
  file?: File;
  url?: string;
}

export interface ClipSegment {
  start: number;
  end: number;
}

export interface Highlight {
  id: number;
  startTime: number;
  endTime: number;
  title: string;
  description: string;
  score: number;
  thumbnailUrl?: string;
  clips?: ClipSegment[];
}

export interface ProcessingStatus {
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
}

export interface VideoProject {
  id: number;
  title: string;
  source: VideoSource;
  duration: number;
  highlights: Highlight[];
  status: ProcessingStatus;
  createdAt: Date;
}
