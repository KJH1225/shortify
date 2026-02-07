import { create } from 'zustand';
import type { VideoProject, Highlight, ProcessingStatus } from '@/types';

interface VideoStore {
  projects: VideoProject[];
  currentProject: VideoProject | null;

  setCurrentProject: (project: VideoProject | null) => void;
  addProject: (project: VideoProject) => void;
  updateProjectStatus: (projectId: string, status: ProcessingStatus) => void;
  addHighlights: (projectId: string, highlights: Highlight[]) => void;
  removeProject: (projectId: string) => void;
}

export const useVideoStore = create<VideoStore>((set) => ({
  projects: [],
  currentProject: null,

  setCurrentProject: (project) => set({ currentProject: project }),

  addProject: (project) =>
    set((state) => ({
      projects: [...state.projects, project],
      currentProject: project
    })),

  updateProjectStatus: (projectId, status) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, status } : p
      ),
      currentProject: state.currentProject?.id === projectId
        ? { ...state.currentProject, status }
        : state.currentProject
    })),

  addHighlights: (projectId, highlights) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, highlights } : p
      ),
      currentProject: state.currentProject?.id === projectId
        ? { ...state.currentProject, highlights }
        : state.currentProject
    })),

  removeProject: (projectId) =>
    set((state) => ({
      projects: state.projects.filter((p) => p.id !== projectId),
      currentProject: state.currentProject?.id === projectId
        ? null
        : state.currentProject
    })),
}));
