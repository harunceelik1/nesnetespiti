# Dilimleme denemesi: masa fotoğrafları, OWLv2 large

Dilimler: 2×2, %25 örtüşme. Tam görsel + 4 dilim = görsel başına 5 forward.
Her satır kendi en iyi eşiğinde ve uygulamanın Sıkı (0.17) / Dengeli (0.14) eşiğinde. IoU >= 0.5.

| Yöntem | Eşik | Bulunan nesne | Precision | Recall | F1 | Olmayan nesneye kutu | Bulunamayanlar |
|---|---|---|---|---|---|---|---|
| Tam görsel (mevcut) | 0.17 (en iyi) | 37/45 | 0.82 | 0.82 | **0.82** | 5/50 (%10) | battery, bottle opener, deodorant, electric shaver, perfume |
| Tam görsel (mevcut) | 0.17 (Sıkı) | 37/45 | 0.82 | 0.82 | **0.82** | 5/50 (%10) | battery, bottle opener, deodorant, electric shaver, perfume |
| Tam görsel (mevcut) | 0.14 (Dengeli) | 38/45 | 0.72 | 0.84 | **0.78** | 5/50 (%10) | battery, bottle opener, deodorant, electric shaver, perfume |
| Tam + dilimler (NMS) | 0.29 (en iyi) | 34/45 | 0.60 | 0.76 | **0.67** | 6/50 (%12) | battery, bottle opener, cream jar, deodorant, electric shaver, perfume |
| Tam + dilimler (NMS) | 0.17 (Sıkı) | 39/45 | 0.44 | 0.87 | **0.58** | 11/50 (%22) | bottle opener, deodorant, electric shaver, perfume |
| Tam + dilimler (NMS) | 0.14 (Dengeli) | 40/45 | 0.40 | 0.89 | **0.56** | 15/50 (%30) | bottle opener, deodorant, electric shaver, perfume |
| Tam + dilimler, kesik kutular atılır | 0.29 (en iyi) | 34/45 | 0.83 | 0.76 | **0.79** | 4/50 (%8) | battery, bottle opener, cream jar, deodorant, electric shaver, perfume |
| Tam + dilimler, kesik kutular atılır | 0.17 (Sıkı) | 38/45 | 0.63 | 0.84 | **0.72** | 8/50 (%16) | bottle opener, deodorant, electric shaver, perfume |
| Tam + dilimler, kesik kutular atılır | 0.14 (Dengeli) | 38/45 | 0.57 | 0.84 | **0.68** | 10/50 (%20) | bottle opener, deodorant, electric shaver, perfume |
| Tam + küçük dilim kutuları (dilim eşiği 0.30) | 0.17 (en iyi) | 38/45 | 0.83 | 0.84 | **0.84** | 5/50 (%10) | bottle opener, deodorant, electric shaver, perfume |
| Tam + küçük dilim kutuları (dilim eşiği 0.30) | 0.17 (Sıkı) | 38/45 | 0.83 | 0.84 | **0.84** | 5/50 (%10) | bottle opener, deodorant, electric shaver, perfume |
| Tam + küçük dilim kutuları (dilim eşiği 0.30) | 0.14 (Dengeli) | 39/45 | 0.74 | 0.87 | **0.80** | 5/50 (%10) | bottle opener, deodorant, electric shaver, perfume |
| Yalnızca dilimler, kesikler atılır | 0.22 (en iyi) | 30/45 | 0.71 | 0.67 | **0.69** | 5/50 (%10) | battery, bottle opener, cream jar, deodorant, electric shaver, headphones, notebook, perfume |
| Yalnızca dilimler, kesikler atılır | 0.17 (Sıkı) | 31/45 | 0.60 | 0.69 | **0.64** | 8/50 (%16) | battery, bottle opener, deodorant, electric shaver, headphones, notebook, perfume |
| Yalnızca dilimler, kesikler atılır | 0.14 (Dengeli) | 31/45 | 0.55 | 0.69 | **0.61** | 10/50 (%20) | battery, bottle opener, deodorant, electric shaver, headphones, notebook, perfume |

Küçük örneklem: 5 fotoğraf, 45 nesne.
