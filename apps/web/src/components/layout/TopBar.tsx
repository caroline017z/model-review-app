"use client";

import { useUiStore, type ViewMode } from "@/stores/ui";
import { usePortfolioStore } from "@/stores/portfolio";
import { useReviewerStore } from "@/stores/reviewer";

const modes: { key: ViewMode; label: string; requiresTwo?: boolean }[] = [
  { key: "portfolio", label: "Portfolio" },
  { key: "project", label: "Project Review" },
  { key: "reference", label: "Reference" },
  { key: "walk", label: "Build Walk", requiresTwo: true },
];

export function TopBar() {
  const mode = useUiStore((s) => s.mode);
  const setMode = useUiStore((s) => s.setMode);
  const portfolio = usePortfolioStore((s) => s.portfolio);
  const model2 = usePortfolioStore((s) => s.model2);
  const clearReviewer = useReviewerStore((s) => s.clearAll);

  const handleReset = () => {
    // Reset all stores to initial state
    usePortfolioStore.setState({
      model1: null, model2: null, reviewProjects: [], portfolio: null,
      selectedIds: new Set(), excludedIds: new Set(),
    });
    useUiStore.setState({ mode: "project", selectedProjectIdx: 0, navSearch: "", navFilter: "all" });
    clearReviewer();
  };

  return (
    <header className="h-[46px] bg-navy text-white flex items-center px-[18px] gap-5 shadow-[0_1px_4px_rgba(5,13,37,0.25)] relative z-10">
      <div className="font-bold tracking-[0.08em] text-[11.5px] uppercase">
        38<span className="text-teal">&deg;</span>N &middot; VP Pricing Review
      </div>

      <div className="flex bg-white/[0.04] rounded p-0.5 gap-px">
        {modes.map((m) => {
          if (m.requiresTwo && !model2) return null;
          return (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              className={`px-[13px] py-[5px] text-[11px] font-semibold rounded tracking-[0.04em] transition-all cursor-pointer ${
                mode === m.key
                  ? "bg-teal text-white shadow-[0_1px_3px_rgba(81,132,132,0.3)]"
                  : "text-white/50 hover:text-white/80 hover:bg-white/[0.04]"
              }`}
            >
              {m.label}
            </button>
          );
        })}
      </div>

      <div className="ml-auto flex items-center gap-4 text-[10.5px] text-white/60 tracking-[0.02em]">
        {portfolio && (
          <>
            <span>Model: <b className="text-white/90 font-semibold">{portfolio.modelName}</b></span>
            <span>Bible: <b className="text-white/90 font-semibold">{portfolio.bibleLabel}</b></span>
            <span>Reviewer: <b className="text-white/90 font-semibold">{portfolio.reviewer}</b></span>
            <button
              onClick={handleReset}
              className="px-2 py-1 rounded text-[10px] font-semibold border border-white/20 text-white/70 hover:text-white hover:border-white/40 transition cursor-pointer"
            >
              New Review
            </button>
          </>
        )}
      </div>
    </header>
  );
}
