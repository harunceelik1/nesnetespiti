import type { DetectionDetails } from "@/lib/detection-api";

export default function InventorySummary({ details }: { details: DetectionDetails | null }) {
  if (!details?.inventory_summary) return null;
  const labels = new Map(details.processed_query_items?.map((item) => [item.primary_query, item.original_query]));
  if (!labels.size) labels.set(details.primary_query, details.original_query);
  const entries = Object.entries(details.inventory_summary);
  const uncertain = new Map<string, number>();
  for (const d of details.detections) if (d.uncertain && d.canonical_query) uncertain.set(d.canonical_query, (uncertain.get(d.canonical_query) ?? 0) + 1);
  return (
    <section className="inventory-summary flex flex-col gap-1 md:w-[min(340px,42%)] md:shrink-0" aria-label="Envanter Özeti">
      <h3 className="text-sm font-semibold">Envanter Özeti</h3>
      <dl className="border-t-2 border-foreground text-sm">
        {entries.map(([query, count]) => (
          <div key={query} className="flex items-baseline justify-between gap-4 border-b py-1.5">
            <dt className="truncate" title={query}>{labels.get(query) || query}</dt>
            <dd className="text-right">
              <span className={count ? "numerals text-xl font-semibold" : "numerals text-xl text-muted-foreground"}>{count}</span>
              {!!uncertain.get(query) && <span className="ml-1.5 text-xs font-normal text-warning-foreground">({uncertain.get(query)} emin değil)</span>}
            </dd>
          </div>
        ))}
        {entries.length > 1 && <div className="inventory-total flex items-baseline justify-between gap-4 py-1.5">
          <dt className="font-semibold">Toplam</dt><dd className="numerals text-xl font-semibold">{details.total_detected_objects}</dd>
        </div>}
      </dl>
    </section>
  );
}
