"use client";

import { useState, useMemo } from "react";
import type { BibleMappingCategory, BibleMappingRow } from "@/lib/api";

const STATUS_CLS: Record<string, string> = {
  OK: "bg-[var(--ok-bg)] text-[var(--ok)]",
  OFF: "bg-[var(--off-bg)] text-[var(--off)]",
  OUT: "bg-[var(--out-bg)] text-[var(--out)]",
  MISSING: "bg-[var(--miss-bg)] text-[var(--miss)]",
  REVIEW: "bg-[var(--rev-bg)] text-[var(--rev)]",
};

const STATUS_LABEL: Record<string, string> = {
  OK: "OK", OFF: "FAIL", OUT: "FLAG", MISSING: "MISSING", REVIEW: "REVIEW",
};

function fmtVal(v: string | number | null | undefined): string {
  if (v == null) return "—";
  if (typeof v === "number") {
    if (Math.abs(v) < 1 && v !== 0) return `${(v * 100).toFixed(2)}%`;
    if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return v.toFixed(3);
  }
  return String(v);
}

function CategorySection({ cat, rows }: { cat: string; rows: BibleMappingRow[] }) {
  const [open, setOpen] = useState(false);
  const failCount = rows.filter((r) => r.status !== "OK").length;
  const summary = failCount > 0
    ? `${failCount} issue${failCount > 1 ? "s" : ""}`
    : "all OK";

  return (
    <div className="border-b border-[var(--border)]">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-[var(--inset)] transition cursor-pointer"
        style={{ background: "var(--raised)" }}
      >
        <span className="text-[10px] transition-transform duration-150" style={{ transform: open ? "rotate(90deg)" : "rotate(0)" }}>
          &#9654;
        </span>
        <span className="text-[10px] font-bold uppercase tracking-[0.06em]" style={{ color: "var(--text-2)" }}>
          {cat}
        </span>
        <span className="text-[9px] tabular-nums" style={{ color: "var(--muted)" }}>
          {rows.length} rows
        </span>
        {failCount > 0 && (
          <span className="text-[8px] font-bold px-1.5 py-px rounded" style={{ background: "var(--off-bg)", color: "var(--off)" }}>
            {summary}
          </span>
        )}
        {failCount === 0 && (
          <span className="text-[8px] font-bold px-1.5 py-px rounded" style={{ background: "var(--ok-bg)", color: "var(--ok)" }}>
            {summary}
          </span>
        )}
      </button>
      {open && (
        <table className="w-full text-[10px]">
          <thead>
            <tr style={{ background: "var(--inset)" }}>
              <th className="text-left px-3 py-1 font-semibold">Label</th>
              <th className="text-center px-2 py-1 font-semibold w-12">Unit</th>
              <th className="text-center px-2 py-1 font-semibold">Bible</th>
              <th className="text-center px-2 py-1 font-semibold">Model</th>
              <th className="text-center px-2 py-1 font-semibold w-16">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isOk = r.status === "OK";
              return (
                <tr
                  key={r.row}
                  className="border-t border-[var(--border)] hover:bg-[var(--inset)]"
                  style={{ opacity: isOk ? 0.6 : 1 }}
                >
                  <td className={`px-3 py-1 ${isOk ? "" : "font-semibold"}`}>{r.label}</td>
                  <td className="text-center px-2 py-1" style={{ color: "var(--muted)" }}>{r.unit}</td>
                  <td className="text-center px-2 py-1 tabular-nums">{fmtVal(r.expected)}</td>
                  <td className="text-center px-2 py-1 tabular-nums">{fmtVal(r.actual)}</td>
                  <td className="text-center px-2 py-1">
                    <span className={`text-[8px] px-1.5 py-px rounded font-bold ${STATUS_CLS[r.status] || ""}`}>
                      {STATUS_LABEL[r.status] || r.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function BibleMapping({ categories }: { categories: BibleMappingCategory[] }) {
  const [open, setOpen] = useState(false);

  const totalRows = useMemo(() => categories.reduce((s, c) => s + c.rows.length, 0), [categories]);
  const totalFails = useMemo(
    () => categories.reduce((s, c) => s + c.rows.filter((r) => r.status !== "OK").length, 0),
    [categories],
  );

  if (!categories.length) return null;

  return (
    <div className="rounded border border-[var(--border)] overflow-hidden" style={{ background: "var(--surface)" }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-[var(--inset)] transition cursor-pointer"
      >
        <span className="text-[11px] transition-transform duration-150" style={{ transform: open ? "rotate(90deg)" : "rotate(0)" }}>
          &#9654;
        </span>
        <span className="text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--muted)" }}>
          Full Bible Mapping
        </span>
        <span className="text-[9px] tabular-nums" style={{ color: "var(--muted)" }}>
          {totalRows} rows checked
        </span>
        {totalFails > 0 && (
          <span className="text-[8px] font-bold px-1.5 py-px rounded" style={{ background: "var(--off-bg)", color: "var(--off)" }}>
            {totalFails} issue{totalFails > 1 ? "s" : ""}
          </span>
        )}
      </button>
      {open && (
        <div className="max-h-[500px] overflow-y-auto">
          {categories.map((cat) => (
            <CategorySection key={cat.category} cat={cat.category} rows={cat.rows} />
          ))}
        </div>
      )}
    </div>
  );
}
