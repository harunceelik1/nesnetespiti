import { CheckCircle2, CircleAlert, Clock, Cpu, Loader2 } from "lucide-react";
import { MODEL_NAMES, type DetectionDetails } from "@/lib/detection-api";

interface Props {
  details: DetectionDetails | null;
  hasResult: boolean;
  phase: "idle" | "image" | "details";
  failed?: boolean;
}

const Dot = () => <span className="separator text-muted-foreground/50" aria-hidden="true">·</span>;

export default function ResultSummary({ details, hasResult, phase, failed = false }: Props) {
  return (
    <div className="result-summary flex min-h-7 flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground tabular-nums" role="status" aria-live="polite" aria-atomic="true">
      {failed ? <span className="flex items-center gap-1.5 text-destructive"><CircleAlert aria-hidden="true" className="size-4" />Analiz tamamlanamadı.</span>
        : phase === "image" ? <span className="flex items-center gap-1.5"><Loader2 aria-hidden="true" className="size-4 animate-spin" />Görüntü analiz ediliyor…</span>
          : phase === "details" ? <span>Görsel hazır, tespit bilgileri alınıyor…</span>
            : details ? <>
              <CheckCircle2 aria-hidden="true" className="size-4 text-primary" />
              <strong className="font-semibold text-foreground">{details.filtered_detection_count} nesne bulundu</strong>
              <Dot />
              <span className="inline-flex items-center gap-1" title="Backend inference süresi"><Clock aria-hidden="true" className="size-3.5" />{Math.round(details.inference_time_ms).toLocaleString("tr-TR")} ms</span>
              <Dot /><span>{MODEL_NAMES[details.model_id]}</span>
              <Dot /><span className="inline-flex items-center gap-1"><Cpu aria-hidden="true" className="size-3.5" />{details.device.toUpperCase()}</span>
            </> : <span>{hasResult ? "Görsel hazır; nesne sayısı alınamadı." : "Analiz sonucu bekleniyor."}</span>}
    </div>
  );
}
