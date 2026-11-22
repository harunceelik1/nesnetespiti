# Göreli filtre · RPC test kümesi (60 görsel, sorgu "product", Dengeli eşik üstüne)

Toplam ürün kutusu: 626 (görsel başına ort. 10.4). Oranlar LVIS'te seçildi, burada yalnızca kontrol edildi.

| Model | Oran | Doğru | Yanlış kutu | Kaçırılan | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| OWLv2 | filtresiz | 531 | 103 | 95 | 0.84 | 0.85 | 0.84 |
| OWLv2 | 0.3 | 512 | 91 | 114 | 0.85 | 0.82 | 0.83 |
| OWLv2 | 0.4 | 474 | 63 | 152 | 0.88 | 0.76 | 0.82 |
| OWLv2 | 0.5 | 414 | 39 | 212 | 0.91 | 0.66 | 0.77 |
| OWLv2 | 0.6 | 333 | 22 | 293 | 0.94 | 0.53 | 0.68 |
| OWLv2 | (Sıkı eşik 0.17) | 475 | 70 | 151 | 0.87 | 0.76 | 0.81 |
| YOLO-World | filtresiz | 0 | 0 | 626 | 0.00 | 0.00 | 0.00 |
| YOLO-World | 0.3 | 0 | 0 | 626 | 0.00 | 0.00 | 0.00 |
| YOLO-World | 0.4 | 0 | 0 | 626 | 0.00 | 0.00 | 0.00 |
| YOLO-World | 0.5 | 0 | 0 | 626 | 0.00 | 0.00 | 0.00 |
| YOLO-World | 0.6 | 0 | 0 | 626 | 0.00 | 0.00 | 0.00 |
| YOLO-World | (Sıkı eşik 0.25) | 0 | 0 | 626 | 0.00 | 0.00 | 0.00 |
