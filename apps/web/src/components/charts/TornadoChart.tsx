"use client";

import { Plot, baseLayout, cfg, OFF, TEAL, NAVY } from "./PlotlyChart";

interface Props {
  labels: string[];
  lo: number[];
  hi: number[];
}

export function TornadoChart({ labels, lo, hi }: Props) {
  const truncate = (s: string, max: number) => s.length > max ? s.slice(0, max - 1) + "…" : s;
  const inputs = [...labels].reverse().map((l) => truncate(l, 16));
  const loR = [...lo].reverse();
  const hiR = [...hi].reverse();
  const tMin = loR.length ? Math.min(...loR, 0) : 0;
  const tMax = hiR.length ? Math.max(...hiR, 0) : 0;
  const pad = Math.max(Math.abs(tMin), Math.abs(tMax)) * 0.25 || 0.02;

  return (
    <Plot
      data={[
        {
          type: "bar", orientation: "h", name: "−10%",
          x: loR, y: inputs,
          marker: { color: OFF, opacity: 0.75 },
          hovertemplate: "%{y}: $%{x:.3f}/W<extra>−10%</extra>",
        },
        {
          type: "bar", orientation: "h", name: "+10%",
          x: hiR, y: inputs,
          marker: { color: TEAL, opacity: 0.75 },
          hovertemplate: "%{y}: $%{x:.3f}/W<extra>+10%</extra>",
        },
      ]}
      layout={{
        ...baseLayout, barmode: "overlay",
        font: { ...baseLayout.font, size: 10 },
        xaxis: {
          ...baseLayout.xaxis,
          title: { text: "ΔNPP ($/W)", standoff: 8, font: { size: 9 } },
          tickprefix: "$", tickformat: ".3f",
          zeroline: true, zerolinewidth: 2, zerolinecolor: NAVY,
          range: [tMin - pad, tMax + pad],
          tickfont: { size: 9 },
          gridcolor: "rgba(5,13,37,0.06)",
        },
        yaxis: {
          ...baseLayout.yaxis,
          automargin: true,
          tickfont: { size: 9 },
        },
        legend: { orientation: "h", y: -0.28, font: { size: 9 }, x: 0.5, xanchor: "center" },
        title: { text: "Sensitivity (±10%)", font: { size: 10, color: "#7d8694" }, x: 0.01, y: 0.98 },
        margin: { l: 120, r: 20, t: 28, b: 50 },
        bargap: 0.2,
      }}
      config={cfg}
      className="w-full"
      style={{ height: Math.max(220, labels.length * 30 + 80) }}
    />
  );
}
