export const MODEL_NAMES = { owlvit: "OWLv2", "grounding-dino": "Grounding DINO", "yolo-world": "YOLO-World" } as const;
export type DetectorModel = keyof typeof MODEL_NAMES;
export type ModelSelection = DetectorModel | "compare";
export type Sensitivity = "strict" | "balanced" | "loose";
export const SENSITIVITY_LABELS: Record<Sensitivity, string> = { strict: "Sıkı", balanced: "Dengeli", loose: "Geniş" };
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export interface Detection {
  label: string;
  model_query?: string;
  canonical_query?: string;
  confidence: number;
  box: { xmin: number; ymin: number; xmax: number; ymax: number };
}

export interface RemovedSceneBox {
  detection: Detection;
  area_ratio: number;
  reason: "oversized_scene_box";
  near_borders: string[];
  threshold?: number;
  phase?: "primary" | "fallback";
  canonical_query?: string;
}

export interface SceneBoxDiagnostic {
  detection: Detection;
  area_ratio: number;
  width_coverage?: number;
  height_coverage?: number;
  box_area: number;
  image_area: number;
  image_size: { width: number; height: number };
  edge_distance_ratios: { left: number; right: number; top: number; bottom: number };
  near_borders: string[];
  touched_edges: number;
  matched_rule: "rule_a" | "rule_b" | "rule_c" | null;
  removed: boolean;
  reason: "oversized_scene_box" | "scene_box_criteria_not_met";
  threshold?: number;
  canonical_query?: string;
}

interface SceneBoxDiagnostics {
  oversized_boxes_removed?: RemovedSceneBox[];
  oversized_boxes_removed_count?: number;
  scene_box_diagnostics?: SceneBoxDiagnostic[];
}

export interface DetectionDetails extends SceneBoxDiagnostics {
  model: string;
  model_id: DetectorModel;
  inference_time_ms: number;
  device: string;
  query: string;
  original_query: string;
  detected_language: string;
  translated_query: string | null;
  /** lexicon / model / user / mixed; null: İngilizce sorgu, çevrilmedi. */
  translation_source?: string | null;
  primary_query: string;
  processed_queries: string[];
  fallback_triggered: boolean;
  fallback_queries_used: string[];
  raw_detection_count: number;
  filtered_detection_count: number;
  detections: Detection[];
  adaptive_threshold_used?: number;
  threshold_attempts?: ThresholdAttempt[];
  threshold_selection_reason?: string;
  inventory_summary?: Record<string, number>;
  total_detected_objects?: number;
  processed_query_items?: ProcessedQueryItem[];
  adaptive_thresholds_by_query?: Record<string, number>;
  /** "example": metin yerine görselde çizilen örnek kutuyla arama (yalnızca OWLv2). */
  search_mode?: "example";
  sensitivity?: Sensitivity;
  example_box?: Box;
}

export type Box = Detection["box"];

export interface ProcessedQueryItem {
  original_query: string;
  detected_language: string;
  translated_query: string | null;
  primary_query: string;
  processed_queries: string[];
  fallback_triggered: boolean;
  fallback_queries_used: string[];
  adaptive_threshold_used: number;
  threshold_attempts: ThresholdAttempt[];
  threshold_selection_reason: string;
}

export interface ThresholdAttempt extends SceneBoxDiagnostics {
  threshold: number;
  raw_detection_count: number;
  filtered_detection_count: number;
  text_threshold?: number;
  phase?: "primary" | "fallback";
  queries?: string[];
  canonical_query?: string;
}

export interface DetectionAnalysis {
  details: DetectionDetails;
  image: Blob;
}

async function postImage(path: string, image: File, query: string, signal: AbortSignal, model: DetectorModel, includeImage = false, englishQuery?: string, sensitivity: Sensitivity = "balanced"): Promise<Response> {
  const form = new FormData();
  form.append("image", image);
  form.append("query", query);
  form.append("model", model);
  // Kullanıcının düzelttiği İngilizce ifade: backend çeviriyi atlar, etiket Türkçe kalır.
  if (englishQuery?.trim()) form.append("english_query", englishQuery.trim());
  // Confidence eşiğini backend model bazında seçer; frontend sayı göndermez.
  if (includeImage) form.append("include_image", "true");
  // Varsayılan (dengeli) gönderilmez; backend kalibre edilmiş eşiği kullanır.
  if (sensitivity !== "balanced") form.append("sensitivity", sensitivity);
  return sendForm(path, form, signal);
}

async function sendForm(path: string, form: FormData, signal: AbortSignal): Promise<Response> {
  let response: Response;
  try {
    // Multipart boundary tarayıcı tarafından oluşturulur; Content-Type elle yazılmaz.
    response = await fetch(API_BASE_URL + path, { method: "POST", body: form, signal });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error("Backend'e ulaşılamadı. FastAPI'nin 8000 portunda çalıştığını ve bağlantı adresini kontrol edin.");
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body) detail = body.detail;
    } catch {
      // HTML veya boş hata yanıtları için anlaşılır varsayılan mesaj kullan.
    }
    if (response.status === 503 && typeof detail === "string") {
      throw new Error(detail);
    }
    if (response.status >= 500) {
      throw new Error("Backend görüntüyü işleyemedi. Biraz sonra tekrar deneyin; hata sürerse backend terminalini kontrol edin.");
    }
    if (response.status === 422) {
      throw new Error(typeof detail === "string" ? detail : "Görsel ve nesne sorgusunu kontrol ederek tekrar deneyin.");
    }
    throw new Error(typeof detail === "string" ? detail : "Görsel işlenemedi. Geçerli bir JPG/PNG dosyası seçin.");
  }
  return response;
}

export async function detectImage(image: File, query: string, signal: AbortSignal, model: DetectorModel = "owlvit"): Promise<Blob> {
  const response = await postImage("/detect-image", image, query, signal, model);
  if (!response.headers.get("content-type")?.includes("image/jpeg")) {
    throw new Error("Backend beklenen JPEG görüntüsünü döndürmedi.");
  }
  const blob = await response.blob();
  if (!blob.size) throw new Error("Backend boş bir sonuç görüntüsü döndürdü.");
  return blob;
}

function isStringList(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isDetection(value: unknown): value is Detection {
  if (!value || typeof value !== "object") return false;
  const detection = value as Partial<Detection>;
  const box = detection.box;
  return typeof detection.label === "string"
    && typeof detection.confidence === "number" && Number.isFinite(detection.confidence)
    && (detection.model_query === undefined || typeof detection.model_query === "string")
    && (detection.canonical_query === undefined || typeof detection.canonical_query === "string")
    && !!box && [box.xmin, box.ymin, box.xmax, box.ymax].every((n) => typeof n === "number" && Number.isFinite(n));
}

export async function getDetectionDetails(image: File, query: string, signal: AbortSignal, model: DetectorModel = "owlvit"): Promise<DetectionDetails> {
  const response = await postImage("/detect", image, query, signal, model);
  return readDetectionDetails(response, model);
}

function isThreshold(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
}

function isThresholdAttempt(value: unknown): value is ThresholdAttempt {
  if (!value || typeof value !== "object") return false;
  const attempt = value as Partial<ThresholdAttempt>;
  return isThreshold(attempt.threshold)
    && Number.isInteger(attempt.raw_detection_count) && (attempt.raw_detection_count ?? -1) >= 0
    && Number.isInteger(attempt.filtered_detection_count) && (attempt.filtered_detection_count ?? -1) >= 0
    && (attempt.text_threshold === undefined || isThreshold(attempt.text_threshold))
    && (attempt.phase === undefined || attempt.phase === "primary" || attempt.phase === "fallback")
    && (attempt.queries === undefined || isStringList(attempt.queries))
    && (attempt.canonical_query === undefined || typeof attempt.canonical_query === "string")
    && validSceneDiagnostics(attempt);
}

function validSceneDiagnostics(value: SceneBoxDiagnostics): boolean {
  const validRemoved = (value.oversized_boxes_removed === undefined && value.oversized_boxes_removed_count === undefined)
    || (Array.isArray(value.oversized_boxes_removed)
    && value.oversized_boxes_removed_count === value.oversized_boxes_removed.length
    && value.oversized_boxes_removed.every((entry) => entry && typeof entry === "object"
      && isDetection(entry.detection)
      && typeof entry.area_ratio === "number" && Number.isFinite(entry.area_ratio) && entry.area_ratio >= 0
      && entry.reason === "oversized_scene_box" && isStringList(entry.near_borders)
      && (entry.threshold === undefined || isThreshold(entry.threshold))
      && (entry.phase === undefined || entry.phase === "primary" || entry.phase === "fallback")
      && (entry.canonical_query === undefined || typeof entry.canonical_query === "string")));
  const nonnegative = (n: unknown): n is number => typeof n === "number" && Number.isFinite(n) && n >= 0;
  return validRemoved && (value.scene_box_diagnostics === undefined
    || (Array.isArray(value.scene_box_diagnostics) && value.scene_box_diagnostics.every((entry) =>
      entry && typeof entry === "object" && isDetection(entry.detection)
      && nonnegative(entry.area_ratio) && nonnegative(entry.box_area) && nonnegative(entry.image_area) && entry.image_area > 0
      && (entry.width_coverage === undefined || nonnegative(entry.width_coverage))
      && (entry.height_coverage === undefined || nonnegative(entry.height_coverage))
      && entry.image_size && nonnegative(entry.image_size.width) && entry.image_size.width > 0
      && nonnegative(entry.image_size.height) && entry.image_size.height > 0
      && entry.edge_distance_ratios
      && [entry.edge_distance_ratios.left, entry.edge_distance_ratios.right, entry.edge_distance_ratios.top, entry.edge_distance_ratios.bottom].every(nonnegative)
      && isStringList(entry.near_borders) && Number.isInteger(entry.touched_edges)
      && entry.touched_edges === entry.near_borders.length && entry.touched_edges >= 0 && entry.touched_edges <= 4
      && (entry.matched_rule === null || entry.matched_rule === "rule_a" || entry.matched_rule === "rule_b" || entry.matched_rule === "rule_c")
      && typeof entry.removed === "boolean" && entry.removed === (entry.matched_rule !== null)
      && (entry.reason === "oversized_scene_box" || entry.reason === "scene_box_criteria_not_met")
      && (entry.threshold === undefined || isThreshold(entry.threshold))
      && (entry.canonical_query === undefined || typeof entry.canonical_query === "string"))));
}

function isQueryItem(value: unknown): value is ProcessedQueryItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<ProcessedQueryItem>;
  return typeof item.original_query === "string" && typeof item.primary_query === "string"
    && typeof item.detected_language === "string"
    && (item.translated_query === null || typeof item.translated_query === "string")
    && isStringList(item.processed_queries) && isStringList(item.fallback_queries_used)
    && typeof item.fallback_triggered === "boolean" && isThreshold(item.adaptive_threshold_used)
    && typeof item.threshold_selection_reason === "string"
    && Array.isArray(item.threshold_attempts) && item.threshold_attempts.every(isThresholdAttempt);
}

function validInventory(details: Partial<DetectionDetails>): boolean {
  const counts = details.inventory_summary;
  if (counts === undefined) return details.total_detected_objects === undefined;
  if (!counts || typeof counts !== "object" || Array.isArray(counts) || !Array.isArray(details.detections)) return false;
  const entries = Object.entries(counts);
  if (!entries.length || entries.some(([query, count]) => !query.trim() || !Number.isInteger(count) || count < 0)) return false;
  if (details.total_detected_objects !== details.detections.length
      || entries.reduce((sum, [, count]) => sum + count, 0) !== details.total_detected_objects) return false;
  const actual = new Map<string, number>(entries.map(([query]) => [query, 0]));
  for (const detection of details.detections) {
    if (!isDetection(detection) || !detection.canonical_query || !actual.has(detection.canonical_query)) return false;
    actual.set(detection.canonical_query, actual.get(detection.canonical_query)! + 1);
  }
  return entries.every(([query, count]) => actual.get(query) === count);
}

async function readDetectionDetails(response: Response, model: DetectorModel): Promise<DetectionDetails> {
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new Error("Backend'in teknik detay yanıtı okunamadı.");
  }
  if (!data || typeof data !== "object") throw new Error("Backend'in teknik detay yanıtı geçersiz.");
  const details = data as Partial<DetectionDetails>;
  if (
    typeof details.model !== "string"
    || details.model_id !== model
    || typeof details.inference_time_ms !== "number" || !Number.isFinite(details.inference_time_ms) || details.inference_time_ms < 0
    || typeof details.device !== "string"
    || typeof details.query !== "string"
    || typeof details.original_query !== "string"
    || typeof details.detected_language !== "string"
    || (details.translated_query !== null && typeof details.translated_query !== "string")
    || typeof details.primary_query !== "string"
    || typeof details.fallback_triggered !== "boolean"
    || !isStringList(details.processed_queries)
    || !isStringList(details.fallback_queries_used)
    || !Number.isInteger(details.raw_detection_count) || (details.raw_detection_count ?? -1) < 0
    || !Number.isInteger(details.filtered_detection_count) || (details.filtered_detection_count ?? -1) < 0
    || !Array.isArray(details.detections) || !details.detections.every(isDetection)
    || (details.adaptive_threshold_used !== undefined && !isThreshold(details.adaptive_threshold_used))
    || (details.threshold_attempts !== undefined && (!Array.isArray(details.threshold_attempts) || !details.threshold_attempts.every(isThresholdAttempt)))
    || (details.threshold_selection_reason !== undefined && typeof details.threshold_selection_reason !== "string")
    || !validInventory(details)
    || !validSceneDiagnostics(details)
    || (details.processed_query_items !== undefined && (!Array.isArray(details.processed_query_items) || !details.processed_query_items.every(isQueryItem)))
    || (details.adaptive_thresholds_by_query !== undefined && (!details.adaptive_thresholds_by_query
      || typeof details.adaptive_thresholds_by_query !== "object" || Array.isArray(details.adaptive_thresholds_by_query)
      || !Object.values(details.adaptive_thresholds_by_query).every(isThreshold)))
  ) {
    throw new Error("Backend'in teknik detay yanıtı beklenen formatta değil.");
  }
  return details as DetectionDetails;
}

function withAnnotatedImage(data: DetectionDetails & { annotated_image?: { media_type?: unknown; data_base64?: unknown } }): DetectionAnalysis {
  const { annotated_image: annotated, ...details } = data;
  if (!annotated || annotated.media_type !== "image/jpeg" || typeof annotated.data_base64 !== "string" || !annotated.data_base64) {
    throw new Error("Backend birleşik görsel yanıtını döndürmedi. Güncel backend sürümünü yeniden başlatın.");
  }
  let bytes: Uint8Array<ArrayBuffer>;
  try {
    bytes = Uint8Array.from(atob(annotated.data_base64), (character) => character.charCodeAt(0));
    if (bytes.length < 3 || bytes[0] !== 0xff || bytes[1] !== 0xd8 || bytes[2] !== 0xff) throw new Error("Invalid JPEG");
  } catch {
    throw new Error("Backend'in sonuç görüntüsü okunamadı.");
  }
  return { details, image: new Blob([bytes], { type: "image/jpeg" }) };
}

export async function getDetectionAnalysis(image: File, query: string, signal: AbortSignal, model: DetectorModel = "owlvit", englishQuery?: string, sensitivity: Sensitivity = "balanced"): Promise<DetectionAnalysis> {
  // Tek orchestration çalışması hem metadata hem annotate edilmiş JPEG üretir.
  const response = await postImage("/detect", image, query, signal, model, true, englishQuery, sensitivity);
  return withAnnotatedImage(await readDetectionDetails(response, model));
}

/** Görselde çizilen kutuya benzeyen nesneleri bulur; kutu orijinal piksel koordinatlarındadır. */
export async function getExampleAnalysis(image: File, box: Box, label: string, signal: AbortSignal, sensitivity: Sensitivity = "balanced"): Promise<DetectionAnalysis> {
  const form = new FormData();
  form.append("image", image);
  for (const key of ["xmin", "ymin", "xmax", "ymax"] as const) form.append(key, String(Math.round(box[key])));
  if (label.trim()) form.append("label", label.trim());
  form.append("model", "owlvit");
  form.append("include_image", "true");
  if (sensitivity !== "balanced") form.append("sensitivity", sensitivity);
  const response = await sendForm("/detect-by-example", form, signal);
  return withAnnotatedImage(await readDetectionDetails(response, "owlvit"));
}
