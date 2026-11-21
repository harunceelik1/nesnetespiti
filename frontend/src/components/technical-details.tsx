import { SENSITIVITY_LABELS, type DetectionDetails } from "@/lib/detection-api";

interface Props { details: DetectionDetails | null; loading: boolean; warning: string | null; elapsedMs: number | null; modelName?: string }

export default function TechnicalDetails({ details, loading, warning, elapsedMs, modelName }: Props) {
  return (
    <details className="technical-details">
      <summary>Teknik detaylar{modelName ? " · " + modelName : ""}</summary>
      <div className="technical-content">
        {!details && <p className="muted">{loading ? "Teknik bilgiler alınıyor…" : warning || "Tespit tamamlandığında sorgu ve model bilgileri burada gösterilir."}</p>}
        {details && (
          <>
            <dl className="debug-grid">
              <div><dt>Model</dt><dd>{details.model}</dd></div>
              <div><dt>Seçilen eşik{details.model_id === "grounding-dino" ? " (box)" : ""}</dt><dd>{details.adaptive_thresholds_by_query
                ? Object.entries(details.adaptive_thresholds_by_query).map(([query, threshold]) => `${query}: ${threshold.toFixed(2)}`).join(" · ")
                : details.adaptive_threshold_used?.toFixed(2) ?? "Backend bildirmedi"}</dd></div>
              <div><dt>Hassasiyet</dt><dd>{SENSITIVITY_LABELS[details.sensitivity ?? "balanced"]}</dd></div>
              <div><dt>Seçim nedeni</dt><dd>{details.threshold_selection_reason ?? "Backend bildirmedi"}</dd></div>
              <div className="wide"><dt>Eşik denemeleri{details.model_id === "grounding-dino" ? " (box / text)" : ""}</dt>
                <dd>{details.threshold_attempts?.length ? <div className="table-scroll"><table>
                  <caption>Adaptive threshold denemeleri</caption>
                  <thead><tr><th scope="col">Eşik{details.model_id === "grounding-dino" ? " (box)" : ""}</th><th scope="col">Text</th><th scope="col">Faz / sorgu</th><th scope="col">Ham kutu</th><th scope="col">Final kutu</th></tr></thead>
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
              <div><dt>raw_detection_count</dt><dd>{details.raw_detection_count}</dd></div>
              <div><dt>filtered_detection_count</dt><dd>{details.filtered_detection_count}</dd></div>
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
              <div><dt>total_request_time</dt><dd>{elapsedMs === null ? "—" : Math.round(elapsedMs).toLocaleString("tr-TR") + " ms"}</dd></div>
              <div><dt>inference_time_ms</dt><dd>{details.inference_time_ms.toFixed(1)}</dd></div>
              <div><dt>device</dt><dd>{details.device}</dd></div>
              <div className="wide"><dt>processed_queries</dt><dd>{details.processed_queries.join(", ")}</dd></div>
              {details.processed_query_items && <div className="wide"><dt>processed_query_items</dt><dd>
                {details.processed_query_items.map((item) => <div key={item.primary_query}>
                  {item.original_query} → {item.translated_query ?? "—"} → {item.primary_query}
                  {` · ${item.detected_language} · fallback=${item.fallback_triggered} · ${item.threshold_selection_reason}`}
                </div>)}
              </dd></div>}
            </dl>
            {details.detections.length > 0 ? (
              <div className="table-scroll">
                <table>
                  <caption>Tespit edilen kutular</caption>
                  <thead><tr><th scope="col">Label</th><th scope="col">Canonical sorgu</th><th scope="col">Model sorgusu</th><th scope="col">Confidence</th></tr></thead>
                  <tbody>{details.detections.map((detection, index) => (
                    <tr key={index}><td>{detection.label}</td><td>{detection.canonical_query || "—"}</td><td>{detection.model_query || "—"}</td><td className="numeric">{detection.confidence.toFixed(3)}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            ) : <p className="muted">Bu sorgu için eşik değerini geçen bir nesne bulunamadı.</p>}
          </>
        )}
        <p className="technical-note">Görsel ve metrikler tek /detect yanıtındaki aynı analiz sonucundandır. inference_time_ms backend ölçümüdür, total_request_time tarayıcının toplam bekleme süresidir. Farklı modellerin confidence değerleri aynı ölçekte kalibre edilmiş olmayabilir.</p>
      </div>
    </details>
  );
}
