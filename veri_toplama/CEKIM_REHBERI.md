# Fotoğraf çekim rehberi

Amaç: modellerin **eğitimde görülmüş** nesnelerdeki başarısını **görülmemiş** nesnelerdeki
başarısıyla karşılaştırmak. Bunun için her fotoğrafta iki türden de nesne olmalı.

- **Görülmüş** = COCO veri setinin 80 sınıfından biri (listesi aşağıda).
- **Görülmemiş** = bu 80 sınıfın hiçbirine girmeyen nesne.

Kendi çektiğin fotoğraflar modellerin eğitim verisinde kesinlikle yoktur. Raporda bunu
söyleyebilmek bu veri setinin en büyük avantajı.

---

## Kaç fotoğraf, hangi sahneler

Toplam **30 fotoğraf**:

| Sahne | Adet | Örnek içerik |
|---|---|---|
| Çalışma masası | 8 | laptop, fare, bardak + şarj aleti, zımba, bant, ilaç kutusu |
| Mutfak tezgâhı | 7 | şişe, kase, çatal, elma + baharat kavanozu, kesme tahtası, sünger, tuzluk |
| Banyo / lavabo | 5 | diş fırçası, lavabo + diş macunu, deodorant, el kremi, tarak |
| Çanta içeriği (masaya serilmiş) | 5 | telefon, kitap, şemsiye + cüzdan, anahtar, kulaklık kutusu, gözlük kılıfı |
| Raf / dolap (envanter) | 5 | şişe, kitap, kutu dizisi; aynı üründen birden fazla |

**Zorluk dağılımı** (her sahne içinde karıştır):

- ~10 **kolay**: düzenli, 4–6 nesne, birbirine değmiyor.
- ~10 **orta**: 6–10 nesne, biraz dağınık.
- ~10 **zor**: 10+ nesne, üst üste binen, küçük nesneler, kalabalık.

---

## Her fotoğrafta

1. **En az 2 görülmüş + en az 2 görülmemiş nesne** olsun.
2. **Kafa karıştırıcı çiftler koy** (bilerek): ilaç kutusunun yanına benzer boyutta başka bir
   kutu, şarj aletinin yanına fare, baharat kavanozunun yanına şişe. Gerçek dünyadaki hatalar
   böyle durumlarda çıkıyor; ölçmek istediğimiz tam olarak bu.
3. **2 tane "olmayan" nesne düşün** ve nesne listesine yaz (ör. masa fotoğrafı için "köpek",
   "şemsiye"). Model bunları bulursa sahte tespit sayılır.

---

## Nasıl çekilir

| Kural | Neden |
|---|---|
| Telefonun normal kamerası, filtre/portre modu yok | Bulanık arka plan ve filtre modeli şaşırtır |
| Gün ışığı veya iyi oda ışığı, flaş yok | Flaş parlama yapar, yazı ve kenarlar kaybolur |
| Net olsun, titreme yok | Bulanık kenar = yanlış kutu |
| Çoğunlukla yukarıdan veya 45° açıdan | Masada nesneler net ayrılır |
| Her nesne **tamamen** kadrajda (kesik nesne az olsun) | Kesik nesnenin doğru kutusu tartışmalı olur |
| Nesne çok küçük olmasın: görselin genişliğinin en az ~%5'i | Daha küçüğü "zor" fotoğraflarda birkaç tane olabilir |
| Çözünürlük: uzun kenar en az 1200 piksel (telefon zaten fazlasını verir) | |

**Gizlilik:** Kadrajda yüz, kimlik, kart, açık ekran, adres veya ilaç reçetesi gibi kişisel
bilgi olmasın. Bu fotoğraflar raporda görünecek.

---

## Dosyalar

- Fotoğrafları `veri_toplama/fotograflar/` klasörüne koy.
- Adlandırma: `01_masa.jpg`, `02_masa.jpg`, … `09_mutfak.jpg`, … (sıra numarası + sahne).
- Her fotoğraf için `veri_toplama/nesne_listesi.csv` dosyasına satır ekle (örnekler içinde var):
  - `grup` sütunu: `gorulmus`, `gorulmemis` veya `yok` (olmayan nesne).
  - `adet`: o nesneden fotoğrafta kaç tane var.
  - `nesne_en`: emin değilsen boş bırak, birlikte doldururuz.
  - Dosya Excel'de açılır (ayırıcı `;`). İlk satırlar senin masa fotoğrafın
    (`fotograflar/00_ornek_masa.jpg`) için örnektir; sayıları ekran görüntüsünden tahmin ettim,
    kontrol et ve kendi satırlarını ekledikten sonra örnekleri silebilirsin.

Kutuları şimdi çizmene gerek yok; fotoğraflar hazır olunca birlikte etiketleyeceğiz.

---

## Görülmüş nesneler (COCO'nun 80 sınıfı)

Gündelik sahnelerde işine yarayacak olanlar **kalın**:

**insan**, bisiklet, araba, motosiklet, uçak, otobüs, tren, kamyon, tekne, trafik ışığı,
yangın musluğu, dur işareti, parkmetre, bank, kuş, **kedi**, **köpek**, at, koyun, inek, fil,
ayı, zebra, zürafa, **sırt çantası**, **şemsiye**, **el çantası**, **kravat**, **valiz**,
frizbi, kayak, snowboard, top, uçurtma, beyzbol sopası, beyzbol eldiveni, kaykay, sörf tahtası,
tenis raketi, **şişe**, **şarap kadehi**, **bardak/fincan (cup)**, **çatal**, **bıçak**,
**kaşık**, **kase**, **muz**, **elma**, sandviç, **portakal**, brokoli, **havuç**, sosisli,
pizza, çörek, **pasta/kek**, **sandalye**, **kanepe**, **saksı bitkisi**, yatak,
**yemek masası**, **klozet**, **televizyon**, **laptop**, **fare**, **kumanda**, **klavye**,
**cep telefonu**, **mikrodalga**, **fırın**, **ekmek kızartma makinesi**, **lavabo**,
**buzdolabı**, **kitap**, **saat (duvar/masa)**, **vazo**, **makas**, **oyuncak ayı**,
**saç kurutma makinesi**, **diş fırçası**.

## Görülmemiş nesne fikirleri (COCO'da yok)

| Sahne | Nesneler |
|---|---|
| Masa | ilaç kutusu, şarj aleti, uzatma kablosu, zımba, ataş, bant, silgi, cetvel, kalem, kalemtıraş, hesap makinesi, USB bellek, powerbank, kulaklık |
| Mutfak | baharat kavanozu, tuzluk, kesme tahtası, sünger, rende, kevgir, tencere, tava, çaydanlık, termos, kavanoz kapağı |
| Banyo | diş macunu, deodorant, el kremi tüpü, tarak, sabun, pamuk, tıraş makinesi |
| Çanta | cüzdan, anahtar, kulaklık kutusu, gözlük kılıfı, kol saati, çakmak, toka, ruj |
| Raf | karton kutu, konserve, makarna paketi, çay paketi, deterjan |

**Dikkat — "alt tür" tuzağı:** "şampuan şişesi" bir *şişe*, "kahve kupası" bir *fincan*dır.
Bunlar görülmüş sınıfın alt türü sayılır, görülmemiş değil. Görülmemiş listesine **hiçbir COCO
sınıfına benzemeyen** nesneleri koy. Emin değilsen `grup` sütununa `?` yaz, birlikte karar veririz.
