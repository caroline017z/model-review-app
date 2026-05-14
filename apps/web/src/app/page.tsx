"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { BibleManager } from "@/components/bible/BibleManager";
import { usePortfolioStore, useActivePortfolio } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";
import { useReviewerStore } from "@/stores/reviewer";
import { useBibleStore } from "@/stores/bible";
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
  const refreshBibles = useBibleStore((s) => s.refresh);
  const activeBible = useBibleStore((s) => s.activeVintage());
  const fileRef1 = useRef<HTMLInputElement>(null);
  const fileRef2 = useRef<HTMLInputElement>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [m1Loading, setM1Loading] = useState(false);
  const [m2Loading, setM2Loading] = useState(false);
  const [m1Status, setM1Status] = useState("");
  const [m2Status, setM2Status] = useState("");
  const [m1Label, setM1Label] = useState("");
  const [m2Label, setM2Label] = useState("");
  const [m1File, setM1File] = useState<string>("");
  const [m2File, setM2File] = useState<string>("");
  const [bibleExpanded, setBibleExpanded] = useState(false);

  useEffect(() => {
    refreshBibles();
  }, [refreshBibles]);

  const uploadMut = useMutation({ mutationFn: uploadModel });

  const handleUpload = useCallback(
    async (file: File, slot: 1 | 2) => {
      setReviewError(null);
      const setLoading = slot === 1 ? setM1Loading : setM2Loading;
      const setStatus = slot === 1 ? setM1Status : setM2Status;
      const otherFile = slot === 1 ? m2File : m1File;

      // Auto-generate label from filename (with MM.DD suffix if names collide)
      const autoLabel = guessLabel(file.name, otherFile || undefined);
      if (slot === 1) { setM1Label(autoLabel); setM1File(file.name); }
      else { setM2Label(autoLabel); setM2File(file.name); }

      // Also update the OTHER model's label if it was auto-generated and now
      // they share the same base name (need to add date suffix to both)
      if (otherFile) {
        const otherLabel = guessLabel(otherFile, file.name);
        if (slot === 1) setM2Label(otherLabel);
        else setM1Label(otherLabel);
      }

      setLoading(true);
      setStatus("Uploading...");
      try {
        const data = await uploadMut.mutateAsync(file);
        const label = slot === 1 ? m1Label || autoLabel : m2Label || autoLabel;
        if (slot === 1) {
          setModel1(data, label);
          setModelScope(data.model_id);
        } else {
          setModel2(data, label);
        }
        // Always run the audit for both slots so the portfolio tab can swap
        // between them without re-fetching.
        setStatus("Running audit...");
        const allIds = data.projects.map((p) => p.id);
        const review = await runReview(data.model_id, allIds, label);
        setReviewData(review, slot);
        setStatus("");
        setLoading(false);
      } catch (err) {
        setStatus("Failed");
        setLoading(false);
        setReviewError(err instanceof Error ? err.message : "Upload or audit failed");
      }
    },
    [setModel1, setModel2, setModelScope, setReviewData, uploadMut, m1File, m2File, m1Label, m2Label],
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
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--teal)" }}>Model 1</span>
            {model1 && !m1Loading && (
              <span className="text-[8px] font-bold px-1 py-px rounded" style={{ background: "var(--ok-bg)", color: "var(--ok)" }}>READY</span>
            )}
            {m1Loading && (
              <span className="text-[9px] font-semibold" style={{ color: "var(--teal)" }}>{m1Status}</span>
            )}
          </div>
          {m1Loading && (
            <div className="w-full h-[3px] rounded-full overflow-hidden mb-1" style={{ background: "var(--inset)" }}>
              <div
                className="h-full rounded-full transition-all duration-1000 ease-out"
                style={{
                  background: "var(--teal)",
                  width: m1Status === "Running audit..." ? "75%" : m1Status === "Uploading..." ? "30%" : "100%",
                }}
              />
            </div>
          )}
          <div className="flex items-center gap-2">
            <div
              onClick={() => !m1Loading && fileRef1.current?.click()}
              className={`flex-1 border rounded px-3 py-2 cursor-pointer transition text-[11px] ${m1Loading ? "opacity-60 pointer-events-none" : "hover:border-[var(--teal)]"}`}
              style={{ borderColor: model1 ? "var(--teal)" : "var(--border)" }}
              role="button" tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && fileRef1.current?.click()}
            >
              <input ref={fileRef1} type="file" accept=".xlsm,.xlsx" className="hidden"
                onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0], 1)} />
              {model1 ? (
                <span style={{ color: "var(--muted)" }}>{m1File || model1.filename} · {model1.projects.length} projects</span>
              ) : (
                <span style={{ color: "var(--muted)" }}>Click to upload .xlsm / .xlsx</span>
              )}
            </div>
          </div>
          {model1 && (
            <input
              type="text"
              value={m1Label}
              onChange={(e) => setM1Label(e.target.value)}
              className="mt-1 w-full px-2 py-1 border rounded text-[11px] font-semibold"
              style={{ borderColor: "var(--teal)", color: "var(--teal)" }}
              placeholder="Portfolio name..."
            />
          )}
        </div>

        {/* Model 2 */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--indigo)" }}>Model 2 (optional)</span>
            {model2 && !m2Loading && (
              <span className="text-[8px] font-bold px-1 py-px rounded" style={{ background: "var(--ok-bg)", color: "var(--ok)" }}>READY</span>
            )}
            {m2Loading && (
              <span className="text-[9px] font-semibold" style={{ color: "var(--indigo)" }}>{m2Status}</span>
            )}
          </div>
          {m2Loading && (
            <div className="w-full h-[3px] rounded-full overflow-hidden mb-1" style={{ background: "var(--inset)" }}>
              <div
                className="h-full rounded-full transition-all duration-1000 ease-out"
                style={{
                  background: "var(--indigo)",
                  width: m2Status === "Running audit..." ? "75%" : m2Status === "Uploading..." ? "30%" : "100%",
                }}
              />
            </div>
          )}
          <div
            onClick={() => !m2Loading && fileRef2.current?.click()}
            className={`border rounded px-3 py-2 cursor-pointer transition text-[11px] ${m2Loading ? "opacity-60 pointer-events-none" : "hover:border-[var(--indigo)]"}`}
            style={{ borderColor: model2 ? "var(--indigo)" : "var(--border)" }}
            role="button" tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && fileRef2.current?.click()}
          >
            <input ref={fileRef2} type="file" accept=".xlsm,.xlsx" className="hidden"
              onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0], 2)} />
            {model2 ? (
              <span style={{ color: "var(--muted)" }}>{m2File || model2.filename} · {model2.projects.length} projects</span>
            ) : (
              <span style={{ color: "rgba(33,43,72,0.4)" }}>Click to upload comparison model</span>
            )}
          </div>
          {model2 && (
            <input
              type="text"
              value={m2Label}
              onChange={(e) => setM2Label(e.target.value)}
              className="mt-1 w-full px-2 py-1 border rounded text-[11px] font-semibold"
              style={{ borderColor: "var(--indigo)", color: "var(--indigo)" }}
              placeholder="Portfolio name..."
            />
          )}
        </div>
      </div>

      {/* Bible vintage manager — collapsed by default; shows active label as teaser */}
      <div className="w-full border rounded" style={{ borderColor: "var(--border)" }}>
        <button
          type="button"
          onClick={() => setBibleExpanded((b) => !b)}
          className="w-full flex items-center justify-between px-3 py-2 text-[11px] hover:bg-[var(--inset)] transition cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--teal)" }}>
              Pricing Bible
            </span>
            <span style={{ color: "var(--muted)" }}>
              {activeBible ? activeBible.label : "Loading..."}
            </span>
          </span>
          <span style={{ color: "var(--muted)" }}>{bibleExpanded ? "−" : "+"}</span>
        </button>
        {bibleExpanded && (
          <div className="border-t px-3 py-3" style={{ borderColor: "var(--border)" }}>
            <BibleManager variant="panel" />
          </div>
        )}
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
  const portfolio = useActivePortfolio();
  return portfolio ? (
    <AppShell><ReviewContent /></AppShell>
  ) : (
    <UploadPanel />
  );
}

/**
 * Extract State_Developer from "38DN-State_Developer_Pricing Model_YYYY.MM.DD.xlsm"
 * Returns { base, dateSuffix } so caller can append MM.DD when two files share the same base.
 */
function parseFilename(filename: string): { base: string; dateSuffix: string } {
  let name = filename.replace(/\.(xlsm|xlsx|xls)$/i, "");
  // Extract date before stripping
  const dateMatch = name.match(/(\d{4})[._-](\d{2})[._-](\d{2})\s*$/);
  const dateSuffix = dateMatch ? `${dateMatch[2]}.${dateMatch[3]}` : "";
  // Strip 38DN prefix
  name = name.replace(/^38DN[\s_-]*/i, "");
  // Strip date
  name = name.replace(/[\s_-]*\d{4}[._-]\d{2}[._-]\d{2}\s*$/, "");
  // Strip "Pricing Model" / "Walk Summary"
  name = name.replace(/[\s_-]*(Pricing[\s_]*Model|Walk[\s_]*Summary).*$/i, "");
  const base = name.replace(/_/g, " ").replace(/\s+/g, " ").trim().replace(/^[-\s]+|[-\s]+$/g, "") || "Model";
  return { base, dateSuffix };
}

/** Smart label: appends MM.DD only if it would collide with another uploaded model's base name. */
function guessLabel(filename: string, otherFilename?: string): string {
  const { base, dateSuffix } = parseFilename(filename);
  if (!otherFilename || !dateSuffix) return base;
  const other = parseFilename(otherFilename);
  // If both files share the same base name, disambiguate with date suffix
  if (base === other.base && dateSuffix) {
    return `${base} ${dateSuffix}`;
  }
  return base;
}
