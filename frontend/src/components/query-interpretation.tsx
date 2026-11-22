"use client";

import { useState, type FormEvent } from "react";
import { Languages, MousePointerSquareDashed, Pencil, TriangleAlert } from "lucide-react";
import type { DetectionDetails } from "@/lib/detection-api";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Props {
  details: DetectionDetails | null;
  busy: boolean;
  onRetry: (englishQuery: string) => void;
}

const SOURCE_LABELS: Record<string, string> = {
  // context: bağlam cümlesiyle çeviri (varsayılan yol). model: cümle kalıp dışı kaldı,
  // sorgu tek başına çevrildi; daha az güvenilir olduğu için uyarı rengiyle gösterilir.
  context: "çeviri",
  lexicon: "sözlükten",
  model: "düz çeviri, kontrol et",
  user: "senin düzeltmen",
  mixed: "birden fazla kaynak",
};

function sourceLabel(details: DetectionDetails): string {
  if (details.translation_source) return SOURCE_LABELS[details.translation_source] ?? details.translation_source;
  return "İngilizce yazıldı, çevrilmedi";
}

/** Modele gerçekte giden İngilizce ifadeyi gösterir; kullanıcı düzeltip tekrar arayabilir. */
export default function QueryInterpretation({ details, busy, onRetry }: Props) {
  // Üst bileşen key={primary_query} verir: yeni sonuçta düzenleme ve taslak sıfırlanır.
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(details?.primary_query ?? "");

  if (!details?.primary_query) return null;
  if (details.search_mode === "example") return (
    <section className="query-interpretation flex flex-wrap items-center gap-2 text-sm" aria-label="Aranan ifade">
      <MousePointerSquareDashed aria-hidden="true" className="size-4 text-muted-foreground" />
      <span className="query-caption text-muted-foreground">Arama</span>
      <span>Çizdiğin örneğe görsel olarak benzeyenler</span>
      <Badge variant="outline" className="query-source font-normal text-muted-foreground">metin ve çeviri kullanılmadı</Badge>
    </section>
  );
  const multi = (details.processed_query_items?.length ?? 0) > 1;
  const fromModel = details.translation_source === "model" || details.translation_source === "mixed";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = draft.trim();
    if (!value || busy) return;
    onRetry(value);
  }

  return (
    <section className={cn("query-interpretation flex flex-col gap-2 text-sm", fromModel && "uncertain")} aria-label="Aranan ifade">
      {!editing ? <div className="query-line flex flex-wrap items-center gap-2">
        <Languages aria-hidden="true" className="size-4 text-muted-foreground" />
        <span className="query-caption text-muted-foreground">Aranan ifade</span>
        <code className="query-value rounded-md bg-muted px-2 py-0.5 font-mono text-[13px] text-foreground">{details.primary_query}</code>
        <Badge variant={fromModel ? "warning" : "outline"} className="query-source font-normal">{sourceLabel(details)}</Badge>
        <Button type="button" variant="link" size="sm" className="h-auto gap-1 text-xs" disabled={busy} onClick={() => setEditing(true)}>
          <Pencil aria-hidden="true" className="size-3" />Düzenle
        </Button>
      </div> : <form className="query-edit flex flex-col gap-2" onSubmit={submit}>
        <label className="query-caption text-xs text-muted-foreground" htmlFor="english-query">Aranan ifade (İngilizce)</label>
        <div className="flex flex-wrap gap-2">
          <Input id="english-query" type="text" className="h-9 flex-1 basis-48 font-mono" value={draft} autoComplete="off" disabled={busy}
            onChange={(event) => setDraft(event.target.value)} />
          <Button type="submit" size="sm" className="h-9" disabled={busy || !draft.trim()}>Bu ifadeyle ara</Button>
          <Button type="button" variant="ghost" size="sm" className="h-9" disabled={busy}
            onClick={() => { setEditing(false); setDraft(details.primary_query); }}>Vazgeç</Button>
        </div>
        {multi && <p className="text-xs text-muted-foreground">Virgülle ayır; sıra yukarıdaki sorgunla aynı olmalı.</p>}
      </form>}
      {fromModel && !editing && <p className="flex items-start gap-1.5 text-xs text-warning-foreground">
        <TriangleAlert aria-hidden="true" className="mt-px size-3.5 shrink-0" />
        Bu ifade çeviri modelinden geldi ve yanlış olabilir. Sonuç beklediğin gibi değilse düzenleyip tekrar ara.
      </p>}
    </section>
  );
}
