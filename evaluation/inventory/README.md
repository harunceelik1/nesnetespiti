# RPC inventory subset hazırlığı

Bu klasör yalnızca ground-truth veri hazırlığı içindir. Detection modeli yüklemez,
Precision/Recall/mAP hesaplamaz ve backend/frontend modüllerini import etmez.
`data/` şu an boş iskelettir; manifest `status=not_prepared` durumundadır.

## Kaynak ve kapsam

- Dataset: [finedet/rpc](https://huggingface.co/datasets/finedet/rpc).
- Split: yalnızca `validation`; train tek ürün exemplar, validation checkout sahneleridir.
- Sabit commit: `d60ce8389c5108c0f59bb01fcb470419c69ccee8`.
- `data/validation-00000-of-00004.parquet` ile `validation-00003-of-00004.parquet`
  arasındaki dört shard seçim havuzuna dahildir. Toplam kaynak boyutu yaklaşık
  1.23 GiB'dir. Her shard bağımsız ve bounded streaming ile açılır; train ve test
  kaynakları açılmaz. Bu tasarım bütün 15+ GB RPC indirmesini önler.
- [categories.csv](https://huggingface.co/datasets/finedet/rpc/blob/d60ce8389c5108c0f59bb01fcb470419c69ccee8/categories.csv)
  tablosundaki dense `id` okunur. `97_milk` için ID 96'dır; prefix'ten ID türetilmez.
- Lisans/atıf bilgisi kaynak kartındadır: CC BY-NC-SA. Kullanım/dağıtımda kaynak
  atfını ve ticari olmayan/share-alike koşullarını koruyun.

## Çalıştırma

Proje kökünden, hiçbir bağımlılık veya ağ erişimi gerektirmeyen dry-run:

```powershell
python evaluation/inventory/prepare_rpc_subset.py --dry-run
```

Gerçek hazırlık için ek bağımlılık `datasets` paketidir; Pillow da kullanılır.
Torch/Transformers evaluation requirements dosyasında bulunmaz. Mevcut backend
ortamını değiştirmemek için ayrı bir sanal ortam tercih edilebilir:

```powershell
python -m venv .venv-evaluation
.\.venv-evaluation\Scripts\python.exe -m pip install -r evaluation/inventory/requirements.txt
.\.venv-evaluation\Scripts\python.exe evaluation/inventory/prepare_rpc_subset.py --dry-run
.\.venv-evaluation\Scripts\python.exe evaluation/inventory/prepare_rpc_subset.py
```

Bağımlılıklar seçilen Python ortamında zaten kuruluysa doğrudan:

```powershell
python evaluation/inventory/prepare_rpc_subset.py
```

Bu son komut ağdan sınırlı veri okur; şu aşamada otomatik çalıştırılmamıştır.
Script herhangi bir klasörden çağrılabilir; varsayılan çıktı script'in yanındaki
`data/` olur, shell'in çalışma klasörüne göre değişmez.

## Seçim ve güvenlik sınırları

1. Küçük kategori tablosu pinned commit'ten alınır (en fazla 128 KiB).
2. `datasets.load_dataset('parquet', ..., streaming=True)` ile her shard'ın
   `width`, `height`, `objects` kolonları ayrı taranır. Varsayılan limit shard başına
   500, toplam 2000 metadata satırıdır. Bu geçişte image kolonu istenmez, büyük
   görüntü shuffle buffer'ı yoktur. `--max-scan-rows` bütün shard'lara bölünen toplamdır;
   örneğin 3000 verildiğinde her shard en fazla 750 satırla sınırlanır.
3. Seed 42 ile karıştırılmış havuzda, shard kotaları içinde en az temsil edilen
   aileye ait sıradaki görüntü seçilir. Yeterli aday varsa 250 görüntü shard'lara
   63/63/62/62 dağılır. Eksik adaylı shard'ın kotası diğerlerine aktarılır.
   Multi-label görüntü tek kayıt olarak seçilir ve bütün seçili ailelerinin sayacı
   artar. Bu basit greedy yöntem tam kategori dengesi garantilemez.
4. İkinci, yine streaming geçişte her shard'da yalnızca son seçilen satıra kadar ilerlenir.
   `Image(decode=False)` ile yalnızca seçili görüntüler decode/kaydedilir. JPEG
   kaynak byte'ları korunur; başka format gerekirse boyut değiştirmeden JPEG olur.
5. Piksel içeriği SHA256 ile denetlenir. Seçimde kopya içerik varsa sessiz leakage
   yerine hata verilir; farklı seed ile tekrar seçilebilir. Seed 43 ile yine aile
   çeşitliliğini ve shard kotalarını gözeterek 50 calibration ayrılır, kalan 200 test
   olur. Calibration kotaları yeterli adayda 13/13/12/12'dir. Görüntü ID/dosya adı
   shard kimliği + shard içindeki satır numarasından oluşur; farklı shard'lardaki
   aynı row index birbiriyle çakışmaz.
6. İş geçici klasörde hazırlanır. Limit veya doğrulama hatasında yarım subset
   yayımlanmaz. Daha önce hazırlanmış çıktının üzerine yazılmaz; otomatik silme yoktur.

CLI: `--seed`, `--max-scan-rows`, `--calibration-count`, `--test-count`, `--output`.
Toplam hedef 250'yi, metadata taraması toplam 3000 satırı (shard başına 750), yerel
JPEG toplamı 256 MiB'yi aşamaz. Varsayılan iki geçiş birlikte en fazla 4000 satır
okur; ikinci geçiş yeni aday eklemez, yalnızca seçilen satırlara ulaşır.
Yeterli toplam aday yoksa script hata verir; başka split veya eager indirmeye geçmez.
Alternatif çıktı gerekiyorsa boş bir klasörü `--output` ile belirtin.

**Ağ miktarı ve disk miktarı aynı değildir.** HF streaming Parquet row-group/
read-ahead nedeniyle diske kaydedilmeyen görüntü byte'larını da okuyabilir.
Kaynak büyüklüğünden kesin dosya boyutu hesaplanamaz; varsayılan
250 görüntü için yaklaşık **30–100 MB yerel JPEG** makul bir planlama tahminidir.
Seçim havuzundaki dört validation shard toplamı yaklaşık **1.23 GiB**'dir; iki geçiş,
bounded satır limitleri, HTTP range cache ve tekrar denemeler nedeniyle ağ aktarımı
farklı olabilir, bu kaynak boyutu katı HTTP kotası
değildir. Bütün RPC indirilmez; daha az ağ kullanımı garanti etmek için kaliteyi/
dengeyi sessizce değiştiren bir yaklaşım yoktur. Gerçek JPEG byte toplamı manifest'e yazılır.

Bu subset dört shard'ın sınırlı önek havuzlarından gelir: bütün validation split'i
için uniform/rastgele satır örneklemesi iddiası yoktur. Eksik kategoriler ve split başına dağılımlar
manifest'te gösterilir. Aynı commit, config ve seed aynı seçimi üretir; dependency
sürümlerini deney kaydında ayrıca sabitlemek önerilir.

## Annotation ve manifest

`calibration/annotations.json` ve `test/annotations.json` kayıt listeleridir.
Her kayıtta image_id, file_name (ilgili images/ klasörüne göre), width, height,
source_shard, source_row_index (shard içindeki indeks), content_sha256 ve objects
bulunur. Her object şunları korur:

- `original_category_id`: HF dense kategori ID'si.
- `original_category_name`: ör. `97_milk`.
- `evaluation_category`: prefix kaldırılıp underscore boşluğa çevrilmiş aile adı.
- `bbox_xywh`: kaynak absolute pixel `[x,y,w,h]`, değiştirilmez.
- `bbox_xyxy`: `[x,y,x+w,y+h]`; normalize edilmiş 0–1 koordinat değildir.

Başlangıçtaki 13 aile config.py içinde tanımlıdır. Diğer ailelerin (ör. alcohol)
kutuları bu evaluation annotation'larına alınmaz. Gelecek evaluation kodu bütün
checkout nesnelerinin etiketlenmiş olduğu varsayımında bulunmamalıdır.

Manifest: dataset/split/revision/seed, source files, taranan/aday/seçilen görüntü
sayıları, calibration/test adetleri ve ID listeleri, kategori başına görüntü ve
nesne sayıları (toplam ve split bazında), mapping tablosu, gerçek yerel JPEG byte
toplamı, config ve eksik kategori kapsamı. Ayrıca `source_files` dört kaynak listesini,
`selected_images_per_shard` gerçek seçim sayılarını, `scanned_rows` toplam metadata
taramasını ve `scanned_rows_per_shard` shard bazlı taramayı içerir.
`per_split_shard_counts` calibration/test dağılımını gösterir.
`image_stream_rows_per_shard` ikinci geçişi, `stream_rows_read_total` iki geçişin
toplamını ayrıca raporlar. Bir görüntü birden fazla aile sayacına
katkı yapabileceğinden kategori görüntü sayılarının toplamı 250'yi aşabilir.

## Küçük testler

Mevcut backend sanal ortamındaki Pillow yeterlidir; bu testler `datasets` import
veya gerçek dataset indirmesi yapmaz. Tam loader bir mock ile doğrulanır.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s evaluation/inventory/tests -v
.\.venv\Scripts\python.exe -m compileall -q evaluation/inventory
```

Testler mapping, ID kökeni, bbox dönüşümü, birden çok nesnenin korunması, seeded
seçim/split ayrımı, leakage/limitler, üzerine yazmama, streaming argümanları ve
birkaç küçük sentetik JPEG ile gerçek dosya/manifest üretimini doğrular.

Streaming davranışı için [resmi HF dokümantasyonu](https://huggingface.co/docs/datasets/stream).

## Calibration inference modları ve prompt karşılaştırması

`evaluate_inventory.py` yalnızca 1–5 calibration görüntüsünü kullanır.
`--inference-mode multi-label` varsayılandır: her görüntünün 17 prompt'u tek
detector forward çağrısında işlenir. `single-query` her kategoriyi ayrı çağırır;
aynı görüntü 17 kez işlenir. Prediction yalnızca kendi canonical kategorisinin
GT kutularıyla eşleşir. Olmayan kategoriler de sorgulanır; FP'ler atlanmaz.
Alias tablosu, threshold, NMS ve matching IoU bu seçimle değişmez.

```powershell
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 1 --model owlvit --prompt-mode canonical --inference-mode single-query
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 1 --model owlvit --prompt-mode canonical --inference-mode multi-label
```

Her komuta `--dry-run` eklemek yalnızca yerel planı, seçilen ID'leri ve forward
sayısını gösterir; model yüklemez, sonuç üretmez, ağ erişimi yapmaz.
`--save-debug-images` aynı prediction'lardan debug görselleri oluşturabilir.
Model ağırlıkları önceden cache'te bulunmalıdır; evaluation indirme başlatmaz.

JSON metadata/summary/record'ları `inference_mode` içerir. Summary'de
`total_forward_calls`, `category_inference_time_ms` (görüntüler boyunca toplam),
`total_evaluation_time_ms` bulunur. Her image run ve CSV satırı kategori sürelerini
ayrıca taşır. Multi-label modunda ayrı kategori süresi ölçülemez: bu alan `null`,
CSV'de boştur; ortak forward süresi `inference_time_ms` ile raporlanır.
Single-query modunda satırdaki süre yalnızca o kategorinin detector çağrısıdır;
image run süresi 17 çağrının toplamıdır. Total evaluation süresi görüntü yükleme,
inference, NMS ve metrik hesaplarını kapsar; model yükleme, rapor/debug kaydı hariçtir.
Inference süreleri mevcut detector çağrısının işlemci/son işleme maliyetini de içerir.

5 aynı görüntüde canonical/alias karşılaştırması (seed aynı tutulmalı):

```powershell
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 5 --seed 42 --model owlvit --prompt-mode canonical --inference-mode single-query
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 5 --seed 42 --model owlvit --prompt-mode alias --inference-mode single-query
.\.venv\Scripts\python.exe evaluation/inventory/compare_prompt_results.py --canonical "CANONICAL_RESULT.json" --alias "ALIAS_RESULT.json"
```

Son komutta ilk iki komutun yazdırdığı JSON yollarını kullanın. Bu araç inference
yapmaz; terminal tablosu ve `results/comparisons/` altında JSON/CSV üretir.
Kategori bazında canonical/alias TP, FP, FN, F1 ve `F1_delta = alias - canonical`
gösterilir. F1, görüntü skorlarının ortalaması değil toplam TP/FP/FN üzerinden
hesaplanır. JSON/CSV ayrıca kaç görüntüde iyileşme/eşitlik/kötüleşme olduğunu taşır.
Bu küçük calibration örneği genel başarı veya istatistiksel üstünlük kanıtı değildir.

Varsayılan karşılaştırma 5 görüntü ister; 1-image kontrolü için
`--expected-images 1` kullanılabilir. Aynı model, inference modu, dataset revision,
annotation/manifest hash, seed, görüntü listesi, kategori listesi, threshold ve
matching IoU doğrulanır. Eski inference-mode metadata formatlı raporları yeniden
üretmek gerekir; kaynak raporlar değiştirilmez.

Tek model için multi-label: 1/5 görüntüde 1/5 forward;
single-query: 1/5 görüntüde 17/85 forward. 5 görüntüde canonical+alias toplamı
single-query için 170, multi-label için 10 forward'dur. `--model both` iki katıdır.
Test split, production pipeline ve adaptive threshold bu deneylere dahil değildir.

## Grounding DINO multi-label phrase çözümleme

Kurulu HF processor, servise gönderilen candidate listesini
`puffed food. dried fruit. ... stationery.` caption'ına dönüştürür.
Evaluation bu desteklenen liste girişini korur; dry-run'daki
`grounding_dino_caption` ve sonuç image-run'ındaki `model_caption` noktalı metni
gösterir. Önceden birleştirilmiş metin nested candidate listesine tekrar konulmaz.

Yalnızca DINO multi-label adapter'ı lowercase/trim, noktalama sınırları ve
bitişik aynı token tekrarlarını normalize eder. Örneğin `instant drink drink`
yalnızca `instant drink` prompt'una eşlenir. Eşleşme gönderilen prompt'lardan
tam birine ve tek biçimde yapılabilmelidir. Alias dönüşümü
`model phrase -> gönderilen alias prompt -> canonical category` şeklindedir.
Substring, fuzzy matching, token sırası değiştirme veya GT'ye bakarak label
seçimi yapılmaz. OWL-ViT ve single-query'nin strict matching davranışı korunur.

Çözülemeyen prediction warning üretir; label, confidence, box ve image ID ile
JSON `unresolved_model_labels` listesine kaydedilir. Image run ve summary'de
`unresolved_model_label_count`, summary'de `label_resolution_complete` bulunur.
Bu prediction'lara tahmini canonical kategori atanmaz: kategori metriklerine
girmezler, GT kutuları ise kalır. Bu nedenle unresolved varsa metrikler yalnızca
çözülen prediction'ları kapsar ve benchmark sonucu tam çözülmüş olarak
yorumlanmamalıdır. Aynı metric ve NMS fonksiyonları değiştirilmeden kullanılır.
