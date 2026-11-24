# Ölçüm özeti: Açık Sözlük Nesne Tespiti

Son güncelleme: 2026-11-24. Bütün ölçümler buradan başlar; her satırın kaynağı yanında yazılı.
Uygulamanın tek yöntemi **OWLv2 large** (eğitimsiz / zero-shot). Diğer modeller yalnızca karşılaştırma için ölçüldü.

## Veri setleri: her birinin tek görevi var

| Veri seti | Görevi | Boyut |
|---|---|---|
| **LVIS v1 val** (ana ölçüt) | Ödevin ana sorusu: eğitimde nadir / görülmemiş nesne | 345 görsel, 175 farklı nadir nesne, 303 nadir soru |
| **RPC market** | Envanter senaryosu: sayım, hassasiyet kalibrasyonu, örnekle arama | 12 kalibrasyon + 60 test görseli |
| **Masa fotoğrafları** (kullanıcının) | Gerçek kullanım örneği (küçük örneklem, ek kanıt) | 5 fotoğraf, 45 elle işaretli nesne |

## 1. Ana sonuç: LVIS, sık / nadir nesne
Kaynak: `lvis_olcum/ana_olcum.md`. Dengeli eşik, IoU ≥ 0.5. Köşeli parantez: görsel bazında %95 güven aralığı.
Nadir (r) = LVIS eğitim kümesinde ≤ 10 görselde geçen nesne. Model makaleleri "görülmemiş nesne" başarısını bununla raporluyor.

| Model | Sık F1 | Nadir F1 [%95] | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |
|---|---|---|---|---|
| **OWLv2 large (uygulama)** | 0.58 | **0.56** [0.50–0.61] | %73 | %4 |
| OWLv2 base | 0.52 | 0.55 [0.49–0.61] | %67 | %4 |
| Grounding DINO tiny | 0.43 | 0.33 [0.25–0.43] | %36 | %17 |
| YOLO-World s | 0.34 | 0.15 [0.11–0.20] | %16 | %3 |

- OWLv2 nadir nesnede sık nesnedeki başarısını koruyor. DINO ve YOLO-World belirgin şekilde düşüyor.
- OWLv2 ailesi ile diğerleri arasındaki fark güven aralıkları çakışmayacak kadar net.
- Large ile base nadir F1'de berabere. Large nadir nesneyi daha sık buluyor ve sık nesnede daha iyi.

## 2. Gerçek kullanım: masa fotoğrafları
Kaynak: `masa_olcum/masa_olcum.md`. Her fotoğrafta 19 soru; 5'i görselde olmayan nesne. Her model kendi en iyi eşiğinde.

| Model | Bulunan nesne | F1 | Olmayan nesneye kutu |
|---|---|---|---|
| **OWLv2 large** | **37/45** | **0.82** | 5/50 |
| OWLv2 base | 31/45 | 0.71 | 4/50 |
| LLMDet base | 21/45 | 0.55 | 4/50 |
| Grounding DINO tiny | 20/45 | 0.51 | 8/50 |
| YOLO-World s | 20/45 | 0.50 | 8/50 |

- Large'ın en iyi eşiği Sıkı (0.17). Uygulamanın varsayılanı olan Dengeli eşikte (0.14) F1 0.78 (38/45).
- Tam görselde hiçbir modelin bulamadığı nesneler: pil, açacak, deodorant, tıraş makinesi, parfüm.

## 3. Envanter (RPC market)
- **Metinle sayım:** OWLv2 large, Dengeli eşik. Kaynak: `config.py` gerekçe tablosu, `hassasiyet/owlv2-large.txt`.
  - P 0.95 / R 0.78 / F1 0.85.
  - Geniş eşikte F1 0.93; market sayımı için Geniş daha uygun.
- **Örnekle arama:** RPC 60 test görseli, Dengeli. P 0.54 / R 0.66.
  - Bu ölçüm OWLv2 base döneminde yapıldı (2026-11-22); large ile tekrarlanmadı.

## 4. Yöntemin sınırları ve denemeler
- **Küçük nesne (dilimleme, 2x2):** uygulamada yok. Kaynak: `masa_olcum/dilimleme.md`, `lvis_olcum/dilimleme_nadir.md`.
  - Masa F1 0.82 → 0.84; pil bulunuyor.
  - Eski 50 görsellik LVIS nadir kümesinde 0.50 → 0.53.
- **Soyut kavram** ("alkollü içecek"): OWLv2 bulamıyor, Grounding DINO buluyor. Örnek: `sunum/sonuclar/04_*`.
- **Kelime baskınlığı** ("tv unit" → televizyon): ifade düzeltilince çözülüyor. Örnek: `sunum/sonuclar/08_*`.

## 5. Çeviri (Türkçe → İngilizce)
Kaynak: `ceviri/karsilastirma.md`. 183 sorgu.
- Marian + bağlam cümlesi: **%93** doğru (uygulamada bu).
- Düz Marian %85, opus-big %90, NLLB %77.

## 6. Hız (RTX 5060 Laptop GPU, OWLv2 large)
- Yeni görselde arama: 1.2 sn. Aynı görselde tekrar arama: 0.05 sn. Türkçe çeviri buna ~0.7 sn ekliyor.
- GPU ve CPU sonuçları birebir aynı (puan farkı ≤ 0.0002).

## Eski ölçümler (tarihçe; ana ölçütün yerine geçmez)
Her biri 50 görsellik LVIS kümeleriyle yapıldı ve ana kümeyle yer değiştirdi:
- `lvis_olcum/temel_olcum.md`
- `lvis_olcum/siklik_karsilastirma.md`
- `lvis_olcum/yontem_secimi.md`
- `lvis_olcum/kisa_karsilastirma.md`
- `lvis_olcum/goreli_filtre*.md`
