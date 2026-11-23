import { CircleAlert, Loader2 } from "lucide-react";
import { MODEL_NAME, type DetectionDetails } from "@/lib/detection-api";

interface Props {
  details: DetectionDetails | null;
  hasResult: boolean;
  phase: "idle" | "image" | "details";
  failed?: boolean;
}

/** 25842 ms yerine "25,8 sn": tr-TR binlik noktası ondalık gibi okunuyordu. */
function duration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 1 })} sn`;
}

export default function ResultSummary({ details, hasResult, phase, failed = false }: Props) {
  const uncertain = details?.detections.filter((d) => d.uncertain).length ?? 0;
  return (
    <div className="result-summary flex min-h-14 flex-col justify-end gap-1.5 text-sm text-muted-foreground" role="status" aria-live="polite" aria-atomic="true">
      {failed ? <span className="flex items-center gap-2 text-base text-destructive"><CircleAlert aria-hidden="true" className="size-5" />Analiz tamamlanamadı.</span>
        : phase === "image" ? <span className="flex items-center gap-2 text-base text-foreground"><Loader2 aria-hidden="true" className="size-5 animate-spin text-signal" />Görüntü analiz ediliyor…</span>
          : phase === "details" ? <span>Görsel hazır, tespit bilgileri alınıyor…</span>
            : details ? <>
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <strong className="flex items-baseline gap-2 font-semibold text-foreground">
                  <span className="numerals text-[3.5rem] font-semibold leading-[0.8]">{details.filtered_detection_count}</span>
                  <span className="text-lg"> nesne bulundu</span>
                </strong>
                {uncertain > 0 && <span className="uncertain-count inline-flex items-center gap-1.5 text-warning-foreground"
                  title="Kesikli turuncu kutular: aynı nesnenin en iyi eşleşmesinin yarısından düşük puan aldı. Ölçümlerde bu kutuların çoğu yanlış çıktı; silinmedi, kontrol etmen için işaretlendi.">
                  <span aria-hidden="true" className="inline-block h-3 w-4 rounded-[2px] border-2 border-dashed border-caution" />
                  {uncertain} tanesi emin değil
                </span>}
              </div>
              <span className="flex flex-wrap gap-x-4 tabular-nums">
                <span title="Modelin çalışma süresi">{duration(details.inference_time_ms)}</span>
                <span>{MODEL_NAME}</span>
                <span>{details.device.toUpperCase()}</span>
              </span>
            </> : <span>{hasResult ? "Görsel hazır; nesne sayısı alınamadı." : "Sonuç burada görünecek: kaç nesne bulunduğu ve modele hangi ifadenin gittiği."}</span>}
    </div>
  );
}
