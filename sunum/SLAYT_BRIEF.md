# Slayt hazırlama brief'i: Açık Sözlük Nesne Tespiti (sürüm 2)

Bu dosya, slaytları hazırlayacak oturum için yazıldı ve tek başına yeterli olacak şekilde düzenlendi.
Rakamlar 2026-11-24 ölçümlerinden; kaynakları her bölümde yazılı (giriş noktası: `outputs/OZET.md`).
**Burada olmayan bir rakam uydurma.** Uygulama bitince değişecek yerler §10'da listeli.

---

## 0. Deneme sunumundan dersler (bunları tekrarlama)
Deneme sunumunu (`Desktop\Açık Sözlük Nesne Tespiti.pdf`, 16 slayt) kullanıcı beğenmedi:
"hep kısa yazılar, açıklayıcı değil, anlatması zor". İncelemede görülen sorunlar:

1. **Slaytların yarısı boş:** içerik üst yarıda bitiyor. Az ve küçük yazıyla bir araya gelince sunum içi boş görünüyor.
2. **Ölçütler yalnızca tanımla verilmiş:** 8 kavram küçük harflerle, tek cümle. Hiçbir görselde örnek yok.
3. **Yöntemin nasıl çalıştığı yok:** "Türkçe sorgu → Çeviri → OWLv2 → Kutular" kutucukları var, ama modelin
   yazılan kelimeyi görselde nasıl bulduğu (açık sözlüğün özü) hiç anlatılmamış.
4. **Test nasıl yapıldı, gösterilmemiş:** yalnızca veri seti tablosu var; adım adım örnek yok.
5. **Ham rakam tabloları açıklamasız:** "0.60 / 0.55 / 0.58" gibi üçlüler okunamıyor.
6. **Jargon açıklanmamış:** LVIS, RPC, zero-shot, Dengeli eşik, bootstrap.
7. **Sınırlar slaytında görsel yok,** oysa hazır görseller var.
8. **Konuşma metni yok.**

Bu sürümde her slayt için **slaytta yazacak cümleler** ve **konuşma metni** hazır (§4). Onları kullan.

## 1. Bağlam
- **Ders ödevi:** Açık Sözlük Nesne Tespiti. Senaryolar: robotik, envanter, güvenlik.
- **Ana soru:** Model eğitimde nadir görülen ya da hiç görülmemiş nesneleri ne kadar iyi buluyor?
- **Yöntem:** OWLv2 large (Google, 2023), eğitimsiz (zero-shot). İnce ayar bilerek yapılmadı:
  nadir nesnelerle eğitmek onları "görülmemiş" olmaktan çıkarır ve ana soruyu bozar.
- **Sunum dili:** Türkçe. Sunum bu laptopla yapılacak.
- **Hocanın beklentisi:** "sınırları zorlayan" bir sistem. Model karşılaştırması şart değil, ama
  "neden bu yöntem" sorusunun kanıtı olarak gösteriliyor.
- **Diğer grupların sunumlarından gözlem:**
  - Her şeyden bahsettiler.
  - **Performans ölçütleri ve test sonuçları önemliydi.**
  - Sonda 3–4 dakika, 1–2 fotoğrafla canlı demo yaptılar.
  - Bu sunum da aynı yapıda olacak.
- **Süre:** kullanıcı belirtmedi. 15 dakika varsay. Daha kısaysa §4'te "yedek" işaretli slaytları sona, yedek bölüme taşı.

## 2. Yazım kuralları (en önemli bölüm)
1. **Başlık tam bir iddia cümlesi olsun,** konu adı değil.
   - Kötü: "Sonuçlar".
   - İyi: "OWLv2 nadir nesnede başarısını koruyor, diğer modeller yarıya düşüyor".
2. **Her içerik slaytı üç katmanlı olsun:**
   - (a) iddia başlığı;
   - (b) kanıt: görsel, grafik ya da sade tablo; slayt alanının yarısından fazlası;
   - (c) **2–4 tam cümlelik açıklama:** rakam ne demek, neden böyle, buradan ne çıkıyor.
     Anahtar kelime listesi değil, okununca anlaşılan cümleler.
3. **"Nasıl okunur" cümlesi:** her rakamlı slaytta, rakamı gündelik dile çeviren bir cümle olsun.
   Örnek: "Nadir nesne sorulduğunda model 100 sorunun 73'ünde doğru yeri buldu."
4. **Jargonu ilk geçtiği yerde açıkla:** parantez içinde ya da tek cümleyle.
   LVIS, RPC, zero-shot, IoU, eşik, güven aralığı.
5. **Üçlü rakam yazma** ("0.60 / 0.55 / 0.58"). Bir tabloda en fazla 4–5 sütun; her sütun tek bir şey göstersin.
   Mesajı taşıyan sütunu vurgula.
6. **Yazı boyutu:** gövde en az 18 pt, başlık en az 28 pt. Slaytı küçük yazıyla doldurmak yerine görseli büyüt.
7. **Boş alan bırakma ama kalabalıklaştırma da:** her slaytta bir görsel ya da grafik ve 2–4 cümle.
   Alt yarı boş kalıyorsa görsel küçük demektir.
8. **Konuşmacı notu:** her slaytın notlar bölümüne §4'teki konuşma metnini koy.
   Konuşma metni slayttaki cümleleri tekrar etmez; onları açar.

## 3. Tasarım
- **Palet:** uygulamanın görsel diliyle aynı, "vizör / ölçüm cihazı".
  - Soğuk açık gri zemin, lacivert koyu alanlar, camgöbeği vurgu.
  - Deneme sunumunun renkleri iyiydi; koru.
- **Kaçınılacak:** sıcak krem/bej zemin ve kırmızı/kil vurgu. Kullanıcı bunu "Claude temasına benziyor" diye istemedi.
- **Kutu renkleri:**
  - Uygulama görsellerinde kırmızı = tespit kutusu, turuncu kesikli = "emin değil".
  - Ölçüt görsellerinde (`sunum/aciklama/`) yeşil = doğru, kırmızı = yanlış, sarı kesikli = kaçırılan / gerçek nesne.
  - Bu farkı ilgili slaytta lejantla belirt.
- **Yazı tipi:** Bahnschrift.
- **Biçim:** .pptx (konuşmacı notları dahil) ve PDF.

---

## 4. Slayt slayt içerik
Her slayt için: **Başlık** · **Slaytta** (görsel ve yazılacak cümleler) · **Konuşma** (notlara konacak metin) · Kaynak.
Konuşma metinleri ~45–60 saniyelik; olduğu gibi okunabilir.

### 1. Başlık
- **Başlık:** Açık Sözlük Nesne Tespiti
- **Alt başlık:** Eğitimde görmediği nesneyi bulabilir mi? · OWLv2 large · eğitimsiz (zero-shot) · tamamen yerel
- **Slaytta:** grup üyeleri, ders adı, tarih (kullanıcı dolduracak).
- **Konuşma:** "Merhaba. Projemiz açık sözlük nesne tespiti. Kısaca: bir fotoğrafta ne aradığımızı yazıyoruz, sistem onu
  buluyor. Ama asıl sorumuz bunun ötesinde: model eğitimde hiç ya da neredeyse hiç görmediği bir nesneyi de bulabiliyor mu?
  Önce sistemin nasıl çalıştığını, sonra bunu nasıl ölçtüğümüzü ve sonuçları anlatacağım; en sonda uygulamayı canlı göstereceğim."

### 2. Klasik dedektör sabit listeyle çalışır, açık sözlükte nesneyi biz yazarız
- **Slaytta:** solda kısa karşılaştırma, sağda büyük görsel `sunum/sonuclar/07_nadir_omlet_owlv2-large.jpg`.
  - **Klasik dedektör (ör. YOLO, COCO verisi):** eğitimde gördüğü 80 sınıfı tanır. Listede "omlet" yoksa omleti asla bulamaz.
  - **Açık sözlük:** aranan nesne kelimeyle yazılır. Liste yok; model kelimenin anlamını görseldeki bölgelerle eşleştirir.
  - Görsel altı: "Sorgu: omlet. Model arka tabaktaki omleti buldu (güven 0.38)."
- **Konuşma:** "Klasik nesne tespit modelleri sabit bir sınıf listesiyle eğitilir. COCO veri setiyle eğitilmiş bir model
  80 sınıf bilir; listede omlet yoksa, omleti ne kadar net görürse görsün bulamaz. Açık sözlük yaklaşımında ise liste yok:
  aradığımız nesneyi kelimeyle yazıyoruz. Sağdaki görselde 'omlet' yazdık, model arka tabaktaki omleti buldu.
  Robotik, envanter ve güvenlikte bu çok önemli, çünkü gerçek dünyada karşılaşılan nesnelerin listesi önceden bilinmez."

### 3. Asıl soru: eğitimde neredeyse hiç görülmemiş nesneleri bulabiliyor mu?
- **Slaytta:**
  - **Nadir nesne tanımı:** LVIS veri setinde (1203 nesne türü, elle ayrıntılı etiketlenmiş) eğitim görsellerinin en fazla
    10'unda geçen nesneler. Model makaleleri "görülmemiş nesne" başarısını bununla ölçer.
  - Üç küçük görsel örnek: omlet, kibrit kutusu (`07_nadir_kibrit_kutusu_owlv2-large.jpg`), kelepçe (`sunum/gorseller/nadir_kelepce.jpg`).
  - Cümle: "Gerçek dünyada nesnelerin çoğu nadirdir. Bir model yalnızca sık nesnelerde iyiyse pratikte işe yaramaz."
- **Konuşma:** "Bir modelin sık görülen nesneleri bulması şaşırtıcı değil; araba, insan, bardak her veri setinde binlerce kez var.
  Asıl zor olan nadir nesneler. LVIS adlı veri seti her nesne türünü eğitimde kaç görselde geçtiğine göre sınıflandırıyor:
  10 ya da daha az görselde geçenler 'nadir'. Omlet, kibrit kutusu, kelepçe bunlardan. Literatür 'görülmemiş nesne'
  başarısını tam olarak bu nadir sınıfla ölçüyor; biz de öyle yaptık. Sorumuz: sistem nadir nesnede, sık nesnedeki başarısını koruyabiliyor mu?"

### 4. Model, yazılan kelimeyi görseldeki 5184 aday bölgeyle karşılaştırır
- **Slaytta:** soldan sağa akan bir şema (oturum çizebilir):
  1. **Görsel** → 1008×1008'e getirilir → 14×14 piksellik **5184 parçaya** bölünür (72×72 ızgara).
  2. Her parça için model **bir aday kutu** ve o bölgenin **anlam vektörünü** üretir.
  3. **Yazı** ("omelet") → metin kodlayıcı → **metin anlam vektörü**.
  4. Her aday kutunun vektörü metin vektörüyle karşılaştırılır → **benzerlik = güven puanı** (0–1).
  5. Puanı **eşiğin** üstündeki kutular gösterilir (uygulamada Dengeli eşik 0.14).
  - Alt not: "OWLv2, milyarlarca web görseli ve onlara ait metinler üzerinde eğitildi. Biz modeli hiç eğitmedik (zero-shot)."
- **Konuşma:** "Peki model kelimeyi nasıl buluyor? OWLv2 görseli küçük parçalara bölüyor; large modelde bu 5184 parça ediyor.
  Her parça için bir aday kutu ve o bölgenin ne içerdiğini özetleyen bir sayı vektörü üretiyor. Yazdığımız kelime de ayrı bir
  kodlayıcıyla aynı türden bir vektöre çevriliyor. Sonra her aday kutu kelimeyle karşılaştırılıyor; ne kadar benziyorsa güven
  puanı o kadar yüksek. Puanı belirli bir eşiği geçen kutuları gösteriyoruz. Model bu eşleştirmeyi milyarlarca web görseli ve
  açıklamasından öğrenmiş; bu yüzden eğitimde etiketli görmediği kelimelerle de çalışabiliyor. Biz modeli hiç eğitmedik:
  nadir nesnelerle eğitseydik onlar artık 'görülmemiş' olmazdı."

### 5. Sistem: Türkçe yazılan nesne yerelde kutuya dönüşüyor
- **Slaytta:** akış şeması + dört özellik kartı. Mümkünse uygulamanın bir ekran görüntüsü; kullanıcı ekleyecek.
  - Akış: **Türkçe sorgu** ("saç spreyi") → **çeviri** (Marian, yerel; "Fotoğrafta saç spreyi var." cümlesiyle çevrilip
    nesne adı çıkarılır → *hairspray*) → **OWLv2 large** → **kutular**.
  - **Envanter sayımı:** "sakız, şişe" yaz; her nesneden kaç tane olduğu tablo halinde çıkar.
  - **Örnekle arama:** adını yazmadan, görselde bir örneğin etrafına kutu çiz; benzerleri bulunur.
  - **Hassasiyet:** Sıkı / Dengeli / Geniş. Eşiği kullanıcı seçer (az ama emin kutu ↔ çok kutu).
  - **"Emin değil" kutuları:** aynı aramanın en iyi puanının yarısından düşük kutular silinmez, turuncu kesikli gösterilir.
  - Cümle: "Her şey laptopta çalışıyor; internet ya da harici servis yok."
- **Konuşma:** "Uygulamada kullanıcı Türkçe yazıyor. Model İngilizce anladığı için önce yerel bir çeviri modeli çalışıyor.
  Tek kelimeyi çevirmek hataya açık olduğundan kelimeyi 'Fotoğrafta saç spreyi var' gibi bir cümlenin içine koyup çeviriyoruz;
  bu, çeviri doğruluğunu yüzde 85'ten 93'e çıkardı. Kullanıcı modele giden İngilizce ifadeyi ekranda görüp düzeltebiliyor.
  Bunun üstüne dört özellik kurduk: birden çok nesneyi sayan envanter, ad yerine örnekle arama, hassasiyet ayarı ve
  emin olunmayan kutuları silmek yerine işaretleme."

### 6. Bir kutu, gerçek nesneyle en az yarı yarıya örtüşürse doğru sayılır (IoU)
- **Slaytta:** büyük görsel `sunum/aciklama/iou_ornegi.jpg`.
  - Cümle 1: "IoU = iki kutunun örtüşen alanı / iki kutunun kapladığı toplam alan. 1 tam örtüşme, 0 hiç örtüşmeme."
  - Cümle 2: "Bardak: modelin kutusu gerçek kutuyla 0.98 örtüşüyor, doğru. Omlet: model salataya kutu çizmiş, örtüşme 0.07, yanlış."
  - Cümle 3: "0.5 sınırı LVIS ve COCO'nun standart kuralı; bütün ölçümlerde bunu kullandık."
- **Konuşma:** "Bir kutunun doğru olup olmadığına nasıl karar veriyoruz? Her test görselinde nesnelerin gerçek yeri elle
  işaretlenmiş; sarı kesikli kutular bunlar. Modelin kutusunu gerçek kutuyla karşılaştırıyoruz: örtüşen alanın iki kutunun
  toplam alanına oranı, yani IoU. Soldaki bardakta model neredeyse birebir aynı kutuyu çizmiş, 0.98. Sağda 'omlet' diye
  salataya kutu çizmiş; gerçek omletle örtüşmesi 0.07. Bu alanda standart kural şu: IoU en az 0.5 ise kutu doğru, değilse yanlış."

### 7. Tek bir görselde precision, recall ve F1
- **Slaytta:** büyük görsel `sunum/aciklama/olcut_ornegi.jpg` (sağ panel hesabı gösteriyor).
  - **Precision (kesinlik):** çizilen kutuların ne kadarı doğru → 4 / (4 + 2) = 0.67.
  - **Recall (duyarlılık):** gerçek nesnelerin ne kadarı bulundu → 4 / (4 + 2) = 0.67.
  - **F1:** ikisinin dengesi; ikisi de yüksekse yüksek. Tek sayıyla karşılaştırma için.
  - Not (küçük): "LVIS etiketinde kupa da 'drinking glass' olarak işaretli; bu yüzden bir bardak 'kaçırılan' görünüyor.
    Etiketler de kusursuz değil."
- **Konuşma:** "Bu görsel bütün ölçütleri tek yerde gösteriyor. Bu görselde modele dokuz şey sorduk: görselde olduğu bilinen
  beş nesne ve kesinlikle olmadığı bilinen dört nesne. Yeşil kutular doğru: nadir nesne olan omlet dahil dört nesneyi buldu.
  Kırmızılar yanlış: biri salataya çizilmiş ikinci bir omlet kutusu, diğeri ilginç: 'elma şarabı' görselde yok, ama model
  portakal suyuna kutu çizmiş. Sarı kesikliler kaçırılanlar, örneğin masanın kendisi. Precision 'çizdiği kutuların ne kadarı doğru',
  recall 'var olanların ne kadarını buldu' sorusunun cevabı. Bu görselde ikisi de 0.67. Bütün sonuçlar bu hesabın yüzlerce
  görsel üzerinde toplanmış hali."

### 8. İki ek ölçüt: olmayan nesneye kutu uydurma ve güven aralığı (yedek)
- **Slaytta:** iki sütun.
  - **Uydurma oranı:** görselde kesinlikle olmayan bir nesne sorulduğunda kutu çizilen soruların oranı.
    Örnek: önceki slayttaki "elma şarabı". Açık sözlük modellerinin bilinen riski: ne sorarsan bir şey bulmaya çalışmak.
  - **%95 güven aralığı:** test görsellerini 2000 kez rastgele yeniden seçip sonucu tekrar hesapladık (bootstrap).
    Aralık, sonucun şanstan ne kadar oynayabileceğini gösteriyor. İki modelin aralıkları çakışmıyorsa fark gerçek.
- **Konuşma:** "İki ölçüt daha kullandık. Birincisi uydurma oranı: görselde olmadığını bildiğimiz bir şeyi sorduğumuzda model
  kaç kez kutu çiziyor. Güvenlik gibi senaryolarda bu çok önemli; olmayan bir bıçağı görmek ciddi bir hata. İkincisi güven aralığı:
  sonuçlarımız sınırlı sayıda görselden geliyor, başka görseller seçseydik ne kadar değişirdi? Bunu görselleri tekrar tekrar
  rastgele seçerek hesapladık. İki modelin aralıkları çakışmıyorsa aradaki farkın şans olmadığını söyleyebiliyoruz."

### 9. Test düzeni: üç veri seti, her birinin tek bir görevi var
- **Slaytta:** sade tablo + altında adım adım test akışı.

  | Veri seti | Ne için | Boyut |
  |---|---|---|
  | **LVIS v1** (ana ölçüt; elle etiketli, 1203 nesne türü) | Nadir / görülmemiş nesne başarısı | 345 görsel · 175 farklı nadir nesne · 303 nadir nesne sorusu · 1284 sık nesne sorusu |
  | **RPC** (market ürünleri veri seti) | Envanter: sayım ve eşik ayarı | 12 ayar + 60 test görseli |
  | **Kendi masa fotoğraflarımız** | Gerçek kullanım | 5 fotoğraf · 45 elle işaretlenmiş nesne |

  - Akış: **1)** görseli al → **2)** etiketli nesneleri "var", kesinlikle olmayanları "yok" diye sor →
    **3)** modelin kutularını al → **4)** IoU ≥ 0.5 ile eşleştir → **5)** doğru / yanlış / kaçırılan say.
  - Cümle: "LVIS'te tam etiketli nadir nesne içeren görsellerin tamamını kullandık; seçme yapmadık."
- **Konuşma:** "Testi üç veri setiyle yaptık ve her birine tek bir görev verdik. Ana ölçütümüz LVIS: 1203 nesne türüyle elle ayrıntılı etiketlenmiş,
  nadir nesne tanımı da buradan geliyor. Doğrulama kümesinde tam etiketli nadir nesne içeren ve test edilebilir olan görsellerin hepsini aldık; 345 görsel,
  303 nadir nesne sorusu. Envanter senaryosu için market ürünlerinden oluşan RPC veri setini, gerçek hayatı görmek için de kendi
  masamızın fotoğraflarını kullandık. Her görselde aynı akış: var olan ve olmayan nesneleri sor, kutuları IoU ile eşleştir, say.
  Karşılaştırma için aynı testi üç başka modelle de yaptık."

### 10. Ana sonuç: OWLv2 nadir nesnede başarısını koruyor, diğerleri yarıya düşüyor
- **Slaytta:** büyük çubuk grafik (deneme sunumundaki iyiydi): her model için "sık nesne F1" ve "nadir nesne F1" yan yana.
  Altında düşüş oranı. Yanında küçük tablo:

  | Model | Nadir nesne F1 | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |
  |---|---|---|---|
  | **OWLv2 large (bizim)** | **0.56** | **%73** | %4 |
  | OWLv2 base | 0.55 | %67 | %4 |
  | Grounding DINO | 0.33 | %36 | %17 |
  | YOLO-World | 0.15 | %16 | %3 |

  - Sık → nadir F1: large 0.58 → 0.56 · base 0.52 → 0.55 · DINO 0.43 → 0.33 · YOLO-World 0.34 → 0.15.
  - **Nasıl okunur:** "Nadir bir nesne sorulduğunda OWLv2 large 100 sorunun 73'ünde nesneyi doğru yerde buldu;
    YOLO-World 16'sında."
  - Cümle: "Fark model ailesinde: iki OWLv2 nadir nesnede düşmüyor, diğer ikisi belirgin düşüyor."
- **Konuşma:** "Ana sonucumuz bu. Gri çubuklar sık nesnelerdeki, koyu çubuklar nadir nesnelerdeki F1 skoru. OWLv2 large sık nesnede
  0.58, nadir nesnede 0.56: neredeyse hiç düşmüyor. Grounding DINO 0.43'ten 0.33'e, YOLO-World 0.34'ten 0.15'e, yani yarıdan fazla
  düşüyor. Daha somut söylersek: nadir bir nesne sorduğumuzda OWLv2 large her dört sorudan üçünde nesneyi doğru yerde buluyor,
  YOLO-World altı sorudan birinde. Grounding DINO ayrıca olmayan nesne sorulduğunda altı sorudan birinde kutu uyduruyor.
  Bunun sebebi eğitim verisi: OWLv2 milyarlarca web görseli ve metniyle eğitildi; diğer ikisi daha dar, elle etiketlenmiş veri setleriyle."

### 11. Fark nesneyi bulmakta: diğer modeller nadir nesneyi çoğu zaman hiç görmüyor (yedek)
- **Slaytta:** nadir nesneler için iki sütunlu sade grafik ya da tablo: precision ve recall.

  | Model (nadir nesne) | Precision: çizdiği kutuların doğru olanı | Recall: gerçek nesnelerin bulunanı |
  |---|---|---|
  | OWLv2 large | 0.55 | **0.56** |
  | OWLv2 base | 0.61 | 0.51 |
  | Grounding DINO | 0.62 | **0.23** |
  | YOLO-World | 0.54 | **0.09** |

  - Cümle: "DINO ve YOLO-World kutu çizdiğinde çoğunlukla haklı (precision benzer), ama nadir nesneyi çoğu zaman hiç bulamıyor
    (recall çok düşük). YOLO-World gerçek nadir nesnelerin 10'da 1'ini bile bulamıyor."
- **Konuşma:** "Bu farkın nereden geldiğine bakınca ilginç bir şey görüyoruz. Precision'lar birbirine yakın: dört model de
  kutu çizdiğinde çoğunlukla doğru yere çiziyor. Fark recall'da. Grounding DINO gerçek nadir nesnelerin yaklaşık dörtte birini,
  YOLO-World onda birinden azını buluyor. Yani bu modeller nadir nesneyi yanlış tanımıyor; onu hiç fark etmiyor.
  OWLv2 ise yarıdan fazlasını buluyor."

### 12. Nadir nesne örnekleri: aynı soruya dört modelin cevabı
- **Slaytta:** 2×2 görsel ızgarası, her görselin üstünde model adı, altında tek satır sonuç. İki slayt da olabilir:
  - **Omlet** (`sunum/sonuclar/07_nadir_omlet_<model>.jpg`): large omleti buluyor (0.38) · base buluyor (0.56) ·
    DINO kutu çizmiyor · YOLO-World portakal dilimlerine "omlet" diyor (yanlış).
  - **Kelepçe** (`07_nadir_kelepce_tr_<model>.jpg`): OWLv2 ve YOLO-World kutu çizmiyor · DINO adamın kol saatine "kelepçe" diyor (0.40).
  - Cümle: "Bulamamak bir hata, ama olmayan şeyi görmek daha tehlikeli: güvenlik senaryosunda kol saatini kelepçe sanmak."
- **Konuşma:** "Rakamların arkasındaki örneklerden ikisi. Omlette OWLv2'nin iki boyutu da omleti buluyor; DINO hiçbir şey çizmiyor;
  YOLO-World ise portakalı omlet sanıyor. Kelepçe örneğinde hiçbir model kelepçeyi bulamıyor; kelepçe fotoğrafta yalnızca 16×36 piksel.
  Ama dikkat edin: Grounding DINO bulamayınca adamın kol saatine 'kelepçe' diyor. Ana tablodaki yüzde 17'lik uydurma oranının
  canlı örneği bu. Güvenlik gibi bir senaryoda olmayan bir şeyi görmek, bir şeyi kaçırmaktan daha pahalı olabilir."

### 13. Gerçek kullanım: kendi masamızdaki 45 nesnenin 37'sini buldu
- **Slaytta:** solda tablo, sağda bir masa görseli (`sunum/sonuclar/05_sac_spreyi_owlv2-large.jpg`; bu kişisel fotoğraf yalnızca laptopta duruyor).

  | Model | Bulunan nesne (45'ten) | F1 |
  |---|---|---|
  | **OWLv2 large** | **37** | **0.82** |
  | OWLv2 base | 31 | 0.71 |
  | LLMDet | 21 | 0.55 |
  | Grounding DINO | 20 | 0.51 |
  | YOLO-World | 20 | 0.50 |

  - Cümle: "Hiçbir modelin bulamadığı nesneler: pil, açacak, deodorant, tıraş makinesi, parfüm. Çoğu küçük ya da birbirine benzeyen şişeler."
  - Dipnot: "Her model kendi en iyi eşiğinde değerlendirildi; uygulamanın varsayılan eşiğinde large 38/45, F1 0.78. Tek masa, küçük örneklem."
- **Konuşma:** "Standart veri seti bir şey, kendi hayatımız başka bir şey. Kendi masamızın beş fotoğrafını çektik, 45 nesneyi elle
  işaretledik ve her fotoğrafta 19 soru sorduk. OWLv2 large 45 nesnenin 37'sini buldu; base 31, diğerleri 20 civarında. Large'ı
  seçmemizin asıl nedeni bu fark. Bulunamayanlar da öğretici: pil, açacak, deodorant, tıraş makinesi, parfüm. Bunlar ya çok küçük
  ya da birbirine benzeyen şişeler. Bu örneklem küçük, tek bir masa; ana kanıtımız LVIS, bu ise gerçek kullanımın bir örneği."

### 14. Envanter: eşik bir denge, seçimi kullanıcı yapıyor (yedek)
- **Slaytta:** solda `sunum/sonuclar/02_envanter_owlv2-large.jpg`, sağda sade tablo (RPC market görselleri, "ürün" sorgusu):

  | Hassasiyet | Çizilen kutuların doğru olanı | Ürünlerin bulunanı |
  |---|---|---|
  | Sıkı | %99 | %65 |
  | **Dengeli (varsayılan)** | %95 | %78 |
  | Geniş | %90 | %95 |

  - Cümle: "Sıkı daha az ama daha emin kutu çiziyor, Geniş neredeyse her ürünü buluyor ama yanlış kutu artıyor."
  - Cümle: "Örnekle arama: bir ürünün etrafına kutu çizince aynı ürünler bulunuyor; market görselinde 5 Stride paketinin 5'i,
    yanlış kutu yok (`03_ornekle_arama_owlv2-large.jpg`)."
  - Dipnot: "Market oranları eşiğin ayarlandığı 12 görselden; bağımsız test değil."
- **Konuşma:** "Envanter senaryosunda market raflarına benzeyen görseller kullandık. Burada bir seçim yapmak gerekiyor: emin olmadığı
  kutuları da göstersin mi? Sıkı ayarda çizilen kutuların neredeyse hepsi doğru, ama ürünlerin üçte biri kaçıyor. Geniş ayarda ürünlerin
  yüzde 95'i bulunuyor ama yanlış kutu artıyor. Bu yüzden ayarı kullanıcıya bıraktık. Adını bilmediğimiz bir ürün için de örnekle arama
  var: bir paketin etrafına kutu çiziyoruz, model aynı paketlerin hepsini buluyor."

### 15. Neden OWLv2 large? Nadir nesnede fark model ailesinde, large'ı gerçek kullanım için seçtik
- **Slaytta:** üç büyük rakam çifti (deneme sunumundaki düzen iyiydi) + dürüst açıklama.
  - Nadir nesne F1: **0.56** large · 0.55 base → berabere (güven aralıkları neredeyse aynı: 0.50–0.61 ve 0.49–0.61).
  - Nadir nesneyi bulduğu soru: **%73** large · %67 base.
  - Kendi fotoğraflarımız: **37/45** large · 31/45 base.
  - Cümle: "Nadir nesnede asıl fark model ailesinde: OWLv2 ile diğerleri arasındaki fark güven aralıkları çakışmayacak kadar net.
    Large'ı gerçek kullanımdaki başarısı için seçtik. Bedeli hızdı; GPU ile çözüldü."
- **Konuşma:** "Neden large dediğimizi dürüstçe söylemek istiyoruz. Nadir nesne F1'inde large ile küçük kardeşi base berabere;
  güven aralıkları neredeyse aynı. Large nadir nesneyi biraz daha sık buluyor, ama asıl farkı kendi fotoğraflarımızda gösterdi:
  45 nesnenin 37'si, base'de 31. Yani 'nadir nesnede kim iyi' sorusunun cevabı model ailesi; 'hangisini kullanalım' sorusunun cevabı
  gerçek kullanımdaki başarı. Large daha yavaş bir model, ama ekran kartıyla bir saniyenin biraz üstüne indi."

### 16. Sınırlar: kavram, kelime, boyut, çeviri
- **Slaytta:** 2×2 düzen, her kutuda bir görsel ve iki cümle:
  - **Soyut kavram** (`04_alkollu_icecek_grounding-dino.jpg`): "'Alkollü içecek' sorusunda OWLv2 hiçbir şey bulamıyor, Grounding DINO
    bira kutularını buluyor. OWLv2 görünüşe bakıyor; 'alkol' bir görünüş değil, bir kavram."
  - **Kelime baskınlığı** (`08_tv_unitesi_grounding-dino.jpg`): "'Televizyon ünitesi' sorusunda DINO ve YOLO-World televizyonu işaretliyor.
    İfade 'tv stand' olarak düzeltilince hepsi dolabı buluyor."
  - **Küçük nesne** (`09_pil_owlv2-large.jpg`): "Model görseli küçülttüğü için pil birkaç düzine piksele iniyor. Görseli 2×2 bölüp
    parçalara ayrı bakınca masa sonucu 0.82'den 0.84'e çıktı ve pil bulundu. Henüz uygulamada değil."
  - **Çeviri hatası:** "'Kibrit kutusu' *matchbook* olarak çevriliyor ve puan düşüyor; kullanıcı ifadeyi *matchbox* olarak düzeltince düzeliyor."
- **Konuşma:** "Sistemin nerede zorlandığını da ölçtük. Birincisi soyut kavramlar: 'alkollü içecek' bir görünüş değil, OWLv2 bulamıyor;
  ilginç şekilde dil modeli daha güçlü olan Grounding DINO buluyor. İkincisi tamlamalar: 'televizyon ünitesi' denince modeller en tanıdık
  kelimeye, 'televizyon'a takılabiliyor. Üçüncüsü küçük nesneler: model görseli küçülttüğünde pil birkaç düzine piksele iniyor.
  Görseli dörde bölüp her parçaya ayrı bakmayı denedik; pil bulundu, sonuç biraz yükseldi. Dördüncüsü çeviri. Hepsinde kullanıcı,
  modele giden ifadeyi görüp düzeltebiliyor."

### 17. Hız ve çeviri: GPU ile 1,2 saniye, çeviri %93 doğru (yedek)
- **Slaytta:** solda üç büyük rakam, sağda çeviri çubuk grafiği.
  - **1,2 sn** yeni görselde arama (ekran kartı RTX 5060; işlemcide ~28 sn idi).
  - **0,05 sn** aynı görselde tekrar arama: görselin model özeti saklanıyor, yalnızca kelime tarafı yeniden hesaplanıyor.
  - **+0,7 sn** Türkçe çeviri.
  - Çeviri doğruluğu (183 Türkçe sorgu): cümleyle çeviri **%93** · opus-big %90 · düz çeviri %85 · NLLB %77.
  - Cümle: "Ekran kartı ve işlemci sonuçları birebir aynı; yalnızca hız değişti."
- **Konuşma:** "Large modelin bedeli hızdı: işlemcide bir görsel 28 saniye sürüyordu. Ekran kartında 1,2 saniyeye indi ve sonuçların
  birebir aynı kaldığını doğruladık. Aynı görselde ikinci bir arama 0,05 saniye, çünkü görselin özetini saklıyoruz. Çeviri için dört
  yöntemi 183 Türkçe sorguyla karşılaştırdık; kelimeyi bir cümlenin içinde çevirmek yüzde 93 ile en iyisi oldu."

### 18. Sonuç
- **Slaytta:** üç numaralı tam cümle:
  1. "Açık sözlük tespitte model ailesi belirleyici: OWLv2 nadir nesnede başarısını koruyor (0.58 → 0.56), Grounding DINO ve
     YOLO-World belirgin düşüyor (0.33 ve 0.15)."
  2. "Gerçek kullanımda kendi masamızdaki 45 nesnenin 37'si bulundu. Sınırlar belli: küçük nesne, soyut kavram, çeviri."
  3. "Sıradaki adımlar: küçük nesne modu (ölçüldü, pil bulunuyor), canlı kamera (ekran kartında saniyede ~1 kare)."
- **Konuşma:** "Özetlersek: sorumuz modelin görmediği nesneleri bulup bulamadığıydı. Cevap model ailesine bağlı: OWLv2 nadir nesnede
  başarısını koruyor, diğerleri koruyamıyor. Kendi masamızda 45 nesnenin 37'sini buldu. Sınırları da biliyoruz: küçük nesneler,
  soyut kavramlar, bazı çeviriler. Şimdi uygulamayı canlı göstereyim."

### 19. Canlı demo (3–4 dk)
- **Slaytta:** iki fotoğrafın küçük hali ve sırası (deneme sunumundaki düzen iyiydi). Ayrıntılar §6'da.

### 20. Sorular
- **Slaytta:** "Sorular". Yedek slaytlar bunun arkasında: 8, 11, 14, 17 ve §8'deki hazır cevaplar.

---

## 5. Rakam referansı (bütün rakamlar)

**LVIS ana tablo** (`outputs/lvis_olcum/ana_olcum.md`). Dengeli eşikler: large 0.14 · base 0.13 · DINO 0.30 · YOLO 0.10.

| Model | Sık F1 | Nadir F1 [%95] | Bulduğu nadir soru | Olmayan nesneye kutu |
|---|---|---|---|---|
| OWLv2 large | 0.58 | 0.56 [0.50–0.61] | 220/303 (%73) | %4 |
| OWLv2 base | 0.52 | 0.55 [0.49–0.61] | 204/303 (%67) | %4 |
| Grounding DINO tiny | 0.43 | 0.33 [0.25–0.43] | 110/303 (%36) | %17 |
| YOLO-World s | 0.34 | 0.15 [0.11–0.20] | 47/303 (%16) | %3 |

**Precision / recall:**

| Model | Sık (f, 1284 soru) | Ara (c, 130 soru) | Nadir (r, 303 soru) |
|---|---|---|---|
| OWLv2 large | P 0.60 · R 0.55 | P 0.52 · R 0.57 | P 0.55 · R 0.56 |
| OWLv2 base | P 0.57 · R 0.48 | P 0.47 · R 0.40 | P 0.61 · R 0.51 |
| Grounding DINO | P 0.73 · R 0.31 | P 0.52 · R 0.22 | P 0.62 · R 0.23 |
| YOLO-World | P 0.59 · R 0.24 | P 0.41 · R 0.05 | P 0.54 · R 0.09 |

**Masa fotoğrafları** (`outputs/masa_olcum/masa_olcum.md`; her model kendi en iyi eşiğinde):

| Model | Bulunan | P | R | F1 | Olmayana kutu |
|---|---|---|---|---|---|
| OWLv2 large | 37/45 | 0.82 | 0.82 | 0.82 | 5/50 |
| OWLv2 base | 31/45 | 0.74 | 0.69 | 0.71 | 4/50 |
| LLMDet base | 21/45 | 0.68 | 0.47 | 0.55 | 4/50 |
| Grounding DINO | 20/45 | 0.59 | 0.44 | 0.51 | 8/50 |
| YOLO-World | 20/45 | 0.57 | 0.44 | 0.50 | 8/50 |

**Diğer rakamlar:**
- Uygulamanın Dengeli eşiğinde large, masada: 38/45, F1 0.78.
- **Hassasiyet (large):**
  - Sıkı 0.17: market P 0.99 / R 0.65 / F1 0.78; masa F1 0.82; masada olmayana kutu 5/50.
  - Dengeli 0.14: market 0.95 / 0.78 / 0.85; masa 0.78; 5/50.
  - Geniş 0.10: market 0.90 / 0.95 / 0.93; masa 0.69; 11/50.
- **Örnekle arama:** RPC 60 test görseli, P 0.54 / R 0.66. OWLv2 base ile ölçüldü.
- **"Emin değil" kuralı:** silmek LVIS'te F1'i 0.51 → 0.54 yapıyordu ama markette 0.84 → 0.77 düşürüyordu. Base ile ölçüldü.
- **Dilimleme:** masa 0.82 → 0.84 (pil bulunuyor); eski 50 görsellik LVIS nadir kümesinde 0.50 → 0.53.
- **Hız:** 1.2 sn (CPU ~28 sn), tekrar arama 0.05 sn, örnekle arama 1.25 sn, VRAM ~2 GB, çeviri +0.7 sn.
- **Çeviri:** 183 sorgu. Marian + bağlam %93, opus-big %90, düz Marian %85, NLLB %77.
- **Model:** OWLv2 large, girdi 1008×1008, 14 px parça → 5184 aday kutu. Base: 960×960, 16 px → 3600.
- **Yazılım:** backend 147 birim testi geçiyor.

## 6. Canlı demo senaryosu (sonda, 3–4 dk, 2 fotoğraf)
Önceden: backend (`127.0.0.1:8000`) ve frontend (`127.0.0.1:3000`) açık, bir arama yapılıp ısınmış olsun.
İnternet gerekmez. Laptop şarjda, kapak açık.

**Fotoğraf 1: `sunum/gorseller/masa_12.jpeg`** (kendi masamız, ~2 dk)
1. `makas` → bulunuyor. "Aranan ifade" satırında *scissors* görünüyor: Türkçe yazdık, modele İngilizcesi gitti.
2. `saç spreyi` → şişe bulunuyor. Yanında iki turuncu "?" kutu: model emin olmadığını söylüyor, saklamıyor.
3. `kedi` → 0 kutu. Olmayan nesneye kutu uydurmuyor. Hassasiyet Sıkı / Dengeli / Geniş'i kısaca göster.

**Fotoğraf 2: `sunum/gorseller/market_12.jpg`** (market, ~1,5 dk)
1. `sakız, şişe` → envanter sayımı tablosu. Bazı paketleri sakız sanıyor: metin aramasının sınırı.
2. **Örnekle ara:** bir Stride paketinin etrafına kutu çiz → 5 paketin hepsi bulunuyor, yanlış yok.

Her arama ~1,5–2,5 sn. Demo takılırsa yedek görseller: `sunum/sonuclar/01_makas_owlv2-large.jpg`, `05_sac_spreyi_…`,
`06_olmayan_kedi_…`, `02_envanter_…`, `03_ornekle_arama_…`.

## 7. Görsel listesi
**`sunum/aciklama/`** (yeniden üretmek için: `.venv\Scripts\python.exe sunum\olcut_gorseli.py`):
- `iou_ornegi.jpg`: IoU açıklaması (slayt 6).
- `olcut_ornegi.jpg`: tek görselde doğru / yanlış / kaçırılan + precision / recall / F1 (slayt 7).

**`sunum/sonuclar/`** (`NN_ad_model.jpg`; model ekleri `owlv2-large`, `owlv2-base`, `grounding-dino`, `yolo-world`;
yeniden üretmek için: `sunum\hazirla.py`):
- `07_nadir_omlet_*`, `07_nadir_kelepce_tr_*`, `07_nadir_kibrit_kutusu_*`: nadir nesne karşılaştırmaları.
- `05_sac_spreyi_*`, `09_pil_*`, `01_makas_*`, `06_olmayan_kedi_*`: kendi masamız.
  **Kişisel fotoğraf:** yalnızca laptopta duruyor, GitHub'da yok.
- `04_alkollu_icecek_*`, `08_tv_unitesi_*`, `08_tv_unitesi_duzeltilmis_*`: sınırlar.
- `02_envanter_owlv2-large.jpg`, `03_ornekle_arama_owlv2-large.jpg`: envanter.
- **`*_owlvit.jpg` dosyalarını kullanma:** eski ve aslında base modele ait.

## 8. Soru-cevap hazırlığı (yedek slayt ya da konuşmacı notu)
- **"Neden modeli eğitmediniz / ince ayar yapmadınız?"**
  Ana sorumuz görülmemiş nesne. Nadir nesnelerle eğitseydik onlar artık görülmemiş olmazdı; ölçtüğümüz şey bozulurdu.
  Açık sözlük yöntemin amacı zaten eğitimsiz çalışmak.
- **"Masa sonuçları iyimser değil mi?"**
  Evet: her model kendi en iyi eşiğinde değerlendirildi ve örneklem küçük. Uygulamanın varsayılan eşiğinde large 38/45, F1 0.78.
  Ana kanıt LVIS.
- **"Market rakamları bağımsız mı?"**
  Hayır, eşiğin ayarlandığı 12 görselden geliyor. Ana kümede de 345 görselin 100'ü daha önce eşik seçiminde kullanılmıştı;
  245'i tamamen yeni.
- **"Neden AP değil F1?"**
  Uygulama tek bir eşikle çalışıyor; kullanıcının göreceği başarıyı o eşikteki F1 gösteriyor. Literatürdeki AP eşikten bağımsız
  bir ölçüt; biz ölçmedik.
- **"Grounding DINO neden soyut kavramda daha iyi?"**
  Dil tarafında daha güçlü bir modeli (BERT) var; kavramları kelimelerle ilişkilendirebiliyor. OWLv2 daha çok görünüşe bakıyor.
- **"Çeviri için neden büyük dil modeli kullanmadınız?"**
  Her şey yerel çalışsın, internet ya da harici servis gerekmesin istedik. Yerel çeviri modeli bağlam cümlesiyle %93'e ulaştı.

## 9. Kaynak dosyalar
- `outputs/OZET.md`: bütün ölçümlerin özeti.
- `outputs/lvis_olcum/ana_olcum.md`: ana tablo.
- `outputs/masa_olcum/masa_olcum.md`, `outputs/masa_olcum/dilimleme.md`.
- `outputs/ceviri/karsilastirma.md`.
- `sunum/SENARYO.md`: eski, demo ağırlıklı akış. Rakamları güncel, ama akış olarak bu brief geçerli.

## 10. Uygulama bitince güncellenecekler
- Yeni özellik eklenirse (ör. küçük nesne modu, canlı kamera): slayt 5, 16 ve 18; demo senaryosu (§6).
- Model, eşik ya da çeviri değişirse: LVIS ana tablosunu yeniden ölç (`evaluation.lvis.evaluate_subset --subset ana`,
  sonra `evaluation.lvis.ana_rapor`) ve §5'i, slayt 10–15'i güncelle. Masa ölçümünü de tekrarla.
- `sunum\hazirla.py` ve `sunum\olcut_gorseli.py` ile görselleri yeniden üret.
