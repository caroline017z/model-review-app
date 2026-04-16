"use client";

import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { HeatmapChart } from "@/components/charts/HeatmapChart";

export function PortfolioView() {
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const portfolio = usePortfolioStore((s) => s.portfolio);
  const excludedIds = usePortfolioStore((s) => s.excludedIds);
  const toggleExcluded = usePortfolioStore((s) => s.toggleExcluded);
  const setMode = useUiStore((s) => s.setMode);
  const setSelected = useUiStore((s) => s.setSelectedProject);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);

  if (!reviewProjects.length) {
    return <p className="text-center py-12 italic" style={{ color: "var(--muted)" }}>No projects loaded.</p>;
  }

  const ranked = reviewProjects
    .map((p, i) => ({ p, i }))
    .sort((a, b) => Math.abs(b.p.equityK || 0) - Math.abs(a.p.equityK || 0));

  const fmtMoney = (k: number) => {
    const abs = Math.abs(k * 1000);
    const s = abs >= 1e6 ? `$${(abs / 1e6).toFixed(2)}M` : abs >= 1e3 ? `$${(abs / 1e3).toFixed(0)}k` : `$${abs.toFixed(0)}`;
    return k < 0 ? `(${s})` : s;
  };

  return (
    <div className="space-y-4">
      <div className="rounded border border-[var(--border)] overflow-hidden" style={{ background: "var(--surface)" }}>
        <div className="px-4 py-2 border-b border-[var(--border)] flex justify-between items-center">
          <span className="text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--muted)" }}>
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
                const included = !excludedIds.has(i);
                const nFail = p.findings?.filter((f) => f.status === "OFF").length || 0;
                const nFlag = p.findings?.filter((f) => f.status === "OUT").length || 0;
                return (
                  <tr
                    key={i}
                    className="border-b border-[var(--border)] hover:bg-[var(--inset)] cursor-pointer transition"
                    style={{ opacity: included ? 1 : 0.45 }}
                    onClick={() => { if (included) { setSelected(i); setMode("project"); } }}
                  >
                    <td className="text-center px-2 py-2">
                      <input
                        type="checkbox"
                        checked={included}
                        onChange={(e) => { e.stopPropagation(); toggleExcluded(i); }}
                        className="accent-[var(--teal)]"
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
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold text-white ${
                        p.verdict === "CLEAN" ? "bg-[var(--ok)]"
                        : p.verdict === "REVIEW" ? "bg-[var(--rev)]"
                        : "bg-[var(--off)]"
                      }`}>
                        {p.verdict}
                      </span>
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
                    <td className="text-center px-2 py-2" style={{ color: "var(--muted)" }}>
                      {included ? "→" : ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
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
