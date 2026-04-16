"use client";

import { useCallback, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { uploadModel, runReview } from "@/lib/api";
import { ProjectReviewView } from "@/components/review/ProjectReviewView";
import { PortfolioView } from "@/components/review/PortfolioView";
import { BuildWalkView } from "@/components/review/BuildWalkView";
import { ReferencePanel } from "@/components/review/ReferencePanel";

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

  if (mode === "walk") return <BuildWalkView />;
  if (mode === "portfolio") return <PortfolioView />;
  if (mode === "reference") return <ReferencePanel />;
  return <ProjectReviewView />;
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
