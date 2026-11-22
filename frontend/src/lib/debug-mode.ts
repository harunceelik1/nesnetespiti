import { useSyncExternalStore } from "react";

/**
 * Geliştirici modu: adres çubuğunda ?debug=1 varsa ham tanılar (eşik denemeleri,
 * scene-box ölçümleri, backend alan adları) Teknik detaylar içinde gösterilir.
 * Sunucu render'ında ve normal kullanımda kapalıdır.
 */
export function isDebugSearch(search: string): boolean {
  const value = new URLSearchParams(search).get("debug");
  return value !== null && value !== "0" && value !== "false";
}

const subscribe = (onChange: () => void) => {
  window.addEventListener("popstate", onChange);
  return () => window.removeEventListener("popstate", onChange);
};

export function useDebugMode(): boolean {
  return useSyncExternalStore(subscribe, () => isDebugSearch(window.location.search), () => false);
}
