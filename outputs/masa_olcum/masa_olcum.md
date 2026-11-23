# Kullanıcının masa fotoğrafları (5 fotoğraf, 45 nesne, elle işaretli)

Her fotoğrafta 19 nesne soruldu; görselde olmayanlar 'yok' sorusu. IoU >= 0.5.
Her model kendi en iyi eşiğinde (bu fotoğraflarda F1'i en yüksek eşik); aynı iyimser muamele.

| Model | En iyi eşik | Bulunan nesne | Precision | Recall | F1 | Olmayan nesneye kutu | Bulunamayanlar |
|---|---|---|---|---|---|---|---|
| OWLv2 | 0.28 | 31/45 | 0.74 | 0.69 | **0.71** | 4/50 (%8) | battery, bottle opener, cream jar, deodorant, electric shaver, notebook, perfume, tic-tac-toe game |
| Grounding DINO | 0.59 | 20/45 | 0.59 | 0.44 | **0.51** | 8/50 (%16) | battery, bottle opener, cream jar, deodorant, electric shaver, hair spray, perfume, tic-tac-toe game, wet wipes |
| YOLO-World | 0.21 | 20/45 | 0.57 | 0.44 | **0.50** | 8/50 (%16) | battery, bottle opener, cream jar, deodorant, electric shaver, hair spray, notebook, perfume, tic-tac-toe game, wet wipes |
| OWLv2 large | 0.17 | 37/45 | 0.82 | 0.82 | **0.82** | 5/50 (%10) | battery, bottle opener, deodorant, electric shaver, perfume |
| LLMDet (base) | 0.42 | 21/45 | 0.68 | 0.47 | **0.55** | 4/50 (%8) | battery, bottle opener, cream jar, deodorant, electric shaver, hair spray, headphones, notebook, perfume, tic-tac-toe game, wet wipes |

Küçük örneklem: tek bir masa, 5 fotoğraf. LVIS ölçümünü tamamlar, yerine geçmez.
