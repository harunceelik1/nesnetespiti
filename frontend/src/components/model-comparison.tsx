import { AlertTriangle, ImageIcon, Loader2 } from "lucide-react";
import { MODEL_NAMES } from "@/lib/detection-api";
import { DETECTOR_MODELS, type ModelResults } from "@/lib/model-result";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import ResultSummary from "./result-summary";
import InventorySummary from "./inventory-summary";

interface Props {
  results: ModelResults;
  previewUrl: string | null;
  query: string;
  loading: boolean;
}

const MODEL_NOTES: Record<string, string> = {
  owlvit: "Görünüşe göre eşleştirir",
  "grounding-dino": "Soyut ifadelerde güçlü",
  "yolo-world": "Hızlı, yaygın nesnelerde iyi",
};

export default function ModelComparison({ results, previewUrl, query, loading }: Props) {
  return (
    <section aria-label="Model karşılaştırması" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">Model karşılaştırması</span>
        <span role="status" aria-live="polite" className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {loading && <Loader2 aria-hidden="true" className="size-3.5 animate-spin" />}
          {loading ? "Modeller çalışıyor…" : "Aynı görsel · aynı sorgu"}
        </span>
      </div>
      <div className="model-comparison grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {DETECTOR_MODELS.map((model) => {
          const result = results[model];
          return (
            <Card key={model} className="model-output gap-4 overflow-hidden py-0" data-model={model} aria-label={MODEL_NAMES[model]} role="region">
              <div className="flex items-baseline justify-between gap-2 px-4 pt-4">
                <h2 className="text-sm font-semibold">{MODEL_NAMES[model]}</h2>
                <span className="text-[11px] text-muted-foreground">{MODEL_NOTES[model]}</span>
              </div>
              <div className="model-canvas relative aspect-[4/3] bg-muted/50">
                {result.imageUrl || previewUrl
                  ? <img className="absolute inset-3 h-[calc(100%-1.5rem)] w-[calc(100%-1.5rem)] object-contain" src={result.imageUrl || previewUrl!}
                    alt={result.imageUrl ? MODEL_NAMES[model] + " · " + query + " tespit sonucu" : "Orijinal görüntü · " + MODEL_NAMES[model] + " sonucu bekleniyor"} />
                  : <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 text-center">
                    <ImageIcon aria-hidden="true" className="size-7 text-muted-foreground/60" strokeWidth={1.25} />
                    <strong className="text-sm font-medium">Görsel yükle</strong>
                    <p className="text-xs text-muted-foreground">Modellerin sonuçları burada gösterilecek.</p>
                  </div>}
                {!result.imageUrl && previewUrl && <Badge variant="secondary" className="original-indicator absolute left-3 top-3">Orijinal</Badge>}
              </div>
              <div className="flex flex-col gap-3 px-4 pb-4">
                <ResultSummary details={result.details} hasResult={!!result.imageUrl} failed={!!result.error} phase={result.phase === "image" || result.phase === "details" ? result.phase : "idle"} />
                <InventorySummary details={result.details} />
                {result.error && <Alert variant="destructive" role="alert"><AlertTriangle aria-hidden="true" /><span>{result.error}</span></Alert>}
                {result.warning && <Alert variant="warning" role="status"><AlertTriangle aria-hidden="true" /><span>{result.warning}</span></Alert>}
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
