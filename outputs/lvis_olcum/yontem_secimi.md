# Tek yöntem seçimi: sık / ara / nadir LVIS nesneleri

Eşik: her model için yalnızca temel kümede (çoğu sık nesne) F1'i en yüksek yapan değer; nadir küme
eşik seçiminde kullanılmadı. Üretimdeki iki model kalibre Dengeli eşikle de verildi.

| Model | Eşik | Sık F1 | Ara F1 | Nadir F1 | Sık→nadir düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |
|---|---|---|---|---|---|---|---|
| OWLv2 | 0.18 | 0.56 | 0.40 | **0.49** | %13 | %71 | %3 |
| OWLv2 (Dengeli) | 0.13 | 0.55 | 0.41 | **0.50** | %10 | %75 | %5 |
| OWLv2 large | 0.14 | 0.57 | 0.45 | **0.50** | %11 | %73 | %4 |
| Grounding DINO | 0.27 | 0.50 | 0.22 | **0.21** | %57 | %37 | %24 |
| Grounding DINO (Dengeli) | 0.30 | 0.48 | 0.21 | **0.21** | %57 | %33 | %21 |
| LLMDet (base) | — | ölçülmedi | | | | | |
| YOLO-World | 0.06 | 0.41 | 0.18 | **0.11** | %72 | %14 | %7 |

Nadir 'var' sorusu 51 tane; iki nokta altı farklar anlamlı sayılmamalı.
