import { useState, type KeyboardEvent } from "react";
import { ImageIcon, Loader2 } from "lucide-react";
import type { Box } from "@/lib/detection-api";
import { cn } from "@/lib/utils";
import ExampleSelector from "./example-selector";

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
  /** Örnekle arama: açıkken orijinal görselin üstüne kutu çizilir. */
  example?: { active: boolean; box: Box | null; onBoxChange: (box: Box | null) => void };
}

/** Görsel ve kutu çizme katmanı aynı iç boşluğu kullanır (ExampleSelector koordinatları buna dayanır). */
const IMAGE_INSET = "absolute inset-8";

export default function ImageViewer(props: Props) {
  const { previewUrl, resultUrl, filename, resultQuery, view, compare, loading, example } = props;
  const [originalImage, setOriginalImage] = useState<HTMLImageElement | null>(null);
  const drawing = !!example?.active && !!previewUrl;

  function switchTab(event: KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? "original" : event.key === "End" ? "result" : view === "original" ? "result" : "original";
    props.onViewChange(next);
    event.currentTarget.querySelector<HTMLButtonElement>("#tab-" + next)?.focus();
  }

  return (
    <section className="flex flex-col" aria-label="Görüntü inceleme">
      <div className="viewer-toolbar flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
        <div className="segmented-control flex" role="tablist" aria-label="Görünüm" tabIndex={-1} onKeyDown={switchTab}>
          {(["original", "result"] as const).map((mode) => (
            <button key={mode} id={"tab-" + mode} type="button" role="tab" aria-selected={view === mode} aria-controls="image-viewer"
              tabIndex={view === mode ? 0 : -1} onClick={() => props.onViewChange(mode)}
              className={cn("-mb-px rounded-t-md px-4 pb-2 pt-2.5 text-sm font-semibold outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50",
                view === mode ? "bg-stage text-white" : "text-muted-foreground hover:text-foreground")}>
              {mode === "original" ? "Orijinal" : "Tespit Sonucu"}
            </button>
          ))}
        </div>
        <div className="flex min-w-0 items-center gap-4 pb-2">
          {resultQuery && <span className="flex min-w-0 items-center gap-2 text-sm" title={resultQuery}>
            <span aria-hidden="true" className="size-2.5 shrink-0 border-2 border-signal" />
            <span className="truncate font-semibold">{resultQuery}</span>
          </span>}
          <label className="compare-option hidden cursor-pointer items-center gap-2 text-xs text-muted-foreground sm:flex">
            <input type="checkbox" className="size-3.5 accent-primary" checked={compare} disabled={!previewUrl || !resultUrl || drawing}
              onChange={(event) => props.onCompareChange(event.target.checked)} />
            Yan yana
          </label>
        </div>
      </div>
      {drawing && view === "original" && <p role="status" className="bg-signal px-4 py-2 text-xs font-medium text-white">
        {example.box ? "Örnek seçildi. İstersen yeniden çizebilirsin." : "Aradığın nesnelerden birinin etrafına sürükleyerek kutu çiz."}
      </p>}
      <div id="image-viewer" role="tabpanel" aria-labelledby={"tab-" + view} tabIndex={0}
        className={cn("viewer-canvas viewfinder stage-grid h-[clamp(320px,64dvh,780px)] overflow-hidden rounded-b-md rounded-tr-md outline-none focus-visible:ring-[3px] focus-visible:ring-ring/60",
          loading && "is-scanning")}>
        <div className="corners" aria-hidden="true" />
        {loading && <div className="scan-line" aria-hidden="true" />}
        <div className={cn("viewer-grid grid h-full grid-cols-1", compare && "is-compare sm:grid-cols-2 sm:divide-x sm:divide-stage-line")}>
          {(["original", "result"] as const).map((mode) => {
            const url = mode === "original" ? previewUrl : resultUrl;
            const visible = compare || view === mode;
            return (
              <figure key={mode} className={cn("viewer-pane relative m-0 min-h-0", visible ? "is-active block" : "hidden")}>
                {compare && <figcaption className="absolute left-10 top-3 z-10 text-xs text-white/70">{mode === "original" ? "Orijinal" : "Tespit Sonucu"}</figcaption>}
                {url
                  ? <>
                    <img src={url} ref={mode === "original" ? setOriginalImage : undefined}
                      className={cn(IMAGE_INSET, "h-[calc(100%-4rem)] w-[calc(100%-4rem)] object-contain", compare && "top-10 h-[calc(100%-4.5rem)]")}
                      alt={mode === "original" ? "Orijinal görüntü: " + filename : resultQuery + " sorgusunun işaretlenmiş sonucu"} />
                    {mode === "original" && drawing && view === "original" && <ExampleSelector className={IMAGE_INSET} image={originalImage} box={example.box} onChange={example.onBoxChange} />}
                  </>
                  : <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-8 text-center">
                    {mode === "result" && loading
                      ? <Loader2 aria-hidden="true" className="size-7 animate-spin text-white/60" />
                      : <ImageIcon aria-hidden="true" className="size-9 text-white/35" strokeWidth={1.25} />}
                    <strong className="text-base font-semibold text-white/90">{mode === "original" ? "İncelemek için bir görsel yükle" : loading ? "Tespit devam ediyor" : "Henüz bir tespit sonucu yok"}</strong>
                    <p className="max-w-xs text-sm text-white/55">{mode === "original" ? "Soldaki panelden görsel seç ve ne aradığını yaz." : loading ? "Bu sırada görseli Orijinal sekmesinden inceleyebilirsin." : "Görsel ve sorgu hazır olduğunda Tespit Et düğmesine bas."}</p>
                  </div>}
              </figure>
            );
          })}
        </div>
      </div>
      {filename && <p className="viewer-caption truncate pt-2 text-xs text-muted-foreground" title={filename}>{filename}</p>}
    </section>
  );
}
