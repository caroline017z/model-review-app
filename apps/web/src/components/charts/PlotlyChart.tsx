"use client";

import dynamic from "next/dynamic";
import type { PlotParams } from "react-plotly.js";

// Dynamic import to avoid SSR issues with Plotly
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const NAVY = "#050D25";
const INDIGO = "#212B48";
const TEAL = "#518484";
const TEAL_DEEP = "#3d6868";
const BLUE = "#1D6FA9";
const OFF = "#b83230";
const MUTED = "#7d8694";

const baseLayout: Partial<Plotly.Layout> = {
  font: { family: "Inter, Segoe UI, sans-serif", size: 11, color: INDIGO },
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  xaxis: { gridcolor: "rgba(5,13,37,0.05)", zerolinecolor: "rgba(5,13,37,0.15)", automargin: true },
  yaxis: { gridcolor: "rgba(5,13,37,0.05)", zerolinecolor: "rgba(5,13,37,0.15)", automargin: true },
};

const cfg: Partial<Plotly.Config> = { displayModeBar: false, responsive: true };

/** Helper to create margin objects without TypeScript complaints about Plotly's strict Margin type. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function margin(m: Record<string, number | boolean>): any { return m; }

export { Plot, baseLayout, cfg, margin, NAVY, INDIGO, TEAL, TEAL_DEEP, BLUE, OFF, MUTED };
export type { PlotParams };
