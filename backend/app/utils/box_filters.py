"""NMS sonrası kutu temizliği: parça kutuları, boşluk kutuları ve bölge kutuları.

Ölçüm (evaluation/region_boxes.py, 20 RPC görseli): OWLv2'nin "ürün" kutularının
%26'sı bir ürünün içindeki parça kutusu, %20'si ürün arası/boşluk kutusuydu.
NMS bunları elemez; çünkü küçük kutu ile büyük kutunun IoU'su düşüktür.
"""

from .nms import calculate_iou


def _inside(inner: dict, outer: dict) -> float:
    """inner kutusunun alanının ne kadarı outer içinde."""
    w = max(0.0, min(inner["xmax"], outer["xmax"]) - max(inner["xmin"], outer["xmin"]))
    h = max(0.0, min(inner["ymax"], outer["ymax"]) - max(inner["ymin"], outer["ymin"]))
    area = max(0.0, inner["xmax"] - inner["xmin"]) * max(0.0, inner["ymax"] - inner["ymin"])
    return w * h / area if area > 0 else 0.0


def clean_boxes(detections: list[dict], *, min_objectness: float = 0.0, max_containment: float | None = None,
                drop_regions: bool = False) -> list[dict]:
    """Aynı etiketli kutular arasında:

    - min_objectness: objectness puanı (yalnızca OWLv2 verir) bunun altındaysa at.
    - max_containment: kutunun alanının bu kadarı daha yüksek puanlı tutulan bir kutunun
      içindeyse at (parça kutusu).
    - drop_regions: içine tutulan en az iki kutuyu (%80) alan kutuyu at (bölge kutusu).
    """
    kept: list[dict] = []
    for det in sorted(detections, key=lambda d: -d["confidence"]):
        if det.get("objectness") is not None and det["objectness"] < min_objectness:
            continue
        same = [k for k in kept if k["label"] == det["label"]]
        if max_containment is not None and any(_inside(det["box"], k["box"]) >= max_containment for k in same):
            continue
        kept.append(det)
    if drop_regions:
        kept = [d for d in kept
                if sum(1 for k in kept if k is not d and k["label"] == d["label"]
                       and _inside(k["box"], d["box"]) >= 0.8 and calculate_iou(k["box"], d["box"]) < 0.5) < 2]
    return kept
