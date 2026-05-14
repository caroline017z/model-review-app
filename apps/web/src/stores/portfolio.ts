import { create } from "zustand";
import type { CandidateProject, UploadResponse, ReviewResponse, ProjectPayload, PortfolioPayload } from "@/lib/api";
import { useUiStore } from "@/stores/ui";

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

type Slot = 1 | 2;

interface PortfolioState {
  model1: ModelEntry | null;
  model2: ModelEntry | null;
  // Per-slot review caches — portfolio tab swaps between them based on
  // `useUiStore.activeModelTab`. Consumers should use the `useActive*`
  // hooks below, never read these fields directly.
  reviewProjects1: ProjectPayload[];
  reviewProjects2: ProjectPayload[];
  portfolio1: PortfolioPayload | null;
  portfolio2: PortfolioPayload | null;
  selectedIds: IdSet;
  // Per-slot exclusion state — kept independent so toggling a row in M1
  // doesn't bleed into M2 (different portfolios may share index positions
  // but different underlying projects).
  excludedIds1: IdxSet;
  excludedIds2: IdxSet;
  pendingExclusions1: IdxSet;
  pendingExclusions2: IdxSet;
  confirmedExclusions1: IdxSet;
  confirmedExclusions2: IdxSet;

  setModel1: (data: UploadResponse, label: string) => void;
  setModel2: (data: UploadResponse, label: string) => void;
  clearModel2: () => void;
  setReviewData: (data: ReviewResponse, slot?: Slot) => void;
  toggleSelected: (id: string) => void;
  /** Toggle exclusion for the currently-active slot only. */
  togglePending: (idx: number) => void;
  /** Bulk include/exclude all rows in the currently-active slot. */
  setAllPending: (included: boolean, count: number) => void;
  /** Commit pending → confirmed for the currently-active slot only. */
  confirmPortfolio: () => void;
  hasPendingChanges: () => boolean;
  isExcluded: (idx: number) => boolean;
  selectAll: (ids: string[]) => void;
  selectNone: () => void;
}

function activeSlot(): Slot {
  return useUiStore.getState().activeModelTab;
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  model1: null,
  model2: null,
  reviewProjects1: [],
  reviewProjects2: [],
  portfolio1: null,
  portfolio2: null,
  selectedIds: {},
  excludedIds1: {},
  excludedIds2: {},
  pendingExclusions1: {},
  pendingExclusions2: {},
  confirmedExclusions1: {},
  confirmedExclusions2: {},

  setModel1: (data, label) => {
    const ids: IdSet = {};
    data.projects.filter((p) => p.suggested).forEach((p) => { ids[p.id] = true; });
    set({
      model1: { modelId: data.model_id, filename: data.filename, label, projects: data.projects },
      selectedIds: ids,
      // Reset slot 1's exclusion state so a fresh upload starts fully
      // included (empty exclusions = everything in).
      excludedIds1: {},
      pendingExclusions1: {},
      confirmedExclusions1: {},
    });
  },

  setModel2: (data, label) =>
    set({
      model2: { modelId: data.model_id, filename: data.filename, label, projects: data.projects },
      // Same reset for slot 2 on fresh upload.
      excludedIds2: {},
      pendingExclusions2: {},
      confirmedExclusions2: {},
    }),

  clearModel2: () =>
    set({
      model2: null, reviewProjects2: [], portfolio2: null,
      excludedIds2: {}, pendingExclusions2: {}, confirmedExclusions2: {},
    }),

  setReviewData: (data, slot = 1) =>
    set(
      slot === 2
        ? { reviewProjects2: data.projects, portfolio2: data.portfolio }
        : { reviewProjects1: data.projects, portfolio1: data.portfolio },
    ),

  toggleSelected: (id) =>
    set((state) => {
      const next = { ...state.selectedIds };
      if (next[id]) delete next[id];
      else next[id] = true;
      return { selectedIds: next };
    }),

  togglePending: (idx) =>
    set((state) => {
      const slot = activeSlot();
      const key = slot === 2 ? "pendingExclusions2" : "pendingExclusions1";
      const next = { ...state[key] };
      if (next[idx]) delete next[idx];
      else next[idx] = true;
      return { [key]: next } as Partial<PortfolioState>;
    }),

  /** Bulk: exclude all (included=false) or include all (included=true). */
  setAllPending: (included, count) =>
    set(() => {
      const slot = activeSlot();
      const key = slot === 2 ? "pendingExclusions2" : "pendingExclusions1";
      if (included) return { [key]: {} } as Partial<PortfolioState>;
      const next: IdxSet = {};
      for (let i = 0; i < count; i++) next[i] = true;
      return { [key]: next } as Partial<PortfolioState>;
    }),

  confirmPortfolio: () =>
    set((state) => {
      const slot = activeSlot();
      if (slot === 2) {
        return {
          confirmedExclusions2: { ...state.pendingExclusions2 },
          excludedIds2: { ...state.pendingExclusions2 },
        };
      }
      return {
        confirmedExclusions1: { ...state.pendingExclusions1 },
        excludedIds1: { ...state.pendingExclusions1 },
      };
    }),

  hasPendingChanges: () => {
    const slot = activeSlot();
    const state = get();
    const pending = slot === 2 ? state.pendingExclusions2 : state.pendingExclusions1;
    const confirmed = slot === 2 ? state.confirmedExclusions2 : state.confirmedExclusions1;
    const pendingKeys = Object.keys(pending);
    const confirmedKeys = Object.keys(confirmed);
    if (pendingKeys.length !== confirmedKeys.length) return true;
    return pendingKeys.some((k) => !confirmed[Number(k)]);
  },

  isExcluded: (idx) => {
    const slot = activeSlot();
    const state = get();
    return !!(slot === 2 ? state.confirmedExclusions2[idx] : state.confirmedExclusions1[idx]);
  },

  selectAll: (ids) => {
    const s: IdSet = {};
    ids.forEach((id) => { s[id] = true; });
    set({ selectedIds: s });
  },
  selectNone: () => set({ selectedIds: {} }),
}));

// ---------------------------------------------------------------------------
// Active-slot hooks — read from both stores so components stay in sync when
// the user switches between Model 1 / Model 2 tabs.
// ---------------------------------------------------------------------------

export function useActiveReviewProjects(): ProjectPayload[] {
  const tab = useUiStore((s) => s.activeModelTab);
  return usePortfolioStore((s) => (tab === 2 ? s.reviewProjects2 : s.reviewProjects1));
}

export function useActivePortfolio(): PortfolioPayload | null {
  const tab = useUiStore((s) => s.activeModelTab);
  return usePortfolioStore((s) => (tab === 2 ? s.portfolio2 : s.portfolio1));
}

export function useActivePendingExclusions(): IdxSet {
  const tab = useUiStore((s) => s.activeModelTab);
  return usePortfolioStore((s) => (tab === 2 ? s.pendingExclusions2 : s.pendingExclusions1));
}

export function useActiveConfirmedExclusions(): IdxSet {
  const tab = useUiStore((s) => s.activeModelTab);
  return usePortfolioStore((s) => (tab === 2 ? s.confirmedExclusions2 : s.confirmedExclusions1));
}

// ---------------------------------------------------------------------------
// Direct-slot hooks — read a specific slot regardless of active tab. Use these
// for the left sidebar (always pinned to Model 1) and BuildWalkView (walk
// always anchors on Model 1).
// ---------------------------------------------------------------------------

export function useReviewProjectsForSlot(slot: Slot): ProjectPayload[] {
  return usePortfolioStore((s) => (slot === 2 ? s.reviewProjects2 : s.reviewProjects1));
}

export function useConfirmedExclusionsForSlot(slot: Slot): IdxSet {
  return usePortfolioStore((s) => (slot === 2 ? s.confirmedExclusions2 : s.confirmedExclusions1));
}

export function usePendingExclusionsForSlot(slot: Slot): IdxSet {
  return usePortfolioStore((s) => (slot === 2 ? s.pendingExclusions2 : s.pendingExclusions1));
}
