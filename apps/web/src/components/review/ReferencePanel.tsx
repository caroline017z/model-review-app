"use client";

import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";

interface RefItem {
  k: string;
  v: string;
  s?: string;
}

function RefSection({ title, items, empty }: { title: string; items?: RefItem[]; empty: string }) {
  return (
    <div className="mb-4">
      <div className="text-[10px] font-bold uppercase tracking-[0.08em] mb-2 pb-1 border-b border-[var(--border)]" style={{ color: "var(--muted)" }}>
        {title}
      </div>
      {items && items.length > 0 ? (
        items.map((item, i) => (
          <div key={i} className="flex justify-between py-1 border-b border-dashed border-[var(--border)]">
            <span className="text-[11px]" style={{ color: "var(--muted)" }}>{item.k}</span>
            <span className="text-[11px] font-semibold tabular-nums">{item.v}</span>
            {item.s && <span className="text-[10px] ml-1" style={{ color: "var(--muted)" }}>{item.s}</span>}
          </div>
        ))
      ) : (
        <p className="text-[11px] italic py-2" style={{ color: "var(--muted)" }}>{empty}</p>
      )}
    </div>
  );
}

export function ReferencePanel() {
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const project = reviewProjects[selectedIdx];

  if (!project) {
    return <p className="text-xs italic" style={{ color: "var(--muted)" }}>Select a project.</p>;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const refs = (project as any).references as {
    bibleHeader?: string;
    marketHeader?: string;
    bible?: RefItem[];
    market?: RefItem[];
    opex?: RefItem[];
    marketMatched?: boolean;
  } | undefined;

  return (
    <div>
      <RefSection
        title={refs?.bibleHeader || "Bible"}
        items={refs?.bible}
        empty="No bible entries"
      />
      <RefSection
        title={refs?.marketHeader || "Market"}
        items={refs?.market}
        empty={refs?.marketMatched === false ? "No market match" : "No market entries"}
      />
      <RefSection
        title="OpEx Benchmarks"
        items={refs?.opex}
        empty="No OpEx benchmarks"
      />
    </div>
  );
}
