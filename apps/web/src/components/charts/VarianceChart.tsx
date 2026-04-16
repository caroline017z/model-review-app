"use client";

import { Plot, baseLayout, cfg, OFF, TEAL_DEEP, MUTED, NAVY } from "./PlotlyChart";

interface Props {
  labels: string[];
  x: number[];
  txt: string[];
  colors: string[];
}

const COLOR_MAP: Record<string, string> = { off: OFF, out: TEAL_DEEP, miss: MUTED };

export function VarianceChart({ labels, x, txt, colors }: Props) {
  const truncate = (s: string, max: number) => s.length > max ? s.slice(0, max - 1) + "…" : s;
  const vColors = colors.map((c) => COLOR_MAP[c] || MUTED);
  const displayLabels = labels.map((l) => truncate(l, 14));
  const minX = Math.min(...x, 0);
  const maxX = Math.max(...x, 0);
  const pad = Math.max(Math.abs(minX), Math.abs(maxX)) * 0.35 || 50;

  return (
    <Plot
      data={[{
        type: "bar", orientation: "h",
        x, y: displayLabels,
        marker: {
          color: vColors,
          line: { color: vColors.map((c) => c), width: 0.5 },
        },
        text: txt,
        textposition: "outside",
        cliponaxis: false,
        textfont: { color: NAVY, size: 10, family: "Inter, sans-serif" },
        hovertemplate: "%{y}<br>Impact: %{text}<extra></extra>",
      }]}
      layout={{
        ...baseLayout,
        font: { ...baseLayout.font, size: 10 },
        margin: { l: 100, r: 60, t: 28, b: 40 },
        title: { text: "Equity Impact by Finding", font: { size: 10, color: "#7d8694" }, x: 0.01, y: 0.98 },
        xaxis: {
          ...baseLayout.xaxis,
          title: { text: "Impact ($k)", standoff: 8, font: { size: 9 } },
          tickprefix: "$", ticksuffix: "k",
          tickfont: { size: 9 },
          range: [minX - pad, maxX + pad],
          gridcolor: "rgba(5,13,37,0.06)",
          zerolinecolor: NAVY,
          zerolinewidth: 1.5,
        },
        yaxis: {
          ...baseLayout.yaxis,
          automargin: true,
          tickfont: { size: 9 },
        },
        bargap: 0.25,
      }}
      config={cfg}
      className="w-full"
      style={{ height: Math.max(200, labels.length * 32 + 80) }}
    />
  );
}
