"use client";

import { TopBar } from "./TopBar";
import { AuditStrip } from "./AuditStrip";
import { ProjectNavigator } from "./ProjectNavigator";
import { ReferencePanel } from "@/components/review/ReferencePanel";
import { useUiStore } from "@/stores/ui";
import { usePortfolioStore } from "@/stores/portfolio";

export function AppShell({ children }: { children: React.ReactNode }) {
  const mode = useUiStore((s) => s.mode);
  const portfolio = usePortfolioStore((s) => s.portfolio);

  // Grid layout adapts per mode
  const gridClass =
    mode === "reference"
      ? "grid-cols-1"
      : mode === "walk"
        ? "grid-cols-[260px_1fr]"
        : "grid-cols-[260px_1fr_280px]";

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <TopBar />
      {portfolio && <AuditStrip />}
      <div className={`flex-1 grid ${gridClass} gap-px bg-[var(--border)] min-h-0 overflow-hidden`}>
        {mode !== "reference" && (
          <aside className="bg-[var(--bg)] overflow-y-auto min-w-0">
            <ProjectNavigator />
          </aside>
        )}
        <main className="bg-[var(--bg)] overflow-y-auto p-[18px] min-w-0">
          {children}
        </main>
        {(mode === "project" || mode === "portfolio") && (
          <aside className="bg-[var(--bg)] overflow-y-auto p-[14px] min-w-0 max-lg:hidden">
            <ReferencePanel />
          </aside>
        )}
      </div>
    </div>
  );
}
