# Sık / ara / nadir LVIS kategorilerinde üç model (Dengeli eşik)

LVIS sıklık sınıfı: f > 100 eğitim görseli, c 11–100, **r ≤ 10 (görülmemiş nesne ölçütü)**.
İki alt küme birlikte: temel (50 görsel, çoğu sık nesne) + nadir (50 görsel, 50 farklı nadir nesne).

| Model | Sınıf | 'Var' sorusu | Nesneyi en az bir kez bulduğu soru | Precision | Recall | F1 | 'Yok' sorusu | Uydurma kutu |
|---|---|---|---|---|---|---|---|---|
| OWLv2 | Sık (f) | 430 | 386 (%90) | 0.57 | 0.53 | 0.55 | 89 | %7 |
| OWLv2 | Ara (c) | 39 | 28 (%72) | 0.49 | 0.35 | 0.41 | 194 | %5 |
| OWLv2 | Nadir (r) | 51 | 38 (%75) | 0.56 | 0.44 | 0.50 | 117 | %4 |
| Grounding DINO | Sık (f) | 430 | 307 (%71) | 0.73 | 0.36 | 0.48 | 89 | %20 |
| Grounding DINO | Ara (c) | 39 | 15 (%38) | 0.52 | 0.14 | 0.21 | 194 | %22 |
| Grounding DINO | Nadir (r) | 51 | 17 (%33) | 0.33 | 0.15 | 0.21 | 117 | %21 |
| YOLO-World | Sık (f) | 430 | 255 (%59) | 0.60 | 0.29 | 0.39 | 89 | %7 |
| YOLO-World | Ara (c) | 39 | 8 (%21) | 0.45 | 0.08 | 0.14 | 194 | %5 |
| YOLO-World | Nadir (r) | 51 | 5 (%10) | 0.28 | 0.04 | 0.08 | 117 | %2 |

## Özet: sık nesneden nadir nesneye F1 düşüşü

| Model | Sık F1 | Nadir F1 | Düşüş |
|---|---|---|---|
| OWLv2 | 0.55 | 0.50 | %10 |
| Grounding DINO | 0.48 | 0.21 | %57 |
| YOLO-World | 0.39 | 0.08 | %80 |

Not: nadir 'var' sorusu sayısı küçüktür (~50); yüzdeler birkaç soruyla değişebilir.
