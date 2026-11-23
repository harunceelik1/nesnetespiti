# Kısa karşılaştırma: aynı 20 nadir-nesne görseli (LVIS r)

Her model kendi en iyi eşiğinde (bu görsellerde F1'i en yüksek eşik).

| Model | En iyi eşik | Nadir nesneyi bulduğu | Tüm 'var' soruları | Precision | Recall | F1 | Olmayan nesneye kutu |
|---|---|---|---|---|---|---|---|
| OWLv2 | 0.15 | **16/20** | 80/96 | 0.65 | 0.56 | **0.60** | 2/80 (%2) |
| OWLv2 large | 0.10 | **18/20** | 84/96 | 0.53 | 0.60 | **0.56** | 4/80 (%5) |
| Grounding DINO | 0.27 | **10/20** | 58/96 | 0.56 | 0.38 | **0.46** | 16/80 (%20) |
| LLMDet (base) | 0.23 | **10/20** | 61/96 | 0.46 | 0.38 | **0.42** | 18/80 (%22) |
| YOLO-World | 0.06 | **4/20** | 38/96 | 0.47 | 0.26 | **0.33** | 4/80 (%5) |

Küçük örneklem (20 görsel); 2–3 soruluk farklar anlamlı değil.
