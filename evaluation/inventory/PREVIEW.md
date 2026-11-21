# Selected ve all ground-truth preview

Varsayılan `selected`, calibration setinin mevcut annotation'larından yalnızca
13 evaluation ailesini çizer. `all`, yerel `data/full_annotations.json` dosyasından
aynı calibration görüntülerinin tüm RPC nesnelerini çizer; test görüntülerine geçmez.
Seçili ailelerin renkleri korunur; diğer aileler gri, ör. `alcohol (88_alcohol)`
etiketiyle gösterilir. `_ground_truth_all.jpg` adları selected çıktıları ezmez.

```powershell
python evaluation/inventory/preview_ground_truth.py
python evaluation/inventory/preview_ground_truth.py --mode selected --count 15
python evaluation/inventory/preview_ground_truth.py --mode all --count 15
```

Üst özet: `RPC objects: X | Selected objects: Y | Ignored objects: Z`.
Sayılar çizilen kutulardan değil, annotation kayıtlarından hesaplanır; geçersiz
kutular warning ile çizimden atlanabilir. Tam kaynak yoksa selected modunda RPC ve
ignored toplamları `?` gösterilir; filtrelenmiş listeden toplam uydurulmaz.
All modu tam dosya yoksa açıklayıcı hata verir; otomatik ağ erişimi yapmaz.

## Mevcut 250 ID için tam annotation recovery

Mevcut subset dosyalarında evaluation dışı kutular korunmamıştır. Ayrı
`recover_full_annotations.py`, manifest'teki sabit ID listesini mevcut calibration/
test kayıtlarının source_shard/source_row_index bilgileriyle doğrular. Aynı pinned
HF revision'ının dört validation shard'ını **yalnızca width/height/objects
kolonlarıyla** streaming olarak okur. Görüntü indirme/decode/kaydetme çağrısı yoktur;
Parquet metadata ve range okuması yine ağ maliyeti oluşturur. Kategori isimleri
manifest'teki mevcut mapping'den alınır; category tablosu yeniden indirilmez.

Önce yerel dry-run (ağ ve yazım yok):

```powershell
python evaluation/inventory/recover_full_annotations.py --dry-run
```

Gerçek recovery aşağıdaki ayrı, ağ erişimi yapan komuttur. Kod geliştirme sırasında
otomatik çalıştırılmamıştır:

```powershell
python evaluation/inventory/recover_full_annotations.py
```

Tahmin: birkaç MB–onlarca MB annotation/metadata aktarımı. Kesin HTTP byte kotası
değildir; dört Parquet kaynak dosyasının toplamı yaklaşık 1.23 GiB'dir, ancak image
kolonu istenmez. Her dosyada yalnızca son gerekli mevcut satıra kadar ilerlenir.
Row-group/read-ahead veya server davranışı tahminden fazla ağ aktarımı yaratabilir.

Yazılan tek dataset dosyası `data/full_annotations.json` olur. `complete`,
dataset/split/revision, image_count ve `images` listesini içerir. Her kayıt mevcut
image_id, file_name, source konumu ve subset bilgisini korur; objects tüm aileleri,
orijinal ID/adı, semantic family, xywh/xyxy ve `is_evaluation_category` içerir.
Mevcut 250 ID'den olmayan bir görüntü eklenmez; JPEG, manifest ve iki split'in
annotation dosyaları değiştirilmez. Seçili nesneler kaynakla uyuşmazsa veya kayıt
eksikse çıktı yazılmaz. Mevcut full_annotations.json üzerine yazılmaz.

Tam dosya hazır olduktan sonra preview her iki modda doğru RPC/selected/ignored
toplamlarını gösterebilir. Kaynak görüntüler değişmez; varsayılan seed 42 ve count
15 korunur. Hazırlama script'i, model servisleri ve frontend değiştirilmemiştir.
