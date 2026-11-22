# Calibration inventory smoke evaluation

Bu aşama yalnızca `full_annotations.json` içindeki mevcut calibration görüntülerini
kullanır. CLI'da `--split test` reddedilir, `--limit` yalnızca 1–5 olabilir.
Dataset hazırlama, indirme, annotation/manifest güncelleme, grafik veya mAP yoktur.
Sonuçlar 5 görüntüden genellenmiş benchmark sonucu olarak yorumlanmamalıdır.

## Komutlar

Proje kökünde, mevcut backend bağımlılıklarının kurulu olduğu sanal ortamla:

```powershell
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 1 --model owlvit
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 5 --model owlvit
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 5 --model grounding-dino
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 5 --model both
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 5 --model yolo-world
.\.venv\Scripts\python.exe evaluation/inventory/evaluate_inventory.py --split calibration --limit 5 --model all
```

`both` geriye uyumluluk için OWL-ViT + Grounding DINO'dur; `all` YOLO-World'ü de
ekler. YOLO-World sabit baseline eşiği production adaptive listesinin ilk değeridir
(0.25). Evaluation indirme başlatmaz: YOLO-World ağırlığı ve CLIP önbellekte yoksa
açıklayıcı hata verir; önce backend'i bir kez başlatıp modelin yüklenmesini bekleyin.

Model yüklemeden, inference/ağ/yazım yapmadan planı görmek için:

```powershell
python evaluation/inventory/evaluate_inventory.py --split calibration --limit 5 --model both --dry-run
```

Gerçek inference komutları geliştirme sırasında çalıştırılmamıştır. Varsayılan seed
42 ile manifest'in sıralanmış calibration ID'lerinden aynı görüntüler seçilir.
Yeni paket gerektirmez; gerçek inference için mevcut torch/transformers/Pillow
kurulumu ve iki modelin mevcut yerel cache'i kullanılır. CLI model import'undan
önce `HF_HUB_OFFLINE=1` ve `TRANSFORMERS_OFFLINE=1` ayarlar. Cache eksikse indirmek
yerine hata verir; production sürecinin ortamını veya dosyalarını değiştirmez.

## Tek görüntü ve çok kategori

17 GT kategorisi kullanıcı tarafından belirlenen semantic adlarla sabitlenmiştir;
`is_evaluation_category` (eski 13 aile filtresi) kullanılmaz. Bir görüntüde olmayan
kategoriler de sorgulanır ve bu kategorilere ait prediction'lar FP olarak sayılır.
Test GT'si prompt veya threshold seçimi için kullanılmaz.

Her model/görüntü için mevcut servisin `infer_queries(image, 17_queries, ...)`
metodu **bir kez** çağrılır. OWL-ViT ve Grounding DINO implementasyonu kopyalanmaz.
`BaseDetector.detect_result` label'ları tek original_query'ye çevirdiğinden çoklu
sınıf evaluation'da bu yüksek seviye API kullanılmaz. Ham sınıf etiketleri korunur,
mevcut class-aware NMS (IoU 0.60) yeniden kullanılır; containment eklenmez.

Bu kontrollü ilk baseline, production adaptive/synonym pipeline'ını çalıştırmaz
ve onu değiştirmez. OWL-ViT sabit confidence 0.05; DINO mevcut merkezi config'deki
box/text eşiklerini (şu anda 0.30/0.25) kullanır. Bunlar veri başarısına bakılarak
seçilmez. Threshold stratejisi her kayıt ve raporda açıkça yazılır. Bu sonuçlar
production tek-sorgu adaptive endpoint performansı ile aynı deney değildir.
Çoklu prompt bağlamı da tek-sorgu bağlamından farklı sonuç üretebilir.

Model etiketleri yalnızca case/boşluk/son nokta bakımından temizlenir ve gönderilen
prompt'un canonical kategori karşılığına eşlenir. DINO belirsiz veya
birleşik phrase döndürürse GT yardımıyla uygun kategoriye atama yapılmaz; kayıt
sessizce düşürülmez. Smoke test açıklayıcı hata verir. Bu durum gerçek ilk denemede
görülürse prompt-label hizalaması ayrıca ele alınmalıdır.

5 görüntü için model başına en fazla 5 forward; both için toplam en fazla 10
forward vardır. Model süreç içinde bir kez yüklenir, both modelleri sırayla işler.
Warm-up veya tekrar ölçümü yoktur. Süre model ön/son işlemleri dahil gerçek
`perf_counter` ölçümüdür; yükleme, JPEG okuma, NMS ve metric hesapları hariçtir.
DINO kendi mevcut CUDA synchronize davranışını korur. Aynı image-level süre
17 kategori kaydında gösterilir ama summary'de yalnızca bir kez kullanılır.

## Metrik tanımları

`metrics.py` saf Python'dur. Matching her image/category içinde ayrı, varsayılan
IoU >= 0.5 ile confidence-ordered greedy one-to-one çalışır. Eşit confidence'ta
prediction indeksi, eşit IoU'da GT indeksi kullanılır; aynı GT/prediction en fazla
bir kez eşleşir. Bu algoritma Hungarian/global-optimum assignment değildir.

- TP: eşleşen kutu; FP: eşleşmeyen prediction; FN: eşleşmeyen GT.
- Precision=TP/(TP+FP), recall=TP/(TP+FN), F1 harmonik ortalama.
- Payda 0 ise ilgili oran 0 olur; GT ve prediction ikisi de boşsa F1=0.
- Average matched IoU yalnızca eşleşen kutuların ortalamasıdır; eşleşme yoksa null.
- Count absolute error = abs(predicted_count - ground_truth_count), image/category bazında.
- Micro: tüm kayıtların TP/FP/FN toplamından hesaplanır.
- Macro: önce sınıf başına bütün görüntüler toplanır, sonra 17 sınıfın oranları
  eşit ağırlıkla ortalanır. Beş görüntüde hiç bulunmayan sınıflar da sıfır oranla dahildir.
- Mean matched IoU bütün eşleşmeler üzerinden ağırlıklı ortalamadır.
- MAE image/category kayıtları üzerindedir (5 görüntü için 85 kayıt); image-level
  toplam ürün sayısının hatasıyla karıştırılmamalıdır.
- Average inference time image/model çağrıları üzerinden hesaplanır.

## Çıktı ve doğrulama

`results/calibration_MODEL_PROMPTMODE_TIMESTAMP_UNIQUE.json` metadata, 17 sınıflı image-level
prediction listeleri/süreleri, image/category kayıtları, matching indeksleri ve
summary içerir. CSV aynı image/category kayıtlarını, threshold JSON kolonuyla
taşır. Kaynak annotation/manifest hash'leri JSON metadata'da saklanır.
Model isimleri ayrı dosyalara yazılır; both için dört dosya oluşur. JSON eşleşme
IoU'su olmayan değerleri null, CSV boş hücre olarak gösterir.

## Debug görselleri

```powershell
python evaluation/inventory/evaluate_inventory.py --split calibration --limit 1 --model owlvit --save-debug-images
```

`--save-debug-images` her image/model için `results/debug/` altında PNG üretir.
Sol panelde full annotation GT kutuları yeşil; sağ panelde evaluation'ın mevcut NMS
sonrası prediction kutuları turuncu gösterilir. İki panelde kategori adı, yalnızca
prediction etiketinde confidence (üç ondalık basamak) bulunur. Üstte panel türü,
model ve kutu sayıları yazılıdır. Dosya adı sonuç JSON stem'ini ve kaynak görüntü
adını içerir; model/run eşleştirmesi korunur. Kaynak görüntü resize edilmez.

Çizim aynı `image_runs[].detections` listesini kullanır; ek inference, prompt,
threshold, NMS veya metric hesabı yapılmaz. Inference süresi debug çizimini içermez.
Clipping yalnızca çizimdedir; metric girdileri ve kaydedilen skorlar değiştirilmez.
Debug hatası warning verir, tamamlanmış JSON/CSV raporlarını geçersiz kılmaz.
Bayrak verilmezse debug üretimi yoktur; `--dry-run` ile birlikte de görsel yazılmaz.

## Canonical ve alias prompt karşılaştırması

`--prompt-mode canonical` varsayılandır: modele semantic kategori adı gider.
`--prompt-mode alias`, yalnızca evaluation'a ait `prompt_aliases.py` tablosunu
kullanır. Eksik alias canonical kategoriye döner; boş veya iki kategoriye aynı
prompt atanması hata verir. Alias eşlemesi GT/production normalizasyonunu değiştirmez.

```powershell
python evaluation/inventory/evaluate_inventory.py --split calibration --limit 1 --model owlvit --seed 42 --prompt-mode canonical --save-debug-images
python evaluation/inventory/evaluate_inventory.py --split calibration --limit 1 --model owlvit --seed 42 --prompt-mode alias --save-debug-images
```

Aynı seed/limit/manifest için image_id listesi moddan bağımsızdır. Önce bu iki
komuta `--dry-run` ekleyerek image_id ve mapping karşılaştırılabilir. Mod değiştirmek
ek forward, threshold taraması veya synonym fallback başlatmaz; her görüntü/model
yine tek 17-sorgulu inference yapar. Model çıktısındaki alias metni ters tabloyla
canonical kategoriye çevrildikten sonra mevcut class-aware NMS ve aynı metric
matching uygulanır. Ground-truth category ve annotation dosyaları değişmez.

JSON/CSV kayıtlarında `category`, `model_prompt`, `prompt_mode` vardır. Prediction
kayıtlarında canonical `label` ve `category` yanında `raw_model_label` korunur.
Summary ve JSON metadata `prompt_mode` ve `category_prompt_mapping` içerir; böylece
dosyadaki mapping snapshot'ı daha sonra alias dosyası düzenlense de korunur.
Sonuç ve debug dosya adlarında mod bulunduğundan canonical/alias karışmaz.
Debug kutuları canonical kategori etiketlerini, panel başlığı model/modu gösterir.

Bu kontrollü prompt tanımları kalibrasyon doğruluğu garantisi değildir. Özellikle
"milk carton" gibi ifade bir kategori içindeki farklı ambalaj tiplerini dışlayabilir;
etki yalnızca calibration üzerinde karşılaştırılmalıdır, test'e göre prompt ayarlanmaz.

Önce yalnızca sentetik metric testleri:

```powershell
python -m unittest evaluation.inventory.tests.test_metrics -v
```

Sonra fake detector ve minik sentetik görüntülerle wiring/CSV testleri:

```powershell
.\.venv\Scripts\python.exe -m unittest evaluation.inventory.tests.test_evaluate_inventory -v
.\.venv\Scripts\python.exe -m compileall -q evaluation/inventory
```
