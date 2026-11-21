import type { DetectionDetails, DetectorModel } from "./detection-api";

export interface ModelResult {
  imageUrl: string | null;
  details: DetectionDetails | null;
  phase: "idle" | "image" | "details" | "done" | "error";
  error: string | null;
  warning: string | null;
  elapsedMs: number | null;
}

export type ModelResults = Record<DetectorModel, ModelResult>;
export const DETECTOR_MODELS: DetectorModel[] = ["owlvit", "grounding-dino", "yolo-world"];

export function emptyResults(): ModelResults {
  const empty = (): ModelResult => ({
    imageUrl: null, details: null, phase: "idle", error: null, warning: null, elapsedMs: null,
  });
  return { owlvit: empty(), "grounding-dino": empty(), "yolo-world": empty() };
}
