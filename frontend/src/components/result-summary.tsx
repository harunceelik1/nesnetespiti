import { MODEL_NAMES, type DetectionDetails } from "@/lib/detection-api";

interface Props {
  details: DetectionDetails | null;
  hasResult: boolean;
  phase: "idle" | "image" | "details";
  failed?: boolean;
}

export default function ResultSummary({ details, hasResult, phase, failed = false }: Props) {
  return (
    <div className="result-summary" role="status" aria-live="polite" aria-atomic="true">
      {failed ? <span>Analiz tamamlanamadı.</span> : phase === "image" ? <span>Görüntü analiz ediliyor…</span>
        : phase === "details" ? <span>Görsel hazır, tespit bilgileri alınıyor…</span>
          : details ? <>
            <strong>{details.filtered_detection_count} nesne bulundu</strong>
            <span className="separator" aria-hidden="true">·</span>
            <span title="Backend inference süresi">{Math.round(details.inference_time_ms).toLocaleString("tr-TR")} ms</span>
            <span className="separator" aria-hidden="true">·</span><span>{MODEL_NAMES[details.model_id]}</span>
            <span className="separator" aria-hidden="true">·</span><span>{details.device.toUpperCase()}</span>
          </> : <span>{hasResult ? "Görsel hazır; nesne sayısı alınamadı." : "Analiz sonucu bekleniyor."}</span>}
    </div>
  );
}
