import { useState, type KeyboardEvent } from "react";
import { AlertTriangle, Columns3, ImageIcon, Loader2, Maximize2 } from "lucide-react";
import { MODEL_NAMES, type DetectorModel } from "@/lib/detection-api";
import { DETECTOR_MODELS, type ModelResult, type ModelResults } from "@/lib/model-result";
import { cn } from "@/lib/utils";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Segmented, segmentClass } from "@/components/ui/segmented";
import ResultSummary from "./result-summary";
import InventorySummary from "./inventory-summary";

interface Props {
  results: ModelResults;
  previewUrl: string | null;
  query: string;
  loading: boolean;
}

type Layout = "focus" | "grid";

const MODEL_NOTES: Record<DetectorModel, string> = {
  owlvit: "Görünüşe göre eşleştirir",
  "grounding-dino": "Soyut ifadelerde güçlü",
  "yolo-world": "Hızlı, yaygın nesnelerde iyi",
};

const busy = (result: ModelResult) => result.phase === "image" || result.phase === "details";

/** Sekmedeki kısa durum: sayı, dönen çark ya da hata işareti. */
function TabStatus({ result }: { result: ModelResult }) {
  if (busy(result)) return <Loader2 aria-label="çalışıyor" className="animate-spin" />;
  if (result.error) return <AlertTriangle aria-label="hata" className="text-destructive" />;
  if (!result.details) return null;
  return <span className="model-count rounded-full bg-muted px-1.5 text-xs tabular-nums text-muted-foreground">{result.details.filtered_detection_count}</span>;
}

/**
 * Üç modelin sonucu. Varsayılan "Büyük" düzende tek model tam boyutta gösterilir ve
 * sekmelerle geçilir; "Yan yana" düzeni üç görseli küçük ama birlikte gösterir.
 * Özetler her iki düzende de altta üç sütun olarak durur.
 */
export default function ModelComparison({ results, previewUrl, query, loading }: Props) {
  const [active, setActive] = useState<DetectorModel>("owlvit");
  const [layout, setLayout] = useState<Layout>("focus");
  const focus = layout === "focus";

  function switchTab(event: KeyboardEvent<HTMLDivElement>) {
    const index = DETECTOR_MODELS.indexOf(active);
    const last = DETECTOR_MODELS.length - 1;
    const next = { ArrowLeft: index === 0 ? last : index - 1, ArrowRight: index === last ? 0 : index + 1, Home: 0, End: last }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    setActive(DETECTOR_MODELS[next]);
    event.currentTarget.querySelector<HTMLButtonElement>("#model-tab-" + DETECTOR_MODELS[next])?.focus();
  }

  function show(model: DetectorModel) {
    setActive(model);
    setLayout("focus");
  }

  return (
    <section aria-label="Model karşılaştırması" className="model-comparison flex flex-col gap-4">
      <Card className="gap-0 overflow-hidden py-0">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
          {focus
            ? <Segmented className="model-tabs w-auto max-w-full overflow-x-auto" role="tablist" aria-label="Gösterilen model" onKeyDown={switchTab}>
              {DETECTOR_MODELS.map((model) => (
                <button key={model} id={"model-tab-" + model} type="button" role="tab" aria-selected={active === model}
                  aria-controls="model-viewer" tabIndex={active === model ? 0 : -1}
                  className={segmentClass(active === model, "flex-none px-3")} onClick={() => setActive(model)}>
                  {MODEL_NAMES[model]}<TabStatus result={results[model]} />
                </button>
              ))}
            </Segmented>
            : <span className="text-sm font-medium">Üç model yan yana</span>}
          <div className="flex items-center gap-3">
            <span role="status" aria-live="polite" className="hidden items-center gap-1.5 text-xs text-muted-foreground md:flex">
              {loading && <Loader2 aria-hidden="true" className="size-3.5 animate-spin" />}
              {loading ? "Modeller çalışıyor…" : query ? "Aynı görsel · aynı sorgu" : null}
            </span>
            <Segmented className="layout-toggle w-auto" role="radiogroup" aria-label="Düzen">
              {([["focus", "Büyük", Maximize2], ["grid", "Yan yana", Columns3]] as const).map(([value, label, Icon]) => (
                <button key={value} type="button" role="radio" aria-checked={layout === value} title={label}
                  className={segmentClass(layout === value, "flex-none px-2.5")} onClick={() => setLayout(value)}>
                  <Icon aria-hidden="true" /><span className="hidden sm:inline">{label}</span>
                </button>
              ))}
            </Segmented>
          </div>
        </div>
        <div id="model-viewer" role={focus ? "tabpanel" : undefined} aria-labelledby={focus ? "model-tab-" + active : undefined}
          className={cn("bg-muted/50", focus ? "relative h-[clamp(320px,62dvh,760px)]" : "grid sm:grid-cols-3 sm:divide-x")}>
          {DETECTOR_MODELS.map((model) => {
            const result = results[model];
            const url = result.imageUrl || previewUrl;
            const visible = !focus || active === model;
            return (
              <figure key={model} data-model-image={model}
                className={cn("model-canvas relative m-0", focus ? "absolute inset-0" : "h-[clamp(220px,40dvh,480px)]", !visible && "hidden")}>
                {!focus && <figcaption className="absolute left-3 top-2 z-10 text-xs font-medium text-muted-foreground">{MODEL_NAMES[model]}</figcaption>}
                {url
                  ? <button type="button" disabled={focus} onClick={() => show(model)} title={focus ? undefined : MODEL_NAMES[model] + " sonucunu büyüt"}
                    className={cn("absolute", focus ? "inset-4 cursor-default" : "inset-x-3 top-7 bottom-3 cursor-zoom-in")}>
                    <img src={url} className="size-full object-contain"
                      alt={result.imageUrl ? MODEL_NAMES[model] + " · " + query + " tespit sonucu" : "Orijinal görüntü · " + MODEL_NAMES[model] + " sonucu bekleniyor"} />
                  </button>
                  : <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 p-6 text-center">
                    <ImageIcon aria-hidden="true" className="size-8 text-muted-foreground/60" strokeWidth={1.25} />
                    <strong className="text-sm font-medium">Görsel yükle</strong>
                    <p className="text-xs text-muted-foreground">Modellerin sonuçları burada gösterilecek.</p>
                  </div>}
                {!result.imageUrl && previewUrl && (
                  <Badge variant="secondary" className={cn("original-indicator absolute right-3", focus ? "top-3" : "top-2")}>
                    {busy(result) ? "Çalışıyor…" : "Orijinal"}
                  </Badge>
                )}
              </figure>
            );
          })}
        </div>
      </Card>
      <Card className="model-summaries gap-0 overflow-hidden py-0 md:grid md:grid-cols-3 md:divide-x">
        {DETECTOR_MODELS.map((model) => {
          const result = results[model];
          const selected = focus && active === model;
          return (
            <div key={model} data-model={model} role="region" aria-label={MODEL_NAMES[model]}
              className={cn("model-output flex min-w-0 flex-col gap-3 px-4 py-4 transition-colors max-md:border-t max-md:first:border-t-0",
                selected && "bg-accent/60")}>
              <button type="button" onClick={() => show(model)} className="flex cursor-pointer flex-col items-start gap-0.5 text-left outline-none focus-visible:underline">
                <h2 className="text-sm font-semibold">{MODEL_NAMES[model]}</h2>
                <span className="text-[11px] text-muted-foreground">{MODEL_NOTES[model]}</span>
              </button>
              <ResultSummary details={result.details} hasResult={!!result.imageUrl} failed={!!result.error} phase={busy(result) ? result.phase as "image" | "details" : "idle"} />
              <InventorySummary details={result.details} />
              {result.error && <Alert variant="destructive" role="alert"><AlertTriangle aria-hidden="true" /><span>{result.error}</span></Alert>}
              {result.warning && <Alert variant="warning" role="status"><AlertTriangle aria-hidden="true" /><span>{result.warning}</span></Alert>}
            </div>
          );
        })}
      </Card>
    </section>
  );
}
