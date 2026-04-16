"use client";

import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { useReviewerStore } from "@/stores/reviewer";

function ModelTab({ label, count, active, onClick }: { label: string; count: number; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 px-2 py-1.5 text-[10px] font-semibold rounded-t border-b-2 transition cursor-pointer truncate ${
        active
          ? "border-[var(--teal)] text-[var(--teal)] bg-[var(--surface)]"
          : "border-transparent text-[var(--muted)] hover:text-[var(--text-2)] bg-transparent"
      }`}
    >
      <div className="truncate">{label}</div>
      <div className="text-[8px] font-normal">{count} projects</div>
    </button>
  );
}

export function ProjectNavigator() {
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const model1 = usePortfolioStore((s) => s.model1);
  const model2 = usePortfolioStore((s) => s.model2);
  const excludedIds = usePortfolioStore((s) => s.confirmedExclusions);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const setSelected = useUiStore((s) => s.setSelectedProject);
  const navSearch = useUiStore((s) => s.navSearch);
  const setNavSearch = useUiStore((s) => s.setNavSearch);
  const navFilter = useUiStore((s) => s.navFilter);
  const setNavFilter = useUiStore((s) => s.setNavFilter);
  const activeModelTab = useUiStore((s) => s.activeModelTab);
  const setActiveModelTab = useUiStore((s) => s.setActiveModelTab);
  const approvals = useReviewerStore((s) => s.approvals);
  const isApproved = (idx: number) => !!approvals[idx]?.approved;

  const hasTwoModels = !!(model1 && model2);

  const filters = ["all", "OFF", "OUT", "REVIEW"];
  const filterLabels: Record<string, string> = {
    all: "All", OFF: "FAIL", OUT: "FLAG", REVIEW: "REVIEW",
  };

  // TODO: When two models loaded, split projects by model. For now, all projects shown.
  const filtered = reviewProjects
    .map((p, i) => ({ p, i }))
    .filter(({ p, i }) => {
      if (excludedIds[i]) return false;
      if (navSearch && !p.name.toLowerCase().includes(navSearch.toLowerCase())) return false;
      if (navFilter !== "all" && !p.findings?.some((f) => f.status === navFilter)) return false;
      return true;
    })
    .sort((a, b) => Math.abs(b.p.equityK || 0) - Math.abs(a.p.equityK || 0));

  return (
    <div className="p-3 overflow-y-auto text-[12px]">
      {/* Model tabs — only shown when 2 models uploaded */}
      {hasTwoModels && (
        <div className="flex gap-px mb-2 border-b border-[var(--border)]">
          <ModelTab
            label={model1.label}
            count={model1.projects.length}
            active={activeModelTab === 1}
            onClick={() => setActiveModelTab(1)}
          />
          <ModelTab
            label={model2.label}
            count={model2.projects.length}
            active={activeModelTab === 2}
            onClick={() => setActiveModelTab(2)}
          />
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
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setNavFilter(f)}
            className={`text-[9px] px-1.5 py-[2px] rounded-[10px] border cursor-pointer transition ${
              navFilter === f
                ? "bg-[var(--indigo)] text-white border-transparent"
                : "bg-[var(--inset)] text-[var(--text-2)] border-transparent hover:border-[var(--border-strong)]"
            }`}
          >
            {filterLabels[f]}
          </button>
        ))}
      </div>

      <div className="space-y-1">
        {filtered.length === 0 && (
          <p className="text-center text-[var(--muted)] text-[10px] py-4 italic">
            {reviewProjects.length === 0 ? "Upload a model to begin." : "No projects match filter."}
          </p>
        )}
        {filtered.map(({ p, i }) => (
          <button
            key={i}
            onClick={() => setSelected(i)}
            className={`w-full text-left border rounded p-[6px_8px] cursor-pointer transition-all border-l-2 ${
              selectedIdx === i
                ? "border-l-[var(--teal)] bg-white shadow-[0_1px_3px_rgba(5,13,37,0.06)] border-[var(--border)]"
                : "border-l-transparent border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--raised)]"
            }`}
            style={{ background: selectedIdx === i ? "var(--surface)" : undefined }}
          >
            <div className="font-bold text-[11px] flex items-center gap-1">
              {p.projNumber != null && (
                <span className="text-[8px] bg-[var(--teal)] text-white px-[3px] py-px rounded font-bold shrink-0">
                  P{p.projNumber}
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
        ))}
      </div>
    </div>
  );
}
