"use client";

import { Plot, baseLayout, cfg, margin, OFF, TEAL } from "./PlotlyChart";

interface Props {
  labels: string[];
  lo: number[];
  hi: number[];
}

export function TornadoChart({ labels, lo, hi }: Props) {
  const inputs = [...labels].reverse();
  const loR = [...lo].reverse();
  const hiR = [...hi].reverse();
  const tMin = loR.length ? Math.min(...loR, 0) : 0;
  const tMax = hiR.length ? Math.max(...hiR, 0) : 0;
  const pad = Math.max(Math.abs(tMin), Math.abs(tMax)) * 0.15 || 0.02;

  return (
    <Plot
      data={[
        { type: "bar", orientation: "h", name: "−10%", x: loR, y: inputs, marker: { color: OFF } },
        { type: "bar", orientation: "h", name: "+10%", x: hiR, y: inputs, marker: { color: TEAL } },
      ]}
      layout={{
        ...baseLayout, barmode: "overlay",
        xaxis: { ...baseLayout.xaxis, title: { text: "ΔNPP ($/W)", standoff: 14 }, tickprefix: "$", tickformat: ".2f", zeroline: true, zerolinewidth: 2, zerolinecolor: "#212B48", range: [tMin - pad, tMax + pad] },
        yaxis: { ...baseLayout.yaxis, automargin: true },
        legend: { orientation: "h", y: -0.25, font: { size: 10 } },
        margin: { l: 10, r: 10, t: 14, b: 60} ,
      }}
      config={cfg}
      className="w-full"
      style={{ height: 280 }}
    />
  );
}
