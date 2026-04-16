"use client";

import { useCallback, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { uploadModel, runReview } from "@/lib/api";

function UploadPanel() {
  const setModel1 = usePortfolioStore((s) => s.setModel1);
  const setModel2 = usePortfolioStore((s) => s.setModel2);
  const model1 = usePortfolioStore((s) => s.model1);
  const model2 = usePortfolioStore((s) => s.model2);
  const setReviewData = usePortfolioStore((s) => s.setReviewData);
  const fileRef1 = useRef<HTMLInputElement>(null);
  const fileRef2 = useRef<HTMLInputElement>(null);

  const uploadMut = useMutation({ mutationFn: uploadModel });

  const reviewMut = useMutation({
    mutationFn: ({ modelId, label }: { modelId: string; label: string }) =>
      runReview(modelId, undefined, label),
    onSuccess: (data) => setReviewData(data),
  });

  const handleUpload = useCallback(
    async (file: File, slot: 1 | 2) => {
      const data = await uploadMut.mutateAsync(file);
      const label = guessLabel(file.name);
      if (slot === 1) {
        setModel1(data, label);
        reviewMut.mutate({ modelId: data.model_id, label });
      } else {
        setModel2(data, label);
      }
    },
    [setModel1, setModel2, uploadMut, reviewMut],
  );

  return (
    <div className="flex flex-col items-center justify-center h-screen gap-8 max-w-lg mx-auto px-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-[0.04em]" style={{ color: "var(--navy)" }}>
          38<span style={{ color: "var(--teal)" }}>&deg;</span>N Pricing Model Review
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          Upload a pricing model to begin validation.
        </p>
      </div>

      <div className="w-full space-y-4">
        <div
          onClick={() => fileRef1.current?.click()}
          className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition"
          style={{ borderColor: "rgba(81,132,132,0.3)" }}
          onMouseOver={(e) => (e.currentTarget.style.borderColor = "rgba(81,132,132,0.6)")}
          onMouseOut={(e) => (e.currentTarget.style.borderColor = "rgba(81,132,132,0.3)")}
        >
          <input
            ref={fileRef1}
            type="file"
            accept=".xlsm,.xlsx"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0], 1)}
          />
          {model1 ? (
            <div>
              <span className="font-semibold" style={{ color: "var(--teal)" }}>{model1.label}</span>
              <span className="text-xs ml-2" style={{ color: "var(--muted)" }}>
                {model1.projects.length} projects
              </span>
            </div>
          ) : (
            <div>
              <p className="font-semibold" style={{ color: "var(--navy)" }}>Model 1 (Primary)</p>
              <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
                Drop .xlsm / .xlsx or click to browse
              </p>
            </div>
          )}
        </div>

        <div
          onClick={() => fileRef2.current?.click()}
          className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition"
          style={{ borderColor: "rgba(33,43,72,0.2)" }}
        >
          <input
            ref={fileRef2}
            type="file"
            accept=".xlsm,.xlsx"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0], 2)}
          />
          {model2 ? (
            <span className="font-semibold" style={{ color: "var(--indigo)" }}>{model2.label}</span>
          ) : (
            <p className="font-semibold" style={{ color: "rgba(33,43,72,0.6)" }}>
              Model 2 (Comparison — optional)
            </p>
          )}
        </div>
      </div>

      {(uploadMut.isPending || reviewMut.isPending) && (
        <p className="text-sm animate-pulse" style={{ color: "var(--teal)" }}>Processing model...</p>
      )}
      {uploadMut.isError && (
        <p className="text-sm" style={{ color: "var(--off)" }}>
          Upload failed: {uploadMut.error?.message}
        </p>
      )}
    </div>
  );
}

function ReviewContent() {
  const mode = useUiStore((s) => s.mode);
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const project = reviewProjects[selectedIdx];

  if (mode === "walk") {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-md bg-[var(--surface)] rounded-lg border border-[var(--border)] p-8">
          <h2 className="text-lg font-bold mb-2" style={{ color: "var(--navy)" }}>Build Walk</h2>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Download the Walk Summary .xlsx using the button below.
          </p>
        </div>
      </div>
    );
  }

  if (mode === "portfolio") {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-bold" style={{ color: "var(--navy)" }}>Portfolio Summary</h2>
        <p className="text-sm italic" style={{ color: "var(--muted)" }}>
          Portfolio table and heatmap — Phase 3.
        </p>
      </div>
    );
  }

  if (mode === "reference") {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-bold" style={{ color: "var(--navy)" }}>Reference</h2>
        <p className="text-sm italic" style={{ color: "var(--muted)" }}>
          Bible &amp; market reference — Phase 3.
        </p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="italic" style={{ color: "var(--muted)" }}>Select a project from the navigator.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg p-4 text-white" style={{ background: "var(--navy)" }}>
        <h2 className="text-lg font-bold">{project.name}</h2>
        <p className="text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>{project.sub}</p>
        <div className="flex gap-6 mt-3 text-sm">
          <div>
            <span className="text-xs uppercase" style={{ color: "rgba(255,255,255,0.5)" }}>IRR</span>
            <p className="font-bold">{project.irrPct.toFixed(2)}%</p>
          </div>
          <div>
            <span className="text-xs uppercase" style={{ color: "rgba(255,255,255,0.5)" }}>NPP</span>
            <p className="font-bold">${project.nppPerW.toFixed(2)}/W</p>
          </div>
          <div>
            <span className="text-xs uppercase" style={{ color: "rgba(255,255,255,0.5)" }}>Equity</span>
            <p className="font-bold">${project.equityK}k</p>
          </div>
          <div className="ml-auto">
            <span className={`px-3 py-1 rounded text-xs font-bold text-white ${
              project.verdict === "CLEAN" ? "bg-[var(--ok)]"
              : project.verdict === "REVIEW" ? "bg-[var(--rev)]"
              : "bg-[var(--off)]"
            }`}>
              {project.verdict}
            </span>
          </div>
        </div>
      </div>

      <div className="rounded border border-[var(--border)] overflow-hidden" style={{ background: "var(--surface)" }}>
        <div className="px-4 py-2 border-b border-[var(--border)] text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--muted)" }}>
          Findings &middot; {project.findings.length}
        </div>
        {project.findings.length === 0 ? (
          <p className="text-center py-6 text-xs italic" style={{ color: "var(--muted)" }}>
            No findings — this project is clean.
          </p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)]" style={{ background: "var(--raised)" }}>
                <th className="text-left px-4 py-2 font-semibold">Field</th>
                <th className="text-center px-2 py-2 font-semibold">Status</th>
                <th className="text-center px-2 py-2 font-semibold">Bible</th>
                <th className="text-center px-2 py-2 font-semibold">Model</th>
                <th className="text-center px-2 py-2 font-semibold">Impact</th>
              </tr>
            </thead>
            <tbody>
              {project.findings.map((f, i) => (
                <tr key={i} className="border-b border-[var(--border)]">
                  <td className="px-4 py-2 font-semibold">{f.field}</td>
                  <td className="text-center px-2 py-2">
                    <span className={`text-[10px] px-[6px] py-px rounded font-bold ${
                      f.status === "OFF" ? "bg-[var(--off-bg)] text-[var(--off)]"
                      : f.status === "OUT" ? "bg-[var(--out-bg)] text-[var(--out)]"
                      : f.status === "REVIEW" ? "bg-[var(--rev-bg)] text-[var(--rev)]"
                      : "bg-[var(--miss-bg)] text-[var(--miss)]"
                    }`}>
                      {f.status === "OFF" ? "FAIL" : f.status === "OUT" ? "FLAG" : f.status}
                    </span>
                  </td>
                  <td className="text-center px-2 py-2 tabular-nums">{f.bible}</td>
                  <td className="text-center px-2 py-2 tabular-nums">{f.model}</td>
                  <td className="text-center px-2 py-2 tabular-nums">
                    {f.impact != null ? `$${(f.impact / 1000).toFixed(0)}k` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default function Home() {
  const portfolio = usePortfolioStore((s) => s.portfolio);
  return portfolio ? (
    <AppShell><ReviewContent /></AppShell>
  ) : (
    <UploadPanel />
  );
}

function guessLabel(filename: string): string {
  let name = filename.replace(/\.(xlsm|xlsx|xls)$/i, "");
  name = name.replace(/^38DN[\s_-]*/i, "");
  name = name.replace(/[\s_-]*(Pricing[\s_]*Model|Walk[\s_]*Summary).*$/i, "");
  name = name.replace(/[\s_-]*\d{4}[._-]\d{2}[._-]\d{2}\s*$/, "");
  return name.replace(/_/g, " ").replace(/\s+/g, " ").trim().replace(/^[-\s]+|[-\s]+$/g, "") || "Model";
}
