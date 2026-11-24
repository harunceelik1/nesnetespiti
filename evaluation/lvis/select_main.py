"""Ana LVIS ölçüm kümesi (subset_ana.json): ödevin tek ana ölçütü.

İçerik:
  - temel küme (subset_50.json, 50 görsel; ödev senaryoları: masa, envanter, güvenlik, küçük, benzer),
  - LVIS v1 val'de tam etiketli nadir (r) nesne içeren ve en az 3 "kesinlikle yok" etiketi olan
    görsellerin **tamamı** (select_rare.rare_subset, count=None; ~295 görsel, ~175 nadir kategori).
Aynı görsel iki listede de varsa temel kümedeki kaydı tutulur (focus alanları birleştirilir).
Eski 50'lik kümeler (subset_50.json, subset_nadir_50.json) ve sonuçları değişmez.

Kullanım (proje kökünden):
  .venv\\Scripts\\python.exe -m evaluation.lvis.select_main --download
Görseller: images.cocodataset.org (LVIS v1 val = COCO 2017 görselleri), .cache/lvis/images altına.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from evaluation.lvis.select_rare import FREQUENCY_FILE, rare_subset
from evaluation.lvis.select_subset import ANNOTATIONS, IMAGE_DIR, SUBSET_FILE as TEMEL_FILE, download

SUBSET_FILE = Path(__file__).with_name("subset_ana.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    data = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    frequency = json.loads(FREQUENCY_FILE.read_text(encoding="utf-8"))
    rare, candidates, _ = rare_subset(data, None)
    subset = json.loads(TEMEL_FILE.read_text(encoding="utf-8"))
    by_id = {item["image_id"]: item for item in subset}
    for item in rare:
        if item["image_id"] in by_id:
            kept = by_id[item["image_id"]]
            kept["focus"] = sorted(set(kept.get("focus", [])) | set(item["focus"]))
        else:
            subset.append(item); by_id[item["image_id"]] = item
    SUBSET_FILE.write_text(json.dumps(subset, ensure_ascii=False, indent=1), encoding="utf-8")

    rare_cats = {c for i in subset for c in i["positives"] if frequency[c] == "r"}
    missing = [i for i in subset if not (IMAGE_DIR / i["file_name"]).exists()]
    print(f"{len(subset)} görsel (temel {len(json.loads(TEMEL_FILE.read_text(encoding='utf-8')))} + nadir havuz {candidates}) · "
          f"{len(rare_cats)} farklı nadir kategori · eksik görsel {len(missing)}")
    print("Gruplar:", dict(Counter(i["group"] for i in subset)))
    if args.download:
        download(missing)
        print(f"Görseller: {IMAGE_DIR}")


if __name__ == "__main__":
    main()
