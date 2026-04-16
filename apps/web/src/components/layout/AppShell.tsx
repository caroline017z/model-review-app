"use client";

import { useEffect } from "react";
import { TopBar } from "./TopBar";
import { AuditStrip } from "./AuditStrip";
import { ProjectNavigator } from "./ProjectNavigator";
import { ReferencePanel } from "@/components/review/ReferencePanel";
import { useUiStore } from "@/stores/ui";
import { usePortfolioStore } from "@/stores/portfolio";

export function AppShell({ children }: { children: React.ReactNode }) {
  const mode = useUiStore((s) => s.mode);
  const portfolio = usePortfolioStore((s) => s.portfolio);
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const setSelected = useUiStore((s) => s.setSelectedProject);

  // Clamp selectedIdx when reviewProjects shrinks (e.g., after re-upload)
  useEffect(() => {
    if (reviewProjects.length > 0 && selectedIdx >= reviewProjects.length) {
      setSelected(Math.max(0, reviewProjects.length - 1));
    }
  }, [reviewProjects.length, selectedIdx, setSelected]);

  // Keyboard navigation: J/K or arrow keys to switch projects
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        setSelected(Math.min(selectedIdx + 1, reviewProjects.length - 1));
      }
      if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        setSelected(Math.max(selectedIdx - 1, 0));
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedIdx, reviewProjects.length, setSelected]);

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
