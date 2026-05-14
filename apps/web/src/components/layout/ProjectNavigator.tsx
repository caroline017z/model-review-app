"use client";

import {
  usePortfolioStore,
  useReviewProjectsForSlot,
  useConfirmedExclusionsForSlot,
} from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { useReviewerStore } from "@/stores/reviewer";

export function ProjectNavigator() {
  // Sidebar always reflects Model 1 — gives Caroline a stable reference for
  // the M1 portfolio while she works on M2 in the main panel.
  const reviewProjects = useReviewProjectsForSlot(1);
  const excludedIds = useConfirmedExclusionsForSlot(1);
  const model1 = usePortfolioStore((s) => s.model1);
  const model2 = usePortfolioStore((s) => s.model2);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const setSelected = useUiStore((s) => s.setSelectedProject);
  const activeModelTab = useUiStore((s) => s.activeModelTab);
  const setActiveModelTab = useUiStore((s) => s.setActiveModelTab);
  const navSearch = useUiStore((s) => s.navSearch);
  const setNavSearch = useUiStore((s) => s.setNavSearch);
  const navFilter = useUiStore((s) => s.navFilter);
  const setNavFilter = useUiStore((s) => s.setNavFilter);
  const approvals = useReviewerStore((s) => s.approvals);
  const isApproved = (idx: number) => !!approvals[idx]?.approved;

  const hasTwoModels = !!(model1 && model2);

  const filters = ["all", "OFF", "OUT", "REVIEW"];
  const filterLabels: Record<string, string> = {
    all: "All", OFF: "FAIL", OUT: "FLAG", REVIEW: "REVIEW",
  };

  const filtered = reviewProjects
    .map((p, i) => ({ p, i }))
    .filter(({ p, i }) => {
      if (excludedIds[i]) return false;
      if (navSearch && !p.name.toLowerCase().includes(navSearch.toLowerCase())) return false;
      if (navFilter !== "all" && !p.findings?.some((f) => f.status === navFilter)) return false;
      return true;
    })
    .sort((a, b) => (a.p.projNumber ?? 999) - (b.p.projNumber ?? 999));

  return (
    <div className="p-3 overflow-y-auto text-[12px]">
      {/* When two models are loaded, the sidebar pins to Model 1 as a
          stable reference. Show a small switch to toggle the *main panel*
          between the two models — the sidebar list itself doesn't change. */}
      {hasTwoModels && (
        <div className="mb-2 pb-2 border-b border-[var(--border)]">
          <div className="text-[9px] font-bold uppercase tracking-[0.08em] mb-1" style={{ color: "var(--muted)" }}>
            Main view
          </div>
          <div className="flex gap-px rounded overflow-hidden bg-[var(--inset)] p-0.5">
            <button
              onClick={() => setActiveModelTab(1)}
              className={`flex-1 px-2 py-1 text-[10px] font-semibold rounded transition cursor-pointer truncate ${
                activeModelTab === 1 ? "bg-[var(--teal)] text-white" : "text-[var(--muted)] hover:text-[var(--text-2)]"
              }`}
              title={`Show ${model1.label} in main panel`}
            >
              {model1.label}
            </button>
            <button
              onClick={() => setActiveModelTab(2)}
              className={`flex-1 px-2 py-1 text-[10px] font-semibold rounded transition cursor-pointer truncate ${
                activeModelTab === 2 ? "bg-[var(--indigo)] text-white" : "text-[var(--muted)] hover:text-[var(--text-2)]"
              }`}
              title={`Show ${model2.label} in main panel`}
            >
              {model2.label}
            </button>
          </div>
          <p className="text-[8.5px] mt-1 italic" style={{ color: "var(--muted)" }}>
            Sidebar pinned to {model1.label} for reference
          </p>
        </div>
      )}

      <div className="flex justify-between text-[9px] font-bold uppercase tracking-[0.08em] mb-2" style={{ color: "var(--muted)" }}>
        <span>Projects &middot; {filtered.length}</span>
      </div>

      <input
        type="text"
        placeholder="Search projects..."
        value={navSearch}
        onChange={(e) => setNavSearch(e.target.value)}
        className="w-full px-2 py-1.5 border border-[var(--border)] rounded text-[11px] mb-2"
        style={{ background: "var(--surface)" }}
      />

      <div className="flex gap-1 flex-wrap mb-3">
        {filters.map((f) => {
          const count = f === "all"
            ? reviewProjects.filter((_, i) => !excludedIds[i]).length
            : reviewProjects.filter((p, i) => !excludedIds[i] && p.findings?.some((fi) => fi.status === f)).length;
          return (
            <button
              key={f}
              onClick={() => setNavFilter(f)}
              className={`text-[9px] px-1.5 py-[2px] rounded-[10px] border cursor-pointer transition ${
                navFilter === f
                  ? "bg-[var(--indigo)] text-white border-transparent"
                  : "bg-[var(--inset)] text-[var(--text-2)] border-transparent hover:border-[var(--border-strong)]"
              }`}
            >
              {filterLabels[f]} <span className="tabular-nums">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="space-y-1">
        {filtered.length === 0 && (
          <p className="text-center text-[var(--muted)] text-[10px] py-4 italic">
            {reviewProjects.length === 0 ? "Upload a model to begin." : "No projects match filter."}
          </p>
        )}
        {filtered.map(({ p, i }) => {
          const isSel = selectedIdx === i;
          const isDone = isApproved(i);
          return (
          <button
            key={i}
            onClick={() => { setActiveModelTab(1); setSelected(i); }}
            className={`w-full text-left border rounded p-[6px_8px] cursor-pointer transition-all border-l-3 ${
              isSel
                ? "border-l-[var(--teal)] bg-white shadow-[0_1px_3px_rgba(5,13,37,0.06)] border-[var(--border)]"
                : isDone
                  ? "border-l-[var(--ok)] border-[var(--border)] opacity-70"
                  : "border-l-transparent border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--raised)]"
            }`}
            style={{ background: isSel ? "var(--surface)" : isDone ? "rgba(58,125,68,0.04)" : undefined }}
          >
            <div className="font-bold text-[11px] flex items-center gap-1">
              {p.projNumber != null && (
                <span className="text-[8px] bg-[var(--teal)] text-white px-[3px] py-px rounded font-bold shrink-0">
                  {p.projNumber}
                </span>
              )}
              <span className="truncate">{p.name}</span>
              {isApproved(i) && (
                <span
                  className="ml-auto text-[8px] bg-[var(--teal)] text-white px-1 py-px rounded font-bold shrink-0"
                  title={`Approved by ${approvals[i]?.reviewer || "—"} at ${approvals[i]?.timestamp || "—"}`}
                >
                  OK
                </span>
              )}
            </div>
            <div className="text-[9px] mt-px truncate" style={{ color: "var(--muted)" }}>{p.sub}</div>
          </button>
          );
        })}
      </div>
    </div>
  );
}
