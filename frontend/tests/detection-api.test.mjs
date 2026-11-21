// Sunucu/model başlatmadan gerçek API servisinin multipart ve hata sözleşmelerini test et.
import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/detection-api.ts", import.meta.url), "utf8");
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const api = await import("data:text/javascript;base64," + Buffer.from(javascript).toString("base64"));
const realFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = realFetch; });

const file = new File(["test image"], "sample.jpg", { type: "image/jpeg" });
const query = "çanta";
const makeDetails = () => ({
  model: "OWL-ViT", model_id: "owlvit", inference_time_ms: 686, device: "cpu", query, original_query: query, detected_language: "tr", translated_query: "bag", primary_query: "bag",
  processed_queries: ["bag"], fallback_triggered: false, fallback_queries_used: [],
  raw_detection_count: 2, filtered_detection_count: 1,
  adaptive_threshold_used: 0.03,
  threshold_attempts: [
    { threshold: 0.05, raw_detection_count: 0, filtered_detection_count: 0 },
    { threshold: 0.03, raw_detection_count: 2, filtered_detection_count: 1 },
  ],
  threshold_selection_reason: "first_valid_result",
  detections: [{
    label: query, model_query: "bag", confidence: 0.84,
    box: { xmin: 10, ymin: 20, xmax: 100, ymax: 120 },
  }],
});

test("scene-box debug metadata korunur; geçersiz area_ratio reddedilir", async () => {
  const details = makeDetails();
  const removed = { detection: details.detections[0], area_ratio: .9604, reason: "oversized_scene_box",
    near_borders: ["left", "right", "top", "bottom"], threshold: .05, phase: "primary", canonical_query: "bag" };
  globalThis.fetch = async () => Response.json({ ...details, oversized_boxes_removed: [removed], oversized_boxes_removed_count: 1 });
  const result = await api.getDetectionDetails(file, query, new AbortController().signal);
  assert.equal(result.oversized_boxes_removed[0].area_ratio, .9604);
  assert.equal(result.oversized_boxes_removed_count, 1);
  globalThis.fetch = async () => Response.json({ ...details, oversized_boxes_removed: [{ ...removed, area_ratio: "invalid" }], oversized_boxes_removed_count: 1 });
  await assert.rejects(api.getDetectionDetails(file, query, new AbortController().signal), /beklenen formatta değil/);
});

test("korunan kutunun gerçek alan/kenar diagnostics bilgileri taşınır", async () => {
  const details = makeDetails();
  const entry = { detection: details.detections[0], area_ratio: .45, box_area: 9000, image_area: 20000,
    image_size: { width: 100, height: 200 }, edge_distance_ratios: { left: .1, right: 0, top: .1, bottom: .4 },
    near_borders: ["right"], touched_edges: 1, matched_rule: null, removed: false,
    reason: "scene_box_criteria_not_met", threshold: .03, canonical_query: "bag" };
  globalThis.fetch = async () => Response.json({ ...details, scene_box_diagnostics: [entry] });
  const result = await api.getDetectionDetails(file, query, new AbortController().signal);
  assert.equal(result.scene_box_diagnostics[0].area_ratio, .45);
  assert.equal(result.scene_box_diagnostics[0].touched_edges, 1);
  assert.equal(result.scene_box_diagnostics[0].removed, false);
  globalThis.fetch = async () => Response.json({ ...details, scene_box_diagnostics: [{ ...entry, touched_edges: 4 }] });
  await assert.rejects(api.getDetectionDetails(file, query, new AbortController().signal), /beklenen formatta değil/);
});

test("rule_c ve eksen coverage metadata desteklenir", async () => {
  const details = makeDetails();
  const entry = { detection: details.detections[0], area_ratio: .8601, width_coverage: .9959505208333334, height_coverage: .8636,
    box_area: 2705640, image_area: 3145728, image_size: { width: 1536, height: 2048 },
    edge_distance_ratios: { left: .0021, right: .002, top: .1304, bottom: .006 },
    near_borders: ["left", "right", "bottom"], touched_edges: 3, matched_rule: "rule_c", removed: true,
    reason: "oversized_scene_box", canonical_query: "backpack" };
  globalThis.fetch = async () => Response.json({ ...details, scene_box_diagnostics: [entry] });
  const result = await api.getDetectionDetails(file, query, new AbortController().signal);
  assert.equal(result.scene_box_diagnostics[0].matched_rule, "rule_c");
  assert.equal(result.scene_box_diagnostics[0].width_coverage, .9959505208333334);
  globalThis.fetch = async () => Response.json({ ...details, scene_box_diagnostics: [{ ...entry, height_coverage: "bad" }] });
  await assert.rejects(api.getDetectionDetails(file, query, new AbortController().signal), /beklenen formatta değil/);
});

test("çoklu query model başına tek istekte gider ve NMS sonrası inventory doğrulanır", async () => {
  for (const model of ["owlvit", "grounding-dino", "yolo-world"]) {
    const body = makeDetails();
    body.model_id = model;
    body.model = model;
    body.query = body.original_query = "bag, bottle";
    body.primary_query = "bag, bottle";
    body.processed_queries = ["bag", "bottle"];
    body.detections[0].canonical_query = "bag";
    body.inventory_summary = { bag: 1, bottle: 0 };
    body.total_detected_objects = 1;
    let requests = 0;
    globalThis.fetch = async (_url, options) => {
      requests++;
      assert.equal(options.body.get("query"), "bag, bottle");
      assert.equal(options.body.get("model"), model);
      assert.equal(options.body.has("threshold"), false);
      return Response.json({ ...body, annotated_image: { media_type: "image/jpeg", data_base64: "/9j/2Q==" } });
    };
    const result = await api.getDetectionAnalysis(file, "bag, bottle", new AbortController().signal, model);
    assert.deepEqual(result.details.inventory_summary, { bag: 1, bottle: 0 });
    assert.equal(result.details.total_detected_objects, 1);
    assert.equal(requests, 1);
    globalThis.fetch = async () => Response.json({ ...body, inventory_summary: { bag: 2, bottle: 0 } });
    await assert.rejects(api.getDetectionDetails(file, "bag, bottle", new AbortController().signal, model), /beklenen formatta değil/);
  }
});

test("JPEG ve detay istekleri doğru modeli kullanır; sabit threshold gönderilmez", async () => {
  const paths = [];
  globalThis.fetch = async (url, options) => {
    paths.push(new URL(url).pathname);
    assert.equal(options.method, "POST");
    assert.ok(options.body instanceof FormData);
    assert.equal(options.body.get("image").name, "sample.jpg");
    assert.equal(options.body.get("query"), query);
    assert.equal(options.body.get("model"), "owlvit");
    assert.equal(options.body.has("threshold"), false);
    assert.equal(options.headers, undefined);
    assert.ok(options.signal instanceof AbortSignal);
    return paths.at(-1) === "/detect-image"
      ? new Response(new Blob(["jpeg"], { type: "image/jpeg" }))
      : Response.json(makeDetails());
  };
  const signal = new AbortController().signal;
  const image = await api.detectImage(file, query, signal);
  const details = await api.getDetectionDetails(file, query, signal);
  assert.equal(image.type, "image/jpeg");
  assert.equal(details.filtered_detection_count, 1);
  assert.equal(details.primary_query, "bag");
  assert.equal(details.adaptive_threshold_used, 0.03);
  assert.equal(details.threshold_attempts.length, 2);
  assert.deepEqual(paths, ["/detect-image", "/detect"]);
});

test("sıfır tespit geçerli sonuç olarak kabul edilir", async () => {
  globalThis.fetch = async () => Response.json({
    ...makeDetails(), detections: [], raw_detection_count: 0, filtered_detection_count: 0,
  });
  const result = await api.getDetectionDetails(file, query, new AbortController().signal);
  assert.equal(result.filtered_detection_count, 0);
});

test("bağlantı hatası anlaşılır mesaj döndürür", async () => {
  globalThis.fetch = async () => { throw new TypeError("fetch failed"); };
  await assert.rejects(api.detectImage(file, query, new AbortController().signal), /Backend'e ulaşılamadı/);
});

test("backend 400 mesajı korunur, 500 için genel mesaj kullanılır", async () => {
  globalThis.fetch = async () => Response.json({ detail: "Geçerli bir görsel dosyası yükleyin." }, { status: 400 });
  await assert.rejects(api.detectImage(file, query, new AbortController().signal), /Geçerli bir görsel/);
  globalThis.fetch = async () => new Response("internal traceback", { status: 500 });
  await assert.rejects(api.detectImage(file, query, new AbortController().signal), /Backend görüntüyü işleyemedi/);
});

test("JPEG olmayan veya boş görsel yanıtı reddedilir", async () => {
  globalThis.fetch = async () => Response.json({ result: "not an image" });
  await assert.rejects(api.detectImage(file, query, new AbortController().signal), /beklenen JPEG/);
  globalThis.fetch = async () => new Response("", { headers: { "Content-Type": "image/jpeg" } });
  await assert.rejects(api.detectImage(file, query, new AbortController().signal), /boş bir sonuç/);
});

test("bozuk JSON ve geçersiz detaylar reddedilir", async () => {
  globalThis.fetch = async () => new Response("not json");
  await assert.rejects(api.getDetectionDetails(file, query, new AbortController().signal), /yanıtı okunamadı/);
  globalThis.fetch = async () => Response.json({ ...makeDetails(), detections: [{ confidence: "invalid" }] });
  await assert.rejects(api.getDetectionDetails(file, query, new AbortController().signal), /beklenen formatta değil/);
});

test("iptal edilmiş istek bağlantı hatası olarak gösterilmez", async () => {
  const controller = new AbortController();
  controller.abort();
  globalThis.fetch = async () => { throw new DOMException("Aborted", "AbortError"); };
  await assert.rejects(api.detectImage(file, query, controller.signal), { name: "AbortError" });
});

test("çeviri 503 mesajı kullanıcıya aktarılır ve İngilizce null çeviri kabul edilir", async () => {
  globalThis.fetch = async () => Response.json({ detail: "Türkçe→İngilizce çeviri modeli yüklenemedi." }, { status: 503 });
  await assert.rejects(api.detectImage(file, query, new AbortController().signal), /çeviri modeli yüklenemedi/);
  globalThis.fetch = async () => Response.json({
    ...makeDetails(), query: "rug", original_query: "rug", detected_language: "en", translated_query: null, primary_query: "rug",
  });
  const result = await api.getDetectionDetails(file, "rug", new AbortController().signal);
  assert.equal(result.translated_query, null);
});

test("Grounding DINO her iki endpoint'e model parametresi gönderir", async () => {
  const paths = [];
  globalThis.fetch = async (url, options) => {
    paths.push(new URL(url).pathname);
    assert.equal(options.body.get("model"), "grounding-dino");
    return paths.at(-1) === "/detect-image"
      ? new Response(new Blob(["jpeg"], { type: "image/jpeg" }))
      : Response.json({ ...makeDetails(), model: "grounding-dino", model_id: "grounding-dino", inference_time_ms: 10097, device: "cuda" });
  };
  const signal = new AbortController().signal;
  await api.detectImage(file, query, signal, "grounding-dino");
  const details = await api.getDetectionDetails(file, query, signal, "grounding-dino");
  assert.equal(details.inference_time_ms, 10097);
  assert.equal(details.device, "cuda");
  assert.deepEqual(paths, ["/detect-image", "/detect"]);
});

test("yanlış model metadatası ve geçersiz inference süresi reddedilir", async () => {
  globalThis.fetch = async () => Response.json(makeDetails());
  await assert.rejects(api.getDetectionDetails(file, query, new AbortController().signal, "grounding-dino"), /beklenen formatta değil/);
  globalThis.fetch = async () => Response.json({ ...makeDetails(), inference_time_ms: -1 });
  await assert.rejects(api.getDetectionDetails(file, query, new AbortController().signal), /beklenen formatta değil/);
});

test("tek /detect isteği threshold göndermeden aynı analizin JPEG ve metadata'sını alır", async () => {
  let calls = 0;
  globalThis.fetch = async (url, options) => {
    calls += 1;
    assert.equal(new URL(url).pathname, "/detect");
    assert.equal(options.body.has("threshold"), false);
    assert.equal(options.body.get("include_image"), "true");
    assert.equal(options.body.get("model"), "owlvit");
    return Response.json({ ...makeDetails(), annotated_image: { media_type: "image/jpeg", data_base64: "/9j/2Q==" } });
  };
  const result = await api.getDetectionAnalysis(file, query, new AbortController().signal);
  assert.equal(calls, 1);
  assert.equal(result.image.type, "image/jpeg");
  assert.equal(result.details.adaptive_threshold_used, 0.03);
  assert.equal(result.details.threshold_selection_reason, "first_valid_result");
  assert.deepEqual(result.details.threshold_attempts, makeDetails().threshold_attempts);
  assert.equal("annotated_image" in result.details, false);
});

test("eski backend veya bozuk birleşik görüntü ikinci inference ile gizlenmez", async () => {
  globalThis.fetch = async () => Response.json(makeDetails());
  await assert.rejects(api.getDetectionAnalysis(file, query, new AbortController().signal), /Güncel backend/);
  for (const data_base64 of ["not-base64!", "aGVsbG8="]) {
    globalThis.fetch = async () => Response.json({ ...makeDetails(), annotated_image: { media_type: "image/jpeg", data_base64 } });
    await assert.rejects(api.getDetectionAnalysis(file, query, new AbortController().signal), /sonuç görüntüsü okunamadı/);
  }
});

test("geçersiz adaptive metadata reddedilir", async () => {
  for (const invalid of [
    { adaptive_threshold_used: -0.03 },
    { threshold_attempts: [{ threshold: 0.03, raw_detection_count: "2", filtered_detection_count: 2 }] },
    { threshold_attempts: [{ threshold: 0.35, text_threshold: 2, raw_detection_count: 1, filtered_detection_count: 1 }] },
    { threshold_selection_reason: 123 },
  ]) {
    globalThis.fetch = async () => Response.json({ ...makeDetails(), ...invalid });
    await assert.rejects(api.getDetectionDetails(file, query, new AbortController().signal), /beklenen formatta değil/);
  }
});
