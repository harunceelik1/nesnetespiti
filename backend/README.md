# Backend sorgu çevirisi

## Türkçe nesne sözlüğü (çeviriden önce)

`app/services/object_lexicon.py` ~200 yaygın nesneyi doğrudan dedektör sınıf adına
çevirir: kravat→tie, yüz→face (Marian "100" üretiyordu), insan→person, fare→mouse.
Çoğul (-lar/-ler), Türkçe karaktersiz yazım (canta) ve "renk/sıfat + nesne"
(kırmızı araba→red car) desteklenir. Sözlükte olmayan ifade Marian'a düşer.
Dil tespitinde sözlükteki İngilizce sözcükler kesin İngilizce sayılır; diğer belirsiz
sözcükler, Lingua İngilizce güveni 0.60'ın altındaysa Türkçe kabul edilir.
Yanıtta `translation_source` alanı `lexicon` veya `model` değerini taşır.

## Üç model karşılaştırması (sabit, kalibre edilmiş eşikler)

| Model | Eşik | Var olan (18) | Olmayan boş (16) | Envanter "ürün" F1 | CPU süre/görsel |
|---|---|---|---|---|---|
| OWLv2 | 0.13 | 16 | 16 | 0.79 | ~5.5 sn |
| Grounding DINO (tiny) | 0.30 | 15 | 16 | 0.89 | ~6–15 sn |
| YOLO-World (s, v2) | 0.10 | 13 | 16 | ~0 ("product"u anlamıyor) | ~0.7 sn |

"Var olan" yalnızca kutu çizilip çizilmediğini sayar, kutunun yerini doğrulamaz;
envanter F1 ise IoU >= 0.5 ile doğru kutulara göre hesaplanır. Sayılar eşiğin
seçildiği kalibrasyon verisinden geldiği için iyimserdir.

YOLO-World: görülmüş (COCO) sınıflarda en güçlü ve en hızlı model (araba 0.94,
insan 0.93), görülmemiş nesnelerde (ilaç kutusu, gözlük kılıfı, şarj aleti) hiçbir
şey bulmaz; "product/snack/item" gibi genel kavramları tanımaz (12 envanter
görselinde "product" 0, "bottle" 34/120 doğru). Eşik bu yüzden RPC ile değil, var/yok
vakalarıyla seçildi. Kurulum: `pip install "ultralytics>=8.3,<9"` ve
`pip install git+https://github.com/ultralytics/CLIP.git`; ilk açılışta
`yolov8s-worldv2.pt` (25 MB, `.cache/yolo-world/`) ve CLIP ViT-B/32 (338 MB,
Ultralytics ayarındaki `weights/` klasörü) iner. `ultralytics` AGPL-3.0 lisanslıdır.

## OWLv2 (OWL yuvasının varsayılan modeli)

API/arayüz kimliği `owlvit` aynı kalır; arkasında `google/owlv2-base-patch16-ensemble`
çalışır (`app/models/owlv2_service.py`, `config.OWL_VERSION = "v2"`; `"v1"` eski
OWL-ViT'e döner). OWLv2 görüntüyü sağ/alttan dolgu ile kareye tamamladığından kutular
uzun kenarla ölçeklenir. Ek bağımlılık: `scipy`. Ağırlıklar `.cache/owlv2/` (~593 MB).
CPU'da görsel başına ~5.5 sn.

Eşik `evaluation/calibrate_threshold.py` ile seçildi (12 RPC kalibrasyon görseli +
16 olmayan nesne vakası): **0.13** → envanter "ürün" F1 0.78, sahte kutu 0.
Karşılaştırma (aynı 12 görsel, sabit eşik): OWL-ViT v1 F1 0.06, OWLv2 0.79,
Grounding DINO 0.84. Bu görseller eşik seçiminde kullanıldığı için sayılar iyimserdir;
son ölçüm RPC test kümesinde yapılmalıdır.

Bilinen hata türleri (masa fotoğrafı): nesneyi çevresiyle birlikte saran büyük
bölge kutuları ("şarj aleti" 0.45 > gerçek şarj aleti 0.33), anlamca komşu
nesneler (kablo → şarj aleti, gözlük kılıfı → fare), ambalaj üzerindeki
resimler (erişte paketindeki figür → "köpek"). Geniş karşıt listesi denendi ve
reddedildi: "snack/package" gibi genel kavramlar çikolataları kendine çekti (11 → 0).

## Sabit eşik ve "bulunamadı" (üretim varsayılanı)

Bir sorgu ilk eşikte hiçbir şey bulamazsa sonuç **boş** döner; eşik düşürülmez ve eş
anlamlı yedek (bag → handbag, backpack) denenmez. Nedeni ölçüldü: nesne görselde
yokken eşiği düşürmek modelin en benzer bölgeyi kabul etmesine yol açıyordu (masa
fotoğrafında "ilaç kutusu" → laptop, "fare" → kulaklık kutusu; "çanta" → adamın eli).
Mekanizmalar ayar olarak durur: `AdaptiveThresholdSettings.allow_lowering` ve
`config.SYNONYM_FALLBACK_ENABLED` (ikisi de False). Eski davranışı sınayan testler
`tests/legacy_adaptive.py` ile bunları açar. Bedeli: eşik altında kalan zayıf ama
gerçek tespitler (ör. DINO'da ceket 0.27) artık döndürülmez.

Türkçe isim tamlamaları sözlükten kurulur: "ilaç kutusu" → medicine box,
"gözlük kutusu" → glasses case, "kırmızı ilaç kutusu" → red medicine box
(`object_lexicon.POSSESSIVE_HEADS`). Marian bunları "pharmaceutical box",
"glass box" diye çeviriyordu.

## Karşıt sorgular (olmayan nesne uydurmasını önleme)

Açık sözlük dedektörler tek sorguda en benzer bölgeyi her zaman bulur: köpek
olmayan resimde adamı "dog" diye işaretler. `app/utils/contrastive.py` sorguya
`config.CONTRASTIVE_QUERIES` içindeki sık sınıfları (person, car, dog, ...) ekler;
her kutu en iyi eşleşen sınıfa atanır ve yalnızca sorulan etiketler tutulur.
Sorguyla ilişkili sınıflar (man↔person, backpack↔bag, coffee cup↔cup) karşıt
yapılmaz. Üç gerçek serviste açıktır (`use_contrastive_queries`); sorgu aktarımını
birebir sınayan testler bu ayarı modül seviyesinde kapatır.

## YOLO-World (üçüncü açık sözlük modeli)

`app/models/yoloworld_service.py`, Ultralytics `YOLOWorld` sınıfını ortak
`BaseDetector` sözleşmesiyle kullanır. Model yeniden eğitilmez: kullanıcı sorgusu
CLIP metin kodlayıcısıyla sınıf adına dönüştürülür (`set_classes`) ve tespit bu
metin gömmelerine göre yapılır. Çeviri, synonym fallback, adaptive eşik, NMS (0.60),
scene-box filtresi ve envanter sayımı diğer iki modelle aynı ortak katmandan geçer.

- Model id: `yolo-world` (`/detect`, `/detect-image`, `/detect-raw-image` form alanı `model`).
- Ağırlık: `config.py` içindeki `YOLO_WORLD.weights` (varsayılan `yolov8s-worldv2.pt`).
  İlk açılışta proje kökündeki `.cache/yolo-world/` içine indirilir. CLIP metin
  kodlayıcısı (ViT-B/32) Ultralytics'in kendi ağırlık klasörüne indirilir.
- Adaptive eşikler: 0.25 → 0.15 → 0.10 → 0.05. YOLO-World skor ölçeği OWL-ViT ve
  DINO ile kıyaslanmaz.
- Aynı sınıf listesi için metin gömmesi yeniden hesaplanmaz; `set_classes` ve tahmin
  bir kilitle birlikte çalışır, paralel istekler birbirinin sınıflarını değiştirmez.
- Çoklu sorguda her kategori ayrı çalıştırılır (DINO gibi); etiket her zaman
  gönderilen sorgunun kendisidir.
- Ultralytics veya CLIP kurulu değilse ya da ağırlık indirilemezse yalnızca
  YOLO-World `available=false` olur; OWL-ViT ve DINO çalışmaya devam eder.

Kurulum (proje kökünden, bir kez):

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install git+https://github.com/ultralytics/CLIP.git
~~~

İkinci komut için bilgisayarda Git kurulu olmalıdır. Atlanırsa Ultralytics ilk
kullanımda aynı paketi kendisi kurmayı dener.

Elle kontrol (backend açıkken):

~~~powershell
curl.exe -s http://127.0.0.1:8000/models
curl.exe -s -F "image=@images/test.jpg" -F "query=cüzdan" -F "model=yolo-world" http://127.0.0.1:8000/detect
~~~

## Parça kutuları ve bölge kutuları (ölçüm + temizlik)

`evaluation/region_boxes.py` (20 RPC kalibrasyon görseli, "ürün" + görseldeki her
kategori) kutuları sınıflar. Büyük "bölge kutusu" (birkaç ürünü saran) sanılandan
nadirdir: OWLv2'de kutuların %1'i, DINO'da %3'ü. Asıl sorun OWLv2'nin **parça kutuları**:
"ürün" sorgusunda 295 kutunun %26'sı bir ürünün içinde kalan küçük kutu, %20'si iki
ürün arası/boşluk. NMS bunları elemez; küçük kutunun büyük kutuyla IoU'su düşüktür.

Temizlik (`utils/box_filters.py`, `config.PART_BOX_CONTAINMENT = 0.70`): bir kutunun
alanının %70'i daha yüksek puanlı aynı etiketli bir kutunun içindeyse atılır. Sahne
kutusu süzgecinden **sonra** çalışır; yoksa görselin tamamını saran tek bir kutu içindeki
gerçek kutuları sildirirdi.

| OWLv2, 20 görsel | Kutu | Precision | Recall | Var olan (18) | Olmayan boş (16) |
|---|---|---|---|---|---|
| "ürün", temizlik yok | 295 | 0.52 | 0.78 | 16 | 16 |
| "ürün", temizlik 0.70 | 257 | 0.59 | 0.77 | 16 | 16 |
| kategori sorguları, temizlik yok | 681 | 0.13 | 0.44 | | |
| kategori sorguları, temizlik 0.70 | 491 | 0.17 | 0.43 | | |

Örnek (5. envanter görseli, "atıştırmalık", OWLv2 Sıkı): 19 kutu → 7 kutu; 3 gerçek
paketin 3'ü de kalır (`outputs/parca_kutusu/`). Kalan 4 yanlış kutu konserve ve bira
kutusudur: OWLv2 paketli her yiyeceği "snack" sayar. Bu kutu temizliğiyle değil model
seçimiyle ilgilidir: kategori sorgularında precision OWLv2'de 0.17, DINO'da 0.44.

Denenip **kapatılanlar**: OWLv2 objectness eşiği (0.2'de var olan vakalar 16 → 9) ve
bölge kutusu atma (kategori recall'unu düşürüyor, kazancı yok).

Sonuç görsellerinde etiket fontu Türkçe karakterli DejaVu Sans'tır ve görsel boyutuyla
ölçeklenir (önceki yerleşik font ı/ş/ğ harflerini kutucuk olarak çiziyordu).

## Hassasiyet (Sıkı / Dengeli / Geniş)

Arayüzün sol panelinde üç seviye vardır; form alanı `sensitivity` (`strict`, `balanced`,
`loose`; `/detect`, `/detect-image`, `/detect-by-example`). **Dengeli** varsayılandır ve
bugüne kadar kullanılan kalibre edilmiş eşiktir; seçilmezse davranış değişmez. Diğer
seviyeler aynı kalibrasyon tablolarından seçildi (`evaluation/calibrate_threshold.py`,
çıktılar `outputs/hassasiyet/`). Her seviye tek sabit eşiktir; eşik düşürerek arama yoktur.

| Model | Sıkı | Dengeli | Geniş | Geniş'te ne değişir |
|---|---|---|---|---|
| OWLv2 | 0.17 | 0.13 | 0.10 | envanter recall 0.81 → 0.85, precision 0.76 → 0.65 |
| Grounding DINO | 0.35 | 0.30 | 0.27 | recall 0.84 → 0.91, precision 0.95 → 0.95 |
| YOLO-World | 0.25 | 0.10 | 0.05 | var olan vakalar 13 → 14 / 18 |
| Örnekle arama (benzerlik) | 0.92 | 0.88 | 0.84 | test kümesi recall 0.66 → 0.77, precision 0.54 → 0.40 |

Kalibrasyon verisinde Geniş seviyede de olmayan nesnelerde sahte kutu çıkmadı, ama
sınır yakındır (OWLv2 ≤ 0.07, DINO ≤ 0.26, YOLO ≤ 0.04'te sahte kutu başlar) ve 16 vaka
azdır; arayüz Geniş seçilince bu yüzden uyarı gösterir.

DINO varsayılanı 0.35'ten 0.30'a indirildi: aynı tabloda olmayan nesnelerde sahte kutu
yine 0, envanter recall 0.75 → 0.84 (precision 0.97 → 0.95), var olan vakalar 13 → 15.
Yeni bulunan iki vaka (el, yüz) gözle doğrulandı. "fare" vakası iki eşikte de yanlış
nesneye (kulaklık kutusu, bardak kapağı) kutu çizer; 0.30 buna ikinci bir yanlış kutu
ekler. Eski 0.35 artık "Sıkı" seviyedir.

## Örnekle arama (OWLv2, görsel sorgu)

Arayüzde **Örnekle ara** → görselde aranan nesnelerden birinin etrafına kutu çiz →
**Benzerlerini bul**. Metin ve çeviri kullanılmaz; yazılan sorgu yalnızca etiket olur.
Kelimeyle zor ayrılan ürünlerde (çikolata ↔ sakız) ve sözlükte olmayan nesnelerde işe yarar.
Uç: `POST /detect-by-example` (`image`, `xmin/ymin/xmax/ymax` piksel, isteğe bağlı `label`).

Nasıl çalışır (`OwlViTService.example_candidates`, `services/exemplar_search.py`):
1. OWLv2 görseldeki her yama için bir kutu ve sınıf gömüsü üretir (tek forward).
2. Çizilen kutuyla en iyi örtüşmenin %80'ine yakın kutular arasından görüntü
   ortalamasına en az benzeyenin gömüsü sorgu olur (OWL makalesi / HF kuralı).
3. Puan = sorgu gömüsüyle kosinüs benzerliği. Süzgeç: benzerlik ≥ 0.88,
   objectness ≥ 0.10, NMS 0.5, kapsama 0.8 (`config.EXEMPLAR_SEARCH`).

Neden hazır `post_process_image_guided_detection` değil: puanları en iyi kutuya göre
ölçekler (en iyi kutu hep 1.0) ve sınıf başlığının sigmoid puanı görsel sorguda
görüntünün her yerinde 0.98+ doyar; ikisi de "yoksa çizme" ilkesini bozar.

Ölçüm (`evaluation/exemplar_eval.py`, RPC; görselde birden fazla kopyası olan ürünün
ilk kopyası örnek; örneğin kendisi sayılmaz, "diğer kopyalar" ölçülür):

| Küme | Görsel | Diğer kopya | Precision | Recall | F1 | Sayı tam doğru |
|---|---|---|---|---|---|---|
| Kalibrasyon (ayar seçimi) | 20 | 35 | 0.58 | 0.80 | 0.68 | 6/20 |
| Test (hiç görülmemiş) | 60 | 110 | 0.54 | 0.66 | 0.60 | 11/60 |

Eşik 0.88 test kümesinde de en iyi F1'i verdi (aşırı uydurma yok). Test kümesindeki
62 sahte kutunun 32'si başka bir ürünün üstünde; bunların önemli kısmı aynı markanın
başka çeşidi (ör. iki farklı aromalı Stride sakız, RPC'de ayrı ürün). Kalan sahteler
yarım/kaymış kutulardır. Sınırlamalar: ürün ters/yan dönmüşse benzerlik düşer; ayrı bir
örnek fotoğrafla (başka görselden) arama henüz yok; DINO ve YOLO-World görsel sorgu almaz.

## Konservatif scene-box sanity filtresi

Production akışı: raw -> mevcut class-aware NMS -> scene-box kontrolü ->
adaptive geçerlilik değerlendirmesi -> final detections -> mevcut inventory sayımı.
Filtre her adaptive threshold denemesinde, modelden bağımsız ortak orchestrator
tarafından çalıştırılır. Model servisleri, confidence threshold'ları, NMS algoritması,
query/translation, inventory mantığı ve evaluation kodu değiştirilmez.

`backend/app/config.py` içindeki `SCENE_BOX_FILTER` varsayılanları:

- Kural A: `min_area_ratio = 0.90` ve `min_near_borders = 3` (en az üç kenar).
- Kural B: `full_scene_min_area_ratio = 0.80` ve `full_scene_near_borders = 4`
  (tam dört kenar). Alan oranı bütün kurallar için de
  `(xmax-xmin)*(ymax-ymin)/(width*height)` olarak hesaplanır.
- Kural C: `axis_scene_min_area_ratio = 0.85`, `axis_scene_min_near_borders = 3`,
  `max(width_coverage, height_coverage) >= axis_scene_long_coverage = 0.97` ve
  `min(width_coverage, height_coverage) >= axis_scene_short_coverage = 0.80`.
  Dört koşulun tamamı gerekir. Coverage değerleri box width/image width ve
  box height/image height'tır; clip veya confidence değişikliği yapılmaz.
  A **veya** B **veya** C yeterlidir; diagnostics önceliği A, B, C şeklindedir.
- `border_tolerance_ratio = 0.03`: sol/sağ mesafesi width'ün, üst/alt mesafesi
  height'ın en fazla %3'ü olmalıdır. Mesafeler mutlak değerdir.

Her kuralın alan/kenar koşulları birlikte gerekir; yalnızca büyük olması kutuyu kaldırmaz. Örneğin %90
alan kaplayan fakat sadece iki kenara yaklaşan nesne korunur. Koordinatlar
clip/resize edilmez. Bu geometrik heuristik nesnenin gerçekten yanlış olduğunun
kanıtı değildir; görüntünün neredeyse tamamını dolduran gerçek bir nesneyi de
eşik/kenar koşulları sağlanırsa kaldırabilir.

Kenar toleransı genişletilmez: %3 olarak kalır. Bu toleransta görüntü içindeki
dört-kenar kutusu en az `(1-2*0.03)^2 = 0.8836` alan kaplar. Dolayısıyla Kural B
default geometride %88.36–90 aralığını da kapsar. %85 + dört kenar varsayımı
bu toleransta mümkün değildir; gerçek kutunun kenar uzaklıklarını kontrol edin.
Testler %85/dört kenar senaryosunu yalnızca test config'inde %5 toleransla,
%65/dört kenar senaryosunu %10 ile doğrular; production toleransı değiştirilmez.

`/detect` JSON'una `oversized_boxes_removed` listesi, `oversized_boxes_removed_count`,
`scene_box_filter` config bilgisi ve `oversized_box_diagnostics_scope` eklenir.
Her kaldırma kaydı detection (box/label/confidence), `area_ratio`, `near_borders`,
`reason="oversized_scene_box"`, eşik/faz ve canonical query içerir. Bu liste
**tüm adaptive denemeleri** kapsar: aynı fiziksel kutu farklı eşiklerde tekrar
üretildiyse birden fazla kayıt bulunabilir. Bu sayaç nesne sayısı değildir.
`threshold_attempts` içinde her denemenin kaldırmaları, `nms_detection_count` ve
filtre sonrası `filtered_detection_count` da bulunur. NMS duplicate oranı sanity
filtresinden önceki NMS sayısıyla hesaplanır; iki eleme nedeni birbirine karışmaz.

`scene_box_diagnostics` artık **korunan ve kaldırılan tüm geçerli NMS kutularını**
gösterir. Her kayıtta gerçek `detection.box`, `image_size`, `box_area`, `image_area`,
`area_ratio`, `width_coverage`, `height_coverage`, normalize `edge_distance_ratios` (left/right/top/bottom),
`near_borders`, `touched_edges`, `matched_rule` (rule_a/rule_b/rule_c/null), `removed`,
eşik ve canonical query bulunur. Teknik Detaylar bu değerleri backend'den alır;
preview veya CSS boyutuyla yeniden hesaplama yapmaz. `touched_edges`, fiziksel
temas değil config toleransı içinde kalan kenar sayısıdır. Liste tüm adaptive
denemeleri kapsar; aynı kutu farklı denemelerde tekrar kaydedilebilir.

Yalnızca scene kutusu kalan deneme `empty` olur; sonraki mevcut adaptive eşiğe
devam edilir. Primary/fallback koşulları değiştirilmez. `/detect-image` ve birleşik
JSON+JPEG yanıtı filtrelenmiş aynı final kutuları kullanır. `/detect-raw-image`
ham kutuları gösterme davranışını korur. Frontend'de kaldırmalar yalnızca Teknik
Detaylar bölümünde görünür; kullanıcıya yeni bir ayar eklenmez.

## Çoklu sorgu ve envanter

`/detect`, `/detect-image` ve `/detect-raw-image` aynı `query` form alanında
`çanta, şişe, kutu` kabul eder. Her parça mevcut translation/normalization
pipeline'ından bağımsız geçer. Boş parçalar ve aynı canonical sorguya dönüşen
tekrarlar çıkarılır; bütün parçalar boşsa HTTP 422 döner. `bottles -> bottle` ve
`boxes -> box` kontrollü tekilleştirme listesine dahildir; genel suffix kuralı yoktur.

Tekli sorgu adaptive/fallback akışı korunur. Çoklu sorguda da her kategori kendi
adaptive eşiklerini ve ancak primary tamamen boşsa fallback'lerini kullanır.
OWL-ViT primary sorguları aynı image/eşik için bir forward ile işlenir ve sonuç
isteğe özel cache'te paylaşılır. Her kategoriye ayrı kalite kontrolü/NMS uygulanır;
başarılı kategorinin eşiği başka bir kategori boş diye düşürülmez. Multi-label
OWL-ViT'ta candidate sınıfları aynı kutu için yarışabilir; çoklu sorgunun sonucu
bağımsız tekli sorguların toplamıyla birebir aynı olmak zorunda değildir.

Grounding DINO decoded phrase'leri çoklu prompt'ta birleştirebildiğinden production
çoklu sorguları ayrı çağırır; tümünü tek bir kategoriye atamak veya fuzzy matching
yapmak yerine güvenli query kimliği kullanılır. Servis/model örneği tekrar yüklenmez.
Raw debug endpoint'i eski sabit threshold davranışında kalır ve NMS eklemez.

Her final detection `canonical_query` taşır; `label` kullanıcının ilk benzersiz
ifadesi, `model_query` (varsa) model/fallback ifadesidir. Inventory yalnızca final
class-aware NMS sonrası kutulardan oluşur. Aynı canonical sınıfın duplicate kutuları
iki kez sayılmaz. Farklı sorgu sınıfları arasında class-agnostic suppression yoktur:
örtüşen farklı gerçek nesneler korunur. Örtüşen anlamlı sorguların (örn. bag/backpack)
fiziksel nesne kimliklerini tekilleştirdiği iddia edilmez.

JSON'a eklenen alanlar:

```json
{
  "inventory_summary": {"bag": 2, "bottle": 4, "box": 0},
  "total_detected_objects": 6,
  "primary_query": "bag, bottle, box"
}
```

Sonuçta olmayan kategori de 0 olarak bulunur. Multi-query debug alanı
`processed_query_items` her sorgunun orijinal metin, dil, çeviri, primary,
processed queries, fallback, raw/filtered sayı, threshold attempts ve seçilen
eşik bilgilerini korur. `adaptive_thresholds_by_query` gerçek sorgu eşiklerini
gösterir; eşikler farklıysa tek bir global `adaptive_threshold_used` uydurulmaz,
alan atlanır ve `/detect-image` ilgili header'ı boş döndürür. Top-level attempts
her denemede `canonical_query` içerir. `inference_time_ms` tüm request inference
akışının süresidir; paylaşılan OWL primary maliyeti sorgu sürelerinden toplanmamalıdır.

`/detect` için `include_image=true`, aynı final kutuların JPEG'ini ve envanterini
tek response'ta verir. Compare frontend'i her model için ayrı bu isteği yapar;
backend'e `model=compare` gönderilmez. Yeni bağımlılık gerekmez.

TR→EN: Helsinki-NLP/opus-mt-tr-en, MarianMTModel + MarianTokenizer.
Dil tespiti: Lingua, bu sürümde Türkçe ve İngilizce ile sınırlı.
Kısa/çok anlamlı sözcüklerde otomatik dil tespiti kesin değildir.

Her sunucu sürecinde startup sırasında bir çeviri servisi ve detector registry
oluşturulur. Registry OWL-ViT ve Grounding DINO'yu birer kez yükler. Çeviri modelinin
dosyaları proje kökündeki .cache/translation içinde tutulur; ilk açılışta
Hugging Face erişimi gerekir, sonraki açılışlarda önbellek kullanılır.

İngilizce sorgu çeviri yapmadan kullanılır. Türkçe ifadeler sözlük lookup yerine
modelin generate çıktısıyla çevrilir. Model "rug" yerine "carpet" veya "sneakers"
gibi eşanlamlı/çoğul bir karşılık üretebilir. Ham çeviri `translated_query` içinde
korunur; ortak query processor article/noktalama temizliğinden sonra yalnızca
tanımlı İngilizce sözcükleri tekilleştirir: people/persons→person, men→man,
women→woman, bags→bag, cars→car, dogs→dog, cats→cat, plants→plant,
pillows→pillow, chairs→chair. Genel suffix silme kuralı yoktur; örneğin glass,
scissors veya red sneakers değiştirilmez. Niteleyiciler korunur: red bags→red bag.
`primary_query` ve detector input'u bu son biçimi kullanır; `original_query`
değişmez. Örneğin çantalar→The bags.→bag. Her iki model aynı katmanı kullanır.
Çeviri başarısı her ifade için aynı doğrulukta garanti edilmez.

Synonym fallback ayrı query_processor katmanındadır. Primary kutu üretirse
fallback çalışmaz; NMS 0.60 korunur. Normal endpoint'ler aşağıda açıklanan
model bazlı adaptive confidence politikasını kullanır.
Çeviri modeli yüklenemezse Türkçe isteğe açıklayıcı HTTP 503 döner.
Backend hata ayrıntısı JSON detail alanındadır. /health yanıtı değiştirilmemiştir;
bu endpoint çeviri modelinin ayrıca hazır olduğunu göstermez.

Bağımlılıkları güncelleme (proje kökünden):

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
~~~

Model indirmeden test:

~~~powershell
python -m unittest discover -s backend/tests -v
~~~

Gerçek translation modeliyle test (sunucu/OWL-ViT başlatmaz):

~~~powershell
$env:RUN_TRANSLATION_SMOKE = "1"
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p test_translation_service.py -v
Remove-Item Env:RUN_TRANSLATION_SMOKE
~~~

## Model mimarisi

- app/services/query_processor.py ve main.py prepare_detection: detector seçilmeden
  önce ortak dil tespiti/çeviri/primary normalizasyonu. Örneğin "çanta" için Marian'ın
  ürettiği "The bag." debug translated_query içinde korunur; primary_query "bag" olur.
- app/models/base_detector.py: hazırlanmış query planı, ortak dönüş sözleşmesi,
  primary-first fallback, mevcut class-aware NMS (0.60), debug akışı ve süre ölçümü.
  Detector'lar çeviri servisine bağımlı değildir; inference yalnızca İngilizce query
  listesi alır. Original query görüntü label'ı/debug için ortak katmanda tutulur.
- app/models/owlvit_service.py: mevcut OWL-ViT inference kodu; CPU davranışı korunur.
- app/models/grounding_dino_service.py: resmi Hugging Face AutoProcessor ve
  AutoModelForZeroShotObjectDetection, IDEA-Research/grounding-dino-tiny.
- app/models/detector_registry.py: süreç başına tek model örnekleri ve model
  bazında kullanılabilirlik; yükleme başarısızlığı diğer modeli durdurmaz.
- app/config.py: GroundingDinoSettings; box_threshold=0.30, text_threshold=0.25.

Grounding DINO CUDA varsa otomatik CUDA, yoksa CPU kullanır. Ağırlıkları proje
kökündeki .cache/grounding-dino içinde tutulur. İlk backend başlangıcında modelin
indirilmesi/yüklenmesi tamamlanana kadar beklenir. Yükleme başarısız olursa
GET /models ilgili modeli available=false gösterir; o modele istek HTTP 503 döner.
Sonraki isteklerde otomatik tekrar yükleme denenmez; erişim sorunu giderildikten
sonra backend yeniden başlatılmalıdır.

Mevcut torch ve transformers sürümleri değiştirilmedi. Kurulu Transformers 5.18.0
API'sinde Grounding DINO post-process box eşiğini threshold adlı argümanla alır;
servis bu argümana merkezi config.box_threshold değerini verir. HTTP threshold
parametresi Grounding DINO eşiklerini değiştirmez.

## Endpoint sözleşmesi

- GET /models: id, name, available alanlarıyla kayıtlı modeller.
- POST /detect ve POST /detect-image: önceki image/query/threshold form alanlarına
  ek olarak model form alanı; owlvit (varsayılan) veya grounding-dino.
- Geçersiz model HTTP 400 döner. Bir istekte yalnızca seçilen detector çalışır.
- POST /detect-raw-image varsayılan OWL-ViT debug davranışını korur; NMS uygulanmaz.
  Opsiyonel model=grounding-dino da aynı ortak query pipeline'ını kullanır.
- JSON alanları korunur. OWL-ViT için model değeri geriye uyumluluk nedeniyle
  OWL-ViT, Grounding DINO için grounding-dino kalır; ayrıca model_id her modelde
  kararlı seçim anahtarını taşır.
- Her iki model JSON yanıtına device ve inference_time_ms ekler. Süre perf_counter
  ile, çeviri/model yükleme hariç detector ön/son işlemleri ve varsa fallback dahil
  ölçülür. Normal endpoint'lerde tüm adaptive denemeler ve NMS de bu süreye
  dahildir. CUDA inference'ında synchronize kullanılır.
- JPEG yanıtı JPEG kalır; metadata X-Model, X-Device, X-Inference-Time-Ms
  header'larında bulunur ve localhost CORS üzerinden okunabilir.
- Frontend dosyaları ve model seçicisiz varsayılan OWL-ViT akışı değiştirilmedi.

Doğrudan İngilizce çoklu model sorgusu için Python servisinin
detect_queries(image, ["bag", "backpack"]) metodu kullanılabilir. HTTP endpoint'i
tek kullanıcı ifadesini önce ortak translation/query katmanından geçirir.

## Doğrulama ve elle test

Proje kökünde, HTTP sunucusu/model yüklemeden:

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -m compileall -q backend/app backend/tests
~~~

Yeni model/API testleri sahte model çıktıları kullanır: seçilen modele yönlendirme,
eşiklerin bağımsızlığı, modelin bir kez yüklenmesi, CPU/CUDA seçimi, JSON/JPEG
sözleşmesi ve yükleme hatasının diğer modeli etkilememesi doğrulanır.
Gerçek Grounding DINO ağırlıkları bu testlerde indirilmez veya çalıştırılmaz.

Backend'i kullanıcı ayrı terminalde başlattıktan sonra (8000 portu):

~~~powershell
curl.exe -s http://127.0.0.1:8000/models
curl.exe -s -F "image=@images/test.jpg" -F "query=bag" -F "model=owlvit" http://127.0.0.1:8000/detect
curl.exe -s -F "image=@images/test.jpg" -F "query=bag" -F "model=grounding-dino" http://127.0.0.1:8000/detect
curl.exe -i -F "image=@images/test.jpg" -F "query=bag" -F "model=invalid" http://127.0.0.1:8000/detect
curl.exe --fail -F "image=@images/test.jpg" -F "query=bag" -F "model=grounding-dino" http://127.0.0.1:8000/detect-image -o outputs/grounding-dino.jpg
~~~

İlk iki JSON isteğinde eski detection/debug alanlarıyla birlikte inference_time_ms
ve device kontrol edilebilir. Invalid model 400; /models içinde available=false
olan bir modele istek 503 olmalıdır.

## Adaptive confidence threshold

`app/services/inference_orchestrator.py`, `/detect` ve `/detect-image` için ortak
seçim katmanıdır. Compare iki ayrı istek gönderdiğinden her model kendi stratejisini
kullanır. Çeviri bir kez yapılır; aynı İngilizce query planı tüm denemelerde korunur.
Önce primary query bütün gerekli adaptive eşiklerde denenir; ilk geçerli sonuçta
durulur. Ancak bütün primary denemelerinde raw sayı 0 ise ayrı fallback fazı
başlar. Bu faz yalnızca synonym adaylarını aynı modelin eşikleriyle dener.
Primary'nin aşırı/bozuk non-empty sonuçları synonym genişletmesiyle aşılmaz.
Her faz mevcut NMS (IoU 0.60) kullanır.

Merkezi `app/config.py` ayarları:

- OWL-ViT: 0.05 → 0.03 → 0.02 → 0.01.
- Grounding DINO box: 0.35 → 0.30 → 0.25 (eski kademeli davranış; üretimde tek 0.30); text: sabit 0.25.
  Bunlar DINO'ya ait ayrı ayarlardır, OWL-ViT skorlarıyla kıyaslanmaz.

İlk makul non-empty sonuç bulunduğunda durulur; daha düşük eşik denenmez.
Heuristic şu bilgileri kullanır:

- 300'den fazla raw veya NMS sonrasında 60'tan fazla kutu: detection_explosion.
  (Eski 8 sınırı envanter raflarını reddediyordu; kaldırıldı.)
- En az 10 raw kutunun en az %90'ı NMS ile elenirse: duplicate_overload.
- NMS sonrası skorların %80'den fazlası kullanılan eşiğin 1.2 katından düşükse:
  weak_confidence_distribution. Bu kontrollü sonuç yedekte tutulur; sıradaki eşik
  denenebilir. Daha düşük eşikte patlama/duplicate baskısı varsa önceki yedek korunur.
- Geçersiz skor veya sıfır/negatif alanlı kutu içeren aday kabul edilmez.
- Tüm sonuçlar boş/aşırı/bozuksa boş liste döner; yalnızca sınırda skorları olan
  kontrollü sonuç varsa yedek seçilir. Raw/filtered sayıları seçilen denemeye aittir;
  no_safe_result durumunda raw sayı korunur, dönen filtered sayı 0 olur.

Bu sınırlar veri setinden öğrenilmemiş, değiştirilebilir ilk sürüm heuristic'leridir.
Örneğin 60'tan fazla gerçek nesneli çok kalabalık görseller de reddedilebilir; kutu/score
istatistikleri tek başına gerçek nesne doğruluğunu kanıtlamaz.

JSON yanıtı `adaptive_threshold_used`, `threshold_attempts` ve
`threshold_selection_reason` alanlarını ekler. Her deneme raw/filtered sayılarını,
NMS duplicate oranını, skor min/max/ortalama ve zayıf skor oranını içerir. DINO'da
`adaptive_threshold_used` box eşiğidir; text eşiği deneme kaydında ayrıca bulunur.
Deneme kayıtlarındaki `phase` ve `queries`, primary ile fallback denemelerini
ayırt eder. JPEG endpoint'i aynı `run_detection` fonksiyonunu kullanır ve JPEG
döndürmeye devam eder. `X-Adaptive-Threshold-Used` ve
`X-Threshold-Selection-Reason` header'ları seçimi ayrıca bildirir. Bu iki endpoint
ayrı çağrılırsa ayrı analiz çalışır; frontend aşağıdaki birleşik yanıtı kullanır.

`POST /detect` için opsiyonel multipart `include_image=true` verildiğinde yanıt,
mevcut JSON metadata'ya ek olarak `annotated_image` nesnesi içerir:
`{"media_type": "image/jpeg", "data_base64": "..."}`. JPEG metadata'daki detection
listesinden çizilir; ek model inference/çeviri/NMS yapılmaz. Varsayılan false
olduğundan eski JSON sözleşmesi korunur. `/detect-image` JPEG endpoint'i de korunur.
Önbellek, dosya depolama veya yeni endpoint eklenmemiştir. Frontend tek model için
bir, Compare için iki paralel /detect isteği kullanır. adaptive denemeler bir
analizin içinde yapılmaya devam eder; model ileri geçiş sayısı her zaman bir değildir.

Geriye uyumluluk için `threshold` form alanı hâlâ kabul edilir ve doğrulanır;
normal endpoint'lerde adaptive politika bu alanın yerine geçer. Frontend'in
gönderdiği eski 0.2 değeri politikayı devre dışı bırakmaz. `/detect-raw-image`
adaptif değildir: OWL-ViT için istenen sabit threshold'u, DINO için modelin mevcut
box/text config'ini kullanır ve NMS uygulamaz. Doğrudan detector servis çağrılarının
eski sabit threshold davranışı korunur. Frontend'e yeni kontrol eklenmemiştir.

Yeni regression testleri model ağırlığı indirmeden çalışır:

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -m compileall -q backend/app backend/tests
~~~

`test_adaptive_runtime_wiring.py` gerçek ASGI route, query processor, orchestrator,
OWL-ViT servis kodu, Hugging Face post-process, NMS ve JPEG çizimini birlikte
çalıştırır. Yalnızca model ağırlıkları sabit logits/boxes ile değiştirilir; gerçek
görselde detection doğruluğu testi değildir. Threshold form alanı gönderilse de
primary denemelerinin 0.05 → 0.03 şeklinde ilerlemesi ve fallback'in beklemesi
kontrol edilir. TestClient TCP sunucusu başlatmaz.

Kod değiştiği halde adaptive metadata hiç gelmiyorsa çalışan sürecin sürümünü
kontrol edin. `--reload` olmadan çalışan uvicorn, dosya değişikliğini belleğe almaz.
Kullanıcı mevcut terminalde Ctrl+C ile süreci kapatıp proje kökünden yeniden
başlatmalıdır (bu işlemler testler tarafından yapılmaz):

~~~powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
~~~
