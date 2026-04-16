import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ReviewAction = "accept" | "flag" | "skip" | null;

interface FindingState {
  action: ReviewAction;
  note: string;
}

interface ProjectApproval {
  approved: boolean;
  timestamp: string;
  reviewer: string;
}

interface ReviewerState {
  // Current model ID scope — actions only apply when this matches
  modelId: string | null;
  // Per-project, per-finding actions: { [projectIdx]: { [fieldName]: { action, note } } }
  actions: Record<number, Record<string, FindingState>>;
  // Per-project approval status
  approvals: Record<number, ProjectApproval>;

  // Actions
  setModelScope: (modelId: string) => void;
  getAction: (projectIdx: number, field: string) => FindingState;
  setAction: (projectIdx: number, field: string, action: ReviewAction) => void;
  setNote: (projectIdx: number, field: string, note: string) => void;
  approveProject: (projectIdx: number, reviewer: string) => void;
  unapproveProject: (projectIdx: number) => void;
  isApproved: (projectIdx: number) => boolean;
  clearAll: () => void;
}

const DEFAULT_STATE: FindingState = { action: null, note: "" };

export const useReviewerStore = create<ReviewerState>()(
  persist(
    (set, get) => ({
      modelId: null,
      actions: {},
      approvals: {},

      setModelScope: (modelId) => {
        // If model changed, clear all actions/approvals to prevent ghosting
        if (get().modelId !== modelId) {
          set({ modelId, actions: {}, approvals: {} });
        }
      },

      getAction: (projectIdx, field) =>
        get().actions[projectIdx]?.[field] || DEFAULT_STATE,

      setAction: (projectIdx, field, action) =>
        set((state) => {
          const projActions = { ...state.actions[projectIdx] };
          const current = projActions[field] || { ...DEFAULT_STATE };
          // Toggle off if same action clicked again
          projActions[field] = {
            ...current,
            action: current.action === action ? null : action,
          };
          return { actions: { ...state.actions, [projectIdx]: projActions } };
        }),

      setNote: (projectIdx, field, note) =>
        set((state) => {
          const projActions = { ...state.actions[projectIdx] };
          const current = projActions[field] || { ...DEFAULT_STATE };
          projActions[field] = { ...current, note };
          return { actions: { ...state.actions, [projectIdx]: projActions } };
        }),

      approveProject: (projectIdx, reviewer) =>
        set((state) => ({
          approvals: {
            ...state.approvals,
            [projectIdx]: {
              approved: true,
              timestamp: new Date().toISOString().slice(0, 16).replace("T", " "),
              reviewer,
            },
          },
        })),

      unapproveProject: (projectIdx) =>
        set((state) => {
          const next = { ...state.approvals };
          delete next[projectIdx];
          return { approvals: next };
        }),

      isApproved: (projectIdx) => !!get().approvals[projectIdx]?.approved,

      clearAll: () => set({ actions: {}, approvals: {} }),
    }),
    {
      name: "vpReview.reviewer",
    },
  ),
);
