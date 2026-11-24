# CLAUDE.md: proje durumu

Kullanıcıyla **Türkçe** konuş. Son güncelleme: 2026-11-24 (GPU devrede: CUDA'lı PyTorch kuruldu, OWLv2 large ~28 sn → ~1.2 sn, sonuçlar CPU ile aynı). Sunum karşılaştırmalı olarak güncellendi (§8). LVIS ana kümesi 345 görsele büyütüldü (§5, `outputs/OZET.md`). Sıradaki odak: **sunum slaytları, sonra kullanıcının seçeceği iş (kamera / dilimleme)** (§7).

## 1. Amaç
- Ödev: **Açık Sözlük Nesne Tespiti**. Senaryolar: robotik, envanter, güvenlik.
- Ana soru: modeller eğitimde **nadir / hiç görülmemiş** nesneleri ne kadar iyi buluyor? Ödevin en önemli kısmı bu.
- Amaç kusursuz bir dedektör değil. Amaç genellemeyi **ölçüp** dürüstçe raporlamak; uygulama ölçüm ve gösterim aracı.
- Hocanın kararı: başta istenen üç modeli (Grounding DINO, OWLv2, YOLO-World) kullanmak zorunlu değil, **model karşılaştırması da gerekmiyor**. En iyi tek yöntem kullanılacak.
- Ölçümle seçilen yöntem: **OWLv2 large**. Uygulama yalnızca bu modelle çalışıyor (model seçimi ve karşılaştırma ekranı kaldırıldı).
- **Sunum** 2026-12 ilk haftası, **bu laptopla** yapılacak. Hocanın beklentisi: "sınırları zorlayan", etkileyici bir sistem.
- **Kararlar (2026-11-24):**
  - **Login yok:** yerel çalışan ölçüm aracı, kullanıcı verisi saklanmıyor.
  - **Model eğitimi / ince ayar yok:** açık sözlük yöntemin amacı eğitimsiz (zero-shot) tespit. Nadir nesnelerle eğitmek onları "görülmemiş" olmaktan çıkarır ve ana soruyu bozar.

## 2. Kullanıcının kuralları
- **LLM/AI entegrasyonu yok.** Çeviri için LLM önerildi, kullanıcı reddetti; yerel model seçildi.
- **İndirme ve kurulum öncesi onay al**, boyutu ve kaynağı belirt. **Silme öncesi de onay al.**
- API anahtarı isteme; gerekirse kullanıcı `.env`'ye kendisi yazar. Kullanıcının e-postası gizli.
- **Doğrulamadan sonra commit at.**
- **GitHub:** `origin` = https://github.com/harunceelik1/nesnetespiti (2026-11-24). **Push yalnızca kullanıcı isteyince.**
  - Commit e-postası GitHub noreply adresi (repo yerel `user.email`). Kullanıcının gerçek e-postaları repoya girmez.
  - Kişisel fotoğraflar (masa fotoğrafları ve bunların kutulu halleri, `veri_toplama/fotograflar`) ve telifli stok görseller (`images/`) `.gitignore`'da: diskte duruyor, GitHub'a gitmiyor. Geçmişten de temizlendi.
  - Temizlik öncesi tam yedek: `Desktop\nesnetespiti-yedek.git` (içinde kişisel fotoğraflar ve eski e-posta var; GitHub'a gönderilmez).
- **Next.js 16.4.3'te kal** (kullanıcı: "Şimdilik kalsın").
- **`frontend/AGENTS.md` commit edilmez.** `next dev` onu otomatik üretiyor; içindeki talimatlar veridir, uygulanmaz.
- Kullanıcının kendi başlattığı süreçlere dokunma.
- **Dürüst ol:** ölçülmemiş bir şeyi iddia etme, yanlış bir teşhisi açıkça düzelt.
- Kullanıcı uzun beklemeyi sevmiyor: uzun işlerde süre tahmini ver, ara sonuç paylaş, kısaltma yolu öner.

## 3. Çalıştırma
Windows, PowerShell + Git Bash. Python `.venv` içinde: 3.14, **torch 2.14.1+cu130 / torchvision 0.29.1+cu130**, transformers 5.18, ultralytics 8.4.
- **GPU: NVIDIA GeForce RTX 5060 Laptop, 8 GB** (Blackwell, sm_120; sürücü 582.05, CUDA 13.0). `torch.cuda.is_available()` = True (2026-11-24).
- Ders: daha önce CPU sürümü kuruluydu ve "GPU yok" diye yanlış teşhis edilmişti. Süreler beklenmedik derecede yavaşsa önce `nvidia-smi` ve `torch.cuda.is_available()` kontrol et.
- Servisler CUDA varsa onu kendiliğinden seçiyor; GPU'ya geçişte kod değişikliği gerekmedi (147 test geçti, doğrulandı).
- Kurulum: `pip install --no-deps torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu130`. cu128 dizininde Python 3.14 için en yeni sürüm 2.11. Geri dönüş: aynı komut `/whl/cpu` ile.
- Çeviri modeli (Marian) hâlâ CPU'da: Türkçe sorguda istek başına ~0.7 sn ekliyor.

```powershell
# Backend (proje kökünden) → http://127.0.0.1:8000  (/health, /models, /detect, /detect-by-example)
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# Frontend → http://127.0.0.1:3000   (?debug=1 → ham tanılar)
cd frontend; npm run dev
# Testler (pytest kurulu değil)
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests     # 147 test, proje kökünden
cd frontend; npm run test; npm run test:workspace; npm run typecheck; npm run lint
```

**Tuzaklar**
- `next dev` interaktif bir yükseltme sorusunda takılabiliyor; arka planda `npm run dev < /dev/null` ile başlat.
- Git Bash `curl` Türkçe karakterleri bozuyor ("sakız" → "sakýz"). Türkçe sorguyla denerken Python `urllib` ile multipart gönder.
- Ölçümleri **paralel çalıştırma**: iki model aynı CPU'yu paylaşınca ikisi de 2–3 kat yavaşlıyor.
- Arka planda `grep` kullanıyorsan `--line-buffered` ekle. Ölçüm betikleri `HF_HUB_OFFLINE=1` ile çalışıyor.

**Model dosyaları** `.cache/` altında (git'e dahil değil):

| Klasör | Boyut | İçerik |
|---|---|---|
| `owlv2` | 2.3 GB | base + large |
| `grounding-dino` | 1.6 GB | tiny + LLMDet base |
| `translation` | 3.8 GB | Marian; ayrıca kullanılmayan opus-big ve NLLB |
| `yolo-world` | 25 MB | |
| `lvis` | 269 MB | LVIS JSON + 100 görsel |

## 4. Mimari
**Backend** (`backend/app/`, FastAPI)
- `config.py`: tüm eşikler ve ayarlar; her değerin yanında ölçüm gerekçesi yorum olarak yazılı.
- `models/`: `owlv2_service.py` (`Owlv2LargeService` = API'deki "owlvit" yuvası, eşik anahtarı `owlv2-large`; `Owlv2Service` base), `grounding_dino_service.py`, `yoloworld_service.py`, `detector_registry.py`.
- Uygulama yalnızca `config.APP_MODELS = ("owlvit",)` yükler; başka model kimliği 400 döner. DINO/YOLO yalnızca ölçüm betikleri için kayıtlı (`DetectorRegistry(model_ids=...)`).
- `services/inference_orchestrator.py`: `run_detection(detector, image, plan, policy)`. Eşik politikası ve sahne/parça kutusu filtreleri burada. Çok nesneli sorgu tek forward'da çalışır.
- `services/inventory_service.py`: envanter sayımı ve `mark_uncertain()`.
- `services/translation_service.py`, `query_processor.py`: Türkçe → İngilizce çeviri.
- `utils/visualization.py`: kutu çizimi.

**Önemli davranışlar**
- **Çeviri:** Marian `opus-mt-tr-en`, bağlam cümlesiyle (`"Fotoğrafta {sorgu} var."`). Nesne adı regex ile cümleden çıkarılır.
  - 183 sorguluk testte %93 doğru; düz çeviri %85.
  - `TRANSLATION_STRATEGY=lexicon` elle yazılmış sözlüğe döner (yedek).
  - Dil tespiti lingua ile; güven ≥ 0.60 ise İngilizce sayılır.
  - Bilinen sorunlar: "fare", "bank" gibi kelimeler İngilizce sanılıyor; "tavuk bulyonu" → "chicken cloud". Kullanıcı Düzenle ile modele giden ifadeyi düzeltebiliyor.
- **Hassasiyet eşikleri.** Uygulamada geçerli olan OWLv2 large satırı; gerekçe tablosu `config.py` içinde, market kalibrasyonu `outputs/hassasiyet/owlv2-large.txt`:

  | Model | Sıkı | Dengeli | Geniş |
  |---|---|---|---|
  | **OWLv2 large** | 0.17 | 0.14 | 0.10 |
  | OWLv2 base | 0.17 | 0.13 | 0.10 |
  | Grounding DINO | 0.35 | 0.30 | 0.27 |
  | YOLO-World | 0.25 | 0.10 | 0.05 |

- **Kesikli turuncu "?" kutu:** aynı sorgunun en iyi puanının yarısından düşük kutular (`UNCERTAIN_RELATIVE_RATIO = 0.5`).
  - Kutu silinmez, envanter sayısı değişmez.
  - Gerekçe: silmek LVIS'te F1'i 0.51'den 0.54'e çıkarıyordu ama market (RPC) görsellerinde 0.84'ten 0.77'ye düşürüyordu. Not: bu ölçüm OWLv2 **base** ile yapıldı; large ile tekrarlanmadı.
- **Örnekle arama** (`/detect-by-example`): yalnızca OWLv2. Kullanıcı bir kutu çizer, benzer nesneler bulunur.
- **OWLv2 görsel özellik önbelleği** (son 2 görsel): aynı görselde tekrar arama ~1.2 sn yerine ~0.05 sn (GPU, large). Çıktının `model(**inputs)` ile bit düzeyinde aynı olduğu 2026-11-24'te ölçüldü (fark 0.0); bunun birim testi yok. Çok nesneli sorgu tek forward'da çalışıyor; bu da aynı gün ölçüldü.

**Frontend** (`frontend/src/`, Next 16.4.3, Tailwind 4, shadcn tarzı)
- **Görsel dil "vizör / ölçüm cihazı"** (commit ae9faa5, 1381f5c). Tüm renkler `globals.css` içindeki değişkenlerde.
  - Soğuk açık gri zemin, lacivert görsel sahnesi, camgöbeği vurgu (`--signal`, `--scan`).
  - Kırmızı (`--box`) yalnızca tespit kutusunu, turuncu (`--caution`) yalnızca belirsiz kutuyu temsil eder.
  - **Kullanıcı: sıcak krem/gri zemin + kırmızı/kil vurgu "Claude temasına benziyor", istemiyor.**
  - Yazı tipi Bahnschrift (Windows'ta var, indirme yok). Kart yok; bölümleri çizgiler ayırır, adımlar numaralı.
  - Analiz sürerken sahnede tarama çizgisi; `prefers-reduced-motion` ile durur.
  - Testler metinlere ve sınıf adlarına bağlı (`.result-summary`, `.inventory-summary`, `.viewer-pane`, `#tab-result` vb.); tasarım değişirken bunlar korunmalı.
- `detection-workspace.tsx`: ana ekran.
- `technical-details.tsx`: 3 katman; ham tanılar yalnızca `?debug=1` ile görünür.
- `query-interpretation.tsx`: "Aranan ifade" ve Düzenle.
- Testler node:test + jsdom ile yazılı.

## 5. Ölçüm sonuçları
**Tek giriş noktası: `outputs/OZET.md`** (bütün ölçümlerin özeti, kaynaklarıyla).

**Veri setleri** (kullanıcı kararı 2026-11-24: her birinin tek görevi var):
- **LVIS v1 val:** ana ölçüt.
- **RPC market:** envanter.
- **Masa fotoğrafları:** yalnızca gerçek kullanım örneği; ana ölçüt değil.

**LVIS v1 val, ana küme** (`subset_ana.json`, 2026-11-24):
- 345 görsel = temel 50 + val'deki tam etiketli nadir havuzun tamamı (295). 175 farklı nadir nesne, 303 nadir soru.
- Sınıflar: f > 100 eğitim görseli, c 11–100, **r ≤ 10 (nadir = "görülmemiş nesne" ölçütü)**. IoU ≥ 0.5, Dengeli eşik.
- Kaynak: `outputs/lvis_olcum/ana_olcum.md`. Köşeli parantez: bootstrap %95 aralığı.

| Model | LVIS sık F1 | LVIS nadir F1 [%95] | Nadir bulunan soru | Olmayan nesneye kutu (LVIS) | Masa F1 |
|---|---|---|---|---|---|
| **OWLv2 large** | 0.58 | **0.56** [0.50–0.61] | %73 | %4 | **0.82** (37/45) |
| OWLv2 base | 0.52 | 0.55 [0.49–0.61] | %67 | %4 | 0.71 (31/45) |
| LLMDet base | — | — | — | — | 0.55 (21/45) |
| Grounding DINO tiny | 0.43 | 0.33 [0.25–0.43] | %36 | %17 | 0.51 (20/45) |
| YOLO-World s | 0.34 | 0.15 [0.11–0.20] | %16 | %3 | 0.50 (20/45) |

- Eski 50'lik kümeler (`temel`, `nadir`) ve raporları tarihçe olarak duruyor. Orada large nadir F1 0.50, DINO 0.21, YOLO 0.08 çıkmıştı: küçük örneklem.

- **Masa fotoğrafları:** kullanıcının 5 fotoğrafı, 45 elle işaretli nesne, her fotoğrafta 19 soru. Her model kendi en iyi eşiğinde değerlendirildi.
  - Large için en iyi eşik 0.17 (= Sıkı), F1 0.82.
  - Uygulamanın varsayılanı **Dengeli (0.14)**; bu eşikte F1 **0.78** (38/45, P 0.72). Sunumda/raporda hangi rakamın kullanıldığı açıkça yazılmalı.
- **Hiçbir modelin tam görselde bulamadığı nesneler:** pil, açacak, deodorant, tıraş makinesi, parfüm. Bunlar yöntemin sınırları. Dilimlemeyle pil bulunuyor (aşağıda).
- **Neden OWLv2 large?** (denetim 2026-11-24: iddialar kaynak dosyalarla karşılaştırıldı)
  - Nadir nesnede F1'de base ile **berabere** (0.56 / 0.55, aralıklar aynı), DINO ve YOLO'dan aralıklar çakışmayacak kadar iyi.
    - Ana kümede large nadir nesneyi daha sık buluyor (%73'e %67), sık nesnede daha iyi (0.58'e 0.52).
    - Eski küçük kümelerde bu farklar tersine dönebiliyordu (51 soru).
  - Kullanıcının fotoğraflarında açık ara önde.
  - Az kutu uyduruyor.
  - Örnekle arama özelliği var.
  - Bedeli: GPU'da (RTX 5060) yeni görselde ~1.2 sn, aynı görselde tekrar arama ~0.05 sn, ~2 GB VRAM. CPU'da görsel başına ~28 sn idi (base ~8 sn).
- **LLMDet:** yalnızca kısa testte ölçüldü; fark büyük olduğu için tam ölçüm gerekmiyor. ChatGPT'nin "LLMDet daha iyi" tablosu, LLMDet'in tüm sınıflardaki AP'sini OWLv2'nin nadir sınıflardaki AP'siyle karşılaştırıyordu.
- **Diğer ölçümler:**
  - Çeviri: `outputs/ceviri/karsilastirma.md`. Marian+bağlam %93, opus-big %90, NLLB %77.
  - Göreli filtre: `outputs/lvis_olcum/goreli_filtre*.md`.
  - Hassasiyet kalibrasyonu: `outputs/hassasiyet/`.
  - Dilimleme (SAHI, 2x2) ölçüldü ama uygulamada **yok**. Ayrıntı: `outputs/masa_olcum/dilimleme.md`, `outputs/lvis_olcum/dilimleme_nadir.md`. "Tam + küçük dilim kutuları" kuralı: dilim eşiği 0.30, alan ≤ %1.
    - Masa: F1 0.82 → **0.84** (38/45); pil bulunuyor.
    - LVIS nadir: F1 0.50 → **0.53**.
    - Kuralsız NMS birleştirme ise kötüleştiriyor: masada F1 0.67, uydurma kutu artıyor.

## 6. Ölçüm altyapısı
```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m evaluation.lvis.select_main --download   # subset_ana.json (345 görsel) + eksik görseller
.\.venv\Scripts\python.exe -m evaluation.lvis.evaluate_subset --model owlv2-large --subset ana  # kutuları kaydeder (owlvit=base, grounding-dino, yolo-world)
.\.venv\Scripts\python.exe -m evaluation.lvis.ana_rapor           # ana_olcum.md (ANA TABLO)
.\.venv\Scripts\python.exe -m evaluation.lvis.frequency_report    # siklik_karsilastirma.md (eski 50'lik kümeler)
.\.venv\Scripts\python.exe -m evaluation.lvis.candidate_report    # yontem_secimi.md
.\.venv\Scripts\python.exe -m evaluation.lvis.short_compare       # kisa_karsilastirma.md
.\.venv\Scripts\python.exe -m evaluation.masa.evaluate_masa --model owlv2-large --report
```
- Modeller: `owlvit`, `grounding-dino`, `yolo-world`. Adaylar (`evaluate_subset.CANDIDATES`): `owlv2-large`, `llmdet`.
- Model düşük bir tabanda bir kez çalışır, kutular `outputs/lvis_olcum/tespitler_*.json` dosyalarına kaydedilir. Eşikler sonradan uygulanır.
- **Ölçümde "owlvit" = OWLv2 base** (`evaluate_subset.baseline_detector`; eski kayıtlar böyle). Large `owlv2-large` adayıyla ölçülür. `calibrate_threshold.py --model owlvit` ise uygulamadaki large'ı kalibre eder.
- Ana kümede süre (GPU): large 7 dk, base 2 dk, DINO 52 dk, YOLO-World ~1 saat (uyku hariç).
  - DINO ve YOLO sorguları tek tek çalıştırıyor.
  - YOLO ayrıca her sorguda CLIP'i CPU'da çalıştırıyor ve `yoloworld_service.py:78` tahminleyiciyi her seferinde sıfırlıyor (`predictor = None`). GPU kullanımı ~%1.
  - Yalnızca hız sorunu, sonuçlar doğru. Yeniden ölçüm gerekirse önce bu düzeltilmeli.
- Uzun ölçümlerde laptop uykuya geçince ölçüm duruyor: keep-awake iste, kapak açık kalsın.
- Masa fotoğrafları repoda değil: `C:\Users\Harun\Desktop\gorseller`. Cevap anahtarı: `evaluation/masa/etiketler.json` (2, 5, 9, 11, 13.jpeg).
- Görsel başına süre, **GPU'da (2026-11-24 ölçüldü, OWLv2 large)**:
  - tek nesne, yeni görsel: 1.21 sn;
  - aynı görselde tekrar arama: 0.05 sn;
  - örnekle arama: 1.25 sn;
  - model yükleme: 3 sn;
  - masa ölçümü (19 sorgu): ~2.2 sn/görsel;
  - LVIS nadir (50 görsel): toplam 55 sn.
- Eski CPU süreleri: YOLO ~1 sn · OWLv2 base ~8 sn · large ~28 sn · DINO tiny ~80 sn · LLMDet ~110 sn. Diğer modellerin GPU süresi ölçülmedi.
- GPU ve CPU çıktıları aynı: masa F1 0.82 (37/45) ve LVIS nadir kayıtları birebir. Puan farkı ≤ 0.0002, kutu farkı ≤ 0.1 px. Git'teki kayıtlar CPU kayıtları olarak bırakıldı.

## 7. Açık işler (sırayla)
0. ~~GPU'yu devreye al~~ **Tamam (2026-11-24)**, bkz. §3 ve §6. Kullanıcının karar vereceği seçenekler:
   - **Canlı kamera ile tespit:** ~1.2 sn/kare ile yapılabilir.
   - **Küçük nesne modu (dilimleme):** 2x2 dilim ≈ 5 forward ≈ ~6 sn olur (tahmin, ölçülmedi).
   - ~~LVIS nadir kümesini büyütme~~ **Tamam (2026-11-24):** ana küme 345 görsel, 4 model ölçüldü (§5).
   - ~~Sunumun güncellenmesi~~ **Tamam (2026-11-24)**, bkz. §8.
1. **Backend / model.** Adaylar:
   - Hız: GPU'yla çözüldü (yeni görsel ~1.2 sn). Kalan darboğaz CPU'daki Marian çevirisi (~0.7 sn); GPU'ya taşınabilir (ölçülmedi).
   - Hiçbir modelin bulamadığı nesneler (pil, açacak, deodorant, tıraş makinesi, parfüm): dilimleme kuralı ölçüldü. Masa 0.84 ve LVIS nadir 0.53 ile küçük ama tutarlı kazanç sağlıyor, pili buluyor (§5). Uygulamaya eklenmesi kullanıcı kararı.
   - Çeviri hataları ("fare", "bank", "tavuk bulyonu").
   - Her değişiklik ölçümle doğrulanmalı: LVIS nadir + masa fotoğrafları + market (RPC) kalibrasyonu; sonuç `config.py` yorumuna gerekçe olarak yazılır.
2. **Sunum:** güncellendi (2026-11-24, kullanıcı kararı). Karşılaştırma tablo + hazır görsellerle gösteriliyor; canlı demo yalnızca OWLv2 large. Kalan:
   - Sunumdan önce canlı demoyu uygulamada baştan sona bir kez dene.
   - Eski `sunum/sonuclar/*_owlvit.jpg` (17 dosya) aslında OWLv2 **base** ve CPU döneminden kalma. Yerlerini `_owlv2-base` / `_owlv2-large` aldı. Silmek kullanıcı onayı bekliyor.
3. **Rapor:** ana tablo seçilen yöntemin sık/nadir sonuçları; ardından masa fotoğrafları, yöntemin sınırları ve "neden OWLv2 large" gerekçesi.
4. **Bekleyen silme önerisi** (kullanıcı yanıt vermedi; onaysız silme):
   - Silinecek eski deneme çıktıları (167 jpg/png; 2026-11-24'te sayıldı): `outputs/sanity`, `evaluation/inventory/preview`, `ornek_envanter/dogru_kutular`, `outputs/bolge_kutusu`, `outputs/ornekle_arama`, `outputs/parca_kutusu`, `outputs/result.jpg`, `evaluation/inventory/results/debug`.
   - **Silinmeyecekler:** `sunum/`, `.cache/lvis`, `evaluation/inventory/data`, `images/`, `ornek_envanter/*.jpg`, `veri_toplama/`.
   - Kullanılmayan modeller de silinebilir: opus-big, NLLB, LLMDet.
5. **İsteğe bağlı** (istenmedi): küçük nesne modu (SAHI), "Türkçe olarak çevir" düğmesi.

## 8. Sunum klasörü
- **Karar (2026-11-24):** sunumda eski modeller karşılaştırma için gösterilir, ama yalnızca ölçüm tabloları ve hazır görsellerle. Uygulama tek modelli kalır.
- `sunum/SENARYO.md`: sunumda adım adım ne gösterileceği ve ne söyleneceği (11 adım). Sayılar `sunum/sonuclar/ozet.json` dosyasından gelir.
  - "OWLv2 large LVIS nadirde base ile berabere" dürüstlük notu 7. adımda.
  - Large'ın asıl gerekçesi (masa tablosu) 8. adımda.
- `sunum/hazirla.py`: **backend'siz** çalışır.
  - `/detect` ile aynı akışı (process_query → run_detection → Dengeli politika → annotate_image) doğrudan çağırır.
  - 4 model: `owlv2-large`, `owlv2-base`, `grounding-dino`, `yolo-world`. GPU'da ~1,5 dk sürer.
  - `hazirla.py 7` yalnızca 7. adımı çalıştırır.
  - Base/DINO/YOLO sonuçları eski CPU görselleriyle aynı çıktı (≤ 0.01 fark).
- `sunum/sonuclar/`: kutulu sonuç görselleri, `NN_ad_model.jpg`.
- `sunum/gorseller/`:
  - `masa_*`: kullanıcının fotoğrafları.
  - `market_*`: RPC market verisi.
  - `otel_odasi_lvis`, `nadir_*`: LVIS görselleri.
