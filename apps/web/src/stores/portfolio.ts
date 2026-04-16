import { create } from "zustand";
import type { CandidateProject, UploadResponse, ReviewResponse, ProjectPayload, PortfolioPayload } from "@/lib/api";

interface ModelEntry {
  modelId: string;
  filename: string;
  label: string;
  projects: CandidateProject[];
}

interface PortfolioState {
  // Uploaded models
  model1: ModelEntry | null;
  model2: ModelEntry | null;

  // Review data (populated after audit)
  reviewProjects: ProjectPayload[];
  portfolio: PortfolioPayload | null;

  // Selected project IDs for review
  selectedIds: Set<string>;
  excludedIds: Set<number>;

  // Actions
  setModel1: (data: UploadResponse, label: string) => void;
  setModel2: (data: UploadResponse, label: string) => void;
  clearModel2: () => void;
  setReviewData: (data: ReviewResponse) => void;
  toggleSelected: (id: string) => void;
  toggleExcluded: (idx: number) => void;
  selectAll: (ids: string[]) => void;
  selectNone: () => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  model1: null,
  model2: null,
  reviewProjects: [],
  portfolio: null,
  selectedIds: new Set(),
  excludedIds: new Set(),

  setModel1: (data, label) =>
    set({
      model1: { modelId: data.model_id, filename: data.filename, label, projects: data.projects },
      selectedIds: new Set(data.projects.filter((p) => p.suggested).map((p) => p.id)),
    }),

  setModel2: (data, label) =>
    set({
      model2: { modelId: data.model_id, filename: data.filename, label, projects: data.projects },
    }),

  clearModel2: () => set({ model2: null }),

  setReviewData: (data) =>
    set({ reviewProjects: data.projects, portfolio: data.portfolio }),

  toggleSelected: (id) =>
    set((state) => {
      const next = new Set(state.selectedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { selectedIds: next };
    }),

  toggleExcluded: (idx) =>
    set((state) => {
      const next = new Set(state.excludedIds);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return { excludedIds: next };
    }),

  selectAll: (ids) => set({ selectedIds: new Set(ids) }),
  selectNone: () => set({ selectedIds: new Set() }),
}));
