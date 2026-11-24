# Slayt hazırlama brief'i: Açık Sözlük Nesne Tespiti

Bu dosya, slaytları hazırlayacak oturum için yazıldı ve tek başına yeterli olacak şekilde düzenlendi.
Bütün rakamlar ölçüm dosyalarından alındı (kaynaklar her bölümde yazılı). **Burada olmayan bir rakam uydurma;**
bir şeyden emin değilsen kaynağına bak (`outputs/OZET.md` bütün ölçümlerin giriş noktası).

## 1. Bağlam ve beklenti
- **Ders ödevi:** Açık Sözlük Nesne Tespiti. Senaryolar: robotik, envanter, güvenlik.
- **Ana soru:** Model eğitimde nadir görülen ya da hiç görülmemiş nesneleri ne kadar iyi buluyor?
- **Yöntem:** OWLv2 large (Google), eğitimsiz (zero-shot). İnce ayar yok; bilerek yapılmadı, çünkü nadir nesnelerle
  eğitmek onları "görülmemiş" olmaktan çıkarır.
- **Sunum dili:** Türkçe. Sunum 2026-12 ilk haftasında, bu laptopla yapılacak.
- **Hocanın beklentisi:** "sınırları zorlayan", etkileyici bir sistem. Model karşılaştırması şart değil, ama
  karşılaştırma "neden bu yöntem" sorusunun kanıtı olduğu için gösteriliyor.
- **Diğer grupların sunumlarından gözlem** (kullanıcı, 2026-11-24):
  - Her şeyden bahsettiler.
  - **Performans ölçütleri ve test performansları önemliydi.**
  - Sunumun sonunda **3–4 dakika, 1–2 fotoğrafla** uygulamayı canlı gösterdiler.
  - **Bu sunum da aynı yapıda olmalı:** önce yöntem, ölçütler ve test sonuçları (sunumun ağırlığı), en sonda kısa canlı demo.
- **Süre:** kullanıcı belirtmedi. ~15 dakika varsay; ana bölüm ~11 dk, demo 3–4 dk.

## 2. Tasarım kuralları (kullanıcının tercihleri)
- **Palet:** uygulamanın görsel diliyle aynı, "vizör / ölçüm cihazı".
  - Soğuk açık gri zemin, lacivert koyu alanlar, camgöbeği vurgu.
  - **Kırmızı yalnızca tespit kutusu, turuncu yalnızca "emin değil" kutusu** anlamında kullanılsın.
- **Kaçınılacak:** sıcak krem/bej zemin ve kırmızı/kil vurgu. Kullanıcı bunu "Claude temasına benziyor" diye istemedi.
- **Yazı tipi:** Bahnschrift (Windows'ta yüklü). Sade, kartsız; bölümleri çizgiler ayırsın.
- **Tablolar:** az sütun, büyük rakam. Her slaytta bir mesaj; slayt başlığı o mesajın cümlesi olsun.
  Örnek: "OWLv2 nadir nesnede başarısını koruyor".
- **Biçim:** .pptx ya da PDF (kullanıcı düzenleyebilsin).

## 3. Ölçütler: slaytta kısaca tanımlanmalı
- **IoU ≥ 0.5:** çizilen kutu gerçek kutuyla en az %50 örtüşürse doğru sayılır. LVIS / COCO standardı.
- **Precision:** çizilen kutuların ne kadarı doğru.
- **Recall:** gerçek nesnelerin ne kadarı bulundu.
- **F1:** precision ve recall'un harmonik ortalaması (tek sayı).
- **Nadir nesneyi bulduğu soru:** sorulan nadir nesnenin görselde en az bir kez doğru bulunduğu soruların oranı.
- **Olmayan nesneye kutu (uydurma oranı):** görselde kesinlikle olmayan bir nesne sorulduğunda kutu çizilen soruların oranı.
  Açık sözlük modellerinin bilinen riski bu.
- **%95 güven aralığı:** görseller yeniden örneklenerek (bootstrap, 2000 tekrar) hesaplandı.
  Aralıklar çakışmıyorsa fark güvenilir.
- **LVIS sıklık sınıfları:** sık (f) > 100 eğitim görseli · ara (c) 11–100 · **nadir (r) ≤ 10**.
  Nadir sınıf, model makalelerinin "görülmemiş nesne" ölçütü.

## 4. Test düzeni: veri setleri (her birinin tek görevi var)

| Veri seti | Görevi | Boyut |
|---|---|---|
| **LVIS v1 val** (ana ölçüt) | Nadir / görülmemiş nesne başarısı | 345 görsel, 175 farklı nadir nesne, 303 nadir soru, 1284 sık nesne sorusu |
| **RPC market** | Envanter: sayım, eşik kalibrasyonu, örnekle arama | 12 kalibrasyon + 60 test görseli |
| **Masa fotoğrafları** (kullanıcının kendi) | Gerçek kullanım örneği | 5 fotoğraf, 45 elle işaretli nesne, fotoğraf başına 19 soru (5'i olmayan nesne) |

- Her görselde hem "var" soruları (görselde etiketli nesneler) hem "yok" soruları (kesinlikle olmayan nesneler) soruldu.
- Sorgular İngilizce LVIS adlarıyla verildi. Ölçülen şey tespit; çeviri ayrıca ölçüldü.
- LVIS ana kümesi: temel 50 görsel (masa, envanter, güvenlik, küçük nesne, benzer nesne senaryoları) +
  LVIS val'de tam etiketli nadir nesne içeren görsellerin **tamamı** (295).

## 5. Önerilen slayt akışı (~15 dk)

| # | Başlık / mesaj | İçerik | Kaynak |
|---|---|---|---|
| 1 | Açık Sözlük Nesne Tespiti | Başlık, grup | — |
| 2 | Soru: görmediği nesneyi bulabilir mi? | Klasik dedektör sabit sınıf listesiyle çalışır; açık sözlükte istenen nesne yazılır. Robotik / envanter / güvenlik. | §1 |
| 3 | Sistem | Türkçe sorgu → çeviri (Marian, yerel) → OWLv2 large → kutular. Ek özellikler: envanter sayımı, örnekle arama, hassasiyet (Sıkı/Dengeli/Geniş), "emin değil" kutuları | §6.6 |
| 4 | Ölçütler | IoU, precision, recall, F1, uydurma oranı, nadir sınıf (§3) | §3 |
| 5 | Test düzeni | 3 veri seti tablosu (§4) | §4 |
| 6 | **Ana sonuç: OWLv2 nadir nesnede başarısını koruyor** | LVIS ana tablosu (§6.1) + sık→nadir grafiği | §6.1 |
| 7 | Ayrıntı: sık / ara / nadir | precision/recall tablosu (§6.1 ayrıntı) | §6.1 |
| 8 | Nadir nesne örnekleri | omlet, kibrit kutusu, kelepçe: 4 modelin görseli yan yana (§7) | §7 |
| 9 | Gerçek kullanım: kendi fotoğraflarımız | masa tablosu (§6.2) | §6.2 |
| 10 | Envanter ve hassasiyet | RPC sonuçları, Sıkı/Dengeli/Geniş tablosu (§6.3) | §6.3 |
| 11 | Neden OWLv2 large? (dürüst) | §6.5 | §6.5 |
| 12 | Sınırlar | soyut kavram, kelime baskınlığı, küçük nesne + dilimleme denemesi (§6.4) | §6.4, §7 |
| 13 | Hız ve çeviri | GPU/CPU süreleri, çeviri doğruluğu (§6.6) | §6.6 |
| 14 | Sonuç | 3 cümle (§8) | §8 |
| 15 | **Canlı demo (3–4 dk)** | §9'daki senaryo; yedek görseller | §9 |
| 16 | Sorular | — | — |

Grafik önerisi (slayt 6): dört model için "sık F1" ve "nadir F1" çubukları yan yana, ya da sık → nadir eğim çizgisi.
OWLv2 düz kalıyor, DINO ve YOLO düşüyor; mesajı bu görsel taşır.

## 6. Rakamlar

### 6.1 Ana sonuç: LVIS v1 val, 345 görsel (`outputs/lvis_olcum/ana_olcum.md`)
Her modelin Dengeli eşiği (uygulamanın varsayılanı): large 0.14 · base 0.13 · DINO 0.30 · YOLO 0.10.

| Model | Sık F1 | Nadir F1 [%95] | Sık→nadir düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |
|---|---|---|---|---|---|
| **OWLv2 large (uygulama)** | 0.58 | **0.56** [0.50–0.61] | %3 | 220/303 (%73) | %4 |
| OWLv2 base | 0.52 | 0.55 [0.49–0.61] | — (artıyor) | 204/303 (%67) | %4 |
| Grounding DINO tiny | 0.43 | 0.33 [0.25–0.43] | %23 | 110/303 (%36) | %17 |
| YOLO-World s | 0.34 | 0.15 [0.11–0.20] | %55 | 47/303 (%16) | %3 |

**Ayrıntı** (precision / recall / F1):

| Model | Sık (f, 1284 soru) | Ara (c, 130 soru) | Nadir (r, 303 soru) |
|---|---|---|---|
| **OWLv2 large** | 0.60 / 0.55 / 0.58 | 0.52 / 0.57 / 0.54 | 0.55 / 0.56 / 0.56 |
| OWLv2 base | 0.57 / 0.48 / 0.52 | 0.47 / 0.40 / 0.43 | 0.61 / 0.51 / 0.55 |
| Grounding DINO | 0.73 / 0.31 / 0.43 | 0.52 / 0.22 / 0.31 | 0.62 / 0.23 / 0.33 |
| YOLO-World | 0.59 / 0.24 / 0.34 | 0.41 / 0.05 / 0.09 | 0.54 / 0.09 / 0.15 |

Yorum:
- DINO ve YOLO'nun precision'ı fena değil ama recall'u çok düşük: nadir nesneyi çoğu zaman hiç bulamıyorlar.
- YOLO'nun uydurma oranı düşük (%3), çünkü az kutu çiziyor.
- Sebep eğitim verisi:
  - OWLv2 web ölçeğinde görsel–metin çiftleriyle eğitildi (kendi ürettiği sözde etiketlerle).
  - DINO ve YOLO-World daha dar, insan etiketli verilerle eğitildi (Objects365, GoldG vb.).

### 6.2 Gerçek kullanım: masa fotoğrafları (`outputs/masa_olcum/masa_olcum.md`)
Her model kendi en iyi eşiğinde değerlendirildi.

| Model | Bulunan nesne | Precision | Recall | F1 | Olmayan nesneye kutu |
|---|---|---|---|---|---|
| **OWLv2 large** | **37/45** | 0.82 | 0.82 | **0.82** | 5/50 |
| OWLv2 base | 31/45 | 0.74 | 0.69 | 0.71 | 4/50 |
| LLMDet base | 21/45 | 0.68 | 0.47 | 0.55 | 4/50 |
| Grounding DINO tiny | 20/45 | 0.59 | 0.44 | 0.51 | 8/50 |
| YOLO-World s | 20/45 | 0.57 | 0.44 | 0.50 | 8/50 |

- Uygulamanın varsayılan (Dengeli) eşiğinde large: 38/45, F1 0.78.
- Hiçbir modelin bulamadığı nesneler: pil, açacak, deodorant, tıraş makinesi, parfüm.

### 6.3 Envanter (RPC market) ve hassasiyet
OWLv2 large. Kaynak: `backend/app/config.py` gerekçe tablosu, `outputs/hassasiyet/owlv2-large.txt`.

| Hassasiyet | Eşik | Market P / R / F1 | Masa F1 | Masada olmayan nesneye kutu |
|---|---|---|---|---|
| Sıkı | 0.17 | 0.99 / 0.65 / 0.78 | 0.82 | 5/50 |
| **Dengeli (varsayılan)** | 0.14 | 0.95 / 0.78 / 0.85 | 0.78 | 5/50 |
| Geniş | 0.10 | 0.90 / 0.95 / 0.93 | 0.69 | 11/50 |

- Mesaj: eşik bir denge. Sıkı daha az ama emin kutu, Geniş daha çok kutu ama uydurma artıyor. Kullanıcı seçiyor.
- **Örnekle arama** (adını yazmadan, bir örnek kutu çizerek arama): RPC 60 test görseli, Dengeli, P 0.54 / R 0.66.
  Bu ölçüm OWLv2 base ile yapıldı.
- **"Emin değil" kutuları:** aynı sorgunun en iyi puanının yarısından düşük kutular silinmiyor, kesikli turuncu gösteriliyor.
  - Silmek LVIS'te F1'i 0.51'den 0.54'e çıkarıyordu, ama markette 0.84'ten 0.77'ye düşürüyordu.
  - Bu ölçüm OWLv2 base ile yapıldı.

### 6.4 Sınırlar ve denemeler
- **Soyut kavram:** "alkollü içecek". OWLv2 0 kutu; Grounding DINO bira kutularını buluyor (0.39, 0.38).
  OWLv2 görünüşe bakıyor, kavrama değil.
- **Kelime baskınlığı:** "televizyon ünitesi" (*tv unit*).
  - DINO ve YOLO televizyonu işaretliyor; OWLv2 dolabı buluyor.
  - İfade "tv stand" olarak düzeltilince hepsi dolabı buluyor. Kullanıcı modele giden ifadeyi düzeltebiliyor.
- **Küçük nesne (pil):** model görseli küçültüyor, pil birkaç düzine piksele iniyor.
  - **Dilimleme denemesi** (görseli 2x2 böl, küçük kutuları dilimlerden de al): masa F1 0.82 → 0.84, pil bulunuyor.
  - Eski 50 görsellik LVIS nadir kümesinde 0.50 → 0.53.
  - Uygulamaya henüz eklenmedi. "Gelecek iş" olarak sunulabilir.
- **Çeviri hataları:** "kibrit kutusu" → *matchbook*, puan düşüyor; "Düzenle" ile *matchbox*'a çevrilince düzeliyor.

### 6.5 Neden OWLv2 large? (dürüst anlatım)
- Nadir nesnede F1'de OWLv2 base ile **berabere** (0.56 / 0.55, aralıklar aynı).
- Ama large nadir nesneyi daha sık buluyor (%73'e %67), sık nesnede daha iyi (0.58'e 0.52).
- Asıl fark gerçek fotoğraflarda: 37/45'e 31/45.
- OWLv2 ailesi ile DINO / YOLO arasındaki fark ise güven aralıkları çakışmayacak kadar net.
- Bedeli hız; GPU ile çözüldü (§6.6).
- **Söylenmesi önerilen cümle:** "Large'ı nadir nesnedeki F1 için değil, gerçek kullanımdaki başarısı için seçtik;
  nadir nesnede asıl fark model ailesinde."

### 6.6 Hız, çeviri, yazılım testleri
- **Hız** (OWLv2 large, RTX 5060 Laptop GPU):
  - Yeni görselde arama 1.2 sn (CPU'da ~28 sn idi, ~23 kat hız).
  - Aynı görselde tekrar arama 0.05 sn.
  - Örnekle arama 1.25 sn. VRAM ~2 GB.
  - Türkçe çeviri ~0.7 sn ekliyor.
  - GPU ve CPU sonuçları birebir aynı (puan farkı ≤ 0.0002).
- **Çeviri** (`outputs/ceviri/karsilastirma.md`, 183 Türkçe sorgu):
  - Marian + bağlam cümlesi ("Fotoğrafta {sorgu} var.") **%93** doğru; uygulamada bu kullanılıyor.
  - Düz Marian %85 · opus-big %90 · NLLB %77.
  - Tamamen yerel çalışıyor, internet ya da harici servis yok.
- **Yazılım testleri:** backend 147 birim testi geçiyor. Frontend testleri node:test + jsdom ile.

### 6.7 Dürüstlük notları (slaytta küçük dipnot ya da soru-cevap için)
- Masa sonuçlarında her model kendi en iyi eşiğinde değerlendirildi (iyimser). Dengeli eşikte large F1 0.78.
- Market kalibrasyon rakamları eşiğin seçildiği 12 görselden geliyor; bağımsız test değil.
- LVIS ana kümesinin 100 görseli eşik seçiminde de kullanılmıştı; 245 görsel tamamen yeni.
- Masa örneklemi küçük (tek masa, 45 nesne). Ana kanıt LVIS.

## 7. Kullanılacak görseller (`sunum/sonuclar/`)
Dosya adı: `NN_ad_model.jpg`. Model ekleri:
- `owlv2-large` (uygulama)
- `owlv2-base`
- `grounding-dino`
- `yolo-world`

Sayılar `sunum/sonuclar/ozet.json` içinde. **`*_owlvit.jpg` dosyalarını kullanma;** eski ve aslında base modele ait.

| Görsel seti | Gösterdiği | OWLv2 large | Diğerleri |
|---|---|---|---|
| `07_nadir_omlet_*` | Nadir nesne | omleti buluyor (0.38) | base 0.56 · DINO 0 · YOLO portakalı omlet sanıyor (yanlış) |
| `07_nadir_kibrit_kutusu_*` | Nadir nesne | kibrit kutusunu buluyor (0.28) | base 0.52 · DINO bıçakla tek büyük kutu (yanlış) · YOLO 0 |
| `07_nadir_kelepce_tr_*` | Uydurma kutu | 0 (bulamıyor) | DINO kol saatine "kelepçe" diyor (0.40) |
| `05_sac_spreyi_*` | Nadir + "emin değil" | şişe 0.52, iki turuncu "?" kutu | DINO 0 · YOLO 0 |
| `09_pil_*` | Küçük nesne | pili buluyor (0.31) + parfüm (0.17) | DINO ve YOLO yanlış nesneler |
| `04_alkollu_icecek_*` | Sınır: soyut kavram | 0 | yalnızca DINO buluyor |
| `08_tv_unitesi_*`, `08_tv_unitesi_duzeltilmis_*` | Sınır: kelime baskınlığı | dolap | DINO / YOLO televizyon |
| `02_envanter_owlv2-large` | Envanter sayımı | 16 kutu (5 sakız + 4 şişe doğru, 7 yanlış sakız) | — |
| `03_ornekle_arama_owlv2-large` | Örnekle arama | 5/5 Stride paketi, yanlış yok | — |

Karşılaştırma slaytında dört görseli 2x2 ızgaraya koy, her birinin üstüne model adını yaz.

## 8. Sonuç slaytı (öneri)
1. Açık sözlük tespitte model ailesi belirleyici: OWLv2 nadir nesnede başarısını koruyor (F1 0.58 → 0.56).
   DINO ve YOLO-World belirgin düşüyor (0.33, 0.15).
2. Gerçek kullanımda (kendi fotoğraflarımız) 45 nesnenin 37'si bulundu; sınırlar belli: küçük nesne, soyut kavram, çeviri.
3. Gelecek iş: küçük nesne modu (dilimleme, ölçüldü: +0.02 F1, pil bulunuyor), canlı kamera (GPU'da 1.2 sn / kare).

## 9. Canlı demo (sunumun sonunda, 3–4 dk, 2 fotoğraf)
Önceden: backend (`127.0.0.1:8000`) ve frontend (`127.0.0.1:3000`) açık olsun; bir arama yapılıp ısınsın.
İnternet gerekmez. Laptop şarjda, kapak açık.

**Fotoğraf 1: `sunum/gorseller/masa_12.jpeg`** (kendi masamız, ~2 dk)
1. `makas` → bulunuyor. "Aranan ifade" satırında *scissors* görünüyor: Türkçe yazdım, modele İngilizcesi gitti.
2. `saç spreyi` → şişe bulunuyor (nadir nesne). Yanında iki turuncu "?" kutu: emin olmadığını söylüyor, saklamıyor.
3. `kedi` → 0 kutu. Olmayan nesneye kutu uydurmuyor. Hassasiyet Sıkı / Dengeli / Geniş'i kısaca göster.

**Fotoğraf 2: `sunum/gorseller/market_12.jpg`** (market rafı, ~1,5 dk)
1. `sakız, şişe` → envanter sayımı tablosu. Bazı paketleri sakız sanıyor (metin aramasının sınırı).
2. **Örnekle ara:** bir Stride paketinin etrafına kutu çiz → 5 paketin hepsi bulunuyor, yanlış yok.
   "Adını bilmesek de bir örnekle bulabiliyoruz."

Her arama ~1,5–2,5 sn sürüyor. Demo takılırsa yedek: §7'deki `01_makas`, `05_sac_spreyi`, `06_olmayan_kedi`,
`02_envanter`, `03_ornekle_arama` görselleri.

## 10. Kaynak dosyalar
- `outputs/OZET.md`: bütün ölçümlerin özeti
- `outputs/lvis_olcum/ana_olcum.md`: ana tablo
- `outputs/masa_olcum/masa_olcum.md`, `outputs/masa_olcum/dilimleme.md`
- `outputs/ceviri/karsilastirma.md`
- `sunum/SENARYO.md`: adım adım anlatım ve "söyle" cümleleri (eski, demo ağırlıklı akış; rakamları güncel)
- `sunum/sonuclar/`: sonuç görselleri, `ozet.json`
