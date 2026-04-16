"use client";

import { Plot, baseLayout, cfg, OFF, TEAL } from "./PlotlyChart";

interface Props {
  labels: string[];
  lo: number[];
  hi: number[];
}

export function TornadoChart({ labels, lo, hi }: Props) {
  // Truncate long labels to prevent overlap
  const truncate = (s: string, max: number) => s.length > max ? s.slice(0, max - 1) + "…" : s;
  const inputs = [...labels].reverse().map((l) => truncate(l, 16));
  const loR = [...lo].reverse();
  const hiR = [...hi].reverse();
  const tMin = loR.length ? Math.min(...loR, 0) : 0;
  const tMax = hiR.length ? Math.max(...hiR, 0) : 0;
  const pad = Math.max(Math.abs(tMin), Math.abs(tMax)) * 0.2 || 0.02;

  return (
    <Plot
      data={[
        { type: "bar", orientation: "h", name: "−10%", x: loR, y: inputs, marker: { color: OFF } },
        { type: "bar", orientation: "h", name: "+10%", x: hiR, y: inputs, marker: { color: TEAL } },
      ]}
      layout={{
        ...baseLayout, barmode: "overlay",
        font: { ...baseLayout.font, size: 10 },
        xaxis: {
          ...baseLayout.xaxis,
          title: { text: "ΔNPP ($/W)", standoff: 10, font: { size: 10 } },
          tickprefix: "$", tickformat: ".2f",
          zeroline: true, zerolinewidth: 2, zerolinecolor: "#212B48",
          range: [tMin - pad, tMax + pad],
          tickfont: { size: 9 },
        },
        yaxis: {
          ...baseLayout.yaxis,
          automargin: true,
          tickfont: { size: 9 },
        },
        legend: { orientation: "h", y: -0.3, font: { size: 9 } },
        title: { text: "Sensitivity (±10%)", font: { size: 10, color: "#7d8694" }, x: 0.01, y: 0.98 },
        margin: { l: 120, r: 10, t: 24, b: 50 },
      }}
      config={cfg}
      className="w-full"
      style={{ height: 280 }}
    />
  );
}
