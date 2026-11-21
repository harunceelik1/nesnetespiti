"use client";

import { useState, type FormEvent } from "react";
import type { DetectionDetails } from "@/lib/detection-api";

interface Props {
  details: DetectionDetails | null;
  busy: boolean;
  onRetry: (englishQuery: string) => void;
}

const SOURCE_LABELS: Record<string, string> = {
  lexicon: "sözlükten",
  model: "çeviri modeli",
  user: "senin düzeltmen",
  mixed: "sözlük + çeviri",
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
  const multi = (details.processed_query_items?.length ?? 0) > 1;
  const fromModel = details.translation_source === "model" || details.translation_source === "mixed";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = draft.trim();
    if (!value || busy) return;
    onRetry(value);
  }

  return (
    <section className={"query-interpretation" + (fromModel ? " uncertain" : "")} aria-label="Aranan ifade">
      {!editing ? <div className="query-line">
        <span className="query-caption">Aranan ifade</span>
        <code className="query-value">{details.primary_query}</code>
        <span className="query-source">{sourceLabel(details)}</span>
        <button type="button" className="text-button" disabled={busy} onClick={() => setEditing(true)}>Düzenle</button>
      </div> : <form className="query-edit" onSubmit={submit}>
        <label className="query-caption" htmlFor="english-query">Aranan ifade (İngilizce)</label>
        <div className="query-edit-row">
          <input id="english-query" type="text" value={draft} autoComplete="off" disabled={busy}
            onChange={(event) => setDraft(event.target.value)} />
          <button type="submit" className="detect-button" disabled={busy || !draft.trim()}>Bu ifadeyle ara</button>
          <button type="button" className="text-button" disabled={busy}
            onClick={() => { setEditing(false); setDraft(details.primary_query); }}>Vazgeç</button>
        </div>
        {multi && <p className="field-helper">Virgülle ayırın; sıra yukarıdaki sorgunuzla aynı olmalı.</p>}
      </form>}
      {fromModel && !editing && <p className="field-helper">
        Bu ifade çeviri modelinden geldi ve yanlış olabilir. Sonuç beklediğin gibi değilse düzenleyip tekrar ara.
      </p>}
    </section>
  );
}
