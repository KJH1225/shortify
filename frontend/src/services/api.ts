/**
 * API Client Layer
 * Centralized API calls for better separation of concerns
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
export interface ApiResponse<T> {
  data: T;
  meta?: Record<string, unknown>;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface VideoResponse {
  id: number;
  title: string;
  source: {
    type: 'file' | 'youtube';
    url?: string;
    filename?: string;
  };
  duration: number | null;
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  message: string | null;
  highlights: HighlightResponse[];
  created_at: string;
  updated_at: string;
}

export interface HighlightResponse {
  id: number;
  video_id: number;
  start_time: number;
  end_time: number;
  title: string;
  description: string | null;
  score: number;
  thumbnail_url: string | null;
  created_at: string;
}

export interface ExportResponse {
  success: boolean;
  message: string;
  export_id: string;
  status: string;
  estimated_time: number;
}

export interface ExportStatusResponse {
  export_id: string;
  highlight_id: number;
  status: 'pending' | 'processing' | 'completed' | 'error';
  download_url: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

// Error handling helper
class ApiRequestError extends Error {
  constructor(
    public statusCode: number,
    public error: ApiError | string
  ) {
    super(typeof error === 'string' ? error : error.message);
    this.name = 'ApiRequestError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiRequestError(response.status, error.detail || error);
  }
  return response.json();
}

// Video API
export const videoApi = {
  /**
   * Upload a video file
   */
  upload: async (file: File): Promise<VideoResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_URL}/api/videos/upload`, {
      method: 'POST',
      body: formData,
    });

    return handleResponse<VideoResponse>(response);
  },

  /**
   * Process a YouTube URL
   */
  processYouTube: async (url: string): Promise<VideoResponse> => {
    const response = await fetch(`${API_URL}/api/videos/youtube`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    return handleResponse<VideoResponse>(response);
  },

  /**
   * Get video by ID
   */
  getById: async (videoId: number): Promise<VideoResponse> => {
    const response = await fetch(`${API_URL}/api/videos/${videoId}`);
    return handleResponse<VideoResponse>(response);
  },

  /**
   * Get all videos
   */
  getAll: async (): Promise<VideoResponse[]> => {
    const response = await fetch(`${API_URL}/api/videos/`);
    return handleResponse<VideoResponse[]>(response);
  },

  /**
   * Delete a video
   */
  delete: async (videoId: number): Promise<ApiResponse<{ success: boolean; message: string }>> => {
    const response = await fetch(`${API_URL}/api/videos/${videoId}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },
};

// Highlight API
export const highlightApi = {
  /**
   * Get highlight by ID
   */
  getById: async (highlightId: number): Promise<HighlightResponse> => {
    const response = await fetch(`${API_URL}/api/highlights/${highlightId}`);
    return handleResponse<HighlightResponse>(response);
  },

  /**
   * Export highlight to short-form video
   */
  export: async (highlightId: number): Promise<ApiResponse<ExportResponse>> => {
    const response = await fetch(`${API_URL}/api/highlights/${highlightId}/export`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  /**
   * Get export job status
   */
  getExportStatus: async (highlightId: number, exportId: string): Promise<ApiResponse<ExportStatusResponse>> => {
    const response = await fetch(`${API_URL}/api/highlights/${highlightId}/export/${exportId}/status`);
    return handleResponse(response);
  },

  /**
   * Download exported highlight clip
   */
  downloadExport: (highlightId: number, exportId: string): void => {
    const url = `${API_URL}/api/highlights/${highlightId}/export/${exportId}/download`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `highlight_${highlightId}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  },

  /**
   * Delete a highlight
   */
  delete: async (highlightId: number): Promise<ApiResponse<{ success: boolean; message: string }>> => {
    const response = await fetch(`${API_URL}/api/highlights/${highlightId}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },
};

// Health API
export const healthApi = {
  /**
   * Check API health
   */
  check: async (): Promise<{ status: string }> => {
    const response = await fetch(`${API_URL}/health`);
    return handleResponse(response);
  },
};

// Export error class for use in components
export { ApiRequestError };
