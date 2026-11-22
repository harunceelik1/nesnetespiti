# TR→EN çeviri karşılaştırması (nesne sorguları)

Test seti: 183 sorgu (ascii 12, belirsiz 20, cogul 8, sifat 8, tamlama 16, tek 62, yeni 57).
Bağlam cümlesi: "Fotoğrafta {query} var.". CPU, num_beams=4, sabit (deterministik) çözümleme.

## Genel sonuç

| Aday | Doğru | Eklemeli | Yanlış | Doğru oranı | Süre (ms/sorgu, toplu) | Kalıp dışı cümle |
|---|---|---|---|---|---|---|
| marian · düz | 156 | 2 | 25 | %85 | 48 | — |
| marian · bağlamla | 170 | 0 | 13 | %93 | 93 | 1 |
| opus-big · düz | 149 | 3 | 31 | %81 | 242 | — |
| opus-big · bağlamla | 164 | 0 | 19 | %90 | 523 | 0 |
| nllb · düz | 123 | 3 | 57 | %67 | 381 | — |
| nllb · bağlamla | 140 | 2 | 41 | %77 | 657 | 3 |
| şimdiki sistem (sözlük + Marian) | 174 | 1 | 8 | %95 | — | — |

Şimdiki sistemde 128 sorgu sözlükten geldi (doğru %99); sözlükte olmayan 55 sorguda Marian'a düştü (doğru %85). Sözlük bu test setinin bir kısmı için elle yazıldığından o satır tavan değeri gibi okunmalı, adil bir rakip değildir.

## Gruplara göre doğru oranı

| Aday | ascii | belirsiz | cogul | sifat | tamlama | tek | yeni |
|---|---|---|---|---|---|---|---|
| marian · düz | 3/12 | 17/20 | 8/8 | 7/8 | 13/16 | 59/62 | 49/57 |
| marian · bağlamla | 7/12 | 20/20 | 8/8 | 8/8 | 15/16 | 62/62 | 50/57 |
| opus-big · düz | 0/12 | 16/20 | 8/8 | 7/8 | 14/16 | 60/62 | 44/57 |
| opus-big · bağlamla | 3/12 | 20/20 | 8/8 | 7/8 | 15/16 | 62/62 | 49/57 |
| nllb · düz | 0/12 | 18/20 | 8/8 | 7/8 | 7/16 | 49/62 | 34/57 |
| nllb · bağlamla | 1/12 | 19/20 | 8/8 | 7/8 | 12/16 | 53/62 | 40/57 |
| şimdiki sistem | 12/12 | 20/20 | 8/8 | 8/8 | 16/16 | 62/62 | 48/57 |

## Sorgu bazında çıktılar

✓ doğru · + eklemeli · ✗ yanlış

| Türkçe | grup | kabul | marian · düz | marian · bağlamla | opus-big · düz | opus-big · bağlamla | nllb · düz | nllb · bağlamla | şimdiki |
|---|---|---|---|---|---|---|---|---|---|
| şişe | tek | bottle | ✓ bottle | ✓ bottle | ✓ Bottle | ✓ bottle | ✓ bottle | ✓ bottle | ✓ bottle |
| bardak | tek | cup / glass | ✓ cup | ✓ glass | ✓ Cup | ✓ glass | ✓ glass | ✓ glass | ✓ cup |
| sandalye | tek | chair | ✓ Chair | ✓ chair | ✓ Chair | ✓ chair | ✓ The chair | ✓ chair | ✓ chair |
| masa | tek | table / desk | ✓ Table | ✓ table | ✓ table | ✓ table | ✓ Table | ✓ table | ✓ table |
| kedi | tek | cat | ✓ cat | ✓ cat | ✓ Cat | ✓ cat | ✓ The cat | ✓ cat | ✓ cat |
| köpek | tek | dog | ✓ Dog | ✓ dog | ✓ Dog | ✓ dog | ✓ The dog | ✓ dog | ✓ dog |
| araba | tek | car / automobile | ✓ car | ✓ car | ✓ Car | ✓ car | ✓ car | ✓ car | ✓ car |
| bisiklet | tek | bicycle / bike | ✓ bicycle | ✓ bicycle | ✓ Bike | ✓ bicycle | ✓ Bicycle | ✓ bicycle | ✓ bicycle |
| uçak | tek | airplane / plane / aircraft | ✓ airplane | ✓ plane | ✓ Aircraft | ✓ plane | ✓ The plane | ✓ plane | ✓ airplane |
| kamyon | tek | truck / lorry | ✓ Truck | ✓ truck | ✓ Truck | ✓ truck | ✓ The truck | ✓ truck | ✓ truck |
| otobüs | tek | bus | ✓ Bus | ✓ bus | ✓ Bus | ✓ bus | ✓ Bus | ✓ bus | ✓ bus |
| çanta | tek | bag / handbag | ✓ The bag. | ✓ bag | ✓ Bag | ✓ bag | ✓ the bag | ✓ bag | ✓ bag |
| cüzdan | tek | wallet / purse | ✓ wallet | ✓ wallet | ✓ Wallet | ✓ wallet | ✓ wallet | ✓ wallet | ✓ wallet |
| şemsiye | tek | umbrella | ✓ umbrella | ✓ umbrella | ✓ Umbrella | ✓ umbrella | ✓ The umbrella | ✓ umbrella | ✓ umbrella |
| gözlük | tek | glasses / eyeglasses / spectacles | ✓ Glasses | ✓ glasses | ✓ Eyeglasses | ✓ glasses | ✓ The glasses | ✓ glasses | ✓ glasses |
| ayakkabı | tek | shoe / shoes | ✓ Shoes | ✓ shoes | ✓ Shoes | ✓ shoes | ✓ The shoe | ✓ shoe | ✓ shoe |
| eldiven | tek | glove / gloves | ✓ glove | ✓ gloves | ✓ Gloves | ✓ gloves | ✓ The gloves | ✓ gloves | ✓ glove |
| şapka | tek | hat / cap | ✓ hat | ✓ hat | ✓ Hat | ✓ hat | ✓ The hat | ✓ hat | ✓ hat |
| kumanda | tek | remote / remote control / controller | ✗ Control | ✓ remote | ✗ Control | ✓ remote | + on the controller | + on the controller | ✓ remote |
| klavye | tek | keyboard | ✓ keyboard | ✓ keyboard | ✓ Keyboard | ✓ keyboard | ✓ Keyboard | ✓ keyboard | ✓ keyboard |
| telefon | tek | phone / telephone | ✓ Phone | ✓ phone | ✓ telephone | ✓ phone | ✓ The phone | ✓ phone | ✓ phone |
| televizyon | tek | television / tv | ✓ television | ✓ TV | ✓ TV | ✓ television | ✓ TV | ✓ TV | ✓ tv |
| kulaklık | tek | headphones / headphone / earphones | ✓ headphones | ✓ headphones | ✓ Headphone | ✓ headphones | ✓ The headset | ✓ headset | ✓ headphones |
| kitap | tek | book | ✓ book | ✓ book | ✓ book | ✓ book | ✓ The book | ✓ book | ✓ book |
| makas | tek | scissors | ✓ scissors | ✓ scissors | ✓ Scissors | ✓ scissors | ✓ scissors | ✓ scissor | ✓ scissors |
| kaşık | tek | spoon | ✓ spoon | ✓ spoon | ✓ spoon | ✓ spoon | ✗ Spoonful | ✓ spoon | ✓ spoon |
| çatal | tek | fork | ✓ fork | ✓ fork | ✓ Fork | ✓ fork | ✗ Forklift | ✓ fork | ✓ fork |
| bıçak | tek | knife | ✓ knife | ✓ knife | ✓ Knife | ✓ knife | ✓ The knife | ✓ knife | ✓ knife |
| tabak | tek | plate / dish | ✓ plate | ✓ plate | ✓ Plate | ✓ plate | ✓ plate | ✓ plate | ✓ plate |
| tencere | tek | pot / saucepan | ✓ Pot | ✓ pot | ✓ pot | ✓ pot | ✓ the pot | ✓ pot | ✓ pot |
| tava | tek | pan / frying pan / skillet | + It's a pan. | ✓ pan | ✓ Pan | ✓ pan | ✗ The bowl | ✗ can | ✓ pan |
| yastık | tek | pillow / cushion | ✓ pillow | ✓ pillow | ✓ Pillow | ✓ pillow | ✓ Pillow | ✓ pillow | ✓ pillow |
| halı | tek | carpet / rug | ✓ carpet | ✓ rug | ✓ Carpet | ✓ carpet | ✓ Carpet | ✓ carpet | ✓ rug |
| perde | tek | curtain / curtains | ✓ curtain | ✓ curtain | ✓ Curtain | ✓ curtain | ✓ The curtain | ✓ curtain | ✓ curtain |
| ayna | tek | mirror | ✓ mirror | ✓ mirror | ✓ Mirror | ✓ mirror | ✓ Mirror | ✓ mirror | ✓ mirror |
| lamba | tek | lamp / light | ✓ lamp | ✓ lamp | ✓ Lamp | ✓ lamp | ✓ The lamp | ✓ lamp | ✓ lamp |
| saksı | tek | flower pot / flowerpot / pot | ✓ pot | ✓ flowerpot | ✓ Flowerpot | ✓ pot | ✗ What's wrong with you? | ✗ rash | ✓ flower pot |
| vazo | tek | vase | ✓ vase | ✓ vase | ✓ vase | ✓ vase | ✓ The vase | ✓ vase | ✓ vase |
| buzdolabı | tek | refrigerator / fridge | ✓ Refrigerator | ✓ fridge | ✓ refrigerator | ✓ refrigerator | ✓ the fridge | ✓ fridge | ✓ refrigerator |
| havlu | tek | towel | ✓ Towel | ✓ towel | ✓ Towel | ✓ towel | ✓ The towel | ✓ towel | ✓ towel |
| kova | tek | bucket / pail | ✓ bucket | ✓ bucket | ✓ bucket | ✓ bucket | ✗ the bowl | ✓ bucket | ✓ bucket |
| mum | tek | candle | ✓ Candle | ✓ candle | ✓ Candle | ✓ candle | ✓ Candle | ✓ candle | ✓ candle |
| anahtar | tek | key / keys | ✓ key | ✓ key | ✓ Key | ✓ key | ✓ the key | ✓ key | ✓ key |
| zımba | tek | stapler | ✓ stapler | ✓ stapler | ✓ Stapler | ✓ stapler | ✗ - What 's going on ? | ✗ zipper | ✓ stapler |
| silgi | tek | eraser / rubber | ✓ eraser | ✓ eraser | ✗ Silgi | ✓ eraser | ✗ Deleted | ✗ blur | ✓ eraser |
| cetvel | tek | ruler | ✓ ruler | ✓ ruler | ✓ Ruler | ✓ ruler | ✗ - What are you doing? | ✗ ring | ✓ ruler |
| sünger | tek | sponge | ✓ sponge | ✓ sponge | ✓ Sponge | ✓ sponge | ✓ The sponge | ✓ sponge | ✓ sponge |
| tarak | tek | comb | ✓ comb | ✓ comb | ✓ comb | ✓ comb | ✗ the tarak | ✗ scratch | ✓ comb |
| çakmak | tek | lighter | ✓ Lighter | ✓ lighter | ✓ Lighter | ✓ lighter | ✗ I'm going to hit you. | ✗ punch | ✓ lighter |
| termos | tek | thermos / flask / vacuum flask | ✓ thermos | ✓ thermos | ✓ Thermos | ✓ thermos | ✓ thermos | ✓ thermos | ✓ thermos |
| poşet | tek | plastic bag / bag | ✓ Bag | ✓ bag | ✓ Bag | ✓ bag | ✓ The bag | ✓ bag | ✓ plastic bag |
| kavanoz | tek | jar | ✓ jar | ✓ jar | ✓ jar | ✓ jar | ✗ the pot | ✓ jar | ✓ jar |
| sakız | tek | chewing gum / gum | ✓ Gum | ✓ gum | ✓ Gum | ✓ gum | ✓ Chewing gum | ✓ gum | ✓ chewing gum |
| cips | tek | chips / crisps | ✓ Chips. | ✓ chips | ✓ Chips | ✓ chips | ✓ The chips | ✓ chips | ✓ chips |
| deterjan | tek | detergent | ✓ detergent | ✓ detergent | ✓ Detergent | ✓ detergent | ✓ The detergent | ✓ detergent | ✓ detergent |
| peçete | tek | napkin / tissue / serviette | ✓ napkin | ✓ napkin | ✓ Napkin | ✓ napkin | ✗ to the blanket | ✗ blanket | ✓ tissue |
| zarf | tek | envelope | ✓ envelope | ✓ envelope | ✓ envelope | ✓ envelope | ✓ envelope | ✓ envelope | ✓ envelope |
| valiz | tek | suitcase / luggage | ✓ luggage | ✓ suitcase | ✓ suitcase | ✓ suitcase | ✓ the suitcase | ✓ suitcase | ✓ suitcase |
| yüz | belirsiz | face | ✗ 100 | ✓ face | ✓ Face | ✓ face | ✓ The face | ✓ face | ✓ face |
| el | belirsiz | hand | ✓ hand | ✓ hand | ✗ el | ✓ hand | ✓ the hand | ✓ hand | ✓ hand |
| at | belirsiz | horse | ✓ Horse | ✓ horse | ✗ At | ✓ horse | ✓ horse | ✓ horse | ✓ horse |
| bank | belirsiz | bench | ✗ Bank | ✓ bench | ✗ Bank | ✓ bench | ✗ bank | ✗ bank | ✓ bench |
| top | belirsiz | ball | ✓ ball | ✓ ball | ✓ Ball | ✓ ball | ✓ The ball | ✓ ball | ✓ ball |
| fare | belirsiz | mouse | ✓ mouse | ✓ mouse | ✓ Mouse | ✓ mouse | ✓ Mouse | ✓ mouse | ✓ mouse |
| bot | belirsiz | boot / boots / boat | ✓ Boot | ✓ boat | ✗ Bot | ✓ boat | ✗ bot | ✓ boat | ✓ boot |
| saat | belirsiz | clock / watch | ✓ clock | ✓ clock | ✓ clock | ✓ clock | ✓ The clock | ✓ clock | ✓ clock |
| çay | belirsiz | tea | ✓ tea | ✓ tea | ✓ Tea | ✓ tea | ✓ tea | ✓ tea | ✓ tea |
| bebek | belirsiz | baby / doll | ✓ Baby | ✓ baby | ✓ Baby | ✓ baby | ✓ The baby | ✓ baby | ✓ baby |
| yüzük | belirsiz | ring | ✓ Ring | ✓ ring | ✓ Ring | ✓ ring | ✓ The ring | ✓ ring | ✓ ring |
| kalem | belirsiz | pen / pencil | ✓ Pen | ✓ pen | ✓ Pen | ✓ pen | ✓ The pencil | ✓ pencil | ✓ pen |
| motor | belirsiz | motorcycle / motorbike / engine | ✓ Engine | ✓ engine | ✓ Engine | ✓ engine | ✓ engine | ✓ motor | ✓ motorcycle |
| ekran | belirsiz | screen / monitor / display | ✓ screen | ✓ screen | ✓ Screen | ✓ screen | ✓ screen | ✓ screen | ✓ screen |
| dolap | belirsiz | cabinet / cupboard / wardrobe | ✗ Locker | ✓ closet | ✓ Cabinet | ✓ closet | ✓ The closet | ✓ closet | ✓ cabinet |
| kase | belirsiz | bowl | ✓ bowl | ✓ bowl | ✓ Bowl | ✓ bowl | ✓ The bowl | ✓ bowl | ✓ bowl |
| kupa | belirsiz | mug / cup / trophy | ✓ cup | ✓ mug | ✓ Cup | ✓ mug | ✓ Cup | ✓ cup | ✓ mug |
| kravat | belirsiz | tie / necktie | ✓ Tie | ✓ tie | ✓ Tie | ✓ tie | ✓ The tie | ✓ tie | ✓ tie |
| tabela | belirsiz | sign / signboard | ✓ sign | ✓ sign | ✓ Signboard | ✓ sign | ✓ The sign | ✓ sign | ✓ sign |
| kaya | belirsiz | rock | ✓ rock | ✓ rock | ✓ Rock | ✓ rock | ✓ rock | ✓ rock | ✓ rock |
| canta | ascii | bag / handbag | ✗ Canta | ✓ bag | ✗ Canta | ✗ canta | ✗ to your chest. | ✗ to your chest. | ✓ bag |
| sise | ascii | bottle | ✗ sise | ✓ bottle | ✗ Sise | ✗ fog | ✗ to the ice | ✗ fox | ✓ bottle |
| kopek | ascii | dog | ✗ kopek | ✓ dog | ✗ kopek | ✗ kopek | ✗ the cape | ✗ mole | ✓ dog |
| cuzdan | ascii | wallet / purse | ✗ Cuzdan | ✓ wallet | ✗ zuzdan | ✗ leprosy | ✗ From the grass . | ✗ knife | ✓ wallet |
| cop kutusu | ascii | trash can / garbage can / bin | ✗ baton box | ✗ baton | ✗ Cop Box | ✗ baton box | ✗ cop box | ✗ copper box | ✓ trash can |
| kasik | ascii | spoon | ✗ Crotch | ✗ helmet | ✗ Kasik | ✗ helmet | ✗ - What ? | ✗ hook | ✓ spoon |
| catal | ascii | fork | ✗ catal | ✗ cat | ✗ Catal | ✗ catal | ✗ Catalan | ✗ cat | ✓ fork |
| bicak | ascii | knife | ✓ knife | ✓ knife | ✗ Bicak | ✓ knife | ✗ Wrists | ✓ knife | ✓ knife |
| gozluk | ascii | glasses / eyeglasses / spectacles | ✗ Eyepiece | ✗ Eyepiece | ✗ Gözluk | ✓ eyeglasses | ✗ The beauty | ✗ beauty | ✓ glasses |
| semsiye | ascii | umbrella | ✗ Semantics | ✗ cessation | ✗ Samsiye | ✓ umbrella | ✗ The seed | ✗ spot | ✓ umbrella |
| sapka | ascii | hat / cap | ✓ Hat | ✓ hat | ✗ Sapka | ✗ sapka | ✗ The stumbling block | ✗ pervert | ✓ hat |
| kulaklik | ascii | headphones / headphone / earphones | ✓ headphones | ✓ headphones | ✗ Earbuds | ✗ earpiece | ✗ earrings | ✗ earpiece | ✓ headphones |
| şişeler | cogul | bottle / bottles | ✓ bottles | ✓ bottles | ✓ Bottles | ✓ bottles | ✓ bottles | ✓ bottles | ✓ bottle |
| kediler | cogul | cat / cats | ✓ Cats | ✓ cats | ✓ Cats | ✓ cats | ✓ cats | ✓ cats | ✓ cat |
| sandalyeler | cogul | chair / chairs | ✓ chairs | ✓ chairs | ✓ Chairs | ✓ chairs | ✓ the chairs | ✓ chairs | ✓ chair |
| kitaplar | cogul | book / books | ✓ books | ✓ books | ✓ Books | ✓ books | ✓ books | ✓ books | ✓ book |
| arabalar | cogul | car / cars | ✓ cars | ✓ cars | ✓ Cars | ✓ cars | ✓ The cars | ✓ cars | ✓ car |
| kutular | cogul | box / boxes | ✓ boxes | ✓ boxes | ✓ Boxes | ✓ boxes | ✓ boxes | ✓ boxes | ✓ box |
| anahtarlar | cogul | key / keys | ✓ Keys | ✓ keys | ✓ Keys | ✓ keys | ✓ the keys | ✓ keys | ✓ key |
| bardaklar | cogul | cup / cups / glass | ✓ cups | ✓ glasses | ✓ Cups | ✓ cups | ✓ cups | ✓ glasses | ✓ cup |
| su şişesi | tamlama | water bottle | ✓ Water bottle | ✓ water bottle | ✓ Water Bottle | ✓ water bottle | ✗ bottle of water | ✓ water bottle | ✓ water bottle |
| ilaç kutusu | tamlama | medicine box / pill box / pillbox | ✗ Pharmaceutical box | ✓ medicine box | ✓ Medicine Box | ✓ medicine box | ✓ medicine box | ✓ medicine box | ✓ medicine box |
| gözlük kılıfı | tamlama | glasses case / spectacle case / eyeglass case | ✗ Glass cover | ✗ glass case | ✗ Eyewear Case | ✓ eyeglass case | ✗ The cover of the glasses | ✗ pair of glasses | ✓ glasses case |
| diş fırçası | tamlama | toothbrush | ✓ toothbrush | ✓ toothbrush | ✓ Toothbrush | ✓ toothbrush | ✓ toothbrush | ✓ toothbrush | ✓ toothbrush |
| kahve fincanı | tamlama | coffee cup / coffee mug | ✓ Coffee cup | ✓ coffee cup | ✓ Coffee Cup | ✓ coffee cup | ✗ a cup of coffee | ✗ cup of coffee | ✓ coffee cup |
| çöp kutusu | tamlama | trash can / garbage can / bin | ✓ trash can | ✓ trash can | + Garbage Bin | ✓ trash can | ✗ trash box | ✓ garbage can | ✓ trash can |
| süt kutusu | tamlama | milk carton / milk box | ✓ milk carton | ✓ milk carton | ✓ Milk Box | ✗ milk can | ✓ Milk box | ✓ milk box | ✓ milk carton |
| kalem kutusu | tamlama | pencil case / pen case / pencil box | ✓ pencil box | ✓ pencil case | ✓ Pencil Box | ✓ pencil box | ✗ pen box | ✓ pencil box | ✓ pencil case |
| sırt çantası | tamlama | backpack / rucksack | ✓ Backpack | ✓ backpack | ✓ Backpack | ✓ backpack | ✓ the backpack | ✓ backpack | ✓ backpack |
| telefon kılıfı | tamlama | phone case | ✓ Phone case | ✓ phone case | ✓ Phone Case | ✓ phone case | ✗ The phone cover | ✗ phone cover | ✓ phone case |
| şarj aleti | tamlama | charger | ✓ Charger | ✓ charger | ✓ Charger | ✓ charger | ✗ charging device | ✓ charger | ✓ charger |
| hesap makinesi | tamlama | calculator | ✓ calculator | ✓ calculator | ✓ Calculator | ✓ calculator | ✗ Calculating machine | ✓ calculator | ✓ calculator |
| trafik ışığı | tamlama | traffic light / traffic lights | ✓ traffic light | ✓ traffic light | ✓ traffic light | ✓ traffic light | ✓ traffic lights | ✓ traffic light | ✓ traffic light |
| diş macunu | tamlama | toothpaste | ✓ toothpaste | ✓ toothpaste | ✓ Toothpaste | ✓ toothpaste | ✓ toothpaste | ✓ toothpaste | ✓ toothpaste |
| kırmızı araba | sifat | red car | ✓ red car | ✓ red car | ✓ red car | ✓ red car | ✓ Red car | ✓ red car | ✓ red car |
| mavi şişe | sifat | blue bottle | ✓ blue bottle | ✓ blue bottle | ✓ Blue Bottle | ✓ blue bottle | ✓ Blue bottle | ✓ blue bottle | ✓ blue bottle |
| siyah çanta | sifat | black bag | ✓ Black bag | ✓ black bag | ✓ Black Bag | ✓ black bag | + It 's a black bag . | ✓ black bag | ✓ black bag |
| beyaz bardak | sifat | white cup / white glass / white mug | ✓ white glass | ✓ white glass | ✓ White Cup | ✓ white glass | ✓ white glass | ✓ white glass | ✓ white cup |
| ahşap sandalye | sifat | wooden chair | ✗ wood chair | ✓ wooden chair | ✗ Wood Chair | ✓ wooden chair | ✓ wooden chair | ✓ wooden chair | ✓ wooden chair |
| plastik kutu | sifat | plastic box / plastic container | ✓ plastic box | ✓ plastic box | ✓ Plastic Box | ✓ plastic box | ✓ plastic box | ✓ plastic box | ✓ plastic box |
| küçük kutu | sifat | small box | ✓ small box | ✓ small box | ✓ Small Box | ✗ little box | ✓ small box | ✗ little box | ✓ small box |
| sarı kask | sifat | yellow helmet / yellow hard hat | ✓ yellow helmet | ✓ yellow helmet | ✓ Yellow Helmet | ✓ yellow helmet | ✓ yellow helmet | ✓ yellow helmet | ✓ yellow helmet |
| baret | yeni | hard hat / helmet / safety helmet | ✓ helmet | ✓ helmet | ✗ Baret | ✗ barnet | ✗ Barrett | ✗ plenty | ✓ helmet |
| koli | yeni | box / cardboard box / parcel | ✓ box | ✓ box | ✗ coli | ✗ coli | ✗ - What is this? | ✗ hook | ✓ box |
| palet | yeni | pallet | ✗ palette | ✗ palette | ✓ Pallet | ✗ palette | ✗ Palette | ✓ pallet | ✗ palette |
| forklift | yeni | forklift | ✓ forklift | ✓ forklift | ✓ forklift | ✓ forklift | ✓ Forklift | ✓ forklift | ✓ forklift |
| transpalet | yeni | pallet jack / pallet truck | ✗ transpalet | ✗ transpalet | ✗ Transpalet | ✗ transpalette | ✗ the transpalet | ✗ transpalet | ✗ transpalet |
| yangın söndürücü | yeni | fire extinguisher | ✓ fire extinguisher | ✓ fire extinguisher | ✓ Fire Extinguisher | ✓ fire extinguisher | ✓ fire extinguisher | ✓ fire extinguisher | ✓ fire extinguisher |
| reflektif yelek | yeni | reflective vest / safety vest / high-visibility vest | ✗ Reflexive vest | ✓ reflective vest | ✓ Reflective Vest | ✓ reflective vest | ✓ reflective vest | ✓ reflective vest | ✗ Reflexive vest |
| yelek | yeni | vest | ✓ The vest. | ✓ vest | ✓ Vest | ✓ vest | ✓ the vest | ✓ vest | ✓ The vest. |
| matkap | yeni | drill | ✓ drill | ✓ drill | ✓ Drill | ✓ drill | ✗ the matkap | ✗ print | ✓ drill |
| tornavida | yeni | screwdriver | ✓ Screwdriver. | ✓ screwdriver | ✓ Screwdriver | ✓ screwdriver | + in the screwdriver | + in the screwdriver | ✓ Screwdriver. |
| çekiç | yeni | hammer | ✓ Hammer | ✓ hammer | ✓ Hammer | ✓ hammer | ✓ the hammer | ✓ hammer | ✓ Hammer |
| pense | yeni | pliers | ✓ pliers | ✓ pliers | ✓ Pliers | ✓ pliers | ✗ On the pencil | ✗ pencil | ✓ pliers |
| anahtar takımı | yeni | wrench set / spanner set / tool set | ✗ key set | ✗ key set | ✗ Key Set | ✗ key set | ✗ Key team | ✗ keypad | ✗ key set |
| el feneri | yeni | flashlight / torch | ✓ flashlight | ✓ flashlight | ✓ Flashlight | ✓ flashlight | ✗ hand lights | ✓ flashlight | ✓ flashlight |
| priz | yeni | socket / outlet / power outlet | ✓ socket | ✓ outlet | ✓ Plug | ✓ plug | ✓ The plug | ✓ plug | ✓ socket |
| merdiven | yeni | ladder / stairs / staircase | ✓ ladder | ✓ ladder | ✓ ladder | ✓ ladder | ✓ The stairs | ✓ staircase | ✓ ladder |
| el arabası | yeni | wheelbarrow | ✗ handcart | ✓ wheelbarrow | ✗ Handheld Trolley | ✓ wheelbarrow | ✗ hand car | ✗ handcart | ✗ handcart |
| trafik konisi | yeni | traffic cone / cone | ✓ traffic cone | ✓ traffic cone | ✓ Traffic Cone | ✓ traffic cone | ✓ traffic cones | ✗ traffic light | ✓ traffic cone |
| güvenlik kamerası | yeni | security camera / surveillance camera / cctv camera | ✓ Security camera | ✓ security camera | ✓ Security Camera | ✓ security camera | ✓ Security camera | ✓ security camera | ✓ Security camera |
| ütü | yeni | iron | ✓ iron | ✓ iron | ✗ Ibis Hotel | ✗ ironing | ✓ iron | ✓ iron | ✓ iron |
| süpürge | yeni | broom / vacuum cleaner / vacuum | ✓ broom | ✓ broom | ✓ Vacuum Cleaner | ✓ broom | ✗ wiping | ✓ broom | ✓ broom |
| paspas | yeni | mop / doormat / mat | ✓ mop | ✓ mop | ✓ mop | ✓ mop | ✗ Paspas | ✗ passport | ✓ mop |
| kürek | yeni | shovel / spade / oar | ✓ shovel | ✓ shovel | ✗ Rowing | ✓ shovel | ✓ Shovel | ✓ shovel | ✓ shovel |
| musluk | yeni | faucet / tap | ✓ tap | ✓ tap | ✓ Tap | ✓ tap | ✓ The faucet | ✓ faucet | ✓ tap |
| kapı kolu | yeni | door handle / doorknob / door knob | ✓ door handle | ✓ doorknob | ✓ Door Handle | ✓ door handle | ✗ hand of the door | ✗ door hand | ✓ door handle |
| etiket | yeni | label / tag / sticker | ✓ label | ✓ tag | ✓ label | ✓ label | ✓ label | ✓ label | ✓ label |
| barkod | yeni | barcode | ✓ barcode | ✗ bar code | ✓ Barcode | ✓ barcode | ✓ Barcode | ✓ barcode | ✓ barcode |
| kasa | yeni | crate / cash register / safe | ✓ Safe | ✓ safe | + Safe deposit box | ✓ safe | ✓ The box | ✗ drawer | ✓ Safe |
| raf | yeni | shelf / shelves / rack | ✓ shelf | ✓ shelf | ✓ Shelf | ✓ shelf | ✓ Shelf | ✓ shelf | ✓ shelf |
| konteyner | yeni | container | ✓ Container | ✓ container | ✓ Container | ✓ container | ✓ Container | ✓ container | ✓ Container |
| bidon | yeni | jerrycan / canister / drum | ✓ Cans | ✓ can | ✗ Bidon | ✓ can | ✗ the bidon | ✗ bucket | ✓ Cans |
| hortum | yeni | hose | ✓ hose | ✓ hose | ✓ Hose | ✓ hose | ✓ the hose | ✓ hose | ✓ hose |
| halat | yeni | rope | ✓ Rope | ✓ rope | ✓ Rope | ✓ rope | ✗ The link | ✗ hose | ✓ Rope |
| zincir | yeni | chain | ✓ chain | ✓ chain | ✓ Chain | ✓ chain | ✓ the chain | ✓ chain | ✓ chain |
| vida | yeni | screw | ✓ screw | ✓ screw | ✓ Screw | ✓ screw | ✗ The viewfinder | ✓ screw | ✓ screw |
| çivi | yeni | nail | ✓ nail | ✓ nail | ✓ Nail | ✓ nail | ✓ Nail | ✓ nail | ✓ nail |
| kilit | yeni | lock / padlock | ✓ lock | ✓ lock | ✓ Lock | ✓ lock | ✓ The lock | ✓ lock | ✓ lock |
| asma kilit | yeni | padlock | ✓ padlock | ✓ padlock | ✓ Padlock | ✓ padlock | ✗ Suspension lock | ✗ hanging lock | ✓ padlock |
| tel | yeni | wire | ✗ string | ✓ wire | ✓ Wire | ✓ wire | ✓ Wire | ✓ wire | ✗ string |
| ampul | yeni | light bulb / bulb / lightbulb | ✓ light bulb | ✓ light bulb | ✓ Bulb | ✓ light bulb | ✓ The light bulb | ✓ light bulb | ✓ light bulb |
| pil | yeni | battery / batteries | ✓ battery | ✓ battery | ✓ Battery | ✓ battery | ✓ Battery | ✓ battery | ✓ battery |
| şarj kablosu | yeni | charging cable / charger cable / charge cable | ✓ Charge cable | ✗ charge cord | ✓ Charging Cable | ✓ charging cable | ✓ charging cable | ✓ charging cable | ✓ Charge cable |
| uzatma kablosu | tamlama | extension cord / extension cable / power strip | ✓ extension cord | ✓ extension cord | ✓ Extension Cable | ✓ extension cable | ✓ extension cable | ✗ transmission cable | ✓ power strip |
| kask | tek | helmet / hard hat | ✓ helmet | ✓ helmet | ✓ Helmet | ✓ helmet | ✓ The helmet | ✓ helmet | ✓ helmet |
| emniyet kemeri | yeni | seat belt / seatbelt / safety belt | ✓ seatbelt | ✓ seat belt | ✓ Seat Belt | ✓ seatbelt | ✓ The safety belt | ✓ seat belt | ✓ seatbelt |
| sırt çantalı adam | yeni | man with a backpack / man with backpack | ✗ The guy with the backpack. | ✗ guy in a backpack | ✗ The guy with the backpack | ✗ guy in a backpack | ✗ The man with the backpack. | ✓ man with a backpack | ✗ The guy with the backpack. |
| bıçaklı adam | yeni | man with a knife / man with knife | ✗ The man with the knife. | ✗ guy with a knife | ✓ Man with a knife | ✓ man with a knife | ✗ The man with the knife | ✓ man with a knife | ✗ The man with the knife. |
| silah | yeni | gun / weapon / firearm | ✓ gun | ✓ gun | ✓ Gun | ✓ gun | ✓ The gun. | ✓ gun | ✓ gun |
| tabanca | yeni | pistol / gun / handgun | ✓ Gun | ✓ gun | ✓ Gun | ✓ gun | ✓ The gun | ✓ gun | ✓ Gun |
| duman | yeni | smoke | ✓ smoke | ✓ smoke | ✓ Smoke | ✓ smoke | ✓ The smoke | ✓ smoke | ✓ smoke |
| alev | yeni | flame / fire / flames | ✓ Fire | ✓ fire | ✓ Flame | ✓ flame | ✓ The flame | ✓ flame | ✓ Fire |
| yangın | yeni | fire | ✓ fire | ✓ fire | ✓ Fire | ✓ fire | ✓ The fire | ✓ fire | ✓ fire |
| alkollü içecek | yeni | alcoholic beverage / alcoholic drink / alcohol | ✓ Alcoholic beverage | ✓ alcohol | ✓ alcoholic beverage | ✓ alcoholic beverage | ✓ alcoholic beverages | ✓ alcoholic beverage | ✓ Alcoholic beverage |
| gazlı içecek | tamlama | soda / soft drink / carbonated drink | ✗ Gatorade | ✓ soda | ✓ Carbonated Drink | ✓ soda | ✗ Gas-filled drinks | ✓ soda | ✓ soda |
| konserve kutusu | yeni | can / tin / canned food | ✓ Can | ✓ can | ✗ Canned Box | ✗ canister | ✗ canned box | ✓ can | + can box |
| ilaç | tek | medicine / medication / drug | ✓ medicine | ✓ medicine | ✓ Medicine | ✓ medicine | ✓ medication | ✓ medicine | ✓ medicine |
| bebek bezi | yeni | diaper / nappy / diapers | ✓ Diapers | ✓ diaper | + Baby Diaper | ✓ diaper | ✗ Baby wipes | ✓ diaper | ✓ Diapers |
| şampuan | tek | shampoo / shampoo bottle | + It's shampoo. | ✓ shampoo | ✓ shampoo | ✓ shampoo | ✓ shampoo | ✓ shampoo | ✓ shampoo bottle |
| sabun | tek | soap | ✓ soap | ✓ soap | ✓ Soap | ✓ soap | ✓ Soap | ✓ soap | ✓ soap |
| diş ipi | yeni | dental floss / floss | ✓ floss | ✓ floss | ✓ Dental floss | ✓ dental floss | ✗ toothpick | ✗ toothpick | ✓ floss |
| oyuncak | yeni | toy | ✓ toy | ✓ toy | ✓ Toy | ✓ toy | ✓ The toy | ✓ toy | ✓ toy |
| oyuncak araba | yeni | toy car | ✓ Toy car | ✓ toy car | ✓ Toy Car | ✓ toy car | ✓ Toy car | ✓ toy car | ✓ Toy car |
| kumbara | yeni | piggy bank / money box | ✓ The piggy bank | ✓ piggy bank | ✗ Kumbara | ✓ piggy bank | ✗ shrimp | ✗ bumber | ✓ The piggy bank |
