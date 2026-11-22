# Sunum senaryosu

Bütün sayılar `sonuclar/ozet.json`'dan; her adımın kutulu sonuç görseli `sonuclar/` altında
(`NN_ad_model.jpg`). Sunumdan önce backend açıkken `.venv\Scripts\python.exe sunum\hazirla.py`
ile yeniden üret: sayılar değişirse bu dosyayı ona göre güncelle.

**Canlı demo önerisi:** CPU'da tek model 8–16 sn, karşılaştırma 20+ sn sürüyor. Canlı olarak yalnızca
1, 3 ve 6. adımları yap; diğerlerinde hazır görselleri göster.

Hassasiyet her adımda **Dengeli** (varsayılan).

---

## 1. Temel kullanım: Türkçe yaz, model bulsun
- **Görsel:** `gorseller/masa_12.jpeg` · **Sorgu:** `makas` · **Model:** Üç modeli karşılaştır
- **Sonuç:** üç model de makası buluyor: OWLv2 0.75 · Grounding DINO 0.90 · YOLO-World 0.58
- **Söyle:** "Türkçe yazıyorum; sistem bağlam cümlesiyle İngilizceye çeviriyor (*scissors*), modele bu gidiyor.
  Aranan ifade satırında modele ne gittiğini görüyorum, gerekirse düzeltebiliyorum."

## 2. Envanter senaryosu: birden fazla nesneyi say
- **Görsel:** `gorseller/market_12.jpg` (RPC market verisi) · **Sorgu:** `sakız, şişe` · **Model:** OWLv2
- **Sonuç:** 24 kutu (envanter özeti tablosu). **Dikkat:** "sakız" → *gum* çevirisi kısa; OWLv2 bazı
  erişte paketlerini de sakız sanıyor (düşük puanlı, 0.14–0.17 kutular).
- **Söyle:** "Metinle arama sayım yapabiliyor ama kısa/genel kelimelerde benzer paketleri karıştırabiliyor.
  Bunun için ikinci bir arama yolumuz var." → 3. adıma geç.

## 3. Örnekle arama: adını bilmeden, örnek göstererek bul
- **Görsel:** `gorseller/market_12.jpg` · **Mod:** Örnekle ara · bir Stride sakız paketinin etrafına kutu çiz
- **Sonuç:** 6 kutu; 5'i Stride paketi (0.91–1.00), 1'i pembe mendil paketi (0.91, yanlış)
- **Söyle:** "Robotik ve envanterde ürünün adı her zaman bilinmez; tek bir örnek yeterli. Metin aramasına göre
  çok daha isabetli, ama renk/şekil olarak benzeyen bir paketi de yakalayabiliyor."

## 4. Modeller farklı düşünür: soyut kavram
- **Görsel:** `gorseller/market_05.jpg` · **Sorgu:** `alkollü içecek` · **Model:** Üç modeli karşılaştır
- **Sonuç:** yalnızca Grounding DINO iki Budweiser kutusunu buluyor (0.39, 0.38); OWLv2 ve YOLO-World 0
- **Söyle:** "OWLv2 görünüşe bakıyor; 'alkol' bir görünüş değil, kavram. DINO'nun dil modeli (BERT) kavramı
  bira kutusuyla ilişkilendirebiliyor. Hangi modelin seçileceği sorunun türüne bağlı."

## 5. Eğitimde nadir görülen nesne
- **Görsel:** `gorseller/masa_12.jpeg` · **Sorgu:** `saç spreyi` · **Model:** Üç modeli karşılaştır
- **Sonuç:** OWLv2 şişeyi 0.44 ile buluyor (düz kırmızı kutu); tıraş makinesi ve pil 0.19 ile
  **kesikli turuncu "?"** kutu olarak gösteriliyor ("3 nesne bulundu · 2 tanesi emin değil").
  Grounding DINO ve YOLO-World hiçbir şey bulamıyor.
- **Söyle:** "Saç spreyi standart veri setlerinde neredeyse yok. OWLv2 web ölçeğinde eğitildiği için genelleyebiliyor,
  diğer ikisi bu nesnede kalıyor. En iyi eşleşmenin yarısından düşük puanlı kutuları silmiyoruz, kesikli gösteriyoruz:
  ölçümde bu kutuların LVIS'te %87'si yanlış çıktı, ama market görsellerinde silmek doğru ürünlerin beşte birini
  kaybettiriyordu (F1 0.84 → 0.77). İşaretlemek ikisinin ortası."

## 6. Olmayan nesneye kutu çiziyor mu?
- **Görsel:** `gorseller/masa_12.jpeg` · **Sorgu:** `kedi` · **Model:** Üç modeli karşılaştır
- **Sonuç:** üç model de 0 kutu
- **Söyle:** "Açık sözlük modellerinin bilinen riski, olmayan nesneye de bir şey uydurmak. Eşikleri bu yüzden
  'olmayan nesne' vakalarıyla kalibre ettik; Hassasiyet ayarı bu dengeyi kullanıcıya veriyor."
  (Hassasiyet: Sıkı / Dengeli / Geniş seçeneklerini burada göster.)

## 7. Hiç görülmeyen nesneler (ödevin ana iddiası)
LVIS'in **nadir (r)** kategorileri: eğitim kümesinde ≤ 10 görselde geçen nesneler. Model makaleleri "görülmemiş nesne"
başarısını bu ölçütle raporluyor. Örnekleri İngilizce yaz (ölçüm İngilizce adlarla yapıldı, çeviri karışmasın).
- **Görsel:** `gorseller/nadir_kibrit_kutusu.jpg` · **Sorgu:** `matchbox` · **Model:** Üç modeli karşılaştır
  - **Sonuç:** OWLv2 kibrit kutusunu buluyor (0.52) · Grounding DINO yanlış nesneye kutu çiziyor · YOLO-World 0
- **Görsel:** `gorseller/nadir_bozuk_para.jpg` · **Sorgu:** `penny` · **Model:** Üç modeli karşılaştır
  - **Sonuç:** yalnızca OWLv2 buluyor (0.78); DINO ve YOLO-World 0
- **Görsel:** `gorseller/nadir_kelepce.jpg` · **Sorgu:** `handcuff` · **Model:** Üç modeli karşılaştır
  - **Sonuç:** üçü de bulamıyor (sınır örneği: nadir nesnede en iyi model de her zaman başaramıyor)
- **Tablo** (`outputs/lvis_olcum/siklik_karsilastirma.md`, Dengeli eşik, 100 LVIS görseli):

  | Model | Sık nesne F1 | Nadir nesne F1 | Düşüş | Olmayan nesneye kutu |
  |---|---|---|---|---|
  | OWLv2 | 0.55 | 0.50 | %10 | %4–7 |
  | Grounding DINO | 0.48 | 0.21 | %57 | %20–22 |
  | YOLO-World | 0.39 | 0.08 | %80 | %2–7 |

- **Söyle:** "Asıl soru buydu: eğitimde neredeyse hiç görülmemiş nesnede ne oluyor? OWLv2 sık nesnedeki başarısının
  %90'ını koruyor; YOLO-World nadir nesnelerin yalnızca %10'unda nesneyi bir kez bulabiliyor. Grounding DINO arada,
  ama olmayan nesneye de kutu uydurma eğilimi her sınıfta ~%20. Sebep eğitim verisi: OWLv2 web ölçeğinde görsel–metin
  çiftleriyle (kendi ürettiği sözde etiketlerle) eğitildi; DINO ve YOLO-World daha dar, insan etiketli verilerle (Objects365, GoldG vb.) eğitildi. Not: nadir soru sayısı 51;
  yüzdeler birkaç soruyla oynayabilir, ama sıralama ve fark net."

## 8. Sınırlar: kelime baskınlığı ve düzeltme
- **Görsel:** `gorseller/otel_odasi_lvis.jpg` · **Sorgu:** `televizyon ünitesi` · **Model:** Üç modeli karşılaştır
- **Sonuç (*tv unit*):** OWLv2 dolabı buluyor (0.36) · DINO **televizyonu** işaretliyor (0.93) ·
  YOLO-World televizyon (0.68) + dolap (0.60)
- **Düzenle → `tv stand`:** OWLv2 dolap (0.41) · DINO dolap 0.53 > televizyon 0.39 · YOLO-World dolap (0.63)
- **Söyle:** "Tamlamalarda modeller en tanıdık kelimeye ('tv') takılıyor. İfade netleşince sonuç düzeliyor;
  kullanıcı modele giden ifadeyi görüp düzeltebiliyor."

## 9. Sınırlar: küçük nesne
- **Görsel:** `gorseller/masa_9.jpeg` · **Sorgu:** `pil` · **Model:** Üç modeli karşılaştır
- **Sonuç:** OWLv2 pili buluyor (0.22) ama parfüme de aynı puanda kutu çiziyor · Grounding DINO parfüm ve krem
  kavanozunu işaretliyor (yanlış) · YOLO-World pili bulamıyor
- **Söyle:** "Modeller görseli 640–960 piksele küçültüyor; telefon fotoğrafında pil birkaç düzine piksele iniyor.
  Ölçtük: aynı görselin pili içeren bir dilimini verince YOLO-World pili buluyor, OWLv2'nin puanı 0.19 → 0.36'ya çıkıyor.
  Çözüm önerisi: dilimleme (SAHI) ile 'küçük nesne modu'."

## 10. Ölçüm tabloları
- `outputs/lvis_olcum/temel_olcum.md`: LVIS 50 görsel, üç model, Sıkı/Dengeli/Geniş · precision / recall / F1 /
  olmayan nesneye kutu oranı
- `outputs/ceviri/karsilastirma.md`: çeviri yöntemlerinin karşılaştırması (Marian + bağlam %93)
- `outputs/lvis_olcum/siklik_karsilastirma.md`: sık / ara / nadir LVIS kategorilerinde üç model (ödevin ana tablosu)
