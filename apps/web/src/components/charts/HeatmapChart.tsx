"use client";

import { Plot, baseLayout, cfg, margin, TEAL } from "./PlotlyChart";

interface Props {
  projects: string[];
  fields: string[];
  z: number[][];
  highlightProject?: string;
}

export function HeatmapChart({ projects, fields, z, highlightProject }: Props) {
  const hlPos = highlightProject ? projects.indexOf(highlightProject) : -1;
  const shapes = hlPos >= 0 ? [{
    type: "rect" as const, xref: "paper" as const, x0: 0, x1: 1,
    y0: hlPos - 0.5, y1: hlPos + 0.5,
    line: { color: TEAL, width: 2 }, fillcolor: "rgba(0,0,0,0)",
  }] : [];

  return (
    <Plot
      data={[{
        type: "heatmap", z, x: fields, y: projects,
        colorscale: [[0, "#f7f8fa"], [0.34, "rgba(81,132,132,0.25)"], [0.67, "rgba(184,50,48,0.55)"], [1, "#dfe2e8"]],
        showscale: false, xgap: 3, ygap: 3,
      }]}
      layout={{
        ...baseLayout,
        margin: { l: 10, r: 10, t: 14, b: 40} ,
        xaxis: { ...baseLayout.xaxis, side: "bottom", automargin: true },
        yaxis: { ...baseLayout.yaxis, automargin: true },
        shapes,
      }}
      config={cfg}
      className="w-full"
      style={{ height: Math.max(200, projects.length * 30 + 80) }}
    />
  );
}
