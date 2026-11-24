# Ana ölçüm: LVIS v1 val, 345 görsel (sık / ara / nadir)

Küme: temel 50 görsel + tam etiketli nadir nesne içeren görsellerin tamamı (175 farklı nadir nesne).
LVIS sıklık sınıfı: f > 100 eğitim görseli, c 11–100, **r ≤ 10 (görülmemiş nesne ölçütü)**. IoU ≥ 0.5.
Eşik: her modelin Dengeli eşiği (uygulamanın varsayılanı). Köşeli parantez: görsel bazında bootstrap %95 aralığı.

## Özet

| Model | Eşik | Sık F1 | Nadir F1 [%95 aralık] | Sık→nadir düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |
|---|---|---|---|---|---|---|
| **OWLv2 large (uygulama)** | 0.14 | 0.58 | **0.56** [0.50–0.61] | %3 | 220/303 (%73) | %4 |
| OWLv2 base | 0.13 | 0.52 | **0.55** [0.49–0.61] | %-6 | 204/303 (%67) | %4 |
| Grounding DINO tiny | 0.30 | 0.43 | **0.33** [0.25–0.43] | %23 | 110/303 (%36) | %17 |
| YOLO-World s | 0.10 | 0.34 | **0.15** [0.11–0.20] | %55 | 47/303 (%16) | %3 |

## Ayrıntı

| Model | Sınıf | 'Var' sorusu | Nesneyi en az bir kez bulduğu | Precision | Recall | F1 | 'Yok' sorusu | Uydurma kutu |
|---|---|---|---|---|---|---|---|---|
| **OWLv2 large (uygulama)** | Sık (f) | 1284 | 1086 (%85) | 0.60 | 0.55 | 0.58 | 156 | %6 |
| **OWLv2 large (uygulama)** | Ara (c) | 130 | 105 (%81) | 0.52 | 0.57 | 0.54 | 649 | %4 |
| **OWLv2 large (uygulama)** | Nadir (r) | 303 | 220 (%73) | 0.55 | 0.56 | 0.56 | 575 | %3 |
| OWLv2 base | Sık (f) | 1284 | 1127 (%88) | 0.57 | 0.48 | 0.52 | 156 | %7 |
| OWLv2 base | Ara (c) | 130 | 98 (%75) | 0.47 | 0.40 | 0.43 | 649 | %4 |
| OWLv2 base | Nadir (r) | 303 | 204 (%67) | 0.61 | 0.51 | 0.55 | 575 | %4 |
| Grounding DINO tiny | Sık (f) | 1284 | 891 (%69) | 0.73 | 0.31 | 0.43 | 156 | %14 |
| Grounding DINO tiny | Ara (c) | 130 | 51 (%39) | 0.52 | 0.22 | 0.31 | 649 | %16 |
| Grounding DINO tiny | Nadir (r) | 303 | 110 (%36) | 0.62 | 0.23 | 0.33 | 575 | %18 |
| YOLO-World s | Sık (f) | 1284 | 727 (%57) | 0.59 | 0.24 | 0.34 | 156 | %9 |
| YOLO-World s | Ara (c) | 130 | 24 (%18) | 0.41 | 0.05 | 0.09 | 649 | %3 |
| YOLO-World s | Nadir (r) | 303 | 47 (%16) | 0.54 | 0.09 | 0.15 | 575 | %2 |

Eski 50'lik kümelerin sonuçları (temel_olcum.md, siklik_karsilastirma.md, yontem_secimi.md) korunur;
bu tablo onların yerine ana ölçüttür.
