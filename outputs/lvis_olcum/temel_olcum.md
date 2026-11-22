# LVIS alt kümesi (50 görsel) · temel ölçüm

Her görselde en fazla 6 'var' ve 4 'yok' sorgusu; IoU >= 0.5 eşleşme.
Yanlış kutu = eşleşmeyen kutu + olmayan nesneye çizilen kutu.

| Model | Hassasiyet | Eşik | Doğru | Yanlış kutu | Kaçırılan | Precision | Recall | F1 | Olmayan nesneye kutu |
|---|---|---|---|---|---|---|---|---|---|
| OWLv2 | Sıkı | 0.17 | 485 | 307 | 585 | 0.61 | 0.45 | 0.52 | 6/200 (%3) |
| OWLv2 | Dengeli | 0.13 | 530 | 483 | 540 | 0.52 | 0.50 | 0.51 | 10/200 (%5) |
| OWLv2 | Geniş | 0.10 | 556 | 701 | 514 | 0.44 | 0.52 | 0.48 | 17/200 (%8) |
| Grounding DINO | Sıkı | 0.35 | 318 | 123 | 752 | 0.72 | 0.30 | 0.42 | 30/200 (%15) |
| Grounding DINO | Dengeli | 0.30 | 358 | 203 | 712 | 0.64 | 0.33 | 0.44 | 41/200 (%20) |
| Grounding DINO | Geniş | 0.27 | 381 | 244 | 689 | 0.61 | 0.36 | 0.45 | 47/200 (%24) |
| YOLO-World | Sıkı | 0.25 | 231 | 90 | 839 | 0.72 | 0.22 | 0.33 | 1/200 (%0) |
| YOLO-World | Dengeli | 0.10 | 297 | 215 | 773 | 0.58 | 0.28 | 0.38 | 8/200 (%4) |
| YOLO-World | Geniş | 0.05 | 363 | 377 | 707 | 0.49 | 0.34 | 0.40 | 17/200 (%8) |

## Gruplara göre (Dengeli) · F1 / olmayan nesneye kutu oranı

| Model | masa | envanter | guvenlik | kucuk | benzer |
|---|---|---|---|---|---|
| OWLv2 | 0.65 / %2 | 0.46 / %8 | 0.53 / %0 | 0.44 / %10 | 0.55 / %4 |
| Grounding DINO | 0.51 / %25 | 0.44 / %19 | 0.59 / %8 | 0.29 / %28 | 0.43 / %25 |
| YOLO-World | 0.45 / %2 | 0.33 / %6 | 0.47 / %0 | 0.34 / %8 | 0.38 / %4 |
