# Göreli puan filtresi · LVIS 50 görsel (Dengeli eşik üstüne)

Kural: aynı görselde aynı sorgunun en iyi kutusunun `oran` katından düşük puanlı kutular atılır.

| Model | Oran | Doğru | Yanlış kutu | Kaçırılan | Precision | Recall | F1 | Olmayan nesneye kutu |
|---|---|---|---|---|---|---|---|---|
| OWLv2 | filtresiz | 530 | 483 | 540 | 0.52 | 0.50 | 0.51 | %5 |
| OWLv2 | 0.3 | 526 | 400 | 544 | 0.57 | 0.49 | 0.53 | %5 |
| OWLv2 | 0.4 | 517 | 320 | 553 | 0.62 | 0.48 | 0.54 | %5 |
| OWLv2 | 0.5 | 495 | 253 | 575 | 0.66 | 0.46 | 0.54 | %5 |
| OWLv2 | 0.6 | 457 | 190 | 613 | 0.71 | 0.43 | 0.53 | %5 |
| OWLv2 | 0.7 | 415 | 152 | 655 | 0.73 | 0.39 | 0.51 | %5 |
| Grounding DINO | — | henüz ölçülmedi | | | | | | |
| YOLO-World | filtresiz | 297 | 215 | 773 | 0.58 | 0.28 | 0.38 | %4 |
| YOLO-World | 0.3 | 285 | 153 | 785 | 0.65 | 0.27 | 0.38 | %4 |
| YOLO-World | 0.4 | 273 | 127 | 797 | 0.68 | 0.26 | 0.37 | %4 |
| YOLO-World | 0.5 | 257 | 95 | 813 | 0.73 | 0.24 | 0.36 | %4 |
| YOLO-World | 0.6 | 239 | 75 | 831 | 0.76 | 0.22 | 0.35 | %4 |
| YOLO-World | 0.7 | 217 | 66 | 853 | 0.77 | 0.20 | 0.32 | %4 |

## Gruplara göre F1 (filtresiz → oran 0.5)

| Model | masa | envanter | guvenlik | kucuk | benzer |
|---|---|---|---|---|---|
| OWLv2 | 0.65 → 0.66 | 0.46 → 0.51 | 0.53 → 0.61 | 0.44 → 0.46 | 0.55 → 0.58 |
| YOLO-World | 0.45 → 0.49 | 0.33 → 0.30 | 0.47 → 0.43 | 0.34 → 0.32 | 0.38 → 0.38 |
