import type { DetectionDetails } from "@/lib/detection-api";

export default function InventorySummary({ details }: { details: DetectionDetails | null }) {
  if (!details?.inventory_summary) return null;
  const labels = new Map(details.processed_query_items?.map((item) => [item.primary_query, item.original_query]));
  if (!labels.size) labels.set(details.primary_query, details.original_query);
  const entries = Object.entries(details.inventory_summary);
  const uncertain = new Map<string, number>();
  for (const d of details.detections) if (d.uncertain && d.canonical_query) uncertain.set(d.canonical_query, (uncertain.get(d.canonical_query) ?? 0) + 1);
  return (
    <section className="inventory-summary flex flex-col gap-2" aria-label="Envanter Özeti">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Envanter Özeti</h3>
      <dl className="divide-y rounded-lg border text-sm">
        {entries.map(([query, count]) => (
          <div key={query} className="flex items-center justify-between gap-4 px-3 py-2">
            <dt className="truncate" title={query}>{labels.get(query) || query}</dt>
            <dd className="font-semibold tabular-nums">{count}
              {!!uncertain.get(query) && <span className="ml-1.5 text-xs font-normal text-warning-foreground">({uncertain.get(query)} emin değil)</span>}
            </dd>
          </div>
        ))}
        {entries.length > 1 && <div className="inventory-total flex items-center justify-between gap-4 bg-muted/50 px-3 py-2">
          <dt className="font-medium">Toplam</dt><dd className="font-semibold tabular-nums">{details.total_detected_objects}</dd>
        </div>}
      </dl>
    </section>
  );
}
