"use client";

import { useEffect, useState, type PointerEvent } from "react";
import type { Box } from "@/lib/detection-api";

interface Props {
  /** Üzerine kutu çizilen <img>; görsel object-fit: contain ile gösterilir. */
  image: HTMLImageElement | null;
  box: Box | null;
  onChange: (box: Box | null) => void;
}

interface Layout { width: number; height: number; naturalWidth: number; naturalHeight: number }

/** object-fit: contain: görselin kutu içindeki gerçek yeri ve ölçeği. */
function contentRect(layout: Layout) {
  const scale = Math.min(layout.width / layout.naturalWidth, layout.height / layout.naturalHeight);
  return { scale, left: (layout.width - layout.naturalWidth * scale) / 2, top: (layout.height - layout.naturalHeight * scale) / 2 };
}

function measure(image: HTMLImageElement): Layout | null {
  const rect = image.getBoundingClientRect();
  if (!image.naturalWidth || !image.naturalHeight || !rect.width || !rect.height) return null;
  return { width: rect.width, height: rect.height, naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight };
}

/** Görselin üstüne sürükleyerek örnek kutu çizdirir; kutu orijinal piksel koordinatlarında döner. */
export default function ExampleSelector({ image, box, onChange }: Props) {
  const [layout, setLayout] = useState<Layout | null>(null);
  const [start, setStart] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!image) return;
    const update = () => setLayout(measure(image));
    update();
    image.addEventListener("load", update);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(update);
    observer?.observe(image);
    return () => { image.removeEventListener("load", update); observer?.disconnect(); };
  }, [image]);

  function toImage(event: PointerEvent<HTMLDivElement>) {
    if (!image) return null;
    const current = measure(image);
    if (!current) return null;
    // Katman CSS ile <img>'nin tam üstündedir; koordinat görselin kendi kutusundan okunur.
    const rect = image.getBoundingClientRect();
    const { scale, left, top } = contentRect(current);
    const clamp = (value: number, max: number) => Math.min(max, Math.max(0, value));
    return {
      x: clamp((event.clientX - rect.left - left) / scale, current.naturalWidth),
      y: clamp((event.clientY - rect.top - top) / scale, current.naturalHeight),
    };
  }

  function boxFrom(a: { x: number; y: number }, b: { x: number; y: number }): Box {
    return { xmin: Math.min(a.x, b.x), ymin: Math.min(a.y, b.y), xmax: Math.max(a.x, b.x), ymax: Math.max(a.y, b.y) };
  }

  function down(event: PointerEvent<HTMLDivElement>) {
    const point = toImage(event);
    if (!point) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setStart(point);
    onChange(null);
  }

  function move(event: PointerEvent<HTMLDivElement>) {
    if (!start) return;
    const point = toImage(event);
    if (point) onChange(boxFrom(start, point));
  }

  function up(event: PointerEvent<HTMLDivElement>) {
    if (!start) return;
    const point = toImage(event);
    setStart(null);
    if (!point) return;
    const drawn = boxFrom(start, point);
    // Tek tık / titreme: kutu sayılmaz.
    onChange(drawn.xmax - drawn.xmin >= 8 && drawn.ymax - drawn.ymin >= 8 ? drawn : null);
  }

  const view = layout && box ? (() => {
    const { scale, left, top } = contentRect(layout);
    return { left: left + box.xmin * scale, top: top + box.ymin * scale,
      width: (box.xmax - box.xmin) * scale, height: (box.ymax - box.ymin) * scale };
  })() : null;

  return (
    <div className="example-overlay" data-testid="example-overlay" aria-label="Örnek nesnenin etrafına kutu çizin"
      onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={() => setStart(null)}>
      {view && <div className="example-box" style={view} />}
    </div>
  );
}
