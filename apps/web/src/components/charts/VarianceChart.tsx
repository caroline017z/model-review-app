"use client";

import { Plot, baseLayout, cfg, margin, OFF, TEAL_DEEP, MUTED } from "./PlotlyChart";

interface Props {
  labels: string[];
  x: number[];
  txt: string[];
  colors: string[];
}

const COLOR_MAP: Record<string, string> = { off: OFF, out: TEAL_DEEP, miss: MUTED };

export function VarianceChart({ labels, x, txt, colors }: Props) {
  const vColors = colors.map((c) => COLOR_MAP[c] || MUTED);
  const minX = Math.min(...x, 0);
  const maxX = Math.max(...x, 0);
  const pad = Math.max(Math.abs(minX), Math.abs(maxX)) * 0.3 || 50;

  return (
    <Plot
      data={[{
        type: "bar", orientation: "h",
        x, y: labels, marker: { color: vColors },
        text: txt, textposition: "outside", cliponaxis: false,
        textfont: { color: "#212B48", size: 11 },
      }]}
      layout={{
        ...baseLayout,
        margin: { l: 10, r: 10, t: 14, b: 50, pad: 4} ,
        xaxis: { ...baseLayout.xaxis, title: { text: "Equity $-impact (thousands)", standoff: 14 }, tickprefix: "$", ticksuffix: "k", range: [minX - pad, maxX + pad] },
        yaxis: { ...baseLayout.yaxis, automargin: true },
      }}
      config={cfg}
      className="w-full"
      style={{ height: 250 }}
    />
  );
}
