"use client";

import { useState } from "react";
import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { useReviewerStore } from "@/stores/reviewer";
import { VarianceChart } from "@/components/charts/VarianceChart";
import { CashflowChart } from "@/components/charts/CashflowChart";
import { TornadoChart } from "@/components/charts/TornadoChart";
import { BibleMapping } from "@/components/review/BibleMapping";
import { fmtNpp, fmtIrr, fmtEquity, fmtImpact } from "@/lib/format";
import type { BibleMappingCategory } from "@/lib/api";

export function ProjectReviewView() {
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const setSelected = useUiStore((s) => s.setSelectedProject);
  const project = reviewProjects[selectedIdx];

  // Persisted reviewer actions (localStorage via Zustand persist)
  // Subscribe to `actions` and `approvals` directly so component re-renders on changes
  const reviewerActions = useReviewerStore((s) => s.actions);
  const reviewerApprovals = useReviewerStore((s) => s.approvals);
  const setActionStore = useReviewerStore((s) => s.setAction);
  const setNoteStore = useReviewerStore((s) => s.setNote);
  const approveProject = useReviewerStore((s) => s.approveProject);

  const getAction = (idx: number, field: string) =>
    reviewerActions[idx]?.[field] || { action: null, note: "" };
  const isApproved = (idx: number) => !!reviewerApprovals[idx]?.approved;
  const [sortBy, setSortBy] = useState<"field" | "status" | "impact">("impact");
  const [sortAsc, setSortAsc] = useState(false);

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="italic" style={{ color: "var(--muted)" }}>Select a project from the navigator.</p>
      </div>
    );
  }

  const findings = project.findings || [];
  const accepted = findings.filter((f) => getAction(selectedIdx, f.field).action === "accept").length;
  const flagged = findings.filter((f) => getAction(selectedIdx, f.field).action === "flag").length;
  const skipped = findings.filter((f) => getAction(selectedIdx, f.field).action === "skip").length;
  const unhandled = findings.length - accepted - flagged - skipped;
  const canApprove = unhandled === 0 && findings.length > 0;
  const approved = isApproved(selectedIdx);

  const handleApprove = () => {
    approveProject(selectedIdx, "Caroline Z.");
    // Auto-advance to next unreviewed project
    const nextIdx = reviewProjects.findIndex((_, i) => i !== selectedIdx && !isApproved(i));
    if (nextIdx >= 0) setTimeout(() => setSelected(nextIdx), 300);
  };

  return (
    <div className="space-y-4">
      {/* Deal header — compact, IB-style */}
      <div className="rounded p-3 text-white flex items-center gap-6" style={{ background: "var(--navy)" }}>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h2 className="text-[13px] font-bold truncate">{project.name}</h2>
            <span className={`px-2 py-0.5 rounded text-[9px] font-bold text-white shrink-0 ${
              project.verdict === "CLEAN" ? "bg-[var(--ok)]"
              : project.verdict === "REVIEW" ? "bg-[var(--rev)]"
              : "bg-[var(--off)]"
            }`}>
              {project.verdict}
            </span>
          </div>
          <p className="text-[10px] text-white/50 truncate">{project.sub}</p>
        </div>
        <div className="flex gap-5 text-[11px] shrink-0">
          <div className="text-center"><div className="text-[9px] uppercase text-white/40 tracking-wider">NPP &Delta;</div><div className="font-bold tabular-nums">{fmtNpp(project.nppPerW)}</div></div>
          <div className="text-center"><div className="text-[9px] uppercase text-white/40 tracking-wider">IRR &Delta;</div><div className="font-bold tabular-nums">{fmtIrr(project.irrPct)}</div></div>
          <div className="text-center"><div className="text-[9px] uppercase text-white/40 tracking-wider">Equity</div><div className={`font-bold tabular-nums ${project.equityK < 0 ? "text-red-300" : ""}`}>{fmtEquity(project.equityK)}</div></div>
        </div>
      </div>

      {/* KPI Strip — curated labels */}
      {(() => {
        const k = project.kpis;
        const rc1 = project.rateComp1 as Record<string, unknown> | undefined;
        const rc1Name = String(rc1?.name || "—");
        const kpis: [string, string][] = [
          ["MWdc", k.dc || "—"],
          ["EPC ($/W)", k.epc || "—"],
          ["NPP ($/W)", k.npp || "—"],
          ["ITC", k.itc || "—"],
          ["Appraisal IRR", k.irr || "—"],
          ["Levered PT IRR", k.levIrr || "—"],
          ["Rate Curve", rc1Name !== "—" ? rc1Name : "—"],
        ];
        return (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(110px,1fr))] gap-1.5">
            {kpis.map(([label, val]) => (
              <div key={label} className="rounded px-2.5 py-1.5 border border-[var(--border)] border-l-2 border-l-[var(--teal)]" style={{ background: "var(--raised)" }}>
                <div className="text-[8.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--muted)" }}>{label}</div>
                <div className="text-[13px] font-bold tabular-nums">{val}</div>
              </div>
            ))}
          </div>
        );
      })()}

      {/* Approval banner */}
      <div className="rounded border border-[var(--border)] px-4 py-3 flex items-center gap-4 text-xs" style={{ background: "var(--raised)" }}>
        <span className="font-semibold" style={{ color: "var(--ok)" }}>{accepted} Accepted</span>
        <span className="font-semibold" style={{ color: "var(--off)" }}>{flagged} Flagged</span>
        <span className="font-semibold" style={{ color: "var(--muted)" }}>{skipped} Skipped</span>
        <span style={{ color: unhandled > 0 ? "var(--off)" : "var(--muted)" }}>{unhandled} Unhandled</span>
        <button
          disabled={!canApprove || approved}
          onClick={handleApprove}
          className="ml-auto px-4 py-1.5 rounded text-xs font-bold text-white transition disabled:opacity-40"
          style={{ background: approved ? "var(--ok)" : canApprove ? "var(--teal)" : "var(--muted)" }}
        >
          {approved ? "Approved" : "Approve Project"}
        </button>
      </div>

      {/* Findings table */}
      <div className="rounded border border-[var(--border)] overflow-hidden" style={{ background: "var(--surface)" }}>
        <div className="px-4 py-2 border-b border-[var(--border)] flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--muted)" }}>
            Findings &middot; {findings.length}
          </span>
          {unhandled > 0 && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded" style={{ background: "var(--off-bg)", color: "var(--off)" }}>
              {unhandled} unhandled
            </span>
          )}
        </div>
        {findings.length === 0 ? (
          <p className="text-center py-6 text-xs italic" style={{ color: "var(--muted)" }}>No findings — this project is clean.</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] sticky top-0 z-10" style={{ background: "var(--raised)" }}>
                <th className="text-left px-4 py-2 font-semibold cursor-pointer select-none" onClick={() => { setSortBy("field"); setSortAsc(sortBy === "field" ? !sortAsc : true); }}>
                  Field {sortBy === "field" ? (sortAsc ? "↑" : "↓") : ""}
                </th>
                <th className="text-center px-2 py-2 font-semibold cursor-pointer select-none" onClick={() => { setSortBy("status"); setSortAsc(sortBy === "status" ? !sortAsc : true); }}>
                  Status {sortBy === "status" ? (sortAsc ? "↑" : "↓") : ""}
                </th>
                <th className="text-center px-2 py-2 font-semibold">Bible</th>
                <th className="text-center px-2 py-2 font-semibold">Model</th>
                <th className="text-center px-2 py-2 font-semibold cursor-pointer select-none" onClick={() => { setSortBy("impact"); setSortAsc(sortBy === "impact" ? !sortAsc : false); }}>
                  Impact {sortBy === "impact" ? (sortAsc ? "↑" : "↓") : ""}
                </th>
                <th className="text-center px-2 py-2 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {[...findings].sort((a, b) => {
                const statusOrder: Record<string, number> = { OFF: 0, OUT: 1, MISSING: 2, REVIEW: 3 };
                if (sortBy === "impact") {
                  const diff = Math.abs(b.impact || 0) - Math.abs(a.impact || 0);
                  return sortAsc ? -diff : diff;
                }
                if (sortBy === "status") {
                  const diff = (statusOrder[a.status] ?? 9) - (statusOrder[b.status] ?? 9);
                  return sortAsc ? diff : -diff;
                }
                return sortAsc ? a.field.localeCompare(b.field) : b.field.localeCompare(a.field);
              }).map((f, fi) => {
                const act = getAction(selectedIdx, f.field);
                const statusCls = f.status === "OFF" ? "bg-[var(--off-bg)] text-[var(--off)]"
                  : f.status === "OUT" ? "bg-[var(--out-bg)] text-[var(--out)]"
                  : f.status === "REVIEW" ? "bg-[var(--rev-bg)] text-[var(--rev)]"
                  : "bg-[var(--miss-bg)] text-[var(--miss)]";
                return (
                  <tr key={fi} className="border-b border-[var(--border)] hover:bg-[var(--inset)]">
                    <td className="px-4 py-2 font-semibold">
                      {act.action && <span className={`text-[9px] mr-1 px-1 rounded font-bold ${
                        act.action === "accept" ? "bg-[var(--ok-bg)] text-[var(--ok)]"
                        : act.action === "flag" ? "bg-[var(--off-bg)] text-[var(--off)]"
                        : "bg-[var(--miss-bg)] text-[var(--miss)]"
                      }`}>{act.action.toUpperCase()}</span>}
                      {f.field}
                    </td>
                    <td className="text-center px-2 py-2"><span className={`text-[10px] px-[6px] py-px rounded font-bold ${statusCls}`}>{f.status === "OFF" ? "FAIL" : f.status === "OUT" ? "FLAG" : f.status}</span></td>
                    <td className="text-center px-2 py-2 tabular-nums">{f.bible}</td>
                    <td className="text-center px-2 py-2 tabular-nums">{f.model}</td>
                    <td className={`text-center px-2 py-2 tabular-nums font-semibold ${f.impact != null && f.impact < 0 ? "text-[var(--off)]" : ""}`}>{fmtImpact(f.impact)}</td>
                    <td className="text-center px-2 py-2">
                      <div className="flex gap-1 justify-center">
                        {(["accept", "flag", "skip"] as const).map((a) => (
                          <button
                            key={a}
                            onClick={() => setActionStore(selectedIdx, f.field, a)}
                            className={`text-[10px] px-2 py-0.5 rounded border transition cursor-pointer ${
                              act.action === a
                                ? a === "accept" ? "bg-[var(--ok-bg)] text-[var(--ok)] border-[var(--ok)]"
                                  : a === "flag" ? "bg-[var(--off-bg)] text-[var(--off)] border-[var(--off)]"
                                  : "bg-[var(--miss-bg)] text-[var(--miss)] border-[var(--miss)]"
                                : "border-[var(--border)] hover:border-[var(--border-strong)]"
                            }`}
                          >
                            {a.charAt(0).toUpperCase() + a.slice(1)}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Charts — no capital stack (only useful in model comparison) */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded border border-[var(--border)] p-3" style={{ background: "var(--surface)" }}>
          <VarianceChart {...project.variance} />
        </div>
        <div className="rounded border border-[var(--border)] p-3" style={{ background: "var(--surface)" }}>
          <TornadoChart labels={project.tornado.labels} lo={project.tornado.lo} hi={project.tornado.hi} />
        </div>
        <div className="col-span-2 rounded border border-[var(--border)] p-3" style={{ background: "var(--surface)" }}>
          <div className="text-[10px] font-bold uppercase tracking-[0.08em] mb-1" style={{ color: "var(--muted)" }}>25-Year Cash Flow</div>
          <CashflowChart opCF={project.cashflow.opCF} taxBn={project.cashflow.taxBn} terminal={project.cashflow.terminal} />
        </div>
      </div>

      {/* Full Bible Mapping dropdown */}
      {(project.fullMapping as BibleMappingCategory[] | undefined)?.length ? (
        <BibleMapping categories={project.fullMapping as BibleMappingCategory[]} />
      ) : null}

      {/* Reviewer Notes */}
      <div className="rounded border border-[var(--border)] overflow-hidden" style={{ background: "var(--surface)" }}>
        <div className="px-4 py-2 border-b border-[var(--border)] text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--muted)" }}>
          Reviewer Notes
        </div>
        <div className="p-4">
          <textarea
            value={getAction(selectedIdx, "__project_note__").note || ""}
            onChange={(e) => setNoteStore(selectedIdx, "__project_note__", e.target.value)}
            placeholder="Add review notes for this project — rationale, conditions, follow-ups..."
            rows={3}
            className="w-full px-3 py-2 border border-[var(--border)] rounded text-xs resize-y"
            style={{ background: "var(--raised)", color: "var(--text)" }}
          />
        </div>
      </div>
    </div>
  );
}
