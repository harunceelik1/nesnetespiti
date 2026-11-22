import assert from "node:assert/strict";
import { after, before, beforeEach, test } from "node:test";
import { JSDOM } from "jsdom";
import { act } from "react";
import type { Root } from "react-dom/client";
import DetectionWorkspace from "../src/components/detection-workspace";

// HTTP sunucusu veya gerçek model gerektirmeyen DOM etkileşim testi.
const dom = new JSDOM("<!doctype html><html><body><div id='root'></div></body></html>", {
  url: "http://127.0.0.1:3000",
});
Object.defineProperties(globalThis, {
  window: { configurable: true, value: dom.window },
  document: { configurable: true, value: dom.window.document },
  navigator: { configurable: true, value: dom.window.navigator },
  IS_REACT_ACT_ENVIRONMENT: { configurable: true, value: true },
});
class DecodableImage {
  src = "";
  async decode() {}
}
Object.defineProperty(dom.window, "Image", { configurable: true, value: DecodableImage });
let root: Root;
before(async () => {
  const { createRoot } = await import("react-dom/client");
  root = createRoot(document.getElementById("root")!);
});
const realFetch = globalThis.fetch;
const file = new File(["fixture"], "objects.jpg", { type: "image/jpeg" });
const responseBody = {
  model: "OWL-ViT", model_id: "owlvit", inference_time_ms: 686, device: "cpu", query: "çanta", original_query: "çanta",
  detected_language: "tr", translated_query: "bag", primary_query: "bag",
  processed_queries: ["bag"], fallback_triggered: false, fallback_queries_used: [],
  raw_detection_count: 3, filtered_detection_count: 2,
  adaptive_threshold_used: 0.03,
  threshold_attempts: [
    { threshold: 0.05, raw_detection_count: 0, filtered_detection_count: 0, phase: "primary", queries: ["bag"] },
    { threshold: 0.03, raw_detection_count: 3, filtered_detection_count: 2, phase: "primary", queries: ["bag"] },
  ],
  threshold_selection_reason: "first_valid_result",
  annotated_image: { media_type: "image/jpeg", data_base64: "/9j/2Q==" },
  detections: [
    { label: "çanta", model_query: "bag", confidence: 0.84, box: { xmin: 0, ymin: 0, xmax: 50, ymax: 50 } },
    { label: "çanta", model_query: "bag", confidence: 0.76, box: { xmin: 60, ymin: 60, xmax: 90, ymax: 90 } },
  ],
};

function element<T extends Element>(selector: string): T {
  const found = document.querySelector<T>(selector);
  assert.ok(found, selector);
  return found;
}

async function upload(image = file) {
  const input = element<HTMLInputElement>("#image-file");
  Object.defineProperty(input, "files", { configurable: true, value: [image] });
  await act(async () => { input.dispatchEvent(new dom.window.Event("change", { bubbles: true })); });
}

async function query(value: string) {
  const input = element<HTMLInputElement>("#object-query");
  const setter = Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, "value")!.set!;
  await act(async () => {
    setter.call(input, value);
    input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  });
}

async function selectModel(model: "owlvit" | "grounding-dino" | "yolo-world" | "compare") {
  const select = element<HTMLSelectElement>("#detector-model");
  await act(async () => {
    select.value = model;
    select.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  });
}

async function submit() {
  await act(async () => {
    element<HTMLFormElement>("form").dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
  });
}

// Geliştirici modu (?debug=1): ham tanılar yalnızca bu adresle görünür.
async function enableDebug() {
  dom.window.history.replaceState(null, "", "/?debug=1");
  await act(async () => { root.render(<DetectionWorkspace key={Math.random()} />); });
}

beforeEach(async () => {
  globalThis.fetch = realFetch;
  dom.window.history.replaceState(null, "", "/");
  await act(async () => { root.render(<DetectionWorkspace key={Math.random()} />); });
});
after(async () => {
  await act(async () => { root.unmount(); });
  globalThis.fetch = realFetch;
  dom.window.close();
});

test("scene-box kaldırma nedeni ve alan oranı sadece teknik detaylarda gösterilir", async () => {
  globalThis.fetch = async () => Response.json({ ...responseBody,
    scene_box_diagnostics: [{ detection: responseBody.detections[0], area_ratio: .0025,
      box_area: 2500, image_area: 1000000, image_size: { width: 1000, height: 1000 },
      edge_distance_ratios: { left: 0, right: .95, top: 0, bottom: .95 },
      near_borders: ["left", "top"], touched_edges: 2, matched_rule: null, removed: false,
      reason: "scene_box_criteria_not_met", threshold: .03, canonical_query: "bag" }],
    oversized_boxes_removed_count: 1,
    oversized_boxes_removed: [{ detection: responseBody.detections[0], area_ratio: .9604,
      reason: "oversized_scene_box", near_borders: ["left", "right", "top", "bottom"],
      threshold: .05, phase: "primary", canonical_query: "bag" }],
  });
  await enableDebug();
  await upload();
  await query("bag");
  await submit();
  assert.match(element(".technical-content").textContent!, /Elenen dev kutu1 kutu görselin/);
  assert.match(element(".technical-content").textContent!, /oversized_boxes_removed.*1.*area_ratio=0\.9604.*oversized_scene_box/);
  assert.match(element(".technical-content").textContent!, /scene_box_diagnostics.*area_ratio=0\.0025.*touched_edges=2.*korundu.*no_rule.*left:0\.0000.*image=1000×1000/);
  assert.doesNotMatch(element(".result-summary").textContent!, /oversized_scene_box|area_ratio/);
});

test("rule_c eksen oranları Teknik Detaylar içinde görünür", async () => {
  globalThis.fetch = async () => Response.json({ ...responseBody,
    scene_box_diagnostics: [{ detection: responseBody.detections[0], area_ratio: .8601,
      width_coverage: .9959505208333334, height_coverage: .8636, box_area: 2705640, image_area: 3145728,
      image_size: { width: 1536, height: 2048 },
      edge_distance_ratios: { left: .0021, right: .002, top: .1304, bottom: .006 },
      near_borders: ["left", "right", "bottom"], touched_edges: 3, matched_rule: "rule_c", removed: true,
      reason: "oversized_scene_box", canonical_query: "backpack" }],
  });
  await enableDebug();
  await upload();
  await query("backpack");
  await submit();
  assert.match(element(".technical-content").textContent!, /width_coverage=0\.9960.*height_coverage=0\.8636.*kaldırıldı.*rule_c/);
});

test("çoklu envanter Compare model panellerinde ayrı gösterilir ve yeni query ile temizlenir", async () => {
  const calls: string[] = [];
  globalThis.fetch = async (_url, options) => {
    const form = options!.body as FormData;
    const model = String(form.get("model"));
    calls.push(model);
    assert.equal(form.get("query"), "çantalar, şişeler");
    assert.equal(form.has("threshold"), false);
    const count = model === "owlvit" ? 2 : 1;
    return Response.json({
      ...responseBody, model_id: model, model,
      query: "çantalar, şişeler", original_query: "çantalar, şişeler", primary_query: "bag, bottle",
      filtered_detection_count: count, total_detected_objects: count,
      inventory_summary: { bag: count, bottle: 0 },
      processed_query_items: ["bag", "bottle"].map((primary, index) => ({
        original_query: index === 0 ? "çantalar" : "şişeler", primary_query: primary,
        detected_language: "tr", translated_query: primary, processed_queries: [primary],
        fallback_triggered: false, fallback_queries_used: [], adaptive_threshold_used: .03,
        threshold_attempts: responseBody.threshold_attempts, threshold_selection_reason: "first_valid_result",
      })),
      detections: responseBody.detections.slice(0, count).map((d) => ({ ...d, canonical_query: "bag" })),
    });
  };
  await upload();
  await query("çantalar, şişeler");
  await selectModel("compare");
  await submit();
  assert.deepEqual(calls.sort(), ["grounding-dino", "owlvit", "yolo-world"]);
  const owl = element('[data-model="owlvit"] .inventory-summary');
  const dino = element('[data-model="grounding-dino"] .inventory-summary');
  const yolo = element('[data-model="yolo-world"] .inventory-summary');
  assert.match(owl.textContent!, /Envanter Özetiçantalar2şişeler0Toplam2/);
  assert.match(dino.textContent!, /Envanter Özetiçantalar1şişeler0Toplam1/);
  assert.match(yolo.textContent!, /Envanter Özetiçantalar1şişeler0Toplam1/);
  await query("bag");
  assert.equal(document.querySelectorAll(".inventory-summary").length, 0);
});

test("sadece virgül ve boşluk olan sorguda istek gönderilmez", async () => {
  let requests = 0;
  globalThis.fetch = async () => { requests++; throw new Error("No request expected"); };
  await upload();
  await query(" , , ");
  assert.equal(element<HTMLButtonElement>("button[type='submit']").disabled, true);
  await submit();
  assert.equal(requests, 0);
});

test("yüklenen görsel önizlenir; boş query backend isteği üretmez", async () => {
  let requests = 0;
  globalThis.fetch = async () => { requests += 1; throw new Error("Unexpected request"); };
  await upload();
  assert.ok(element<HTMLImageElement>(".viewer-pane.is-active img").src.startsWith("blob:"));
  assert.equal(element<HTMLButtonElement>("button[type='submit']").disabled, true);
  await submit();
  assert.equal(requests, 0);
});

test("tek /detect akışı, adaptive detaylar, loading, sekmeler ve sonuç temizleme korunur", async () => {
  const requests: string[] = [];
  let resolveImage!: (response: Response) => void;
  globalThis.fetch = async (url, options) => {
    const path = new URL(String(url)).pathname;
    requests.push(path);
    const form = options!.body as FormData;
    assert.equal(form.get("query"), "çanta");
    assert.equal(form.has("threshold"), false);
    assert.equal(form.get("include_image"), "true");
    assert.equal(form.get("model"), "owlvit");
    return new Promise<Response>((resolve) => { resolveImage = resolve; });
  };
  await upload();
  await query("çanta");
  await submit();
  assert.equal(element<HTMLButtonElement>("button[type='submit']").disabled, true);
  assert.match(element(".viewer-pane.is-active img").getAttribute("alt")!, /Orijinal/);
  await act(async () => {
    resolveImage(Response.json(responseBody));
  });
  assert.deepEqual(requests, ["/detect"]);
  assert.match(element(".result-summary").textContent!, /2 nesne bulundu/);
  assert.match(element(".result-summary").textContent!, /ms.*OWLv2/);
  assert.equal(element("#tab-result").getAttribute("aria-selected"), "true");
  const compare = element<HTMLInputElement>(".compare-option input");
  await act(async () => { compare.click(); });
  assert.ok(document.querySelector(".viewer-grid.is-compare"));
  await act(async () => { element<HTMLButtonElement>("#tab-original").click(); });
  assert.equal(element("#tab-original").getAttribute("aria-selected"), "true");
  await act(async () => {
    element(".viewer-toolbar .segmented-control").dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
  });
  assert.equal(element("#tab-result").getAttribute("aria-selected"), "true");
  assert.match(element(".technical-content").textContent!, /Aranan ifadeçanta → bag/);
  assert.match(element(".technical-content").textContent!, /0\.840/);
  const technical = element<HTMLDetailsElement>(".technical-details");
  await act(async () => { element<HTMLElement>(".technical-details summary").click(); });
  assert.equal(technical.open, true);
  assert.match(technical.textContent!, /Seçilen eşik0\.03/);
  assert.match(technical.textContent!, /Kutular3 aday → 2 kutu kaldı/);
  assert.match(technical.textContent!, /Model süresi686 ms/);
  assert.doesNotMatch(technical.textContent!, /0\.20|ayrı inference/);
  await upload(new File(["next"], "next.png", { type: "image/png" }));
  assert.equal(document.querySelectorAll(".viewer-pane img").length, 1);
  assert.match(element(".file-name").textContent!, /next.png/);
  assert.doesNotMatch(element(".result-summary").textContent!, /2 nesne/);
});

test("ham tanılar varsayılan olarak gizlidir; okunur özet görünür", async () => {
  globalThis.fetch = async () => Response.json({ ...responseBody,
    scene_box_diagnostics: [{ detection: responseBody.detections[0], area_ratio: .0025,
      box_area: 2500, image_area: 1000000, image_size: { width: 1000, height: 1000 },
      edge_distance_ratios: { left: 0, right: .95, top: 0, bottom: .95 },
      near_borders: ["left", "top"], touched_edges: 2, matched_rule: null, removed: false,
      reason: "scene_box_criteria_not_met", threshold: .03, canonical_query: "bag" }],
    oversized_boxes_removed_count: 0, oversized_boxes_removed: [],
  });
  await upload();
  await query("çanta");
  await submit();
  const text = element(".technical-content").textContent!;
  assert.match(text, /Elenen dev kutuYok/);
  assert.match(text, /Seçilen eşik0\.03/);
  assert.equal(document.querySelector(".raw-diagnostics"), null);
  assert.equal(document.querySelector(".attempts-table"), null);
  assert.doesNotMatch(text, /scene_box_diagnostics|area_ratio|first_valid_result|translated_query/);
  assert.doesNotMatch(element(".technical-details summary").textContent!, /geliştirici modu/);
});

test("?debug=1 ile eşik denemeleri ve ham alanlar gösterilir", async () => {
  globalThis.fetch = async () => Response.json(responseBody);
  await enableDebug();
  await upload();
  await query("çanta");
  await submit();
  const technical = element<HTMLDetailsElement>(".technical-details");
  assert.match(element(".technical-details summary").textContent!, /geliştirici modu/);
  assert.match(technical.textContent!, /threshold_selection_reasonfirst_valid_result/);
  assert.match(technical.textContent!, /translated_query.*bag/);
  const attempts = element(".attempts-table").querySelectorAll("tbody tr");
  assert.equal(attempts.length, 2);
  assert.deepEqual(Array.from(attempts[0].querySelectorAll("td"), (cell) => cell.textContent), ["0.05", "—", "primary / bag", "0", "0"]);
  assert.deepEqual(Array.from(attempts[1].querySelectorAll("td"), (cell) => cell.textContent), ["0.03", "—", "primary / bag", "3", "2"]);
});

test("backend hatası solda gösterilir ve orijinal görüntü korunur", async () => {
  globalThis.fetch = async () => { throw new TypeError("connection refused"); };
  await upload();
  await query("çanta");
  await submit();
  assert.match(element(".control-panel [role='alert']").textContent!, /Backend'e ulaşılamadı/);
  assert.ok(element(".viewer-pane.is-active img"));
  assert.equal(element<HTMLButtonElement>("button[type='submit']").disabled, false);
});

test("birleşik yanıt hatasında orijinal korunur ve traceback gösterilmez", async () => {
  globalThis.fetch = async () => new Response("internal traceback", { status: 500 });
  await upload();
  await query("çanta");
  await submit();
  assert.ok(element(".viewer-pane.is-active img"));
  assert.match(element(".control-panel [role='alert']").textContent!, /Backend görüntüyü işleyemedi/);
  assert.match(element(".viewer-pane.is-active img").getAttribute("alt")!, /Orijinal/);
  assert.doesNotMatch(document.body.textContent!, /internal traceback/);
});

test("geçersiz dosya backend'e gönderilmez", async () => {
  await upload(new File(["text"], "notes.txt", { type: "text/plain" }));
  assert.match(element("[role='alert']").textContent!, /JPG veya PNG/);
  assert.equal(document.querySelectorAll(".viewer-pane img").length, 0);
});

test("tek Grounding DINO seçimi yalnızca o modeli çağırır ve gerçek metrikleri gösterir", async () => {
  const calls: string[] = [];
  globalThis.fetch = async (url, options) => {
    const form = options!.body as FormData;
    assert.equal(form.get("model"), "grounding-dino");
    assert.equal(form.has("threshold"), false);
    calls.push(new URL(String(url)).pathname);
    return Response.json({ ...responseBody, model: "grounding-dino", model_id: "grounding-dino", inference_time_ms: 10097, device: "cuda",
      adaptive_threshold_used: 0.30,
      threshold_attempts: [
        { threshold: 0.35, text_threshold: 0.25, raw_detection_count: 0, filtered_detection_count: 0 },
        { threshold: 0.30, text_threshold: 0.25, raw_detection_count: 3, filtered_detection_count: 2 },
      ],
    });
  };
  await enableDebug();
  await upload();
  await query("çanta");
  await selectModel("grounding-dino");
  await submit();
  assert.deepEqual(calls, ["/detect"]);
  assert.match(element(".result-summary").textContent!, /10\.097 ms.*Grounding DINO.*CUDA/);
  assert.match(element(".technical-content").textContent!, /Seçilen eşik \(kutu\)0\.30/);
  assert.match(element(".technical-content").textContent!, /0\.350\.25/);
});

test("tek YOLO-World seçimi yalnızca o modeli çağırır ve kendi eşiğini gösterir", async () => {
  const models: string[] = [];
  globalThis.fetch = async (_url, options) => {
    const form = options!.body as FormData;
    models.push(String(form.get("model")));
    assert.equal(form.has("threshold"), false);
    return Response.json({ ...responseBody, model: "yolo-world", model_id: "yolo-world", inference_time_ms: 412, device: "cpu",
      adaptive_threshold_used: 0.15,
      threshold_attempts: [
        { threshold: 0.25, raw_detection_count: 0, filtered_detection_count: 0 },
        { threshold: 0.15, raw_detection_count: 2, filtered_detection_count: 2 },
      ],
    });
  };
  await upload();
  await query("cüzdan");
  await selectModel("yolo-world");
  await submit();
  assert.deepEqual(models, ["yolo-world"]);
  assert.match(element(".result-summary").textContent!, /412 ms.*YOLO-World.*CPU/);
  assert.match(element(".technical-content").textContent!, /Seçilen eşik0\.15/);
  assert.doesNotMatch(element(".technical-content").textContent!, /\(kutu\)/);
});

test("Compare üç modeli çağırır; biri tamamlanınca ortak loading diğerlerini bekler", async () => {
  const calls: { model: string; path: string }[] = [];
  let releaseDino!: (response: Response) => void;
  let owlFinished!: () => void;
  const owlDone = new Promise<void>((resolve) => { owlFinished = resolve; });
  globalThis.fetch = async (url, options) => {
    const form = options!.body as FormData;
    const model = String(form.get("model"));
    const path = new URL(String(url)).pathname;
    calls.push({ model, path });
    assert.equal(form.get("query"), "çanta");
    assert.equal((form.get("image") as File).name, file.name);
    assert.equal(path, "/detect");
    assert.equal(form.has("threshold"), false);
    if (model === "grounding-dino") return new Promise<Response>((resolve) => { releaseDino = resolve; });
    if (model === "owlvit") owlFinished();
    return Response.json({
      ...responseBody, model: model === "owlvit" ? "OWL-ViT" : model, model_id: model,
      filtered_detection_count: model === "owlvit" ? 2 : 1,
      inference_time_ms: model === "owlvit" ? 686 : 412, device: "cpu",
    });
  };
  await upload();
  await query("çanta");
  await selectModel("compare");
  await submit();
  await act(async () => { await owlDone; });
  assert.equal(element<HTMLButtonElement>("button[type='submit']").disabled, true);
  assert.match(element('[data-model="owlvit"] .result-summary').textContent!, /2 nesne bulundu.*686 ms.*CPU/);
  await act(async () => {
    releaseDino(Response.json({ ...responseBody, model: "grounding-dino", model_id: "grounding-dino", filtered_detection_count: 1, inference_time_ms: 10097,
      adaptive_threshold_used: 0.30,
      threshold_attempts: [{ threshold: 0.30, text_threshold: 0.25, raw_detection_count: 1, filtered_detection_count: 1 }],
    }));
    // Blob gövdesi asenkron okunurken event loop'un tamamlanmasına izin ver.
    await new Promise<void>((resolve) => setImmediate(resolve));
  });
  assert.equal(element<HTMLButtonElement>("button[type='submit']").disabled, false);
  assert.equal(calls.filter((call) => call.model === "owlvit").length, 1);
  assert.equal(calls.filter((call) => call.model === "grounding-dino").length, 1);
  assert.equal(calls.filter((call) => call.model === "yolo-world").length, 1);
  assert.match(element('[data-model="grounding-dino"] .result-summary').textContent!, /1 nesne bulundu.*10\.097 ms.*CPU/);
  assert.match(element('[data-model="yolo-world"] .result-summary').textContent!, /1 nesne bulundu.*412 ms.*YOLO-World/);
  assert.equal(document.querySelectorAll(".model-canvas img").length, 3);
  assert.equal(document.querySelectorAll(".technical-details").length, 3);
  assert.match(document.querySelectorAll(".technical-details")[2].textContent!, /Teknik detaylar · YOLO-World/);
  assert.match(document.querySelectorAll(".technical-details")[1].textContent!, /Model süresi10\.097 ms/);
  assert.match(document.querySelectorAll(".technical-details")[0].textContent!, /Seçilen eşik0\.03/);
  assert.match(document.querySelectorAll(".technical-details")[1].textContent!, /Seçilen eşik \(kutu\)0\.30/);
});

test("karşılaştırmada tek model büyük gösterilir; sekme ve Yan yana düzeni değiştirir", async () => {
  globalThis.fetch = async (_url, options) => {
    const model = (options!.body as FormData).get("model");
    return Response.json({ ...responseBody, model_id: model, filtered_detection_count: model === "owlvit" ? 2 : 1 });
  };
  await upload();
  await query("çanta");
  await selectModel("compare");
  await submit();
  const visible = () => [...document.querySelectorAll<HTMLElement>(".model-canvas")]
    .filter((figure) => !figure.classList.contains("hidden")).map((figure) => figure.dataset.modelImage);
  assert.deepEqual(visible(), ["owlvit"]);
  assert.match(element("#model-tab-owlvit").textContent!, /OWLv22/);
  await act(async () => { element<HTMLButtonElement>("#model-tab-grounding-dino").click(); });
  assert.deepEqual(visible(), ["grounding-dino"]);
  assert.equal(element("#model-tab-grounding-dino").getAttribute("aria-selected"), "true");
  await act(async () => { element<HTMLButtonElement>(".layout-toggle [role='radio']:last-child").click(); });
  assert.deepEqual(visible(), ["owlvit", "grounding-dino", "yolo-world"]);
  assert.equal(document.querySelector("[role='tablist'].model-tabs"), null);
  // Yan yana düzende bir görsele tıklamak onu büyük gösterir.
  await act(async () => { element<HTMLButtonElement>('[data-model-image="yolo-world"] button').click(); });
  assert.deepEqual(visible(), ["yolo-world"]);
});

test("adaptive metadata yoksa sabit threshold uydurulmaz", async () => {
  globalThis.fetch = async () => Response.json({ ...responseBody,
    adaptive_threshold_used: undefined, threshold_attempts: undefined, threshold_selection_reason: undefined,
  });
  await upload();
  await query("çanta");
  await submit();
  assert.match(element(".technical-content").textContent!, /Seçilen eşikBackend bildirmedi/);
  assert.doesNotMatch(element(".technical-content").textContent!, /0\.20/);
});

test("Compare içinde bir model hata verirse başarılı modelin sonucu korunur", async () => {
  for (const failed of ["owlvit", "grounding-dino", "yolo-world"]) {
    const successful = failed === "owlvit" ? "grounding-dino" : "owlvit";
    globalThis.fetch = async (_url, options) => {
      const model = (options!.body as FormData).get("model");
      if (model === failed) return Response.json({ detail: "Bu model şu anda kullanılamıyor." }, { status: 503 });
      return Response.json({ ...responseBody, model_id: model, model: model === "owlvit" ? "OWL-ViT" : model });
    };
    await upload();
    await query("çanta");
    await selectModel("compare");
    await submit();
    assert.ok(element('[data-model-image="' + successful + '"] img'));
    assert.match(element('[data-model="' + successful + '"] .result-summary').textContent!, /2 nesne bulundu/);
    assert.match(element('[data-model="' + failed + '"] [role="alert"]').textContent!, /kullanılamıyor/);
    assert.equal(element<HTMLButtonElement>("button[type='submit']").disabled, false);
  }
});

test("aranan İngilizce ifade gösterilir; düzeltilince english_query ile tekrar aranır", async () => {
  const sent: Array<{ query: FormDataEntryValue | null; english: FormDataEntryValue | null }> = [];
  globalThis.fetch = async (_url, options) => {
    const form = options!.body as FormData;
    const english = form.get("english_query");
    sent.push({ query: form.get("query"), english });
    return Response.json({
      ...responseBody, query: "ilaç kutusu", original_query: "ilaç kutusu",
      translated_query: english ?? "Pharmaceutical box",
      translation_source: english ? "user" : "model",
      primary_query: english ? String(english) : "pharmaceutical box",
    });
  };
  await upload();
  await query("ilaç kutusu");
  await submit();
  const section = element<HTMLElement>(".query-interpretation");
  assert.equal(element(".query-value").textContent, "pharmaceutical box");
  assert.match(section.textContent!, /çeviri modeli/);
  assert.ok(section.classList.contains("uncertain"), "çeviri modeli kaynağı uyarı ile işaretlenir");
  assert.equal(sent[0].english, null);

  const editButton = [...section.querySelectorAll("button")].find((b) => b.textContent === "Düzenle")!;
  await act(async () => { editButton.click(); });
  const input = element<HTMLInputElement>("#english-query");
  assert.equal(input.value, "pharmaceutical box");
  const setter = Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, "value")!.set!;
  await act(async () => {
    setter.call(input, "pill box");
    input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  });
  await act(async () => {
    element<HTMLFormElement>(".query-edit").dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
  });
  assert.deepEqual(sent[1], { query: "ilaç kutusu", english: "pill box" });
  assert.equal(element(".query-value").textContent, "pill box");
  assert.match(element(".query-interpretation").textContent!, /senin düzeltmen/);
  assert.equal(element<HTMLInputElement>("#object-query").value, "ilaç kutusu", "Türkçe sorgu korunur");
});

test("örnekle ara: çizilen kutu orijinal piksel koordinatlarıyla gönderilir", async () => {
  const sent: Array<{ url: string; form: FormData }> = [];
  globalThis.fetch = async (url, options) => {
    sent.push({ url: String(url), form: options!.body as FormData });
    return Response.json({
      ...responseBody, query: "çikolata", original_query: "çikolata", detected_language: "example",
      translated_query: null, translation_source: null, primary_query: "çikolata", processed_queries: [],
      threshold_attempts: undefined, adaptive_threshold_used: 0.88, threshold_selection_reason: "example_similarity",
      search_mode: "example", example_box: { xmin: 100, ymin: 100, xmax: 300, ymax: 200 },
      inventory_summary: { "çikolata": 2 }, total_detected_objects: 2,
      detections: responseBody.detections.map((d) => ({ ...d, label: "çikolata", canonical_query: "çikolata" })),
    });
  };
  await upload();
  await query("çikolata");
  const start = [...document.querySelectorAll("button")].find((b) => b.textContent === "Örnekle ara")!;
  assert.ok(start, "Örnekle ara düğmesi görünür");
  await act(async () => { start.click(); });
  const searchButton = () => [...document.querySelectorAll("button")].find((b) => b.textContent === "Benzerlerini bul")!;
  assert.equal(searchButton().disabled, true, "kutu çizilmeden arama yapılamaz");

  // Görsel 800x400; ekranda 400x200 gösteriliyor (ölçek 0.5).
  const img = element<HTMLImageElement>(".viewer-pane img");
  Object.defineProperties(img, { naturalWidth: { value: 800 }, naturalHeight: { value: 400 } });
  img.getBoundingClientRect = () => ({ left: 0, top: 0, width: 400, height: 200, right: 400, bottom: 200, x: 0, y: 0, toJSON() {} });
  const overlay = element<HTMLElement>("[data-testid='example-overlay']");
  const pointer = (type: string, x: number, y: number) =>
    overlay.dispatchEvent(new dom.window.MouseEvent(type, { bubbles: true, clientX: x, clientY: y }));
  await act(async () => { pointer("pointerdown", 50, 50); });
  await act(async () => { pointer("pointermove", 120, 80); });
  await act(async () => { pointer("pointerup", 150, 100); });
  assert.equal(searchButton().disabled, false);

  await act(async () => { searchButton().click(); });
  assert.equal(sent.length, 1);
  assert.match(sent[0].url, /\/detect-by-example$/);
  const fields = Object.fromEntries(["xmin", "ymin", "xmax", "ymax", "label", "model"].map((k) => [k, sent[0].form.get(k)]));
  assert.deepEqual(fields, { xmin: "100", ymin: "100", xmax: "300", ymax: "200", label: "çikolata", model: "owlvit" });
  assert.match(element(".result-summary").textContent!, /2 nesne bulundu/);
  assert.match(element(".query-interpretation").textContent!, /Çizdiğin örneğe/);
  assert.equal(document.querySelector("[data-testid='example-overlay']"), null, "arama bitince çizim katmanı kapanır");
});

test("hassasiyet: varsayılan gönderilmez; Geniş seçilince uyarı görünür ve loose gönderilir", async () => {
  const sent: Array<FormDataEntryValue | null> = [];
  globalThis.fetch = async (_url, options) => {
    sent.push((options!.body as FormData).get("sensitivity"));
    return Response.json(responseBody);
  };
  await upload();
  await query("çanta");
  const radio = (value: string) => element<HTMLInputElement>(`input[name='sensitivity'][value='${value}']`);
  assert.equal(radio("balanced").checked, true, "varsayılan Dengeli");
  await submit();
  assert.equal(sent[0], null, "dengeli seviye backend'e gönderilmez");

  await act(async () => { radio("loose").click(); });
  assert.match(element("#sensitivity-helper").textContent!, /olmayan nesneye de kutu çizebilir/);
  assert.ok(element("#sensitivity-helper").classList.contains("sensitivity-warning"));
  assert.equal(document.querySelector(".result-summary strong"), null, "seviye değişince eski sonuç temizlenir");
  await submit();
  assert.equal(sent[1], "loose");
});
