import type { ChangeEvent, FormEvent, ReactNode } from "react";
import { AlertTriangle, ImageUp, Loader2, MousePointerSquareDashed, Search, Type } from "lucide-react";
import { SENSITIVITY_LABELS, type Sensitivity } from "@/lib/detection-api";
import { cn } from "@/lib/utils";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Segmented, segmentClass } from "@/components/ui/segmented";

export type SearchMode = "text" | "example";

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
  mode: SearchMode;
  onModeChange: (mode: SearchMode) => void;
  /** Örnekle aramada görselde kutu çizildi mi. */
  exampleReady: boolean;
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

/** Adımlar gerçekten sıralı (görsel → sorgu → hassasiyet); numara bu sırayı gösterir. */
function Step({ number, title, children }: { number: number; title: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-x-3 border-t border-border py-5 first:border-t-0 first:pt-1">
      <span aria-hidden="true" className="numerals -mt-1 text-[2.5rem] font-light leading-none text-foreground/30">{number}</span>
      <div className="flex min-w-0 flex-col gap-2.5">
        <div className="text-base font-semibold leading-tight">{title}</div>
        {children}
      </div>
    </div>
  );
}

export default function ControlPanel(props: Props) {
  const { image, query, busy, loading, checkingFile, mode, error, warning } = props;
  const example = mode === "example";
  const canSubmit = !!image && !busy && (example ? props.exampleReady : query.split(",").some((part) => part.trim()));
  const buttonText = loading ? (example ? "Aranıyor…" : "Tespit ediliyor…") : example ? "Benzerlerini bul" : "Tespit Et";

  return (
    <aside className="control-panel lg:sticky lg:top-6" aria-label="Analiz kontrolleri">
          <form className="flex flex-col" onSubmit={props.onSubmit}>
            <Step number={1} title="Görsel">
              <input id="image-file" className="peer sr-only" type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" disabled={busy} onChange={props.onChooseImage} />
              <label htmlFor="image-file" className={cn(
                "flex cursor-pointer items-center gap-3 rounded-md border-[1.5px] border-dashed border-foreground/40 px-4 py-4 transition-colors hover:border-foreground hover:bg-card peer-focus-visible:ring-[3px] peer-focus-visible:ring-ring/50",
                busy && "pointer-events-none opacity-60")}>
                {checkingFile ? <Loader2 aria-hidden="true" className="size-5 shrink-0 animate-spin" /> : <ImageUp aria-hidden="true" className="size-5 shrink-0" strokeWidth={1.5} />}
                <span className="flex flex-col">
                  <span className="text-sm font-semibold">{checkingFile ? "Görsel kontrol ediliyor…" : image ? "Görseli değiştir" : "Görsel yükle"}</span>
                  <span className="text-xs text-muted-foreground">JPG veya PNG</span>
                </span>
              </label>
              <p className="flex justify-between gap-3 text-xs text-muted-foreground">
                <span className="file-name truncate" title={image?.name}>{image?.name || "Henüz bir dosya seçilmedi."}</span>
                {image && <span className="shrink-0 tabular-nums">{(image.size / 1024 / 1024).toFixed(2)} MB</span>}
              </p>
            </Step>

            <Step number={2} title="Ne arıyorsun?">
              <Segmented role="radiogroup" aria-label="Arama yolu">
                {([["text", "Metinle ara", Type], ["example", "Örnekle ara", MousePointerSquareDashed]] as const).map(([value, label, Icon]) => (
                  <button key={value} type="button" role="radio" aria-checked={mode === value} disabled={busy}
                    className={segmentClass(mode === value)} onClick={() => props.onModeChange(value)}>
                    <Icon aria-hidden="true" />{label}
                  </button>
                ))}
              </Segmented>
              {example && <p className="border-l-2 border-signal pl-3 text-xs leading-relaxed">
                {props.exampleReady ? "Örnek seçildi. Benzerlerini bulmak için aşağıdaki düğmeye bas." : "Sağdaki görselde aradığın nesnelerden birinin etrafına fareyle kutu çiz."}
              </p>}
              <label htmlFor="object-query" className="sr-only">{example ? "Ad (isteğe bağlı)" : "Aranacak nesne"}</label>
              <Input id="object-query" type="text" value={query} disabled={busy} autoComplete="off" aria-describedby="query-helper"
                placeholder={example ? "Ad (isteğe bağlı), ör. sakız" : "ör. ilaç kutusu, şişe"}
                onChange={(event) => props.onQueryChange(event.target.value)} />
              <p className="text-xs text-muted-foreground" id="query-helper">
                {example ? "Yazdığın ad yalnızca sonuçta etiket olarak görünür." : "Birden fazla nesne için virgülle ayır: şişe, kutu, çanta"}
              </p>
            </Step>

            <fieldset className="sensitivity-group grid min-w-0 grid-cols-[2.25rem_minmax(0,1fr)] gap-x-3 border-t border-border py-5" disabled={busy}>
              <legend className="sr-only">Hassasiyet</legend>
              <span aria-hidden="true" className="numerals -mt-1 text-[2.5rem] font-light leading-none text-foreground/30">3</span>
              <div className="flex min-w-0 flex-col gap-2.5">
              <div aria-hidden="true" className="text-base font-semibold leading-tight">Hassasiyet</div>
              <Segmented className="sensitivity-control">
                {(Object.keys(SENSITIVITY_LABELS) as Sensitivity[]).map((level) => (
                  <label key={level} className={segmentClass(props.sensitivity === level)}>
                    <input type="radio" name="sensitivity" value={level} className="sr-only" checked={props.sensitivity === level}
                      onChange={() => props.onSensitivityChange(level)} />
                    {SENSITIVITY_LABELS[level]}
                  </label>
                ))}
              </Segmented>
              <p id="sensitivity-helper" className={cn("text-xs", props.sensitivity === "loose" ? "sensitivity-warning text-warning-foreground" : "text-muted-foreground")}>
                {SENSITIVITY_HELP[props.sensitivity]}
              </p>
              </div>
            </fieldset>

            <Button type="submit" size="lg" className="w-full" disabled={!canSubmit}>
              {loading ? <Loader2 aria-hidden="true" className="animate-spin" /> : <Search aria-hidden="true" />}
              {buttonText}
            </Button>
            <p className="mt-2 text-xs leading-snug text-muted-foreground">İlk arama yaklaşık 30 saniye sürer. Aynı görselde sonraki aramalar birkaç saniyede biter.</p>
          </form>
          {(error || warning) && <div className="mt-4 flex flex-col gap-2">
            {error && <Alert variant="destructive" role="alert"><AlertTriangle aria-hidden="true" /><span>{messageText(error)}</span></Alert>}
            {warning && <Alert variant="warning" role="status"><AlertTriangle aria-hidden="true" /><span>{messageText(warning)}</span></Alert>}
          </div>}
    </aside>
  );
}
