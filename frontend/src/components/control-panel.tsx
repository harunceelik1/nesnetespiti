import type { ChangeEvent, FormEvent, ReactNode } from "react";
import { AlertTriangle, ImageUp, Loader2, MousePointerSquareDashed, Search, Type } from "lucide-react";
import { SENSITIVITY_LABELS, type Sensitivity } from "@/lib/detection-api";
import { cn } from "@/lib/utils";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

function Step({ number, title, children, htmlFor }: { number: number; title: string; children: ReactNode; htmlFor?: string }) {
  const heading = <><span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary">{number}</span>{title}</>;
  return (
    <div className="flex flex-col gap-2.5">
      {htmlFor
        ? <label htmlFor={htmlFor} className="flex items-center gap-2 text-sm font-medium">{heading}</label>
        : <div className="flex items-center gap-2 text-sm font-medium">{heading}</div>}
      {children}
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
      <Card className="gap-0 py-0">
        <CardContent className="px-5 py-5">
          <form className="flex flex-col gap-6" onSubmit={props.onSubmit}>
            <Step number={1} title="Görsel">
              <input id="image-file" className="sr-only" type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" disabled={busy} onChange={props.onChooseImage} />
              <label htmlFor="image-file" className={cn(
                "flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border border-dashed border-input bg-muted/40 px-4 py-6 text-center transition-colors hover:border-primary/40 hover:bg-accent",
                busy && "pointer-events-none opacity-60")}>
                {checkingFile ? <Loader2 aria-hidden="true" className="size-5 animate-spin text-muted-foreground" /> : <ImageUp aria-hidden="true" className="size-5 text-muted-foreground" />}
                <span className="text-sm font-medium">{checkingFile ? "Görsel kontrol ediliyor…" : image ? "Görseli değiştir" : "Görsel yükle"}</span>
                <span className="text-xs text-muted-foreground">JPG veya PNG</span>
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
              {example && <p className="rounded-md bg-accent px-3 py-2 text-xs leading-relaxed text-accent-foreground">
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

            <fieldset className="sensitivity-group flex min-w-0 flex-col gap-2.5" disabled={busy}>
              <legend className="mb-2.5 text-sm font-medium">Hassasiyet</legend>
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
            </fieldset>

            <Button type="submit" size="lg" className="w-full" disabled={!canSubmit}>
              {loading ? <Loader2 aria-hidden="true" className="animate-spin" /> : <Search aria-hidden="true" />}
              {buttonText}
            </Button>
          </form>
          {(error || warning) && <div className="mt-4 flex flex-col gap-2">
            {error && <Alert variant="destructive" role="alert"><AlertTriangle aria-hidden="true" /><span>{messageText(error)}</span></Alert>}
            {warning && <Alert variant="warning" role="status"><AlertTriangle aria-hidden="true" /><span>{messageText(warning)}</span></Alert>}
          </div>}
        </CardContent>
      </Card>
    </aside>
  );
}
