"use client";

import InventorySummary from "./inventory-summary";

import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { getDetectionAnalysis, getExampleAnalysis, MODEL_NAMES, type Box, type DetectorModel, type ModelSelection, type Sensitivity } from "@/lib/detection-api";
import { DETECTOR_MODELS, emptyResults, type ModelResult, type ModelResults } from "@/lib/model-result";
import { Card } from "@/components/ui/card";
import ControlPanel, { type SearchMode } from "./control-panel";
import ImageViewer, { type ViewerMode } from "./image-viewer";
import ModelComparison from "./model-comparison";
import ResultSummary from "./result-summary";
import QueryInterpretation from "./query-interpretation";
import TechnicalDetails from "./technical-details";

export default function DetectionWorkspace() {
  const [selection, setSelection] = useState<ModelSelection>("owlvit");
  const [sensitivity, setSensitivity] = useState<Sensitivity>("balanced");
  const [results, setResults] = useState<ModelResults>(emptyResults);
  const [view, setView] = useState<ViewerMode>("original");
  const [compare, setCompare] = useState(false);
  const [image, setImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [resultQuery, setResultQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingFile, setCheckingFile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // "example": kullanıcı orijinal görselde bir kutu çizer, benzerleri aranır (yalnızca OWLv2).
  const [mode, setMode] = useState<SearchMode>("text");
  const [exampleBox, setExampleBox] = useState<Box | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const fileSelection = useRef(0);
  const resultUrls = useRef<Partial<Record<DetectorModel, string>>>({});
  const busy = loading || checkingFile;

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  useEffect(() => () => {
    activeRequest.current?.abort();
    fileSelection.current += 1;
    Object.values(resultUrls.current).forEach(URL.revokeObjectURL);
  }, []);

  function clearResult() {
    Object.values(resultUrls.current).forEach(URL.revokeObjectURL);
    resultUrls.current = {};
    setResults(emptyResults());
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

  function updateResult(model: DetectorModel, update: Partial<ModelResult>) {
    setResults((current) => ({ ...current, [model]: { ...current[model], ...update } }));
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
    const models: DetectorModel[] = selection === "compare" ? DETECTOR_MODELS : [selection];
    setResultQuery(submittedQuery);
    setLoading(true);

    async function runModel(model: DetectorModel) {
      const startedAt = performance.now();
      updateResult(model, { phase: "image" });
      try {
        const analysis = await getDetectionAnalysis(image!, submittedQuery, controller.signal, model, englishQuery, sensitivity);
        if (controller.signal.aborted) return;
        const url = URL.createObjectURL(analysis.image);
        resultUrls.current[model] = url;
        updateResult(model, { imageUrl: url, details: analysis.details, phase: "done" });
        setView("result");
      } catch (requestError) {
        if (!controller.signal.aborted) updateResult(model, {
          phase: "error",
          error: requestError instanceof Error ? requestError.message : "Tespit sırasında bir hata oluştu.",
        });
      } finally {
        if (!controller.signal.aborted) updateResult(model, { elapsedMs: performance.now() - startedAt });
      }
    }

    // Her görev kendi hatasını yakalar; erken gelen başarılı sonuç hemen gösterilir.
    try {
      await Promise.all(models.map(runModel));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
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
    updateResult("owlvit", { phase: "image" });
    try {
      const analysis = await getExampleAnalysis(image, exampleBox, label, controller.signal, sensitivity);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(analysis.image);
      resultUrls.current.owlvit = url;
      updateResult("owlvit", { imageUrl: url, details: analysis.details, phase: "done" });
      setView("result");
    } catch (requestError) {
      if (!controller.signal.aborted) updateResult("owlvit", {
        phase: "error",
        error: requestError instanceof Error ? requestError.message : "Örnekle arama sırasında bir hata oluştu.",
      });
    } finally {
      if (!controller.signal.aborted) {
        updateResult("owlvit", { elapsedMs: performance.now() - startedAt });
        setLoading(false);
      }
    }
  }

  // Örnekle arama her zaman OWLv2 ile tek sonuç gösterir; karşılaştırma yalnızca metin aramasında.
  const activeModel: DetectorModel = mode === "example" || selection === "compare" ? "owlvit" : selection;
  const comparing = mode === "text" && selection === "compare";
  const singleResult = results[activeModel];
  // Çeviri tüm modellerde ortaktır; ilk gelen sonucun planı gösterilir.
  const interpretedDetails = comparing
    ? DETECTOR_MODELS.map((model) => results[model].details).find(Boolean) ?? null
    : singleResult.details;
  const interpretation = <QueryInterpretation key={interpretedDetails?.primary_query ?? "none"} details={interpretedDetails} busy={busy} onRetry={(value) => { void runDetection(value); }} />;
  const phase = singleResult.phase === "image" || singleResult.phase === "details" ? singleResult.phase : "idle";

  return (
    <div className="workspace-shell grid items-start gap-6 lg:grid-cols-[minmax(300px,360px)_minmax(0,1fr)]">
      <ControlPanel
        image={image} query={query} busy={busy} loading={loading} checkingFile={checkingFile}
        mode={mode} onModeChange={changeMode} exampleReady={!!exampleBox}
        model={selection}
        error={error || (comparing ? null : singleResult.error)}
        warning={comparing ? null : singleResult.warning}
        onChooseImage={chooseImage}
        onQueryChange={(value) => { setQuery(value); clearResult(); }}
        onModelChange={(model) => { setSelection(model); clearResult(); }}
        sensitivity={sensitivity}
        onSensitivityChange={(level) => { setSensitivity(level); clearResult(); }}
        onSubmit={submit}
      />
      <section className="analysis-area flex min-w-0 flex-col gap-4" aria-label="Görüntü analiz alanı">
        {comparing ? <>
          {interpretedDetails && <Card className="px-5 py-4">{interpretation}</Card>}
          <ModelComparison results={results} previewUrl={previewUrl} query={resultQuery} loading={loading} />
          <div className="flex flex-col gap-2">
            {DETECTOR_MODELS.map((model) => <TechnicalDetails key={model}
              modelName={MODEL_NAMES[model]} details={results[model].details}
              loading={results[model].phase === "image" || results[model].phase === "details"}
              warning={results[model].error || results[model].warning} elapsedMs={results[model].elapsedMs}
            />)}
          </div>
        </> : <>
          <ImageViewer previewUrl={previewUrl} resultUrl={singleResult.imageUrl} filename={image?.name ?? null}
            resultQuery={resultQuery} view={view} compare={compare} loading={phase === "image"}
            onViewChange={setView} onCompareChange={setCompare}
            example={{ active: mode === "example", box: exampleBox, onBoxChange: setExampleBox }}
          />
          <Card className="gap-4 px-5 py-4">
            <ResultSummary details={singleResult.details} hasResult={!!singleResult.imageUrl} phase={phase} failed={!!singleResult.error} />
            {interpretation}
            <InventorySummary details={singleResult.details} />
          </Card>
          <TechnicalDetails details={singleResult.details} loading={loading}
            warning={singleResult.warning || singleResult.error} elapsedMs={singleResult.elapsedMs}
          />
        </>}
      </section>
    </div>
  );
}
