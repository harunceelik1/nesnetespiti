import { useState, type KeyboardEvent } from "react";
import { ImageIcon, Loader2 } from "lucide-react";
import type { Box } from "@/lib/detection-api";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Segmented, segmentClass } from "@/components/ui/segmented";
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
const IMAGE_INSET = "absolute inset-4";

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
    <Card className="gap-0 overflow-hidden py-0" aria-label="Görüntü inceleme" role="region">
      <div className="viewer-toolbar flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <Segmented className="segmented-control w-auto" role="tablist" aria-label="Görünüm" tabIndex={-1} onKeyDown={switchTab}>
          {(["original", "result"] as const).map((mode) => (
            <button key={mode} id={"tab-" + mode} type="button" role="tab" aria-selected={view === mode} aria-controls="image-viewer"
              tabIndex={view === mode ? 0 : -1} className={segmentClass(view === mode, "flex-none px-4")} onClick={() => props.onViewChange(mode)}>
              {mode === "original" ? "Orijinal" : "Tespit Sonucu"}
            </button>
          ))}
        </Segmented>
        <div className="flex min-w-0 items-center gap-3">
          {resultQuery && <Badge variant="secondary" className="max-w-[16rem] truncate" title={resultQuery}>{resultQuery}</Badge>}
          <label className="compare-option hidden cursor-pointer items-center gap-2 text-xs text-muted-foreground sm:flex">
            <input type="checkbox" className="size-3.5 accent-primary" checked={compare} disabled={!previewUrl || !resultUrl || drawing}
              onChange={(event) => props.onCompareChange(event.target.checked)} />
            Yan yana
          </label>
        </div>
      </div>
      {drawing && view === "original" && <p role="status" className="border-b bg-accent px-4 py-2 text-xs text-accent-foreground">
        {example.box ? "Örnek seçildi. İstersen yeniden çizebilirsin." : "Aradığın nesnelerden birinin etrafına sürükleyerek kutu çiz."}
      </p>}
      <div id="image-viewer" role="tabpanel" aria-labelledby={"tab-" + view} tabIndex={0}
        className="viewer-canvas h-[clamp(320px,62dvh,760px)] bg-muted/50 outline-none">
        <div className={cn("viewer-grid grid h-full grid-cols-1", compare && "is-compare sm:grid-cols-2 sm:divide-x")}>
          {(["original", "result"] as const).map((mode) => {
            const url = mode === "original" ? previewUrl : resultUrl;
            const visible = compare || view === mode;
            return (
              <figure key={mode} className={cn("viewer-pane relative m-0 min-h-0", visible ? "is-active block" : "hidden")}>
                {compare && <figcaption className="absolute left-4 top-2 z-10 text-[11px] text-muted-foreground">{mode === "original" ? "Orijinal" : "Tespit Sonucu"}</figcaption>}
                {url
                  ? <>
                    <img src={url} ref={mode === "original" ? setOriginalImage : undefined}
                      className={cn(IMAGE_INSET, "h-[calc(100%-2rem)] w-[calc(100%-2rem)] object-contain", compare && "top-7 h-[calc(100%-2.75rem)]")}
                      alt={mode === "original" ? "Orijinal görüntü: " + filename : resultQuery + " sorgusunun işaretlenmiş sonucu"} />
                    {mode === "original" && drawing && view === "original" && <ExampleSelector className={IMAGE_INSET} image={originalImage} box={example.box} onChange={example.onBoxChange} />}
                  </>
                  : <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-8 text-center">
                    {mode === "result" && loading
                      ? <Loader2 aria-hidden="true" className="size-8 animate-spin text-muted-foreground" />
                      : <ImageIcon aria-hidden="true" className="size-9 text-muted-foreground/60" strokeWidth={1.25} />}
                    <strong className="text-sm font-medium text-foreground/80">{mode === "original" ? "İncelemek için bir görsel yükle" : loading ? "Tespit devam ediyor" : "Henüz bir tespit sonucu yok"}</strong>
                    <p className="max-w-xs text-xs text-muted-foreground">{mode === "original" ? "Soldaki panelden görsel seç ve ne aradığını yaz." : loading ? "Bu sırada görseli Orijinal sekmesinden inceleyebilirsin." : "Görsel ve sorgu hazır olduğunda Tespit Et düğmesine bas."}</p>
                  </div>}
              </figure>
            );
          })}
        </div>
      </div>
      {filename && <p className="viewer-caption truncate border-t px-4 py-2 text-xs text-muted-foreground" title={filename}>{filename}</p>}
    </Card>
  );
}
