"use client";

import { usePortfolioStore } from "@/stores/portfolio";
import { useUiStore } from "@/stores/ui";

/* ---------- tiny helpers ---------- */

interface RefItem {
  k: string;
  v: string;
  s?: string;
}

/** Generic key/value section with teal header and muted labels. */
function RefSection({ title, items, empty }: { title: string; items?: RefItem[]; empty: string }) {
  return (
    <div className="mb-4">
      <div
        className="text-[10px] font-bold uppercase tracking-[0.08em] mb-2 pb-1 border-b"
        style={{ color: "#0d9488", borderColor: "var(--border)" }}
      >
        {title}
      </div>
      {items && items.length > 0 ? (
        <table className="w-full text-[10px]">
          <tbody>
            {items.map((item, i) => (
              <tr key={i} className="border-b border-dashed border-[var(--border)]">
                <td className="py-1 pr-2 text-left" style={{ color: "var(--muted)", width: "45%" }}>{item.k}</td>
                <td className="py-1 px-1 text-left font-semibold tabular-nums" style={{ width: "30%" }}>{item.v}</td>
                {item.s && <td className="py-1 pl-1 text-left italic" style={{ color: "var(--muted)", width: "25%", fontSize: "9px" }}>{item.s}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-[11px] italic py-2" style={{ color: "var(--muted)" }}>{empty}</p>
      )}
    </div>
  );
}

/** KPI summary banner — compact project identity strip. */
function KpiSummary({ project }: { project: Record<string, unknown> }) {
  const pills: { label: string; value: string }[] = [
    { label: "Proj #", value: String(project.projNumber ?? "—") },
    { label: "MWdc", value: String((project.kpis as Record<string, string>)?.dc ?? "—") },
    { label: "State", value: String(project.state ?? "—") },
    { label: "Utility", value: String(project.utility ?? "—") },
    { label: "Program", value: String(project.program ?? "—") },
  ];

  return (
    <div className="mb-4">
      <div
        className="text-[10px] font-bold uppercase tracking-[0.08em] mb-2 pb-1 border-b"
        style={{ color: "#0d9488", borderColor: "var(--border)" }}
      >
        Project Summary
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {pills.map((p) => (
          <span key={p.label} className="text-[11px]">
            <span style={{ color: "var(--muted)" }}>{p.label}: </span>
            <span className="font-semibold">{p.value}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/** Build RefItem[] from the rateComp1 backend payload. */
function rateComp1Items(rc: Record<string, unknown> | undefined): RefItem[] {
  if (!rc) return [];
  const items: RefItem[] = [];

  if (rc.name) items.push({ k: "RC1 Name", v: String(rc.name) });
  items.push({
    k: "Energy Rate at COD",
    v: String(rc.rateDisplay ?? "—"),
    s: String(rc.rateSource ?? ""),
  });
  items.push({
    k: "Rate Source",
    v: rc.isCustom ? "Custom (Rate Curves)" : "Generic (Project Inputs)",
  });
  // GH Haircut vs Bible
  const haircutVal = String(rc.ghHaircutDisplay ?? "—");
  const bibleVal = String(rc.bibleDiscountDisplay ?? "—");
  const match = rc.discountMatch as string | null;
  items.push({
    k: "GH Discount (from RC1 name)",
    v: haircutVal,
    s: match === "OK" ? `Ref: ${bibleVal} ✓` : match === "OFF" ? `Ref: ${bibleVal} ✗` : bibleVal !== "—" ? `Ref: ${bibleVal}` : "",
  });
  items.push({
    k: "Customer Discount %",
    v: String(rc.custDiscountDisplay ?? "—"),
  });

  return items;
}

/** Build RefItem[] from the propertyTax backend payload. */
function propertyTaxItems(pt: Record<string, unknown> | undefined): RefItem[] {
  if (!pt) return [];
  return [
    { k: "Custom Toggle", v: pt.customToggle ? "On" : "Off" },
    { k: "Year 1 Amount", v: String(pt.yr1Display ?? "—") },
    { k: "Escalator", v: String(pt.escalator ?? "—") },
  ];
}

/** Extract customer-mix items from the market section's opex hint or market data. */
function customerMixItems(refs: Record<string, unknown> | undefined): RefItem[] {
  if (!refs) return [];
  const items: RefItem[] = [];

  // The market section may contain customer mix info embedded in the opex
  // entries' "s" field (e.g., "50% Resi / 50% Comm"). Walk market items
  // to surface customer discount and acquisition blend context.
  const market = (refs.market as RefItem[]) || [];
  const opex = (refs.opex as RefItem[]) || [];

  // Find customer discount from market items
  const discountItem = market.find((m) => m.k.toLowerCase().includes("customer discount"));
  if (discountItem) {
    items.push({ k: "Customer Discount", v: discountItem.v, s: discountItem.s });
  }

  // Find customer mix from opex items (cust acquisition blended entry has mix in .s)
  const acqItem = opex.find((o) => o.k.toLowerCase().includes("cust acquisition"));
  if (acqItem?.s) {
    items.push({ k: "Customer Mix", v: acqItem.s });
    items.push({ k: "Blended Cust Acq", v: acqItem.v });
  }

  // Find cust mgmt from opex
  const mgmtItem = opex.find((o) => o.k.toLowerCase().includes("cust mgmt"));
  if (mgmtItem) {
    items.push({ k: "Cust Mgmt Rate", v: mgmtItem.v });
  }

  return items;
}

/* ---------- main panel ---------- */

export function ReferencePanel() {
  const reviewProjects = usePortfolioStore((s) => s.reviewProjects);
  const selectedIdx = useUiStore((s) => s.selectedProjectIdx);
  const project = reviewProjects[selectedIdx];

  if (!project) {
    return <p className="text-xs italic" style={{ color: "var(--muted)" }}>Select a project.</p>;
  }

  const refs = project.references;
  const rc1 = project.rateComp1 as Record<string, unknown> | undefined;
  const pt = project.propertyTax as Record<string, unknown> | undefined;
  const custMix = customerMixItems(refs as unknown as Record<string, unknown>);

  return (
    <div>
      {/* KPI Summary strip */}
      <KpiSummary project={project as unknown as Record<string, unknown>} />

      {/* Rate Component 1 */}
      <RefSection
        title="Rate Component 1"
        items={rateComp1Items(rc1)}
        empty="No RC1 data"
      />

      {/* Property Tax */}
      <RefSection
        title="Property Tax"
        items={propertyTaxItems(pt)}
        empty="No property tax data"
      />

      {/* Customer Mix */}
      {custMix.length > 0 && (
        <RefSection
          title="Customer Mix"
          items={custMix}
          empty="No customer mix data"
        />
      )}

      {/* Pricing Reference */}
      <RefSection
        title="Q1 '26 Pricing Reference"
        items={refs?.bible}
        empty="No reference entries"
      />

      {/* Market */}
      <RefSection
        title="Market Assumptions"
        items={refs?.market}
        empty={refs?.marketMatched === false ? "No market match" : "No market entries"}
      />

      {/* OpEx Benchmarks */}
      <RefSection
        title="OpEx Benchmarks"
        items={refs?.opex}
        empty="No OpEx benchmarks"
      />
    </div>
  );
}
