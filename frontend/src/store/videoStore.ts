import { create } from 'zustand';
import type { Highlight, ProcessingStatus } from '@/types';

// 공통 Mock 데이터 (Backend와 동기화)
export const MOCK_HIGHLIGHTS: Highlight[] = [
  {
    id: 1,
    startTime: 45,
    endTime: 78,
    title: '핵심 개념 설명',
    description: '영상에서 가장 중요한 핵심 개념을 설명하는 구간입니다.',
    score: 0.95,
  },
  {
    id: 2,
    startTime: 120,
    endTime: 165,
    title: '놀라운 반전',
    description: '시청자들의 반응이 가장 뜨거웠던 반전 구간입니다.',
    score: 0.92,
  },
  {
    id: 3,
    startTime: 210,
    endTime: 245,
    title: '실용적인 팁',
    description: '바로 적용할 수 있는 실용적인 팁을 공유하는 구간입니다.',
    score: 0.88,
  },
  {
    id: 4,
    startTime: 300,
    endTime: 340,
    title: '감동적인 순간',
    description: '영상에서 가장 감동적인 순간이 담긴 구간입니다.',
    score: 0.85,
  },
  {
    id: 5,
    startTime: 420,
    endTime: 480,
    title: '결론 및 요약',
    description: '전체 내용을 깔끔하게 정리하는 마무리 구간입니다.',
    score: 0.82,
  },
];

// 분석 단계 메시지 (Backend와 동기화)
export const PROCESSING_MESSAGES = [
  '오디오 트랙 추출 중...',
  '음성을 텍스트로 변환 중...',
  '감정 분석 진행 중...',
  '하이라이트 구간 탐지 중...',
  '최적의 클립 선택 중...',
];

interface VideoState {
  // 현재 처리 상태
  status: ProcessingStatus;
  highlights: Highlight[];

  // 액션
  setStatus: (status: ProcessingStatus) => void;
  setHighlights: (highlights: Highlight[]) => void;
  reset: () => void;

  // 시뮬레이션 (개발용)
  simulateProcessing: () => Promise<void>;
}

const initialStatus: ProcessingStatus = {
  status: 'idle',
  progress: 0,
  message: '',
};

export const useVideoStore = create<VideoState>((set) => ({
  status: initialStatus,
  highlights: [],

  setStatus: (status) => set({ status }),
  setHighlights: (highlights) => set({ highlights }),
  reset: () => set({ status: initialStatus, highlights: [] }),

  simulateProcessing: async () => {
    // 업로드 단계
    set({ status: { status: 'uploading', progress: 0, message: '영상 업로드 중...' } });

    for (let i = 0; i <= 30; i += 10) {
      await new Promise(r => setTimeout(r, 200));
      set({ status: { status: 'uploading', progress: i, message: '영상 업로드 중...' } });
    }

    // 분석 단계
    set({ status: { status: 'processing', progress: 30, message: 'AI가 영상을 분석하고 있어요...' } });

    for (let i = 0; i < PROCESSING_MESSAGES.length; i++) {
      await new Promise(r => setTimeout(r, 800));
      const progress = 30 + ((i + 1) * 15);
      set({
        status: {
          status: 'processing',
          progress: Math.min(progress, 95),
          message: PROCESSING_MESSAGES[i]
        }
      });
    }

    // 완료
    set({
      status: { status: 'completed', progress: 100, message: '분석이 완료되었습니다!' },
      highlights: MOCK_HIGHLIGHTS
    });
  },
}));
