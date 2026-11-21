import type { DetectionDetails } from "@/lib/detection-api";

export default function InventorySummary({ details }: { details: DetectionDetails | null }) {
  if (!details?.inventory_summary) return null;
  const labels = new Map(details.processed_query_items?.map((item) => [item.primary_query, item.original_query]));
  if (!labels.size) labels.set(details.primary_query, details.original_query);
  return (
    <section className="inventory-summary" aria-label="Envanter Özeti">
      <h3>Envanter Özeti</h3>
      <dl>
        {Object.entries(details.inventory_summary).map(([query, count]) => (
          <div key={query}><dt title={query}>{labels.get(query) || query}</dt><dd>{count}</dd></div>
        ))}
        <div className="inventory-total"><dt>Toplam</dt><dd>{details.total_detected_objects}</dd></div>
      </dl>
    </section>
  );
}
