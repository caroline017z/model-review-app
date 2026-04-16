"use client";

import { useCallback, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { useReviewerStore } from "@/stores/reviewer";
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
  const setModelScope = useReviewerStore((s) => s.setModelScope);
  const fileRef1 = useRef<HTMLInputElement>(null);
  const fileRef2 = useRef<HTMLInputElement>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [m1Loading, setM1Loading] = useState(false);
  const [m2Loading, setM2Loading] = useState(false);
  const [m1Status, setM1Status] = useState("");
  const [m2Status, setM2Status] = useState("");

  const uploadMut = useMutation({ mutationFn: uploadModel });

  const reviewMut = useMutation({
    mutationFn: ({ modelId, label }: { modelId: string; label: string }) =>
      runReview(modelId, undefined, label),
    onSuccess: (data) => setReviewData(data),
    onError: (err) => setReviewError(err instanceof Error ? err.message : "Review failed"),
  });

  const handleUpload = useCallback(
    async (file: File, slot: 1 | 2) => {
      setReviewError(null);
      const setLoading = slot === 1 ? setM1Loading : setM2Loading;
      const setStatus = slot === 1 ? setM1Status : setM2Status;
      setLoading(true);
      setStatus("Uploading...");
      try {
        const data = await uploadMut.mutateAsync(file);
        const label = guessLabel(file.name);
        if (slot === 1) {
          setStatus("Running audit...");
          setModel1(data, label);
          setModelScope(data.model_id);
          reviewMut.mutate({ modelId: data.model_id, label });
        } else {
          setModel2(data, label);
          setStatus("");
          setLoading(false);
        }
      } catch {
        setStatus("Failed");
        setLoading(false);
      }
    },
    [setModel1, setModel2, setModelScope, uploadMut, reviewMut],
  );

  return (
    <div className="flex flex-col items-center justify-center h-screen gap-6 max-w-md mx-auto px-6">
      <div className="text-center">
        <h1 className="text-lg font-bold tracking-[0.06em] uppercase" style={{ color: "var(--navy)" }}>
          38<span style={{ color: "var(--teal)" }}>&deg;</span>N &middot; Pricing Model Review
        </h1>
        <p className="text-[11px] mt-1" style={{ color: "var(--muted)" }}>
          Upload a pricing model to begin validation
        </p>
      </div>

      <div className="w-full space-y-3">
        {/* Model 1 */}
        <div className="flex items-center gap-3">
          <div
            onClick={() => !m1Loading && fileRef1.current?.click()}
            className={`flex-1 border rounded p-4 text-center cursor-pointer transition ${m1Loading ? "opacity-60 pointer-events-none" : "hover:border-[var(--teal)]"}`}
            style={{ borderColor: model1 ? "var(--teal)" : "var(--border)" }}
            role="button" tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && fileRef1.current?.click()}
          >
            <input ref={fileRef1} type="file" accept=".xlsm,.xlsx" className="hidden"
              onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0], 1)} />
            {model1 ? (
              <div className="text-[12px]">
                <span className="font-semibold" style={{ color: "var(--teal)" }}>{model1.label}</span>
                <span className="text-[10px] ml-2" style={{ color: "var(--muted)" }}>{model1.projects.length} projects</span>
              </div>
            ) : (
              <div>
                <p className="text-[12px] font-semibold" style={{ color: "var(--navy)" }}>Model 1 (Primary)</p>
                <p className="text-[10px]" style={{ color: "var(--muted)" }}>.xlsm / .xlsx</p>
              </div>
            )}
          </div>
          {m1Loading && (
            <div className="text-[10px] w-24 shrink-0" style={{ color: "var(--teal)" }}>
              <div className="animate-pulse font-semibold">{m1Status}</div>
              <div className="mt-1 h-1 rounded-full overflow-hidden" style={{ background: "var(--inset)" }}>
                <div className="h-full rounded-full animate-pulse" style={{ background: "var(--teal)", width: m1Status === "Running audit..." ? "70%" : "30%" }} />
              </div>
            </div>
          )}
          {model1 && !m1Loading && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: "var(--ok-bg)", color: "var(--ok)" }}>READY</span>
          )}
        </div>

        {/* Model 2 */}
        <div className="flex items-center gap-3">
          <div
            onClick={() => !m2Loading && fileRef2.current?.click()}
            className={`flex-1 border rounded p-3 text-center cursor-pointer transition ${m2Loading ? "opacity-60 pointer-events-none" : "hover:border-[var(--indigo)]"}`}
            style={{ borderColor: model2 ? "var(--indigo)" : "var(--border)" }}
            role="button" tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && fileRef2.current?.click()}
          >
            <input ref={fileRef2} type="file" accept=".xlsm,.xlsx" className="hidden"
              onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0], 2)} />
            {model2 ? (
              <span className="text-[12px] font-semibold" style={{ color: "var(--indigo)" }}>{model2.label}</span>
            ) : (
              <p className="text-[11px] font-semibold" style={{ color: "rgba(33,43,72,0.5)" }}>
                Model 2 (Comparison — optional)
              </p>
            )}
          </div>
          {m2Loading && (
            <div className="text-[10px] w-24 shrink-0 animate-pulse font-semibold" style={{ color: "var(--indigo)" }}>{m2Status}</div>
          )}
          {model2 && !m2Loading && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: "var(--ok-bg)", color: "var(--ok)" }}>READY</span>
          )}
        </div>
      </div>

      {(uploadMut.isError || reviewError) && (
        <p className="text-[11px]" style={{ color: "var(--off)" }}>
          {uploadMut.isError ? `Upload failed: ${uploadMut.error?.message}` : `Review failed: ${reviewError}`}
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
