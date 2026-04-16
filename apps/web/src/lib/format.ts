/**
 * Centralized financial number formatters.
 * Consistent precision across the entire app:
 *   NPP: 3dp ($/W)  |  IRR: 2dp (%)  |  Dollar: accounting parens  |  MW: 2dp
 */

/** NPP in $/W — always 3 decimal places */
export function fmtNpp(val: number | null | undefined): string {
  if (val == null) return "—";
  const s = `$${Math.abs(val).toFixed(3)}/W`;
  return val < 0 ? `(${s})` : s;
}

/** IRR as percentage — always 2 decimal places */
export function fmtIrr(val: number | null | undefined): string {
  if (val == null) return "—";
  const pct = Math.abs(val).toFixed(2);
  return val < 0 ? `(${pct}%)` : `${pct}%`;
}

/** Dollar amount — accounting parentheses for negatives */
export function fmtDollar(val: number | null | undefined): string {
  if (val == null) return "—";
  const abs = Math.abs(val);
  let s: string;
  if (abs >= 1_000_000) s = `$${(abs / 1_000_000).toFixed(2)}M`;
  else if (abs >= 1_000) s = `$${(abs / 1_000).toFixed(1)}k`;
  else s = `$${abs.toFixed(0)}`;
  return val < 0 ? `(${s})` : s;
}

/** Dollar impact from equityK (thousands) */
export function fmtEquity(equityK: number | null | undefined): string {
  if (equityK == null) return "—";
  return fmtDollar((equityK || 0) * 1000);
}

/** MW with 2dp */
export function fmtMw(val: number | null | undefined): string {
  if (val == null) return "—";
  return `${val.toFixed(2)} MW`;
}

/** $/W with 3dp */
export function fmtPerW(val: number | null | undefined): string {
  if (val == null) return "—";
  return `$${Math.abs(val).toFixed(3)}/W`;
}

/** Percentage with configurable dp */
export function fmtPct(val: number | null | undefined, dp = 2): string {
  if (val == null) return "—";
  return `${val.toFixed(dp)}%`;
}

/** Impact in $k — 1dp for precision */
export function fmtImpact(val: number | null | undefined): string {
  if (val == null) return "—";
  const k = (val || 0) / 1000;
  return fmtDollar(val);
}
