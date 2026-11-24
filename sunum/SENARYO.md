# Sunum senaryosu

**Uygulama tek yöntemle çalışır: OWLv2 large.** Diğer modeller (OWLv2 base, Grounding DINO, YOLO-World)
yalnızca karşılaştırma için gösterilir: ölçüm tabloları ve hazır sonuç görselleri.

- Sayılar `sonuclar/ozet.json` dosyasından gelir. Her adımın kutulu sonuç görseli `sonuclar/NN_ad_model.jpg` adıyla kayıtlı.
  Model ekleri: `owlv2-large` (uygulama), `owlv2-base`, `grounding-dino`, `yolo-world`.
- Yeniden üretmek için backend gerekmez, GPU'da ~1,5 dk sürer: `.venv\Scripts\python.exe sunum\hazirla.py`.
  Sayılar değişirse bu dosyayı güncelle.
- **Canlı demo:** GPU'da (RTX 5060) uygulama yeni görselde ~1,5–2,5 sn, aynı görselde tekrar aramada ~0,8 sn sürüyor
  (Türkçe çeviri dahil; çeviri hâlâ CPU'da ve ~0,7 sn tutuyor). Backend'i sunumdan önce başlat: model yükleme birkaç saniye.
  OWLv2 large adımlarının hepsi canlı yapılabilir. Diğer modeller canlı değil; onların hazır görsellerini göster.
- Hassasiyet her adımda **Dengeli** (varsayılan).
- **Önemli:** güven puanları modeller arasında karşılaştırılamaz; her modelin puan ölçeği farklı.
  Karşılaştırılacak olan, doğru nesnenin bulunup bulunmadığı.

---

## 1. Temel kullanım: Türkçe yaz, model bulsun
- **Görsel:** `gorseller/masa_12.jpeg` · **Sorgu:** `makas` **(canlı)**
- **Sonuç:** OWLv2 large makası buluyor (0.54). Karşılaştırma görsellerinde dört model de buluyor:
  base 0.75 · Grounding DINO 0.90 · YOLO-World 0.58.
- **Söyle:** "Türkçe yazıyorum; sistem bağlam cümlesiyle İngilizceye çeviriyor (*scissors*), modele bu gidiyor.
  'Aranan ifade' satırında modele ne gittiğini görüyorum, gerekirse düzeltebiliyorum. Sık görülen bir nesnede bütün
  modeller başarılı; fark nadir nesnede ortaya çıkıyor."

## 2. Envanter senaryosu: birden fazla nesneyi say
- **Görsel:** `gorseller/market_12.jpg` (RPC market verisi) · **Sorgu:** `sakız, şişe` **(canlı)**
- **Sonuç:** 16 kutu.
  - Doğru olanlar: 5 Stride sakız paketinin hepsi ve 4 şişe.
  - Yanlış olanlar: 7 kutu daha "sakız" diyor (pembe paketler, gofretler, erişte). Hepsi düşük puanlı, 0.15–0.26.
  - Ama doğru sakız kutuları da 0.17–0.27 arasında, yani eşik bunları ayıramıyor.
- **Söyle:** "Metinle arama sayım yapabiliyor ama 'sakız' gibi kısa, genel kelimelerde benzer paketleri karıştırıyor.
  Bunun için ikinci bir arama yolumuz var." → 3. adıma geç.

## 3. Örnekle arama: adını bilmeden, örnek göstererek bul
- **Görsel:** `gorseller/market_12.jpg` · **Mod:** Örnekle ara · bir Stride paketinin etrafına kutu çiz **(canlı)**
- **Sonuç:** 5 kutu, 5'i de Stride paketi (0.93–1.00); yanlış kutu yok.
- **Söyle:** "Robotik ve envanterde ürünün adı her zaman bilinmez; tek bir örnek yeterli. Aynı görselde metin araması
  7 yanlış kutu verirken örnekle arama hepsini doğru buluyor."

## 4. Sınır: soyut kavram
- **Görsel:** `gorseller/market_05.jpg` · **Sorgu:** `alkollü içecek` **(canlı + karşılaştırma görselleri)**
- **Sonuç:** OWLv2 large 0 kutu (base ve YOLO-World de 0). Yalnızca Grounding DINO iki Budweiser kutusunu buluyor (0.39, 0.38).
- **Söyle:** "OWLv2 görünüşe bakıyor; 'alkol' bir görünüş değil, bir kavram. DINO'nun dil modeli (BERT) kavramı bira
  kutusuyla ilişkilendirebiliyor. Seçtiğimiz yöntemin zayıf olduğu bir soru türü bu; dürüstçe gösteriyoruz."

## 5. Eğitimde nadir görülen nesne
- **Görsel:** `gorseller/masa_12.jpeg` · **Sorgu:** `saç spreyi` **(canlı + karşılaştırma görselleri)**
- **Sonuç:** OWLv2 large şişeyi 0.52 ile buluyor (düz kırmızı kutu).
  - Tıraş makinesi (0.22) ve pil (0.25) **kesikli turuncu "?"** kutu olarak gösteriliyor ("3 nesne bulundu · 2 tanesi emin değil").
  - Base de buluyor (0.44). Grounding DINO ve YOLO-World hiçbir şey bulamıyor.
- **Söyle:** "Saç spreyi standart veri setlerinde neredeyse yok. OWLv2 web ölçeğinde eğitildiği için genelleyebiliyor,
  diğer iki model bu nesnede kalıyor.
  En iyi eşleşmenin yarısından düşük puanlı kutuları silmiyoruz, kesikli gösteriyoruz. Ölçümde bu kutuların LVIS'te
  çoğu yanlış çıktı, ama market görsellerinde silmek doğru ürünlerin bir kısmını kaybettiriyordu (F1 0.84 → 0.77).
  İşaretlemek ikisinin ortası." (Bu ölçüm OWLv2 base ile yapıldı.)

## 6. Olmayan nesneye kutu çiziyor mu?
- **Görsel:** `gorseller/masa_12.jpeg` · **Sorgu:** `kedi` **(canlı)**
- **Sonuç:** dört model de 0 kutu.
- **Söyle:** "Açık sözlük modellerinin bilinen riski, olmayan nesneye de bir şey uydurmak. Eşikleri bu yüzden
  'olmayan nesne' vakalarıyla kalibre ettik; Hassasiyet ayarı bu dengeyi kullanıcıya veriyor."
  (Hassasiyet: Sıkı / Dengeli / Geniş seçeneklerini burada göster.)

## 7. Hiç görülmeyen nesneler (ödevin ana iddiası)
LVIS'in **nadir (r)** kategorileri, eğitim kümesinde ≤ 10 görselde geçen nesneler. Model makaleleri "görülmemiş nesne"
başarısını bu ölçütle raporluyor.

- **Görsel:** `gorseller/nadir_omlet.jpg` · **Sorgu:** `omlet` **(canlı)**
  - **Sonuç:** OWLv2 large arka tabaktaki omleti buluyor (0.38); base de buluyor (0.56).
  - Grounding DINO 0. YOLO-World portakal dilimlerini omlet sanıyor (0.15, yanlış).
- **Görsel:** `gorseller/nadir_kibrit_kutusu.jpg` · **Sorgu:** `matchbox`
  - **Sonuç:** OWLv2 large bıçağın yanındaki kibrit kutusunu buluyor (0.28); base de buluyor (0.52).
  - Grounding DINO bıçakla kutuyu tek büyük kutuya alıyor (0.31, ölçümde yanlış sayıldı). YOLO-World 0.
  - Türkçe `kibrit kutusu` *matchbook* olarak çevriliyor ve large'ın puanı 0.18'e düşüyor.
    Düzenle → `matchbox` ile düzelir (çeviri sınırı örneği).
- **Görsel:** `gorseller/nadir_kelepce.jpg` · **Sorgu:** `kelepçe`
  - **Sonuç (*handcuffs*):** OWLv2 (large ve base) ve YOLO-World 0. Grounding DINO adamın **kol saatine** "kelepçe" diyor (0.40).
  - Tekil `handcuff` ile DINO da 0 kutu veriyor; uydurma kutu ifadeye bağlı.
  - **Söyle:** "Nadir nesnede en iyi model de bazen bulamıyor; DINO ise bulamayınca benzer bir şeye kutu uyduruyor.
    Tablodaki ~%20 uydurma oranının canlı örneği."
- (Yedek) `gorseller/nadir_bozuk_para.jpg` · `penny`: yalnızca OWLv2 buluyor (large 0.59, base 0.78), ama paralar
  çok küçük, ekranda zor görünüyor.
- **Tablo** (`outputs/lvis_olcum/yontem_secimi.md` ve `siklik_karsilastirma.md`; Dengeli eşik; 100 LVIS görseli, 51 nadir soru):

  | Model | Sık nesne F1 | Nadir nesne F1 | Düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |
  |---|---|---|---|---|---|
  | **OWLv2 large (uygulama)** | 0.57 | **0.50** | %11 | %73 | %4 |
  | OWLv2 base | 0.55 | 0.50 | %10 | %75 | %5 |
  | Grounding DINO tiny | 0.48 | 0.21 | %57 | %33 | %21 |
  | YOLO-World s | 0.39 | 0.08 | %80 | %10 | %2–7 |

- **Söyle:** "Asıl soru buydu: eğitimde neredeyse hiç görülmemiş nesnede ne oluyor? OWLv2 sık nesnedeki başarısının
  ~%90'ını koruyor. YOLO-World nadir nesnelerin yalnızca %10'unu bir kez bulabiliyor. Grounding DINO arada kalıyor,
  ama olmayan nesneye kutu uydurma eğilimi her sınıfta ~%20.
  Sebep eğitim verisi: OWLv2 web ölçeğinde görsel–metin çiftleriyle (kendi ürettiği sözde etiketlerle) eğitildi;
  DINO ve YOLO-World daha dar, insan etiketli verilerle (Objects365, GoldG vb.) eğitildi."
- **Dürüstlük notu (söyle):** "LVIS nadir nesnelerinde OWLv2 large ile base berabere. Large'ı seçmemizin sebebi kendi
  fotoğraflarımız (8. adımdaki tablo): orada fark büyük. Nadir soru sayısı 51; 1–2 soruluk farklar anlamlı değil,
  ama aileler arasındaki fark (0.50'ye 0.21 ve 0.08) net."

## 8. Gerçek kullanım: kendi masa fotoğraflarımız
- 5 fotoğraf, 45 elle işaretli nesne, her fotoğrafta 19 soru; 5'i görselde olmayan nesne
  (`outputs/masa_olcum/masa_olcum.md`). Her model kendi en iyi eşiğinde değerlendirildi:

  | Model | Bulunan nesne | F1 | Olmayan nesneye kutu |
  |---|---|---|---|
  | **OWLv2 large (uygulama)** | **37/45** | **0.82** | 5/50 (%10) |
  | OWLv2 base | 31/45 | 0.71 | 4/50 (%8) |
  | LLMDet base | 21/45 | 0.55 | 4/50 (%8) |
  | Grounding DINO tiny | 20/45 | 0.51 | 8/50 (%16) |
  | YOLO-World s | 20/45 | 0.50 | 8/50 (%16) |

- Uygulamanın varsayılanı Dengeli eşik; orada large'ın F1'i 0.78 (38/45). Sorulursa bunu söyle.
- **Söyle:** "Large'ı seçmemizin asıl gerekçesi bu: gerçek kullanımda base'den 6, diğer ailelerden 16–17 nesne fazla buluyor.
  Örneklem küçük (tek masa), LVIS ölçümünü tamamlıyor ama yerine geçmiyor."

## 9. Sınırlar: kelime baskınlığı ve düzeltme
- **Görsel:** `gorseller/otel_odasi_lvis.jpg` · **Sorgu:** `televizyon ünitesi` **(canlı + karşılaştırma görselleri)**
- **Sonuç (*tv unit*):** OWLv2 large dolabı buluyor (0.28), base de öyle (0.36). DINO **televizyonu** işaretliyor (0.92).
  YOLO-World televizyon (0.69) + dolap (0.60).
- **Düzenle → `tv stand`:** OWLv2 large dolap 0.43 · base dolap 0.41 · DINO dolap 0.53 > televizyon 0.39 · YOLO-World dolap 0.63
- **Söyle:** "Tamlamalarda modeller en tanıdık kelimeye ('tv') takılabiliyor. İfade netleşince sonuç düzeliyor;
  kullanıcı modele giden ifadeyi görüp düzeltebiliyor."

## 10. Sınırlar: küçük nesne
- **Görsel:** `gorseller/masa_9.jpeg` · **Sorgu:** `pil` **(canlı + karşılaştırma görselleri)**
- **Sonuç:**
  - OWLv2 large pili buluyor (0.31; cevap anahtarındaki kutuyla örtüşüyor), parfüme de daha düşük bir kutu çiziyor (0.17).
  - Base pil ve parfüme aynı puanı veriyor (0.22 / 0.22).
  - Grounding DINO parfüm ve krem kavanozunu işaretliyor (yanlış).
  - YOLO-World parfümü ve tıraş makinesini işaretliyor (yanlış).
- **Söyle:** "Modeller görseli 640–960 piksele küçültüyor; telefon fotoğrafında pil birkaç düzine piksele iniyor.
  Ölçtük: görseli 2x2 dilime bölüp küçük nesneleri dilimlerden de alınca masa fotoğraflarında F1 0.82'den 0.84'e,
  LVIS nadir nesnelerde 0.50'den 0.53'e çıkıyor ve pil her fotoğrafta bulunuyor
  (`outputs/masa_olcum/dilimleme.md`, `outputs/lvis_olcum/dilimleme_nadir.md`). Uygulamada henüz yok."
- Tam görselde hiçbir modelin bulamadığı nesneler: açacak, deodorant, tıraş makinesi, parfüm (ve dilimlemesiz pil).

## 11. Ölçüm tabloları
- `outputs/lvis_olcum/yontem_secimi.md`: aday modeller, sık / ara / nadir LVIS (tek yöntem seçimi)
- `outputs/lvis_olcum/siklik_karsilastirma.md`: sık / ara / nadir ayrıntılı tablo (Grounding DINO, YOLO-World, OWLv2 base)
- `outputs/masa_olcum/masa_olcum.md`: kendi masa fotoğraflarımız
- `outputs/ceviri/karsilastirma.md`: çeviri yöntemleri (Marian + bağlam %93)
- `outputs/lvis_olcum/dilimleme_nadir.md`, `outputs/masa_olcum/dilimleme.md`: küçük nesne denemesi
