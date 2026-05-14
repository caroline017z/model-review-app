"use client";

import { useActiveReviewProjects, useActivePortfolio, useActiveConfirmedExclusions } from "@/stores/portfolio";
import { useReviewerStore } from "@/stores/reviewer";

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
  const portfolio = useActivePortfolio();
  const reviewProjects = useActiveReviewProjects();
  const confirmedExclusions = useActiveConfirmedExclusions();
  const reviewerApprovals = useReviewerStore((s) => s.approvals);
  if (!portfolio) return null;

  // Derive counts from confirmed (included) projects only
  const included = reviewProjects.filter((_, i) => !confirmedExclusions[i]);
  const nOff = included.reduce((s, p) => s + (p.findings?.filter((f) => f.status === "OFF").length || 0), 0);
  const nOut = included.reduce((s, p) => s + (p.findings?.filter((f) => f.status === "OUT").length || 0), 0);
  const nReview = included.filter((p) => p.verdict === "REVIEW").length;
  const totalMw = included.reduce((s, p) => s + parseFloat(String(p.kpis?.dc || 0)), 0);
  const nApproved = reviewProjects.filter((_, i) => !confirmedExclusions[i] && reviewerApprovals[i]?.approved).length;
  const nPending = included.length - nApproved;

  return (
    <div className="bg-surface border-b border-[var(--border)] px-[18px] py-2 flex gap-[6px] items-center">
      <span className="text-[9.5px] font-bold uppercase tracking-[0.10em] text-muted mr-1">
        Portfolio Audit
      </span>
      <Pill count={nOff} label="FAIL" variant="off" />
      <Pill count={nOut} label="FLAG" variant="out" />
      <Pill count={nReview} label="REVIEW" variant="rev" />
      <div className="w-px h-[22px] bg-[var(--border)] mx-[6px]" />
      <Pill count={included.length} label="Projects" />
      <span className="inline-flex items-center gap-[5px] px-[9px] py-1 rounded text-[11px] font-semibold border border-[var(--border)] bg-surface text-[var(--text-2)]">
        <span className="text-[12.5px] font-bold tabular-nums">{totalMw.toFixed(1)}</span> MW
      </span>
      <div className="ml-auto flex gap-[6px]">
        <Pill count={nApproved} label="Reviewed" />
        <Pill count={nPending} label="Pending" />
      </div>
    </div>
  );
}
