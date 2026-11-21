"use client";

import InventorySummary from "./inventory-summary";

import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { getDetectionAnalysis, getExampleAnalysis, MODEL_NAMES, type Box, type DetectorModel, type ModelSelection } from "@/lib/detection-api";
import { DETECTOR_MODELS, emptyResults, type ModelResult, type ModelResults } from "@/lib/model-result";
import ControlPanel from "./control-panel";
import ImageViewer, { type ViewerMode } from "./image-viewer";
import ModelComparison from "./model-comparison";
import ResultSummary from "./result-summary";
import QueryInterpretation from "./query-interpretation";
import TechnicalDetails from "./technical-details";

export default function DetectionWorkspace() {
  const [selection, setSelection] = useState<ModelSelection>("owlvit");
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
  // Örnekle arama: kullanıcı orijinal görselde bir kutu çizer (yalnızca OWLv2).
  const [selectingExample, setSelectingExample] = useState(false);
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
      setSelectingExample(false);
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
    await runDetection();
  }

  // englishQuery: "Aranan ifade" düzeltmesi; verilmezse backend sorguyu kendisi çevirir.
  async function runDetection(englishQuery?: string) {
    if (!image || !query.split(",").some((part) => part.trim()) || busy) return;
    clearResult();
    cancelExample();
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
        const analysis = await getDetectionAnalysis(image!, submittedQuery, controller.signal, model, englishQuery);
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

  function startExample() {
    clearResult();
    setSelection((current) => current === "owlvit" ? current : "owlvit");
    setExampleBox(null);
    setSelectingExample(true);
  }

  function cancelExample() {
    setSelectingExample(false);
    setExampleBox(null);
  }

  async function runExample() {
    if (!image || !exampleBox || busy) return;
    clearResult();
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    // Yazılan sorgu varsa yalnızca etiket olur; aramayı kutu belirler.
    const label = query.trim() || "örnek nesne";
    setResultQuery(label + " (örnekle)");
    setLoading(true);
    const startedAt = performance.now();
    updateResult("owlvit", { phase: "image" });
    try {
      const analysis = await getExampleAnalysis(image, exampleBox, label, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(analysis.image);
      resultUrls.current.owlvit = url;
      updateResult("owlvit", { imageUrl: url, details: analysis.details, phase: "done" });
      setSelectingExample(false);
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

  const singleResult = results[selection === "compare" ? "owlvit" : selection];
  // Çeviri tüm modellerde ortaktır; ilk gelen sonucun planı gösterilir.
  const interpretedDetails = selection === "compare"
    ? DETECTOR_MODELS.map((model) => results[model].details).find(Boolean) ?? null
    : singleResult.details;
  const interpretation = <QueryInterpretation key={interpretedDetails?.primary_query ?? "none"} details={interpretedDetails} busy={busy} onRetry={(value) => { void runDetection(value); }} />;
  const phase = singleResult.phase === "image" || singleResult.phase === "details" ? singleResult.phase : "idle";

  return (
    <div className="workspace-shell">
      <ControlPanel
        image={image} query={query} busy={busy} loading={loading} checkingFile={checkingFile}
        model={selection}
        error={error || (selection === "compare" ? null : singleResult.error)}
        warning={selection === "compare" ? null : singleResult.warning}
        onChooseImage={chooseImage}
        onQueryChange={(value) => { setQuery(value); clearResult(); }}
        onModelChange={(model) => { setSelection(model); clearResult(); cancelExample(); }}
        onSubmit={submit}
      />
      <section className="analysis-area" aria-label="Görüntü analiz alanı">
        {selection === "compare" ? <>
          {interpretation}
          <ModelComparison results={results} previewUrl={previewUrl} query={resultQuery} loading={loading} />
          {DETECTOR_MODELS.map((model) => <TechnicalDetails key={model}
            modelName={MODEL_NAMES[model]} details={results[model].details}
            loading={results[model].phase === "image" || results[model].phase === "details"}
            warning={results[model].error || results[model].warning} elapsedMs={results[model].elapsedMs}
          />)}
        </> : <>
          <ImageViewer previewUrl={previewUrl} resultUrl={singleResult.imageUrl} filename={image?.name ?? null}
            resultQuery={resultQuery} view={view} compare={compare} loading={phase === "image"}
            onViewChange={setView} onCompareChange={setCompare}
            example={{ selecting: selectingExample, box: exampleBox, busy,
              onStart: startExample, onCancel: cancelExample, onBoxChange: setExampleBox, onSearch: () => { void runExample(); } }}
          />
          {interpretation}
          <ResultSummary details={singleResult.details} hasResult={!!singleResult.imageUrl} phase={phase} failed={!!singleResult.error} />
          <InventorySummary details={singleResult.details} />
          <TechnicalDetails details={singleResult.details} loading={loading}
            warning={singleResult.warning || singleResult.error} elapsedMs={singleResult.elapsedMs}
          />
        </>}
      </section>
    </div>
  );
}
