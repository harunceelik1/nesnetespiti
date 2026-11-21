import type { ChangeEvent, FormEvent } from "react";
import { SENSITIVITY_LABELS, type ModelSelection, type Sensitivity } from "@/lib/detection-api";

const SENSITIVITY_HELP: Record<Sensitivity, string> = {
  strict: "Yalnızca emin olunan kutular. Bazı gerçek nesneler kaçabilir.",
  balanced: "Önerilen. Olmayan nesneye kutu çizmeyecek şekilde ayarlandı.",
  loose: "Daha çok nesne bulur ama olmayan nesneye de kutu çizebilir.",
};

interface Props {
  image: File | null;
  query: string;
  busy: boolean;
  loading: boolean;
  checkingFile: boolean;
  model: ModelSelection;
  onModelChange: (model: ModelSelection) => void;
  sensitivity: Sensitivity;
  onSensitivityChange: (sensitivity: Sensitivity) => void;
  error: string | null;
  warning: string | null;
  onChooseImage: (event: ChangeEvent<HTMLInputElement>) => void;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function messageText(message: string): string {
  // Beklenmeyen sunucu yanıtlarını stack trace olarak arayüze taşımayız.
  if (/traceback|stack trace|at \w+\s*\(/i.test(message)) return "İşlem tamamlanamadı. Lütfen tekrar deneyin.";
  return message.split(/\r?\n/)[0].slice(0, 260);
}

export default function ControlPanel(props: Props) {
  const { image, query, busy, loading, checkingFile, error, warning } = props;
  return (
    <aside className="control-panel" aria-label="Analiz kontrolleri">
      <h2 className="panel-title">Analiz kontrolleri</h2>
      <form className="control-form" onSubmit={props.onSubmit}>
        <div className="field-group">
          <label className="field-label" htmlFor="image-file">Görsel</label>
          <input id="image-file" className="visually-hidden" type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" disabled={busy} onChange={props.onChooseImage} />
          <label htmlFor="image-file" className={"file-picker" + (busy ? " disabled" : "")}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true"><path d="M12 16V4m-4 4 4-4 4 4M4 15v5h16v-5" /></svg>
            <strong>{checkingFile ? "Görsel kontrol ediliyor…" : image ? "Görseli değiştir" : "Görsel yükle"}</strong>
            <span>JPG veya PNG</span>
          </label>
          <div className="file-metadata">
            <span className="file-name">{image?.name || "Henüz bir dosya seçilmedi."}</span>
            {image && <span>{(image.size / 1024 / 1024).toFixed(2)} MB</span>}
          </div>
        </div>
        <div className="field-group">
          <label className="field-label" htmlFor="object-query">Aranacak nesne</label>
          <input id="object-query" type="text" placeholder="Nesne veya nesne ifadesi" value={query} disabled={busy} onChange={(event) => props.onQueryChange(event.target.value)} autoComplete="off" aria-describedby="query-helper" />
          <p className="field-helper" id="query-helper">Birden fazla nesne için virgülle ayırın: şişe, kutu, çanta</p>
        </div>
        <div className="field-group">
          <label className="field-label" htmlFor="detector-model">Model</label>
          <select id="detector-model" value={props.model} disabled={busy} onChange={(event) => props.onModelChange(event.target.value as ModelSelection)}>
            <option value="owlvit">OWLv2</option>
            <option value="grounding-dino">Grounding DINO</option>
            <option value="yolo-world">YOLO-World</option>
            <option value="compare">Compare</option>
          </select>
        </div>
        <fieldset className="field-group sensitivity-group" disabled={busy}>
          <legend className="field-label">Hassasiyet</legend>
          <div className="segmented-control sensitivity-control">
            {(Object.keys(SENSITIVITY_LABELS) as Sensitivity[]).map((level) => <label key={level} className={props.sensitivity === level ? "is-selected" : undefined}>
              <input type="radio" name="sensitivity" value={level} checked={props.sensitivity === level}
                onChange={() => props.onSensitivityChange(level)} />
              {SENSITIVITY_LABELS[level]}
            </label>)}
          </div>
          <p className={"field-helper" + (props.sensitivity === "loose" ? " sensitivity-warning" : "")} id="sensitivity-helper">{SENSITIVITY_HELP[props.sensitivity]}</p>
        </fieldset>
        <button type="submit" className="detect-button" disabled={!image || !query.split(",").some((part) => part.trim()) || busy}>{loading ? "Tespit ediliyor…" : "Tespit Et"}</button>
      </form>
      {error && <p className="panel-message" role="alert">{messageText(error)}</p>}
      {warning && <p className="panel-message warning" role="status">{messageText(warning)}</p>}
    </aside>
  );
}
