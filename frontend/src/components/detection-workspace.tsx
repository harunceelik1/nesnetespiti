"use client";

import InventorySummary from "./inventory-summary";

import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { getDetectionAnalysis, getExampleAnalysis, type Box, type Sensitivity } from "@/lib/detection-api";
import { emptyResult, type ModelResult } from "@/lib/model-result";
import ControlPanel, { type SearchMode } from "./control-panel";
import ImageViewer, { type ViewerMode } from "./image-viewer";
import ResultSummary from "./result-summary";
import QueryInterpretation from "./query-interpretation";
import TechnicalDetails from "./technical-details";

export default function DetectionWorkspace() {
  const [sensitivity, setSensitivity] = useState<Sensitivity>("balanced");
  const [result, setResult] = useState<ModelResult>(emptyResult);
  const [view, setView] = useState<ViewerMode>("original");
  const [compare, setCompare] = useState(false);
  const [image, setImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [resultQuery, setResultQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingFile, setCheckingFile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // "example": kullanıcı orijinal görselde bir kutu çizer, benzerleri aranır.
  const [mode, setMode] = useState<SearchMode>("text");
  const [exampleBox, setExampleBox] = useState<Box | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const fileSelection = useRef(0);
  const resultUrl = useRef<string | null>(null);
  const busy = loading || checkingFile;

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  useEffect(() => () => {
    activeRequest.current?.abort();
    fileSelection.current += 1;
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current);
  }, []);

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current);
    resultUrl.current = null;
    setResult(emptyResult());
    setView("original");
    setCompare(false);
    setResultQuery("");
    setError(null);
  }

  async function chooseImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || busy) return;
    if (!/\.(jpe?g|png)$/i.test(file.name) || (file.type && !["image/jpeg", "image/png"].includes(file.type))) {
      setError("Lütfen JPG veya PNG formatında bir görsel seçin.");
      return;
    }
    const id = ++fileSelection.current;
    const url = URL.createObjectURL(file);
    setCheckingFile(true);
    setError(null);
    try {
      const decoder = new window.Image();
      decoder.src = url;
      await decoder.decode();
      if (id !== fileSelection.current) { URL.revokeObjectURL(url); return; }
      clearResult();
      setExampleBox(null);
      setImage(file);
      setPreviewUrl(url);
    } catch {
      URL.revokeObjectURL(url);
      if (id === fileSelection.current) setError("Bu görsel okunamadı. Başka bir JPG veya PNG dosyası deneyin.");
    } finally {
      if (id === fileSelection.current) setCheckingFile(false);
    }
  }

  function updateResult(update: Partial<ModelResult>) {
    setResult((current) => ({ ...current, ...update }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await (mode === "example" ? runExample() : runDetection());
  }

  function changeMode(next: SearchMode) {
    if (next === mode) return;
    clearResult();
    setExampleBox(null);
    setMode(next);
  }

  // englishQuery: "Aranan ifade" düzeltmesi; verilmezse backend sorguyu kendisi çevirir.
  async function runDetection(englishQuery?: string) {
    if (!image || !query.split(",").some((part) => part.trim()) || busy) return;
    clearResult();
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const submittedQuery = query.trim();
    setResultQuery(submittedQuery);
    setLoading(true);
    const startedAt = performance.now();
    updateResult({ phase: "image" });
    try {
      const analysis = await getDetectionAnalysis(image, submittedQuery, controller.signal, englishQuery, sensitivity);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(analysis.image);
      resultUrl.current = url;
      updateResult({ imageUrl: url, details: analysis.details, phase: "done" });
      setView("result");
    } catch (requestError) {
      if (!controller.signal.aborted) updateResult({
        phase: "error",
        error: requestError instanceof Error ? requestError.message : "Tespit sırasında bir hata oluştu.",
      });
    } finally {
      if (!controller.signal.aborted) {
        updateResult({ elapsedMs: performance.now() - startedAt });
        setLoading(false);
      }
    }
  }

  async function runExample() {
    if (!image || !exampleBox || busy) return;
    clearResult();
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    // Yazılan sorgu varsa yalnızca etiket olur; aramayı kutu belirler.
    // Örnek tek bir nesnedir; virgüllü metin sorgusundan yalnızca ilk ad etiket olur.
    const label = query.split(",")[0].trim() || "örnek nesne";
    setResultQuery(label + " (örnekle)");
    setLoading(true);
    const startedAt = performance.now();
    updateResult({ phase: "image" });
    try {
      const analysis = await getExampleAnalysis(image, exampleBox, label, controller.signal, sensitivity);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(analysis.image);
      resultUrl.current = url;
      updateResult({ imageUrl: url, details: analysis.details, phase: "done" });
      setView("result");
    } catch (requestError) {
      if (!controller.signal.aborted) updateResult({
        phase: "error",
        error: requestError instanceof Error ? requestError.message : "Örnekle arama sırasında bir hata oluştu.",
      });
    } finally {
      if (!controller.signal.aborted) {
        updateResult({ elapsedMs: performance.now() - startedAt });
        setLoading(false);
      }
    }
  }

  const phase = result.phase === "image" || result.phase === "details" ? result.phase : "idle";

  return (
    <div className="workspace-shell grid items-start gap-x-10 gap-y-8 pt-6 lg:grid-cols-[minmax(290px,340px)_minmax(0,1fr)]">
      <ControlPanel
        image={image} query={query} busy={busy} loading={loading} checkingFile={checkingFile}
        mode={mode} onModeChange={changeMode} exampleReady={!!exampleBox}
        error={error || result.error}
        warning={result.warning}
        onChooseImage={chooseImage}
        onQueryChange={(value) => { setQuery(value); clearResult(); }}
        sensitivity={sensitivity}
        onSensitivityChange={(level) => { setSensitivity(level); clearResult(); }}
        onSubmit={submit}
      />
      <section className="analysis-area flex min-w-0 flex-col gap-6" aria-label="Görüntü analiz alanı">
        <ImageViewer previewUrl={previewUrl} resultUrl={result.imageUrl} filename={image?.name ?? null}
          resultQuery={resultQuery} view={view} compare={compare} loading={phase === "image"}
          onViewChange={setView} onCompareChange={setCompare}
          example={{ active: mode === "example", box: exampleBox, onBoxChange: setExampleBox }}
        />
        <div className="readout flex flex-col gap-x-10 gap-y-5 md:flex-row md:items-start">
          <div className="flex min-w-0 flex-1 flex-col gap-4">
            <ResultSummary details={result.details} hasResult={!!result.imageUrl} phase={phase} failed={!!result.error} />
            <QueryInterpretation key={result.details?.primary_query ?? "none"} details={result.details} busy={busy} onRetry={(value) => { void runDetection(value); }} />
          </div>
          <InventorySummary details={result.details} />
        </div>
        <TechnicalDetails details={result.details} loading={loading}
          warning={result.warning || result.error} elapsedMs={result.elapsedMs}
        />
      </section>
    </div>
  );
}
