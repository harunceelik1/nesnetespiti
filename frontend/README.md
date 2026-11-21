# Nesne tespiti arayüzü

Çoklu nesne için query alanına `çantalar, şişeler, kutular` yazılabilir.
Boş parçalar, tekrarlar, çeviri ve canonical normalizasyon backend'de yapılır.
Sadece virgül/boşluk içeren query gönderilmez. Sonuçta kompakt Envanter Özeti
ve toplam sayım gösterilir; Compare her modelin kendi sayımlarını ayrı tutar.
Sayım yalnızca backend'in final NMS sonuçlarına dayanır; model başarısı yorumu
yapılmaz. API servisi inventory toplamını detection listesiyle doğrular.
Teknik detaylarda sorgu başına çeviri, canonical sorgu ve adaptive eşikler vardır.
Eski backend inventory alanlarını döndürmüyorsa mevcut detection görünümü çalışır,
frontend tahmini inventory üretmez. Yeni bağımlılık gerekmez.

Next.js App Router, React ve TypeScript. Arayüz/CSS için ek bir paket, uzaktan yüklenen font veya ikon kütüphanesi kullanılmaz.

## Workspace düzeni

Masaüstünde 340 px kontrol paneli ve geniş görsel inceleme alanı bulunur.
Tablette panel daralır; mobilde kontroller üstte, sekmeli görsel alanı altta gösterilir.
Orijinal ve Tespit Sonucu sekmeleri klavye ok tuşlarıyla da değiştirilebilir.
Masaüstünde sonuç hazır olduğunda Yan yana karşılaştır seçeneği açılır.
Görsel alanının yüksekliği sonuç gelmeden önce de ayrılır; yükleme sırasında
orijinal görüntü korunur, yeni dosya/sorgu seçildiğinde eski sonuç temizlenir.
Kontrol panelindeki küçük model alanı OWL-ViT, Grounding DINO, YOLO-World ve Compare sunar.
Tek model modunda sonuç çubuğu detection sayısı, backend inference süresi ve
device bilgisini gösterir. Compare aynı dosya ve sorguyu üç modele bağımsız gönderir;
sonuçlar geniş ekranda yan yana, dar ekranda alt alta gösterilir.
Üç model aynı anda CPU paylaştığından Compare süreleri tek model süresinden uzundur;
hız ölçümü için modeli tek başına seçin. Ortak loading tüm işler
bitene kadar sürer; bir model hata verirse diğerinin başarılı sonucu korunur.

Bileşenler: DetectionWorkspace, ControlPanel, ImageViewer, ModelComparison,
ResultSummary ve TechnicalDetails. API servis katmanı model parametresini ve yeni
metrikleri taşır. `/detect` için geriye uyumlu `include_image=true` seçeneği,
tek analiz sonucundan metadata ve JPEG almayı sağlar; detection mantığı değişmez.
ESLint/TypeScript, React Hooks ve erişilebilirlik kurallarıyla kontrol edilir.
jsdom + React act testleri model veya HTTP sunucusu başlatmadan arayüz akışını doğrular.

## Kurulum ve çalıştırma

İki ayrı PowerShell penceresi kullanın. Backend paketleri mevcut sanal ortamda zaten kuruluysa yeniden kurmak gerekmez.

Backend (proje kökünden):

~~~powershell
cd C:\Users\Harun\Desktop\nesnetespiti
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
~~~

Frontend:

~~~powershell
cd C:\Users\Harun\Desktop\nesnetespiti\frontend
npm install
npm run dev
~~~

Arayüz: http://127.0.0.1:3000

Varsayılan API adresi http://127.0.0.1:8000. Farklı backend adresi gerekiyorsa .env.example dosyasını .env.local olarak kopyalayıp NEXT_PUBLIC_API_BASE_URL değerini düzenleyin ve frontend'i yeniden başlatın. Frontend portunu değiştirirseniz backend CORS origin listesine de o localhost portunu eklemeniz gerekir. Mevcut liste yalnızca localhost:3000 ve 127.0.0.1:3000 origin'lerine izin verir.

## Birlikte test etme

1. Backend açılınca http://127.0.0.1:8000/health adresinde {"status":"ok"} yanıtını doğrulayın. İlk model yüklemesi bitmeden backend hazır olmaz.
2. Frontend'de JPG/PNG seçin; orijinal görüntüyü kontrol edin.
3. Önce http://127.0.0.1:8000/models yanıtında iki modelin available durumunu kontrol edin.
4. Bir sorgu girip OWL-ViT seçerek **Tespit Et** düğmesine basın. Network bölümünde tek /detect isteği model=owlvit ve include_image=true taşımalı; threshold gönderilmemeli.
5. Aynı görsel/sorgu için Grounding DINO seçin; tek istekte model=grounding-dino olmalı. Sonuçta model adı, detection sayısı, inference_time_ms ve device gösterilir.
6. Compare seçip tespit edin. Üç paralel /detect isteğini (her model için bir tane), yan yana sonuçları ve her modele ait Teknik detaylar bölümünü kontrol edin. Teknik detaylarda Seçilen eşik, Eşik denemeleri ve Seçim nedeni backend yanıtını göstermeli; DINO için box/text sütunları ayrı olmalı.
7. Tarayıcı geliştirme araçlarında yalnızca model=grounding-dino içeren istekleri engelleyerek tek model hatasını test edebilirsiniz. OWL-ViT sonucu korunmalı, diğer panel hata göstermeli.
8. Mobilde iki model sonucu alt alta gösterilir. Yeni görsel/query/model seçiminde eski sonuçlar temizlenir. Backend kapalıyken kısa bağlantı hatası gösterilir.

## API davranışı

- Her model için POST /detect çağrısına image, query, model ve include_image=true gönderilir. Sabit threshold gönderilmez; adaptive eşiği backend model bazında seçer.
- Tek model modunda bir HTTP analiz isteği, Compare modunda üç paralel HTTP analiz isteği yapılır. Her analiz backend'de gerekirse birden fazla adaptive deneme yapabilir; görsel için ayrı inference yapılmaz.
- JSON içindeki annotated_image.media_type=image/jpeg ve annotated_image.data_base64 alanı aynı detection listesinden çizilmiş JPEG'i taşır. Servis bunu Blob'a dönüştürür, base64 veriyi React metadata state'inde saklamaz. Base64 aktarımının JPEG byte boyutuna göre yaklaşık üçte bir ek maliyeti vardır.
- Nesne sayısı, device, süre ve görsel aynı analiz sonucundandır. Backend'de eski /detect JSON ve /detect-image JPEG çağrıları desteklenmeye devam eder; UI artık /detect-image çağırmaz.
- Eski backend birleşik görsel alanını döndürmezse yeniden başlatma mesajı gösterilir. Sessizce ikinci bir inference'a geri dönülmez. Hata halinde orijinal preview korunur; Compare diğer modelin başarılı sonucunu kaybetmez.
- Adaptive metadata tiplenir ve doğrulanır. Alanlar yoksa Teknik Detaylar "Backend bildirmedi" gösterir; 0.20 gibi sabit bir değer üretilmez. Normal arayüzde threshold/NMS kontrolü yoktur.
- Türkçe sorgular backend'de Marian TR→EN modeliyle otomatik çevrilir; İngilizce sorgular doğrudan kullanılır. Çeviri ayarı yoktur. Teknik Detaylar'da detected_language ve translated_query görülebilir. Yeni backend bağımlılıkları ve model testleri backend/README.md içinde açıklanır.
- Sonuç çubuğundaki süre backend'in inference_time_ms alanıdır. Tarayıcının isteği bekleme süresi (çeviri/JPEG/ağ dahil) yalnızca Teknik detaylar içinde total_request_time olarak gösterilir.
- Confidence değerleri her modelin Teknik detaylar bölümündedir. Modeller arasında confidence sıralaması, kalite puanı veya daha iyi model yorumu yapılmaz; skorların kalibrasyonu farklı olabilir.
- Yeni dosya/sorgu seçildiğinde eski sonuç temizlenir. Object URL'ler temizlenir ve sayfa kapanırken devam eden tarayıcı isteği iptal edilir.

## Kontroller

~~~powershell
cd C:\Users\Harun\Desktop\nesnetespiti\frontend
npm run typecheck
npm run lint
npm test
npm run test:workspace
npm run build
~~~

Backend'in model yüklemeyen testleri (proje kökünden):

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
~~~

Typecheck ve build komutları uygulama sunucularını başlatmaz.
