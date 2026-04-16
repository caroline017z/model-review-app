"use client";

import { usePortfolioStore } from "@/stores/portfolio";

interface PillProps {
  count: number;
  label: string;
  variant?: "off" | "out" | "miss" | "rev" | "default";
}

const variantClasses: Record<string, string> = {
  off: "bg-[var(--off-bg)] text-[var(--off)] border-[rgba(184,50,48,0.2)]",
  out: "bg-[var(--out-bg)] text-[var(--out)] border-[rgba(81,132,132,0.25)]",
  miss: "bg-[var(--miss-bg)] text-[var(--miss)] border-[rgba(125,134,148,0.25)]",
  rev: "bg-[var(--rev-bg)] text-[var(--rev)] border-[rgba(29,111,169,0.25)]",
  default: "bg-surface text-[var(--text-2)] border-[var(--border)]",
};

function Pill({ count, label, variant = "default" }: PillProps) {
  return (
    <span
      className={`inline-flex items-center gap-[5px] px-[9px] py-1 rounded text-[11px] font-semibold border ${variantClasses[variant]}`}
    >
      <span className="text-[12.5px] font-bold tabular-nums">{count}</span>
      {label}
    </span>
  );
}

export function AuditStrip() {
  const portfolio = usePortfolioStore((s) => s.portfolio);
  if (!portfolio) return null;

  return (
    <div className="bg-surface border-b border-[var(--border)] px-[18px] py-2 flex gap-[6px] items-center">
      <span className="text-[9.5px] font-bold uppercase tracking-[0.10em] text-muted mr-1">
        Portfolio Audit
      </span>
      <Pill count={portfolio.off} label="FAIL" variant="off" />
      <Pill count={portfolio.out} label="FLAG" variant="out" />
      <Pill count={portfolio.missing} label="MISSING" variant="miss" />
      <Pill count={portfolio.review} label="REVIEW" variant="rev" />
      <div className="w-px h-[22px] bg-[var(--border)] mx-[6px]" />
      <Pill count={portfolio.count} label="Projects" />
      <Pill count={0} label={`${portfolio.totalMw} MW`} />
      <div className="ml-auto flex gap-[6px]">
        <Pill count={0} label="Reviewed" />
        <Pill count={portfolio.count} label="Pending" />
      </div>
    </div>
  );
}
