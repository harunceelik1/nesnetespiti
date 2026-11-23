import DetectionWorkspace from "@/components/detection-workspace";

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-[1480px] flex-col px-4 pb-10 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-x-8 gap-y-1 border-b border-foreground/80 pb-3 pt-6 lg:pt-8">
        <h1 className="text-[1.75rem] font-semibold leading-none tracking-[-0.01em] sm:text-[2.125rem]">Açık Sözlük Nesne Tespiti</h1>
        <p className="max-w-[46ch] text-sm leading-snug text-muted-foreground">
          Görsel yükle, ne aradığını Türkçe yaz. Model, eğitimde hiç görmediği nesneleri de bulmaya çalışır.
        </p>
      </header>
      <DetectionWorkspace />
    </main>
  );
}
