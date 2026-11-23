# CLAUDE.md: proje durumu

Kullanıcıyla **Türkçe** konuş.

## Amaç
- Ödev: **Açık Sözlük Nesne Tespiti**. Senaryolar: robotik, envanter, güvenlik.
- Ana soru: modeller eğitimde **nadir / hiç görülmemiş** nesneleri ne kadar iyi buluyor? Amaç bunu **ölçmek**; uygulama bir araç.
- Hocanın kararı: model karşılaştırması gerekmiyor, en iyi tek yöntem kullanılacak.
- Ölçümle seçilen yöntem: **OWLv2 large**.

## Kurallar
- LLM/AI entegrasyonu yok.
- İndirme, kurulum ve silme öncesi onay al. İndirmede boyutu ve kaynağı belirt.
- API anahtarı isteme. Kullanıcının e-postası gizli.
- Doğrulamadan sonra commit at. Git yalnızca yerel; push yok.
- Next.js 16.4.3'te kal. `frontend/AGENTS.md` commit edilmez.
- Dürüst ol: ölçülmemiş iddiada bulunma. Uzun işlerde süre tahmini ver.

## Çalıştırma (Windows, CPU, `.venv`)
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
cd frontend; npm run dev          # 127.0.0.1:3000, ?debug=1 ham tanılar
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests   # 143 test
cd frontend; npm run test; npm run test:workspace; npm run typecheck; npm run lint
```
- Modeller `.cache/` altında (git'e dahil değil). Ölçümleri paralel çalıştırma, CPU'da birbirini yavaşlatıyor.
- Git Bash `curl` Türkçe karakterleri bozuyor. Türkçe sorgularla denerken `sunum/hazirla.py` içindeki `post()` fonksiyonunu kullan.

## Mimari (kısa)
- **Backend** (`backend/app/`, FastAPI):
  - `config.py`: tüm eşikler, gerekçeleri yorum olarak yazılı.
  - `models/`: OWLv2 (API'de "owlvit" yuvası), Grounding DINO, YOLO-World.
  - `services/inference_orchestrator.py`: `run_detection`.
- **Çeviri:** Marian + bağlam cümlesi ("Fotoğrafta {sorgu} var."). Testte %93 doğru. Elle yazılmış sözlük yalnızca yedek.
- **Hassasiyet:** Sıkı / Dengeli / Geniş. Eşikler base modeller için kalibre edildi, large için değil.
- **Kesikli turuncu kutu:** aynı sorgunun en iyi puanının yarısından düşük kutular. Silinmez, yalnızca işaretlenir.
- **Örnekle arama:** yalnızca OWLv2.
- OWLv2'de görsel özellik önbelleği var: aynı görselde tekrar arama hızlı.
- **Frontend** (`frontend/src/`): `detection-workspace.tsx`, `model-comparison.tsx`, `technical-details.tsx`.

## Ölçüm sonuçları
| Model | LVIS nadir F1 | Aynı 20 nadir görsel | Kullanıcının masa fotoğrafları (F1) | Olmayan nesneye kutu |
|---|---|---|---|---|
| **OWLv2 large** | 0.50 | **18/20** | **0.82** (37/45) | ~%5 |
| OWLv2 base | 0.50 | 16/20 | 0.71 | ~%5 |
| LLMDet | — | 10/20 | 0.55 | %22 |
| Grounding DINO | 0.21 | 10/20 | 0.51 | %20 |
| YOLO-World | 0.08 | 4/20 | 0.50 | %5 |

- Hiçbir modelin bulamadığı nesneler: pil, açacak, deodorant, tıraş makinesi, parfüm. Bunlar yöntemin sınırları.
- Large'ın bedeli: CPU'da görsel başına ~28 sn (base ~8 sn).
- Raporlar: `outputs/lvis_olcum/` (`siklik_karsilastirma.md`, `yontem_secimi.md`, `kisa_karsilastirma.md`), `outputs/masa_olcum/`, `outputs/ceviri/`.
- Betikler: `evaluation/lvis/` (`evaluate_subset`, `frequency_report`, `candidate_report`, `short_compare`) ve `evaluation/masa/evaluate_masa`.
- Masa fotoğrafları repoda değil: `C:\Users\Harun\Desktop\gorseller`. Cevap anahtarı: `evaluation/masa/etiketler.json`.

## Açık işler
1. **Uygulamayı tek model OWLv2 large'a geçir** (kullanıcının onayını bekliyor):
   - Model adı: `google/owlv2-large-patch14-ensemble`.
   - Eşikleri yeniden kalibre et: LVIS'te en iyi eşik 0.14, masa fotoğraflarında 0.17 çıktı.
   - Karşılaştırma ekranını kaldır, testleri güncelle.
2. **Sunum:** `sunum/SENARYO.md` hâlâ üç model karşılaştırmasına göre yazılı. Model geçişinden sonra yeniden yaz ve `sunum/hazirla.py` ile görselleri yeniden üret.
3. **Rapor:** seçilen yöntemin sık/nadir sonuçları, masa fotoğrafları ve yöntemin sınırları.
4. **Bekleyen silme önerisi** (onay yok): eski deneme çıktıları, ~186 görsel. `outputs/sanity`, `outputs/bolge_kutusu` ve benzerleri. Kullanılmayan çeviri modelleri ve LLMDet de silinebilir.
