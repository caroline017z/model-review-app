"use client";

import { Plot, baseLayout, cfg, margin, NAVY, TEAL, INDIGO, BLUE } from "./PlotlyChart";

interface Props {
  model: number[];
  bible: number[];
}

export function CapitalStackChart({ model, bible }: Props) {
  const names = ["Sponsor Equity", "Tax Equity", "Debt", "Incentives"];
  const colors = [NAVY, TEAL, INDIGO, BLUE];

  return (
    <Plot
      data={names.map((name, i) => ({
        type: "bar" as const, name,
        x: ["Model", "Bible"],
        y: [model[i], bible[i]],
        marker: { color: colors[i] },
      }))}
      layout={{
        ...baseLayout, barmode: "stack",
        yaxis: { ...baseLayout.yaxis, title: { text: "$/W", standoff: 12 }, tickprefix: "$", tickformat: ".2f" },
        legend: { orientation: "h", y: -0.22, font: { size: 10 } },
        title: { text: "Capital Stack ($/W)", font: { size: 11, color: "#7d8694" }, x: 0.01, y: 0.98 },
        margin: { l: 10, r: 10, t: 24, b: 60} ,
      }}
      config={cfg}
      className="w-full"
      style={{ height: 280 }}
    />
  );
}
