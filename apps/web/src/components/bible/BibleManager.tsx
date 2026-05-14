"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useBibleStore } from "@/stores/bible";

interface BibleManagerProps {
  /** Layout variant: `panel` (inline on upload page) vs `modal` (popover from TopBar). */
  variant?: "panel" | "modal";
  /** Called when a vintage becomes active — lets the parent close a modal or refresh data. */
  onActivate?: () => void;
}

export function BibleManager({ variant = "panel", onActivate }: BibleManagerProps) {
  const vintages = useBibleStore((s) => s.vintages);
  const loading = useBibleStore((s) => s.loading);
  const error = useBibleStore((s) => s.error);
  const refresh = useBibleStore((s) => s.refresh);
  const upload = useBibleStore((s) => s.upload);
  const activate = useBibleStore((s) => s.activate);
  const remove = useBibleStore((s) => s.remove);

  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    if (vintages.length === 0) refresh();
  }, [refresh, vintages.length]);

  const handleFile = useCallback(
    async (file: File) => {
      if (!/\.xlsx$/i.test(file.name)) {
        setUploadStatus("Bible uploads must be .xlsx");
        return;
      }
      setUploading(true);
      setUploadStatus("Uploading...");
      try {
        // Default label = filename minus extension
        const label = file.name.replace(/\.xlsx$/i, "");
        await upload(file, label, true); // set_active=true
        setUploadStatus("");
        onActivate?.();
      } catch (e) {
        setUploadStatus(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [upload, onActivate],
  );

  const handleActivate = async (vintageId: string) => {
    try {
      await activate(vintageId);
      onActivate?.();
    } catch {
      /* surfaced via store.error */
    }
  };

  const handleDelete = async (vintageId: string, label: string) => {
    if (!confirm(`Delete vintage "${label}"? This cannot be undone.`)) return;
    try {
      await remove(vintageId);
    } catch {
      /* surfaced via store.error */
    }
  };

  const wrapperClass = variant === "modal" ? "p-4 min-w-[520px]" : "";

  return (
    <div className={wrapperClass}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-[11px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--teal)" }}>
          Pricing Bible Vintages
        </h2>
        {variant === "modal" && (
          <span className="text-[10px]" style={{ color: "var(--muted)" }}>
            {vintages.length} vintage{vintages.length === 1 ? "" : "s"}
          </span>
        )}
      </div>

      {/* Drag-drop / click upload zone */}
      <div
        onClick={() => !uploading && fileRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        className={`border-2 border-dashed rounded px-4 py-3 mb-3 text-center cursor-pointer transition text-[11px] ${
          uploading ? "opacity-60 pointer-events-none" : "hover:border-[var(--teal)]"
        }`}
        style={{
          borderColor: dragOver ? "var(--teal)" : "var(--border)",
          background: dragOver ? "var(--ok-bg)" : "transparent",
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
        {uploading ? (
          <span style={{ color: "var(--teal)" }}>{uploadStatus || "Uploading..."}</span>
        ) : (
          <span style={{ color: "var(--muted)" }}>
            Drop .xlsx here or click to upload a new vintage
          </span>
        )}
      </div>

      {(uploadStatus && !uploading) || error ? (
        <p className="text-[10px] mb-2" style={{ color: "var(--off)" }}>
          {uploadStatus || error}
        </p>
      ) : null}

      {/* Vintage list */}
      {vintages.length > 0 ? (
        <div className="border rounded overflow-hidden" style={{ borderColor: "var(--border)" }}>
          <table className="w-full text-[10.5px]">
            <thead>
              <tr style={{ background: "var(--inset)" }}>
                <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--muted)" }}>Label</th>
                <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--muted)" }}>Source</th>
                <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--muted)" }}>Uploaded</th>
                <th className="text-center px-2 py-1.5 font-semibold" style={{ color: "var(--muted)" }}>Status</th>
                <th className="text-right px-2 py-1.5"></th>
              </tr>
            </thead>
            <tbody>
              {vintages.map((v) => (
                <tr
                  key={v.vintage_id}
                  className="border-t"
                  style={{ borderColor: "var(--border)" }}
                >
                  <td className="px-2 py-1.5 font-semibold">{v.label}</td>
                  <td className="px-2 py-1.5" style={{ color: "var(--muted)" }}>
                    {v.source}
                  </td>
                  <td className="px-2 py-1.5 tabular-nums" style={{ color: "var(--muted)" }}>
                    {formatUploadedAt(v.uploaded_at)}
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    {v.is_active ? (
                      <span
                        className="inline-block text-[9px] font-bold px-1.5 py-px rounded"
                        style={{ background: "var(--ok-bg)", color: "var(--ok)" }}
                      >
                        ACTIVE
                      </span>
                    ) : (
                      <button
                        onClick={() => handleActivate(v.vintage_id)}
                        disabled={loading}
                        className="text-[10px] font-semibold underline decoration-dotted cursor-pointer disabled:opacity-50"
                        style={{ color: "var(--teal)" }}
                      >
                        Set active
                      </button>
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-right">
                    {!v.is_active && v.source !== "bundled" && (
                      <button
                        onClick={() => handleDelete(v.vintage_id, v.label)}
                        disabled={loading}
                        className="text-[10px] cursor-pointer disabled:opacity-50"
                        style={{ color: "var(--off)" }}
                        title="Delete this vintage"
                      >
                        ×
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-[11px] italic py-2" style={{ color: "var(--muted)" }}>
          {loading ? "Loading vintages..." : "No vintages yet."}
        </p>
      )}

      <p className="text-[9.5px] mt-2" style={{ color: "var(--muted)" }}>
        The active vintage is used for every audit. Upload a new Pricing Bible xlsx
        when a quarterly update lands- it becomes active immediately.
      </p>
    </div>
  );
}

function formatUploadedAt(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
}
