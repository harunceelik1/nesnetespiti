# Dilimleme doğrulaması: LVIS nadir kümesi, OWLv2 large

50 görsel (çoğu 640×480). 2×2 dilim, %25 örtüşme; tam görsel + 4 dilim = 5 forward.
Eşik 0.14 = temel kümede F1'i en yüksek eşik (yontem_secimi.md ile aynı); 0.17 = Sıkı.
Sık / ara / nadir: yalnızca bu kümede sorulan nesneler. IoU >= 0.5.

## Tam görsel eşiği 0.14

| Yöntem | Eşik | Sık F1 | Ara F1 | Nadir F1 | Sık→nadir düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |
|---|---|---|---|---|---|---|---|
| Tam görsel (mevcut) | 0.14 | 0.58 | 0.45 | **0.50** | %12 | %73 | %4 |
| Tam + dilimler (NMS) | 0.14 | 0.49 | 0.35 | **0.51** | %-3 | %78 | %8 |
| Tam + dilimler, kesik kutular atılır | 0.14 | 0.59 | 0.41 | **0.58** | %2 | %75 | %8 |
| **Masada seçilen kural** (dilim eşiği 0.3, alan <= %1) | 0.14 | 0.58 | 0.47 | **0.53** | %10 | %73 | %4 |
| (ayar) dilim eşiği 0.2, alan <= %1 | 0.14 | 0.59 | 0.45 | **0.60** | %-2 | %75 | %5 |
| (ayar) dilim eşiği 0.25, alan <= %1 | 0.14 | 0.59 | 0.47 | **0.59** | %0 | %73 | %4 |
| (ayar) dilim eşiği 0.35, alan <= %1 | 0.14 | 0.58 | 0.47 | **0.51** | %13 | %73 | %4 |
| (ayar) dilim eşiği 0.4, alan <= %1 | 0.14 | 0.58 | 0.47 | **0.51** | %13 | %73 | %4 |
| (ayar) dilim eşiği 0.30, alan sınırı yok | 0.14 | 0.59 | 0.47 | **0.52** | %11 | %73 | %4 |

## Tam görsel eşiği 0.17

| Yöntem | Eşik | Sık F1 | Ara F1 | Nadir F1 | Sık→nadir düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |
|---|---|---|---|---|---|---|---|
| Tam görsel (mevcut) | 0.17 | 0.56 | 0.42 | **0.47** | %17 | %69 | %4 |
| Tam + dilimler (NMS) | 0.17 | 0.51 | 0.40 | **0.52** | %-2 | %78 | %6 |
| Tam + dilimler, kesik kutular atılır | 0.17 | 0.61 | 0.43 | **0.58** | %4 | %73 | %6 |
| **Masada seçilen kural** (dilim eşiği 0.3, alan <= %1) | 0.17 | 0.57 | 0.43 | **0.53** | %8 | %69 | %4 |
| (ayar) dilim eşiği 0.2, alan <= %1 | 0.17 | 0.59 | 0.44 | **0.60** | %-2 | %71 | %4 |
| (ayar) dilim eşiği 0.25, alan <= %1 | 0.17 | 0.59 | 0.43 | **0.59** | %-1 | %69 | %4 |
| (ayar) dilim eşiği 0.35, alan <= %1 | 0.17 | 0.57 | 0.43 | **0.51** | %11 | %69 | %4 |
| (ayar) dilim eşiği 0.4, alan <= %1 | 0.17 | 0.57 | 0.43 | **0.48** | %16 | %69 | %4 |
| (ayar) dilim eşiği 0.30, alan sınırı yok | 0.17 | 0.58 | 0.43 | **0.53** | %7 | %71 | %4 |

Nadir 'var' sorusu 51 tane; iki nokta altı farklar anlamlı sayılmamalı.
'(ayar)' satırları LVIS'te ayarlanmıştır, kanıt değil bilgi içindir.
