import { ScanSearch } from "lucide-react";
import DetectionWorkspace from "@/components/detection-workspace";

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 px-4 py-6 sm:px-6 lg:py-8">
      <header className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <ScanSearch aria-hidden="true" className="size-5" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight sm:text-xl">Açık Sözlük Nesne Tespiti</h1>
          <p className="text-sm text-muted-foreground">Görsel yükle, ne aradığını yaz; model eğitimde görmediği nesneleri de bulmaya çalışsın.</p>
        </div>
      </header>
      <DetectionWorkspace />
    </main>
  );
}
