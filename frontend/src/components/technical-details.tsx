import { ChevronRight } from "lucide-react";
import { MODEL_NAME, SENSITIVITY_LABELS, type DetectionDetails } from "@/lib/detection-api";
import { useDebugMode } from "@/lib/debug-mode";

interface Props { details: DetectionDetails | null; loading: boolean; warning: string | null; elapsedMs: number | null }

const ms = (value: number) => Math.round(value).toLocaleString("tr-TR") + " ms";

/**
 * Katman 2: kapalı gelen, okunur Türkçe özet (eşik, aday → kutu, süre, tespit tablosu).
 * Katman 3: yalnızca ?debug=1 ile görünen ham tanılar (backend alan adları, eşik denemeleri,
 * scene-box ölçümleri). Kullanıcının asıl sonucu (katman 1) sonuç kartındadır.
 */
export default function TechnicalDetails({ details, loading, warning, elapsedMs }: Props) {
  const debug = useDebugMode();
  return (
    <details className="technical-details group border-t border-foreground/80 text-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 py-3 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 [&::-webkit-details-marker]:hidden">
        <ChevronRight aria-hidden="true" className="size-4 transition-transform group-open:rotate-90" />
        <span className="font-semibold">Teknik detaylar</span>
        <span className="hidden text-xs sm:inline">eşik, süre ve her kutunun güven puanı</span>
        {debug && <span className="ml-auto rounded bg-warning px-1.5 text-[11px] text-warning-foreground">geliştirici modu</span>}
      </summary>
      <div className="technical-content pb-6 pt-2">
        {!details && <p className="muted">{loading ? "Teknik bilgiler alınıyor…" : warning || "Tespit tamamlandığında eşik, süre ve kutu bilgileri burada gösterilir."}</p>}
        {details && (
          <>
            <dl className="debug-grid">
              <div><dt>Model</dt><dd>{MODEL_NAME}</dd></div>
              <div><dt>Hassasiyet</dt><dd>{SENSITIVITY_LABELS[details.sensitivity ?? "balanced"]}</dd></div>
              <div><dt>Seçilen eşik</dt><dd>{details.adaptive_thresholds_by_query
                ? Object.entries(details.adaptive_thresholds_by_query).map(([query, threshold]) => `${query}: ${threshold.toFixed(2)}`).join(" · ")
                : details.adaptive_threshold_used?.toFixed(2) ?? "Backend bildirmedi"}</dd></div>
              <div><dt>Kutular</dt><dd>{details.raw_detection_count} aday → {details.filtered_detection_count} kutu kaldı</dd></div>
              <div className="wide"><dt>Aranan ifade</dt><dd>
                {details.processed_query_items?.length
                  ? details.processed_query_items.map((item) => <div key={item.primary_query}>{item.original_query} → {item.primary_query}</div>)
                  : `${details.original_query} → ${details.primary_query}`}
                {details.fallback_triggered && <div className="muted">Sonuç çıkmadığı için yedek ifade denendi: {details.fallback_queries_used.join(", ") || "—"}</div>}
              </dd></div>
              {details.oversized_boxes_removed_count !== undefined && <div className="wide">
                <dt>Elenen dev kutu</dt>
                <dd>{details.oversized_boxes_removed_count
                  ? `${details.oversized_boxes_removed_count} kutu görselin neredeyse tamamını kapladığı için çizilmedi.`
                  : "Yok"}</dd>
              </div>}
              <div><dt>Model süresi</dt><dd>{ms(details.inference_time_ms)}</dd></div>
              <div><dt>Toplam bekleme</dt><dd>{elapsedMs === null ? "—" : ms(elapsedMs)}</dd></div>
              <div><dt>Cihaz</dt><dd>{details.device.toUpperCase()}</dd></div>
            </dl>
            {details.detections.length > 0 ? (
              <div className="table-scroll">
                <table className="detections-table">
                  <caption>Tespit edilen kutular</caption>
                  <thead><tr><th scope="col">Nesne</th><th scope="col">Modele giden ifade</th><th scope="col">Güven</th><th scope="col">Durum</th></tr></thead>
                  <tbody>{details.detections.map((detection, index) => (
                    <tr key={index}><td>{detection.label}</td><td>{detection.model_query || "—"}</td><td className="numeric">{detection.confidence.toFixed(3)}</td>
                      <td className={detection.uncertain ? "text-warning-foreground" : "text-muted-foreground"}>{detection.uncertain ? "emin değil" : "—"}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            ) : <p className="muted">Bu sorgu için eşik değerini geçen bir nesne bulunamadı.</p>}
            <p className="technical-note">Model süresi backend&apos;in ölçtüğü çalışma süresi, toplam bekleme tarayıcının beklediği süredir. Güven puanı bir olasılık değildir; yalnızca aynı görseldeki kutuları birbiriyle karşılaştır.</p>
            {debug && <RawDiagnostics details={details} />}
          </>
        )}
      </div>
    </details>
  );
}

/** Katman 3: ham backend alanları. Yalnızca geliştirici modunda render edilir. */
function RawDiagnostics({ details }: { details: DetectionDetails }) {
  return (
    <section className="raw-diagnostics flex flex-col gap-4 border-t border-dashed pt-4" aria-label="Ham tanılar">
      <h3 className="text-xs font-semibold text-warning-foreground">Ham tanılar (?debug=1)</h3>
      <dl className="debug-grid">
        <div><dt>threshold_selection_reason</dt><dd>{details.threshold_selection_reason ?? "Backend bildirmedi"}</dd></div>
        <div className="wide"><dt>threshold_attempts</dt>
          <dd>{details.threshold_attempts?.length ? <div className="table-scroll"><table className="attempts-table">
            <caption>Eşik denemeleri</caption>
            <thead><tr><th scope="col">Eşik</th><th scope="col">Text</th><th scope="col">Faz / sorgu</th><th scope="col">Ham kutu</th><th scope="col">Final kutu</th></tr></thead>
            <tbody>{details.threshold_attempts.map((attempt, index) => <tr key={index}>
              <td>{attempt.threshold.toFixed(2)}</td><td>{attempt.text_threshold?.toFixed(2) ?? "—"}</td>
              <td>{[attempt.phase, attempt.queries?.join(", ")].filter(Boolean).join(" / ") || "—"}</td>
              <td>{attempt.raw_detection_count}</td><td>{attempt.filtered_detection_count}</td>
            </tr>)}</tbody>
          </table></div> : "Backend bildirmedi"}</dd>
        </div>
        <div><dt>original_query</dt><dd>{details.original_query}</dd></div>
        <div><dt>detected_language</dt><dd>{details.detected_language}</dd></div>
        <div><dt>translated_query</dt><dd>{details.translated_query ?? "— (İngilizce sorgu)"}</dd></div>
        <div><dt>primary_query</dt><dd>{details.primary_query}</dd></div>
        <div><dt>fallback_triggered</dt><dd>{String(details.fallback_triggered)}</dd></div>
        <div><dt>fallback_queries_used</dt><dd>{details.fallback_queries_used.join(", ") || "—"}</dd></div>
        <div><dt>inference_time_ms</dt><dd>{details.inference_time_ms.toFixed(1)}</dd></div>
        <div><dt>device</dt><dd>{details.device}</dd></div>
        <div className="wide"><dt>processed_queries</dt><dd>{details.processed_queries.join(", ")}</dd></div>
        {details.processed_query_items && <div className="wide"><dt>processed_query_items</dt><dd>
          {details.processed_query_items.map((item) => <div key={item.primary_query}>
            {item.original_query} → {item.translated_query ?? "—"} → {item.primary_query}
            {` · ${item.detected_language} · fallback=${item.fallback_triggered} · ${item.threshold_selection_reason}`}
          </div>)}
        </dd></div>}
        {details.oversized_boxes_removed_count !== undefined && <div className="wide">
          <dt>oversized_boxes_removed (tüm eşik denemeleri)</dt>
          <dd>{details.oversized_boxes_removed_count}
            {details.oversized_boxes_removed?.map((entry, index) => <div key={index}>
              {entry.canonical_query || entry.detection.label}
              {` · area_ratio=${entry.area_ratio.toFixed(4)} · ${entry.reason}`}
              {` · borders=${entry.near_borders.join(", ")}`}
              {entry.threshold !== undefined ? ` · threshold=${entry.threshold.toFixed(2)}` : ""}
            </div>)}
          </dd>
        </div>}
        {details.scene_box_diagnostics && <div className="wide">
          <dt>scene_box_diagnostics (NMS sonrası, tüm eşik denemeleri)</dt>
          <dd>{details.scene_box_diagnostics.length ? details.scene_box_diagnostics.map((entry, index) => <div key={index}>
            {entry.canonical_query || entry.detection.label}
            {` · area_ratio=${entry.area_ratio.toFixed(4)} · touched_edges=${entry.touched_edges}`}
            {entry.width_coverage !== undefined ? ` · width_coverage=${entry.width_coverage.toFixed(4)}` : ""}
            {entry.height_coverage !== undefined ? ` · height_coverage=${entry.height_coverage.toFixed(4)}` : ""}
            {` · ${entry.removed ? "kaldırıldı" : "korundu"} · ${entry.matched_rule ?? "no_rule"}`}
            {` · near_borders=${entry.near_borders.join(", ") || "—"}`}
            {` · edge_distance_ratios=${Object.entries(entry.edge_distance_ratios).map(([edge, distance]) => `${edge}:${distance.toFixed(4)}`).join(", ")}`}
            {` · image=${entry.image_size.width}×${entry.image_size.height}`}
            {` · box=[${Object.values(entry.detection.box).join(", ")}]`}
            {entry.threshold !== undefined ? ` · threshold=${entry.threshold.toFixed(2)}` : ""}
          </div>) : "Geçerli NMS kutusu yok."}</dd>
        </div>}
      </dl>
    </section>
  );
}
