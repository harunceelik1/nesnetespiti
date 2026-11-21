# Örnek envanter görselleri

Siteye yükleyip denemek için 12 market ürünü görseli. Kaynak: RPC (Retail Product
Checkout) veri seti, `finedet/rpc`, lisans CC BY-NC-SA (ticari olmayan kullanım, atıf gerekli).
Görseller `evaluation/inventory` kalibrasyon kümesinden kopyalandı; 200 görsellik test
kümesine dokunulmadı, rapordaki son ölçüm için ayrılmış durumda.

`dogru_kutular/` klasöründe her görselin elle etiketlenmiş doğru kutuları yeşil çizili.
Sitedeki sonucu bu görselle yan yana koyarak karşılaştır.

## Nasıl denenir

1. Görseli yükle, sorguya **`ürün`** yaz. Bulunan kutu sayısını aşağıdaki **Toplam** ile karşılaştır.
   Bu en güvenilir kontrol: veri setindeki her nesne bir üründür.
2. Sonra tür sorguları dene: `şişe`, `konserve`, `paket`, `peçete`, `süt kutusu`.
   Bunlar yaklaşıktır: veri setinin kategorileri (ör. "içecek") şişe de, kutu da olabilir.
3. Her görselde bir de **olmayan** nesne sor (ör. `köpek`, `ayakkabı`). Doğru cevap 0 kutudur.
4. Yanlış sonuçları (görsel, sorgu, model, beklenen/bulunan sayı) not al ve paylaş.

## Görseller ve doğru sayılar

| Görsel | Toplam | Veri setindeki kategoriler |
|---|---|---|
| `01_envanter.jpg` | **5** | baharat/sos 2, peçete 2, çikolata 1 |
| `02_envanter.jpg` | **5** | cips/atıştırmalık 2, tatlı 2, çikolata 1 |
| `03_envanter.jpg` | **7** | içecek 2, kuru gıda 2, peçete 1, süt 2 |
| `04_envanter.jpg` | **7** | konserve 3, kuru meyve 1, süt 3 |
| `05_envanter.jpg` | **7** | alkollü içecek 2, cips/atıştırmalık 3, konserve 2 |
| `06_envanter.jpg` | **9** | hazır içecek 3, peçete 1, tatlı 2, çikolata 3 |
| `07_envanter.jpg` | **10** | cips/atıştırmalık 2, hazır erişte 2, içecek 3, peçete 3 |
| `08_envanter.jpg` | **10** | içecek 3, kişisel bakım 2, peçete 2, şeker 3 |
| `09_envanter.jpg` | **12** | alkollü içecek 3, hazır erişte 3, içecek 2, kişisel bakım 1, peçete 3 |
| `10_envanter.jpg` | **12** | hazır içecek 2, konserve 4, kuru meyve 3, peçete 3 |
| `11_envanter.jpg` | **16** | cips/atıştırmalık 2, konserve 1, kuru gıda 2, kuru meyve 5, süt 4, tatlı 2 |
| `12_envanter.jpg` | **20** | alkollü içecek 2, cips/atıştırmalık 1, hazır erişte 5, kişisel bakım 2, peçete 3, sakız 5, çikolata 2 |

Zorluk 5 üründen 20 ürüne doğru artıyor; 11 ve 12 numara üst üste binen ürünler içerir.
