import type { KeyboardEvent } from "react";

export type ViewerMode = "original" | "result";

interface Props {
  previewUrl: string | null;
  resultUrl: string | null;
  filename: string | null;
  resultQuery: string;
  view: ViewerMode;
  compare: boolean;
  loading: boolean;
  onViewChange: (view: ViewerMode) => void;
  onCompareChange: (compare: boolean) => void;
}

export default function ImageViewer(props: Props) {
  const { previewUrl, resultUrl, filename, resultQuery, view, compare, loading } = props;

  function switchTab(event: KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? "original" : event.key === "End" ? "result" : view === "original" ? "result" : "original";
    props.onViewChange(next);
    event.currentTarget.querySelector<HTMLButtonElement>("#tab-" + next)?.focus();
  }

  return (
    <section aria-label="Görüntü inceleme">
      <div className="viewer-toolbar">
        <div className="segmented-control" role="tablist" aria-label="Görünüm" tabIndex={-1} onKeyDown={switchTab}>
          <button id="tab-original" type="button" role="tab" aria-selected={view === "original"} aria-controls="image-viewer" tabIndex={view === "original" ? 0 : -1} onClick={() => props.onViewChange("original")}>Orijinal</button>
          <button id="tab-result" type="button" role="tab" aria-selected={view === "result"} aria-controls="image-viewer" tabIndex={view === "result" ? 0 : -1} onClick={() => props.onViewChange("result")}>Tespit Sonucu</button>
        </div>
        <label className="compare-option"><input type="checkbox" checked={compare} disabled={!previewUrl || !resultUrl} onChange={(event) => props.onCompareChange(event.target.checked)} />Yan yana karşılaştır</label>
      </div>
      <div className="viewer-caption">
        <span title={filename ?? undefined}>{filename || "Görüntü çalışma alanı"}</span>
        <span>{resultQuery || (previewUrl ? "Analize hazır" : "—")}</span>
      </div>
      <div id="image-viewer" className="viewer-canvas" role="tabpanel" aria-labelledby={"tab-" + view} tabIndex={0}>
        <div className={"viewer-grid" + (compare ? " is-compare" : "")}>
          {(["original", "result"] as const).map((mode) => {
            const url = mode === "original" ? previewUrl : resultUrl;
            return (
              <figure key={mode} className={"viewer-pane" + (view === mode ? " is-active" : "")}>
                <figcaption>{mode === "original" ? "Orijinal" : "Tespit Sonucu"}</figcaption>
                {url
                  ? <img src={url} alt={mode === "original" ? "Orijinal görüntü: " + filename : resultQuery + " sorgusunun işaretlenmiş sonucu"} />
                  : <div className="viewer-empty">
                    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.2" aria-hidden="true"><rect x="5" y="7" width="30" height="26" rx="2" /><circle cx="14" cy="15" r="3" /><path d="m6 29 9-9 6 6 5-5 9 9" /></svg>
                    <strong>{mode === "original" ? "İncelemek için bir görsel yükleyin" : loading ? "Tespit devam ediyor" : "Henüz bir tespit sonucu yok"}</strong>
                    <p>{mode === "original" ? "Soldaki panelden görsel seçin ve aranacak nesneyi yazın." : loading ? "Mevcut görseli Orijinal sekmesinden inceleyebilirsiniz." : "Görsel ve sorgu hazır olduğunda Tespit Et düğmesini kullanın."}</p>
                  </div>}
              </figure>
            );
          })}
        </div>
      </div>
    </section>
  );
}
