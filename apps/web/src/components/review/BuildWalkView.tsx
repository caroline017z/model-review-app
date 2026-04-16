"use client";

import { useState } from "react";
import { usePortfolioStore } from "@/stores/portfolio";
import { downloadWalk } from "@/lib/api";

export function BuildWalkView() {
  const model1 = usePortfolioStore((s) => s.model1);
  const model2 = usePortfolioStore((s) => s.model2);
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const confirmedExclusions = usePortfolioStore((s) => s.confirmedExclusions);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!model1 || !model2) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-md rounded-lg border border-[var(--border)] p-8" style={{ background: "var(--surface)" }}>
          <h2 className="text-lg font-bold mb-2" style={{ color: "var(--navy)" }}>Build Walk</h2>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Upload two models to generate a Walk Summary comparing NPP, IRR, and input drivers.
          </p>
        </div>
      </div>
    );
  }

  const handleDownload = async () => {
    setLoading(true);
    setError(null);
    try {
      // Derive included project numbers from confirmed portfolio selection
      const includedProjNumbers = reviewProjects
        .filter((_, i) => !confirmedExclusions[i])
        .map((p) => p.projNumber)
        .filter((n): n is number => n != null);

      const blob = await downloadWalk(
        model1.modelId, model2.modelId, model1.label, model2.label,
        includedProjNumbers.length > 0 ? includedProjNumbers : undefined,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Build_Walk_${model1.label}_vs_${model2.label}.xlsx`.replace(/ /g, "_");
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center max-w-md rounded-lg border border-[var(--border)] p-8" style={{ background: "var(--surface)" }}>
        <h2 className="text-lg font-bold mb-3" style={{ color: "var(--navy)" }}>Build Walk</h2>
        <p className="text-sm mb-1" style={{ color: "var(--text-2)" }}>
          Comparing <b style={{ color: "var(--teal)" }}>{model1.label}</b> vs{" "}
          <b style={{ color: "var(--teal)" }}>{model2.label}</b>
        </p>
        <p className="text-xs mb-6" style={{ color: "var(--muted)" }}>
          {model1.projects.length} projects in Model 1 &middot; {model2.projects.length} in Model 2
        </p>

        <button
          onClick={handleDownload}
          disabled={loading}
          className="px-6 py-2.5 rounded font-bold text-white text-sm transition disabled:opacity-50"
          style={{ background: "var(--teal)" }}
        >
          {loading ? "Generating..." : "Download Walk Summary (.xlsx)"}
        </button>

        {error && (
          <p className="text-xs mt-3" style={{ color: "var(--off)" }}>{error}</p>
        )}
      </div>
    </div>
  );
}
