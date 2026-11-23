import type { DetectionDetails } from "./detection-api";

export interface ModelResult {
  imageUrl: string | null;
  details: DetectionDetails | null;
  phase: "idle" | "image" | "details" | "done" | "error";
  error: string | null;
  warning: string | null;
  elapsedMs: number | null;
}

export function emptyResult(): ModelResult {
  return { imageUrl: null, details: null, phase: "idle", error: null, warning: null, elapsedMs: null };
}
