"use client";

import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { useReviewerStore } from "@/stores/reviewer";

export function ProjectNavigator() {
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const excludedIds = usePortfolioStore((s) => s.excludedIds);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const setSelected = useUiStore((s) => s.setSelectedProject);
  const navSearch = useUiStore((s) => s.navSearch);
  const setNavSearch = useUiStore((s) => s.setNavSearch);
  const navFilter = useUiStore((s) => s.navFilter);
  const setNavFilter = useUiStore((s) => s.setNavFilter);
  const isApproved = useReviewerStore((s) => s.isApproved);

  const filters = ["all", "OFF", "OUT", "MISSING", "REVIEW"];
  const filterLabels: Record<string, string> = {
    all: "All", OFF: "FAIL", OUT: "FLAG", MISSING: "MISSING", REVIEW: "REVIEW",
  };

  const filtered = reviewProjects
    .map((p, i) => ({ p, i }))
    .filter(({ p, i }) => {
      if (excludedIds.has(i)) return false;
      if (navSearch && !p.name.toLowerCase().includes(navSearch.toLowerCase())) return false;
      if (navFilter !== "all" && !p.findings?.some((f) => f.status === navFilter)) return false;
      return true;
    })
    .sort((a, b) => Math.abs(b.p.equityK || 0) - Math.abs(a.p.equityK || 0));

  return (
    <div className="p-[14px] overflow-y-auto">
      <div className="flex justify-between text-[10px] font-bold uppercase tracking-[0.08em] text-muted mb-[10px]">
        <span>Projects &middot; {filtered.length}</span>
      </div>

      <input
        type="text"
        placeholder="Search projects..."
        value={navSearch}
        onChange={(e) => setNavSearch(e.target.value)}
        className="w-full px-[10px] py-[7px] border border-[var(--border)] rounded bg-surface text-xs mb-[10px]"
      />

      <div className="flex gap-1 flex-wrap mb-[14px]">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setNavFilter(f)}
            className={`text-[10px] px-2 py-[3px] rounded-[10px] border cursor-pointer transition ${
              navFilter === f
                ? "bg-indigo text-white border-transparent"
                : "bg-inset text-[var(--text-2)] border-transparent hover:border-[var(--border-strong)]"
            }`}
          >
            {filterLabels[f]}
          </button>
        ))}
      </div>

      <div className="space-y-1">
        {filtered.length === 0 && (
          <p className="text-center text-muted text-xs py-6 italic">
            {reviewProjects.length === 0
              ? "Upload a model to begin."
              : "No projects match the current filter."}
          </p>
        )}
        {filtered.map(({ p, i }) => (
          <button
            key={i}
            onClick={() => setSelected(i)}
            className={`w-full text-left bg-surface border rounded p-[7px_10px] cursor-pointer transition-all border-l-2 ${
              selectedIdx === i
                ? "border-l-teal bg-white shadow-[0_1px_3px_rgba(5,13,37,0.06)]"
                : "border-l-transparent border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-raised"
            }`}
          >
            <div className="font-bold text-[12.5px] flex items-center gap-[6px]">
              {p.projNumber != null && (
                <span className="text-[9px] bg-teal text-white px-[4px] py-px rounded font-bold">
                  P{p.projNumber}
                </span>
              )}
              {p.name}
              {isApproved(i) && (
                <span className="ml-auto text-[9px] bg-[var(--teal)] text-white px-[6px] py-px rounded font-bold tracking-[0.05em]">
                  APPROVED
                </span>
              )}
            </div>
            <div className="text-[10.5px] text-muted mt-px">{p.sub}</div>
            <div className="flex gap-1 mt-1 flex-wrap">
              {(!p.findings || p.findings.length === 0) && (
                <span className="text-[9px] px-[6px] py-px rounded bg-[var(--ok-bg)] text-[var(--ok)] font-semibold">
                  CLEAN
                </span>
              )}
              {p.findings?.slice(0, 4).map((f, fi) => (
                <span
                  key={fi}
                  className={`text-[9px] px-[6px] py-px rounded font-semibold ${
                    f.status === "OFF" ? "bg-[var(--off-bg)] text-[var(--off)]"
                    : f.status === "OUT" ? "bg-[var(--out-bg)] text-[var(--out)]"
                    : f.status === "REVIEW" ? "bg-[var(--rev-bg)] text-[var(--rev)]"
                    : "bg-[var(--miss-bg)] text-[var(--miss)]"
                  }`}
                >
                  {f.short}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
