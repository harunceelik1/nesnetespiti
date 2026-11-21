import { MODEL_NAMES } from "@/lib/detection-api";
import { DETECTOR_MODELS, type ModelResults } from "@/lib/model-result";
import ResultSummary from "./result-summary";
import InventorySummary from "./inventory-summary";

interface Props {
  results: ModelResults;
  previewUrl: string | null;
  query: string;
  loading: boolean;
}

export default function ModelComparison({ results, previewUrl, query, loading }: Props) {
  return (
    <section aria-label="Model karşılaştırması">
      <div className="comparison-heading">
        <span>Model karşılaştırması</span>
        <span role="status" aria-live="polite">{loading ? "Modeller çalışıyor…" : "Aynı görsel · aynı sorgu"}</span>
      </div>
      <div className="model-comparison">
        {DETECTOR_MODELS.map((model) => {
          const result = results[model];
          return (
            <section key={model} className="model-output" data-model={model} aria-label={MODEL_NAMES[model]}>
              <h2>{MODEL_NAMES[model]}</h2>
              <div className="model-canvas">
                {result.imageUrl || previewUrl
                  ? <img src={result.imageUrl || previewUrl!} alt={result.imageUrl ? MODEL_NAMES[model] + " · " + query + " tespit sonucu" : "Orijinal görüntü · " + MODEL_NAMES[model] + " sonucu bekleniyor"} />
                  : <div className="viewer-empty"><strong>Görsel yükleyin</strong><p>Modellerin sonuçları burada gösterilecek.</p></div>}
                {!result.imageUrl && previewUrl && <span className="original-indicator">Orijinal</span>}
              </div>
              <ResultSummary details={result.details} hasResult={!!result.imageUrl} failed={!!result.error} phase={result.phase === "image" || result.phase === "details" ? result.phase : "idle"} />
              <InventorySummary details={result.details} />
              {result.error && <p className="panel-message" role="alert">{result.error}</p>}
              {result.warning && <p className="panel-message warning" role="status">{result.warning}</p>}
            </section>
          );
        })}
      </div>
    </section>
  );
}
