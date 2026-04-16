"use client";

import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { HeatmapChart } from "@/components/charts/HeatmapChart";
import { fmtEquity } from "@/lib/format";

export function PortfolioView() {
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const portfolio = usePortfolioStore((s) => s.portfolio);
  const model1 = usePortfolioStore((s) => s.model1);
  const model2 = usePortfolioStore((s) => s.model2);
  const pendingExclusions = usePortfolioStore((s) => s.pendingExclusions);
  const confirmedExclusions = usePortfolioStore((s) => s.confirmedExclusions);
  const togglePending = usePortfolioStore((s) => s.togglePending);
  const confirmPortfolio = usePortfolioStore((s) => s.confirmPortfolio);

  // Compute pending changes reactively (not via store get() which isn't reactive)
  const hasPending = (() => {
    const pKeys = Object.keys(pendingExclusions);
    const cKeys = Object.keys(confirmedExclusions);
    if (pKeys.length !== cKeys.length) return true;
    return pKeys.some((k) => !confirmedExclusions[Number(k)]);
  })();
  const setMode = useUiStore((s) => s.setMode);
  const setSelected = useUiStore((s) => s.setSelectedProject);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const activeModelTab = useUiStore((s) => s.activeModelTab);
  const setActiveModelTab = useUiStore((s) => s.setActiveModelTab);
  const hasTwoModels = !!(model1 && model2);

  if (!reviewProjects.length) {
    return <p className="text-center py-12 italic text-[11px]" style={{ color: "var(--muted)" }}>No projects loaded.</p>;
  }

  // Sort by project number (row 2) for natural portfolio ordering
  const ranked = reviewProjects
    .map((p, i) => ({ p, i }))
    .sort((a, b) => (a.p.projNumber ?? 999) - (b.p.projNumber ?? 999));

  const fmtMoney = (k: number) => {
    const abs = Math.abs(k * 1000);
    const s = abs >= 1e6 ? `$${(abs / 1e6).toFixed(2)}M` : abs >= 1e3 ? `$${(abs / 1e3).toFixed(0)}k` : `$${abs.toFixed(0)}`;
    return k < 0 ? `(${s})` : s;
  };

  return (
    <div className="space-y-3">
      <div className="rounded border border-[var(--border)] overflow-hidden" style={{ background: "var(--surface)" }}>
        {/* Model tabs for portfolio */}
        {hasTwoModels && (
          <div className="flex border-b border-[var(--border)]">
            {[
              { tab: 1 as const, label: model1!.label, count: model1!.projects.length },
              { tab: 2 as const, label: model2!.label, count: model2!.projects.length },
            ].map(({ tab, label, count }) => (
              <button
                key={tab}
                onClick={() => setActiveModelTab(tab)}
                className={`flex-1 px-3 py-2 text-[11px] font-semibold border-b-2 transition cursor-pointer ${
                  activeModelTab === tab
                    ? "border-[var(--teal)] text-[var(--teal)] bg-[var(--surface)]"
                    : "border-transparent text-[var(--muted)] hover:text-[var(--text-2)]"
                }`}
              >
                {label} <span className="text-[9px] font-normal ml-1">({count})</span>
              </button>
            ))}
          </div>
        )}
        <div className="px-4 py-1.5 border-b border-[var(--border)] flex justify-between items-center">
          <span className="text-[9px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--muted)" }}>
            Portfolio Summary &middot; {ranked.length} projects
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs min-w-[720px]">
            <thead>
              <tr className="border-b border-[var(--border)]" style={{ background: "var(--raised)" }}>
                <th className="w-10 px-2 py-2"></th>
                <th className="text-left px-4 py-2 font-semibold">Project</th>
                <th className="text-left px-2 py-2 font-semibold">Developer</th>
                <th className="text-left px-2 py-2 font-semibold">State &middot; Program</th>
                <th className="text-center px-2 py-2 font-semibold">MWdc</th>
                <th className="text-center px-2 py-2 font-semibold">Verdict</th>
                <th className="text-center px-2 py-2 font-semibold">Equity &Delta;</th>
                <th className="text-center px-2 py-2 font-semibold">Issues</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {ranked.map(({ p, i }, rank) => {
                const pendingIncluded = !pendingExclusions[i];
                const confirmedIncluded = !confirmedExclusions[i];
                const nFail = p.findings?.filter((f) => f.status === "OFF").length || 0;
                const nFlag = p.findings?.filter((f) => f.status === "OUT").length || 0;
                const changed = pendingIncluded !== confirmedIncluded;
                return (
                  <tr
                    key={i}
                    className="border-b border-[var(--border)] hover:bg-[var(--inset)] transition"
                    style={{ opacity: pendingIncluded ? 1 : 0.45 }}
                  >
                    <td className="text-center px-2 py-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={pendingIncluded}
                        onChange={() => togglePending(i)}
                        onClick={(e) => e.stopPropagation()}
                        className={`accent-[var(--teal)] cursor-pointer ${changed ? "ring-2 ring-[var(--rev)]" : ""}`}
                      />
                    </td>
                    <td className="px-4 py-2 font-semibold">
                      <span className="text-[9px] font-bold mr-1" style={{ color: "var(--muted)" }}>#{rank + 1}</span>
                      {p.projNumber != null && <span className="text-[9px] bg-[var(--teal)] text-white px-1 rounded mr-1">P{p.projNumber}</span>}
                      {p.name}
                    </td>
                    <td className="px-2 py-2">{p.developer || "—"}</td>
                    <td className="px-2 py-2">{[p.state, p.program].filter(Boolean).join(" · ") || "—"}</td>
                    <td className="text-center px-2 py-2 tabular-nums">{p.kpis?.dc || "—"}</td>
                    <td className="text-center px-2 py-2">
                      {(() => {
                        const severity = Math.min(1, (nFail * 2 + nFlag) / 10);
                        const bg = p.verdict === "CLEAN" ? "var(--ok)"
                          : p.verdict === "REVIEW" ? `rgba(29,111,169,${0.2 + severity * 0.8})`
                          : `rgba(184,50,48,${0.2 + severity * 0.8})`;
                        return (
                          <span className="text-[10px] px-2 py-0.5 rounded font-semibold text-white" style={{ background: bg }}>
                            {p.verdict === "REWORK REQUIRED" ? "REWORK" : p.verdict}
                          </span>
                        );
                      })()}
                    </td>
                    <td className={`text-center px-2 py-2 tabular-nums font-semibold ${(p.equityK || 0) < 0 ? "text-[var(--off)]" : ""}`}>
                      {fmtMoney(p.equityK || 0)}
                    </td>
                    <td className="text-center px-2 py-2">
                      {nFail + nFlag > 0 ? (
                        <span className="font-bold">{nFail + nFlag}</span>
                      ) : (
                        <span style={{ color: "var(--muted)" }}>0</span>
                      )}
                    </td>
                    <td className="text-center px-2 py-2">
                      {confirmedIncluded && (
                        <button
                          onClick={() => { setSelected(i); setMode("project"); }}
                          className="text-[var(--muted)] hover:text-[var(--teal)] transition cursor-pointer text-sm"
                          title="Open in Project Review"
                        >
                          →
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-[var(--border-strong)] font-bold text-xs" style={{ background: "var(--raised)" }}>
                <td className="px-2 py-2"></td>
                <td className="px-4 py-2">Portfolio Total</td>
                <td className="px-2 py-2"></td>
                <td className="px-2 py-2"></td>
                <td className="text-center px-2 py-2 tabular-nums">
                  {ranked.reduce((s, { p }) => s + parseFloat(String(p.kpis?.dc || 0)), 0).toFixed(1)}
                </td>
                <td className="text-center px-2 py-2">
                  {ranked.filter(({ p }) => p.verdict !== "CLEAN").length} issues
                </td>
                <td className="text-center px-2 py-2 tabular-nums">
                  {fmtEquity(ranked.reduce((s, { p }) => s + (p.equityK || 0), 0))}
                </td>
                <td className="text-center px-2 py-2">
                  {ranked.reduce((s, { p }) => s + (p.findings?.filter(f => f.status === "OFF").length || 0) + (p.findings?.filter(f => f.status === "OUT").length || 0), 0)}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>

        {/* Set Portfolio confirmation bar */}
        <div className="px-4 py-2.5 border-t border-[var(--border)] flex items-center justify-between" style={{ background: "var(--raised)" }}>
          <span className="text-[10px] tabular-nums" style={{ color: "var(--muted)" }}>
            {ranked.filter(({ i }) => !pendingExclusions[i]).length} selected
            {hasPending && (
              <span className="ml-1 text-[var(--rev)] font-semibold">
                (pending changes)
              </span>
            )}
          </span>
          <button
            onClick={confirmPortfolio}
            disabled={!hasPending}
            className={`px-4 py-1.5 rounded text-[11px] font-bold transition cursor-pointer ${
              hasPending
                ? "bg-[var(--teal)] text-white hover:opacity-90"
                : "bg-[var(--inset)] text-[var(--muted)] cursor-not-allowed"
            }`}
          >
            Set Portfolio
          </button>
        </div>
      </div>

      {portfolio?.heatmap && (
        <div className="rounded border border-[var(--border)] p-4" style={{ background: "var(--surface)" }}>
          <div className="text-[10px] font-bold uppercase tracking-[0.08em] mb-2" style={{ color: "var(--muted)" }}>
            Audit Heatmap
          </div>
          <HeatmapChart
            projects={portfolio.heatmap.projects}
            fields={portfolio.heatmap.fields}
            z={portfolio.heatmap.z}
            highlightProject={reviewProjects[selectedIdx]?.name}
          />
        </div>
      )}
    </div>
  );
}
