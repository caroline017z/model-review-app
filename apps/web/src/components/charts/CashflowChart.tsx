"use client";

import { Plot, baseLayout, cfg, margin } from "./PlotlyChart";

interface Props {
  opCF: number[];
  taxBn: number[];
  terminal: number[];
}

export function CashflowChart({ opCF, taxBn, terminal }: Props) {
  const yrs = Array.from({ length: Math.max(opCF.length, 25) }, (_, i) => i + 1);

  return (
    <Plot
      data={[
        { type: "scatter", mode: "none", stackgroup: "one", name: "Operating CF", x: yrs, y: opCF, fillcolor: "rgba(81,132,132,0.55)" },
        { type: "scatter", mode: "none", stackgroup: "one", name: "Tax Benefits", x: yrs, y: taxBn, fillcolor: "rgba(33,43,72,0.45)" },
        { type: "scatter", mode: "none", stackgroup: "one", name: "Terminal", x: yrs, y: terminal, fillcolor: "rgba(29,111,169,0.45)" },
      ]}
      layout={{
        ...baseLayout,
        xaxis: { ...baseLayout.xaxis, title: { text: "Year", standoff: 12 }, dtick: 5, automargin: true },
        yaxis: { ...baseLayout.yaxis, title: { text: "$ thousands", standoff: 14 }, tickprefix: "$", tickformat: ",.0f" },
        legend: { orientation: "h", y: -0.25, font: { size: 10 } },
        margin: { l: 10, r: 10, t: 14, b: 60} ,
      }}
      config={cfg}
      className="w-full"
      style={{ height: 280 }}
    />
  );
}
