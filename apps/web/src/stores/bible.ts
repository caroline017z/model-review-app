import { create } from "zustand";
import type { VintageSummary } from "@/lib/api";
import {
  listVintages,
  uploadVintage,
  setActiveVintage,
  deleteVintage,
} from "@/lib/api";

interface BibleState {
  vintages: VintageSummary[];
  loading: boolean;
  error: string | null;

  refresh: () => Promise<void>;
  upload: (file: File, label: string, setActive: boolean) => Promise<void>;
  activate: (vintageId: string) => Promise<void>;
  remove: (vintageId: string) => Promise<void>;

  activeVintage: () => VintageSummary | null;
}

export const useBibleStore = create<BibleState>((set, get) => ({
  vintages: [],
  loading: false,
  error: null,

  refresh: async () => {
    set({ loading: true, error: null });
    try {
      const vintages = await listVintages();
      set({ vintages, loading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to load vintages",
        loading: false,
      });
    }
  },

  upload: async (file, label, setActive) => {
    set({ loading: true, error: null });
    try {
      await uploadVintage(file, label, setActive);
      await get().refresh();
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Upload failed",
        loading: false,
      });
      throw e;
    }
  },

  activate: async (vintageId) => {
    set({ loading: true, error: null });
    try {
      await setActiveVintage(vintageId);
      await get().refresh();
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Set-active failed",
        loading: false,
      });
      throw e;
    }
  },

  remove: async (vintageId) => {
    set({ loading: true, error: null });
    try {
      await deleteVintage(vintageId);
      await get().refresh();
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Delete failed",
        loading: false,
      });
      throw e;
    }
  },

  activeVintage: () => get().vintages.find((v) => v.is_active) ?? null,
}));
