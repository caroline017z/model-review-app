import { create } from "zustand";

export type ViewMode = "portfolio" | "project" | "reference" | "walk";

interface UiState {
  mode: ViewMode;
  selectedProjectIdx: number;
  navSearch: string;
  navFilter: string;
  setMode: (mode: ViewMode) => void;
  setSelectedProject: (idx: number) => void;
  setNavSearch: (q: string) => void;
  setNavFilter: (f: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  mode: "project",
  selectedProjectIdx: 0,
  navSearch: "",
  navFilter: "all",
  setMode: (mode) => set({ mode }),
  setSelectedProject: (idx) => set({ selectedProjectIdx: idx }),
  setNavSearch: (q) => set({ navSearch: q }),
  setNavFilter: (f) => set({ navFilter: f }),
}));
