import { create } from "zustand";
import type { CandidateProject, UploadResponse, ReviewResponse, ProjectPayload, PortfolioPayload } from "@/lib/api";

interface ModelEntry {
  modelId: string;
  filename: string;
  label: string;
  projects: CandidateProject[];
}

// Use plain objects instead of Set — Zustand can shallow-compare objects
// but not Set instances (every new Set() is a new reference → infinite re-renders).
type IdSet = Record<string, boolean>;
type IdxSet = Record<number, boolean>;

interface PortfolioState {
  model1: ModelEntry | null;
  model2: ModelEntry | null;
  reviewProjects: ProjectPayload[];
  portfolio: PortfolioPayload | null;
  selectedIds: IdSet;
  excludedIds: IdxSet;

  setModel1: (data: UploadResponse, label: string) => void;
  setModel2: (data: UploadResponse, label: string) => void;
  clearModel2: () => void;
  setReviewData: (data: ReviewResponse) => void;
  toggleSelected: (id: string) => void;
  toggleExcluded: (idx: number) => void;
  isExcluded: (idx: number) => boolean;
  selectAll: (ids: string[]) => void;
  selectNone: () => void;
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  model1: null,
  model2: null,
  reviewProjects: [],
  portfolio: null,
  selectedIds: {},
  excludedIds: {},

  setModel1: (data, label) => {
    const ids: IdSet = {};
    data.projects.filter((p) => p.suggested).forEach((p) => { ids[p.id] = true; });
    set({
      model1: { modelId: data.model_id, filename: data.filename, label, projects: data.projects },
      selectedIds: ids,
    });
  },

  setModel2: (data, label) =>
    set({
      model2: { modelId: data.model_id, filename: data.filename, label, projects: data.projects },
    }),

  clearModel2: () => set({ model2: null }),

  setReviewData: (data) =>
    set({ reviewProjects: data.projects, portfolio: data.portfolio }),

  toggleSelected: (id) =>
    set((state) => {
      const next = { ...state.selectedIds };
      if (next[id]) delete next[id];
      else next[id] = true;
      return { selectedIds: next };
    }),

  toggleExcluded: (idx) =>
    set((state) => {
      const next = { ...state.excludedIds };
      if (next[idx]) delete next[idx];
      else next[idx] = true;
      return { excludedIds: next };
    }),

  isExcluded: (idx) => !!get().excludedIds[idx],

  selectAll: (ids) => {
    const s: IdSet = {};
    ids.forEach((id) => { s[id] = true; });
    set({ selectedIds: s });
  },
  selectNone: () => set({ selectedIds: {} }),
}));
