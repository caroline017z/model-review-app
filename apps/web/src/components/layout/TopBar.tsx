"use client";

import { useEffect, useState } from "react";
import { useUiStore, type ViewMode } from "@/stores/ui";
import { usePortfolioStore, useActiveReviewProjects, useActivePortfolio } from "@/stores/portfolio";
import { useReviewerStore } from "@/stores/reviewer";
import { useBibleStore } from "@/stores/bible";
import { exportReview, runReview } from "@/lib/api";
import { BibleManager } from "@/components/bible/BibleManager";

const modes: { key: ViewMode; label: string; requiresTwo?: boolean }[] = [
  { key: "portfolio", label: "Portfolio" },
  { key: "project", label: "Project Review" },
  { key: "reference", label: "Reference" },
  { key: "walk", label: "Build Walk", requiresTwo: true },
];

export function TopBar() {
  const mode = useUiStore((s) => s.mode);
  const setMode = useUiStore((s) => s.setMode);
  const portfolio = useActivePortfolio();
  const model1 = usePortfolioStore((s) => s.model1);
  const model2 = usePortfolioStore((s) => s.model2);
  const setReviewData = usePortfolioStore((s) => s.setReviewData);
  const clearReviewer = useReviewerStore((s) => s.clearAll);
  const reviewProjects = useActiveReviewProjects();
  const approvals = useReviewerStore((s) => s.approvals);
  const actions = useReviewerStore((s) => s.actions);
  const refreshBibles = useBibleStore((s) => s.refresh);
  const activeBible = useBibleStore((s) => s.activeVintage());
  const [exporting, setExporting] = useState(false);
  const [bibleOpen, setBibleOpen] = useState(false);
  const [rerunning, setRerunning] = useState(false);

  useEffect(() => {
    refreshBibles();
  }, [refreshBibles]);

  // After switching the active vintage, re-run the audit for both loaded
  // models so either tab reflects the new Bible findings without reload.
  const handleBibleActivated = async () => {
    setBibleOpen(false);
    if (!model1) return;
    setRerunning(true);
    try {
      const ids1 = model1.projects.map((p) => p.id);
      const data1 = await runReview(model1.modelId, ids1, model1.label);
      setReviewData(data1, 1);
      if (model2) {
        const ids2 = model2.projects.map((p) => p.id);
        const data2 = await runReview(model2.modelId, ids2, model2.label);
        setReviewData(data2, 2);
      }
    } catch (e) {
      console.error("Re-audit after bible switch failed:", e);
    } finally {
      setRerunning(false);
    }
  };

  const handleExport = async () => {
    if (!portfolio || !reviewProjects.length) return;
    setExporting(true);
    try {
      const projects = reviewProjects.map((p, i) => {
        const projActions = actions[i] || {};
        const approval = approvals[i];
        return {
          name: p.name,
          verdict: p.verdict,
          nppPerW: p.nppPerW,
          irrPct: p.irrPct,
          equityK: p.equityK,
          approved: !!approval?.approved,
          approvalTimestamp: approval?.timestamp || null,
          approvalReviewer: approval?.reviewer || null,
          projectNote: projActions["__project_note__"]?.note || null,
          findings: (p.findings || []).map((f) => ({
            field: f.field,
            status: f.status,
            bible: f.bible,
            model: f.model,
            impact: f.impact,
            action: projActions[f.field]?.action || null,
            note: projActions[f.field]?.note || null,
          })),
        };
      });
      const blob = await exportReview({
        model_label: portfolio.modelName,
        reviewer: portfolio.reviewer,
        bible_label: portfolio.bibleLabel,
        projects,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Review_Summary_${portfolio.modelName}.xlsx`.replace(/ /g, "_");
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Export failed:", e);
    } finally {
      setExporting(false);
    }
  };

  const handleReset = () => {
    // Reset all stores to initial state
    usePortfolioStore.setState({
      model1: null, model2: null,
      reviewProjects1: [], reviewProjects2: [],
      portfolio1: null, portfolio2: null,
      selectedIds: {},
      excludedIds1: {}, excludedIds2: {},
      pendingExclusions1: {}, pendingExclusions2: {},
      confirmedExclusions1: {}, confirmedExclusions2: {},
    });
    useUiStore.setState({ mode: "project", selectedProjectIdx: 0, navSearch: "", navFilter: "all", activeModelTab: 1 });
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
            <button
              onClick={() => setBibleOpen(true)}
              className="hover:bg-white/[0.08] rounded px-1 py-0.5 transition cursor-pointer"
              title="Switch or upload Pricing Bible vintage"
            >
              Bible: <b className="text-white/90 font-semibold underline decoration-dotted">{activeBible?.label ?? portfolio.bibleLabel}</b>
              {rerunning && <span className="ml-1 text-[9px] italic">(re-auditing...)</span>}
            </button>
            <span>Reviewer: <b className="text-white/90 font-semibold">{portfolio.reviewer}</b></span>
            <button
              onClick={handleExport}
              disabled={exporting}
              className="px-2 py-1 rounded text-[10px] font-semibold border border-[var(--teal)] bg-[var(--teal)] text-white hover:bg-[var(--teal-deep)] transition cursor-pointer disabled:opacity-50"
            >
              {exporting ? "Exporting..." : "Export Review"}
            </button>
            <button
              onClick={handleReset}
              className="px-2 py-1 rounded text-[10px] font-semibold border border-white/20 text-white/70 hover:text-white hover:border-white/40 transition cursor-pointer"
            >
              New Review
            </button>
          </>
        )}
      </div>

      {/* Bible vintage manager modal */}
      {bibleOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setBibleOpen(false)}
        >
          <div
            className="bg-[var(--bg)] rounded-lg shadow-xl max-h-[80vh] overflow-y-auto"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <BibleManager variant="modal" onActivate={handleBibleActivated} />
          </div>
        </div>
      )}
    </header>
  );
}
