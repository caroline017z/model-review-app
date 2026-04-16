"use client";

import { useState, useCallback } from "react";
import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { VarianceChart } from "@/components/charts/VarianceChart";
import { CapitalStackChart } from "@/components/charts/CapitalStackChart";
import { CashflowChart } from "@/components/charts/CashflowChart";
import { TornadoChart } from "@/components/charts/TornadoChart";
import type { Finding } from "@/lib/api";

type ReviewAction = "accept" | "flag" | "skip" | null;
type ActionMap = Record<string, { action: ReviewAction; note: string }>;

export function ProjectReviewView() {
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const setSelected = useUiStore((s) => s.setSelectedProject);
  const project = reviewProjects[selectedIdx];

  // Per-project action state (persisted in component for now; will be localStorage in Phase 4)
  const [actions, setActions] = useState<Record<number, ActionMap>>({});

  const getAction = useCallback(
    (field: string) => actions[selectedIdx]?.[field] || { action: null, note: "" },
    [actions, selectedIdx],
  );

  const setAction = useCallback(
    (field: string, action: ReviewAction) => {
      setActions((prev) => ({
        ...prev,
        [selectedIdx]: {
          ...prev[selectedIdx],
          [field]: { ...prev[selectedIdx]?.[field], action: prev[selectedIdx]?.[field]?.action === action ? null : action, note: prev[selectedIdx]?.[field]?.note || "" },
        },
      }));
    },
    [selectedIdx],
  );

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="italic" style={{ color: "var(--muted)" }}>Select a project from the navigator.</p>
      </div>
    );
  }

  const findings = project.findings || [];
  const accepted = findings.filter((f) => getAction(f.field).action === "accept").length;
  const flagged = findings.filter((f) => getAction(f.field).action === "flag").length;
  const skipped = findings.filter((f) => getAction(f.field).action === "skip").length;
  const unhandled = findings.length - accepted - flagged - skipped;
  const canApprove = unhandled === 0 && findings.length > 0;

  const handleApprove = () => {
    // Auto-advance to next unreviewed project
    const nextIdx = reviewProjects.findIndex((_, i) => i !== selectedIdx && !actions[i]);
    if (nextIdx >= 0) setTimeout(() => setSelected(nextIdx), 300);
  };

  return (
    <div className="space-y-4">
      {/* Deal header */}
      <div className="rounded-lg p-4 text-white" style={{ background: "var(--navy)" }}>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold">{project.name}</h2>
            <p className="text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>{project.sub}</p>
          </div>
          <span className={`px-3 py-1 rounded text-xs font-bold text-white ${
            project.verdict === "CLEAN" ? "bg-[var(--ok)]"
            : project.verdict === "REVIEW" ? "bg-[var(--rev)]"
            : "bg-[var(--off)]"
          }`}>
            {project.verdict}
          </span>
        </div>
        <div className="flex gap-6 mt-3 text-sm">
          <div><span className="text-xs uppercase text-white/50">IRR</span><p className="font-bold">{project.irrPct.toFixed(2)}%</p></div>
          <div><span className="text-xs uppercase text-white/50">NPP</span><p className="font-bold">${project.nppPerW.toFixed(2)}/W</p></div>
          <div><span className="text-xs uppercase text-white/50">Equity</span><p className="font-bold">${project.equityK}k</p></div>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-[repeat(auto-fill,minmax(130px,1fr))] gap-2">
        {Object.entries(project.kpis).map(([key, val]) => (
          <div key={key} className="rounded p-[10px_12px] border border-[var(--border)] border-l-2 border-l-[var(--teal)]" style={{ background: "var(--raised)" }}>
            <div className="text-[9.5px] font-bold uppercase tracking-[0.07em]" style={{ color: "var(--muted)" }}>{key}</div>
            <div className="text-[16px] font-bold mt-0.5 tabular-nums">{String(val)}</div>
          </div>
        ))}
      </div>

      {/* Approval banner */}
      <div className="rounded border border-[var(--border)] px-4 py-3 flex items-center gap-4 text-xs" style={{ background: "var(--raised)" }}>
        <span className="font-semibold" style={{ color: "var(--ok)" }}>{accepted} Accepted</span>
        <span className="font-semibold" style={{ color: "var(--off)" }}>{flagged} Flagged</span>
        <span className="font-semibold" style={{ color: "var(--muted)" }}>{skipped} Skipped</span>
        <span style={{ color: unhandled > 0 ? "var(--off)" : "var(--muted)" }}>{unhandled} Unhandled</span>
        <button
          disabled={!canApprove}
          onClick={handleApprove}
          className="ml-auto px-4 py-1.5 rounded text-xs font-bold text-white transition disabled:opacity-40"
          style={{ background: canApprove ? "var(--teal)" : "var(--muted)" }}
        >
          Approve Project
        </button>
      </div>

      {/* Findings table */}
      <div className="rounded border border-[var(--border)] overflow-hidden" style={{ background: "var(--surface)" }}>
        <div className="px-4 py-2 border-b border-[var(--border)] text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--muted)" }}>
          Findings &middot; {findings.length}
        </div>
        {findings.length === 0 ? (
          <p className="text-center py-6 text-xs italic" style={{ color: "var(--muted)" }}>No findings — this project is clean.</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)]" style={{ background: "var(--raised)" }}>
                <th className="text-left px-4 py-2 font-semibold">Field</th>
                <th className="text-center px-2 py-2 font-semibold">Status</th>
                <th className="text-center px-2 py-2 font-semibold">Bible</th>
                <th className="text-center px-2 py-2 font-semibold">Model</th>
                <th className="text-center px-2 py-2 font-semibold">Impact</th>
                <th className="text-center px-2 py-2 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f, fi) => {
                const act = getAction(f.field);
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
                    <td className="text-center px-2 py-2 tabular-nums">{f.impact != null ? `$${(f.impact / 1000).toFixed(0)}k` : "—"}</td>
                    <td className="text-center px-2 py-2">
                      <div className="flex gap-1 justify-center">
                        {(["accept", "flag", "skip"] as const).map((a) => (
                          <button
                            key={a}
                            onClick={() => setAction(f.field, a)}
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

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded border border-[var(--border)] p-3" style={{ background: "var(--surface)" }}>
          <div className="text-[10px] font-bold uppercase tracking-[0.08em] mb-1" style={{ color: "var(--muted)" }}>Variance</div>
          <VarianceChart {...project.variance} />
        </div>
        <div className="rounded border border-[var(--border)] p-3" style={{ background: "var(--surface)" }}>
          <div className="text-[10px] font-bold uppercase tracking-[0.08em] mb-1" style={{ color: "var(--muted)" }}>Capital Stack</div>
          <CapitalStackChart model={project.stack.model} bible={project.stack.bible} />
        </div>
        <div className="rounded border border-[var(--border)] p-3" style={{ background: "var(--surface)" }}>
          <div className="text-[10px] font-bold uppercase tracking-[0.08em] mb-1" style={{ color: "var(--muted)" }}>25-Year Cash Flow</div>
          <CashflowChart opCF={project.cashflow.opCF} taxBn={project.cashflow.taxBn} terminal={project.cashflow.terminal} />
        </div>
        <div className="rounded border border-[var(--border)] p-3" style={{ background: "var(--surface)" }}>
          <div className="text-[10px] font-bold uppercase tracking-[0.08em] mb-1" style={{ color: "var(--muted)" }}>Sensitivity Tornado</div>
          <TornadoChart labels={project.tornado.labels} lo={project.tornado.lo} hi={project.tornado.hi} />
        </div>
      </div>
    </div>
  );
}
