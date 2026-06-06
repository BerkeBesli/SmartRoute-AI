# 🏭 SmartRoute AI — Sipariş Toplama Rota Optimizasyonu

> **Miuul AI Data Scientist Bootcamp — 20. Dönem Bitirme Projesi**

ABC Arı Kolonisi Algoritması + Apriori Birliktelik Kuralları ile depo sipariş toplama rotalarını optimize eden uçtan uca AI sistemi.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-API-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![Algorithm](https://img.shields.io/badge/ABC-Karaboğa%202005-green?style=flat-square)](https://abc.erciyes.edu.tr)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## 📊 Sonuçlar

| Metrik | Değer |
|--------|-------|
| Stok Yerleşim Kazanımı | **↓%78.7** (1.131m → 241m) |
| ABC vs Greedy Rota İyileşmesi | **↓%8.96** ortalama |
| Maksimum Rota İyileşmesi | **↓%45.45** |
| Apriori Birliktelik Kuralı | **3.561** (max lift: 85.81) |
| Random Forest R² | **0.7958** (5-Fold CV) |
| En İyi Storage Policy | **Hybrid ↓%18.1** |
| Tahmini Yıllık İşçilik Tasarrufu | **~578K TL** |

---

## 🏗️ Proje Mimarisi

```
warehouse_optimization/
├── backend/
│   ├── app.py                          # Flask REST API
│   ├── data_loader.py                  # CSV veri yükleme & işleme
│   ├── optimizer.py                    # ABC Arı Kolonisi algoritması
│   └── report_generator.py            # PDF rapor üretici
├── data/                               # 9 CSV veri seti (PMC12269467)
│   ├── Customer_Order.csv             # 122.370 sipariş satırı
│   ├── Picking_Wave.csv               # 215.192 wave kaydı
│   ├── Storage_Location.csv           # 2.292 raf lokasyonu
│   ├── Product.csv                    # 208 ürün
│   └── Support_Points_Navigation.csv  # 44 LC koridor noktası
├── frontend/
│   ├── index.html                     # Web arayüzü
│   ├── style.css                      # GitHub Dark tema
│   └── app.js                         # Chart.js dashboard
├── outputs/
│   └── association_rules.csv          # Apriori çıktısı (pipeline sonrası)
├── src/
│   └── warehouse_optimization_full.py # Ana pipeline (8 Faz)
├── n8n_warehouse_workflow.json         # n8n otomasyon workflow
├── start.bat                           # Windows başlatma scripti
└── KURULUM.md                         # Detaylı kurulum rehberi
```

---

## 🔬 Metodoloji — 8 Faz Pipeline

### Faz 1 — EDA & Veri Ön İşleme
- 122.370 sipariş, 9.707 wave analizi
- Outlier tespiti (baskılama yok — gerçek operasyonel değerler)
- Saatlik yoğunluk, skewness analizi (2.46)

### Faz 2 — Feature Engineering
- `Dalga_Yogunlugu` = total_items / unique_products
- `Loc_Verimlilik` = unique_products / unique_locations
- `nearest_lc` — Min. Öklid mesafesiyle LC ataması
- Wave bazında toplam mesafe hesabı

### Faz 3 — ABC Analizi & Stok Yerleşimi
- Pareto bazlı A/B/C sınıflandırması (%80/%95 kümülatif)
- IO noktası (LC-01: 66, -29, 1) bazlı Manhattan mesafesi
- Makale ABCCOD uyum oranı: %57.2 → **Veri bazlı ABC kullanıldı**
- **Kazanım: 1.131m → 241m (↓%78.7)**

### Faz 4 — Apriori Birliktelik Kuralları
```
min_support    = 0.004
min_confidence = 0.10
min_lift       = 1.2
```
- 3.561 kural, max lift: **85.81** (F7LULH ↔ B24J86)
- Güçlü kural (Lift ≥ 3): 800+

### Faz 5 — Özgün Algoritma: Apriori + ABC (⭐ Projenin Kalbi)
```
Apriori Güçlü Kurallar (Lift≥3)
        ↓
Union-Find Proximity Cluster
        ↓
Centroid → IO Mesafe Sıralaması (Guided Seed)
        ↓
ABC Arı Kolonisi Optimizasyonu (Karaboğa 2005)
```
- Greedy'ye kıyasla **ortalama ↓%8.96**, maksimum **↓%45.45**
- 8.778 wave'in %62.3'ünde ABC > Greedy

### Faz 6 — Hiperparametre Optimizasyonu
| Yöntem | Deneme | Süre | Best Dist |
|--------|--------|------|-----------|
| Grid Search | 27 | ~42s | 1.014m |
| ABC-HP (Karaboğa Orijinal) | 600 | ~38s | 1.011m |

`x_new = x_i + phi*(x_i - x_k)` — Karaboğa (2005) sürekli uzay formülü

### Faz 7 — ML Modeli (Random Forest)
- **Hedef:** `abc_optimized_distance` (Apriori+ABC çıktısı)
- **Features:** total_items, unique_locations, unique_lc, unique_products, Dalga_Yogunlugu
- **En önemli feature:** unique_lc (%93.4)
- **R² = 0.7958** | MAE = 184.83m (5-Fold CV)

### Faz 8 — Storage Policy Karşılaştırması
| Strateji | Greedy | Apriori+ABC | Kazanım |
|----------|--------|-------------|---------|
| Mevcut | 1.270m | 1.116m | ↓%12.1 |
| Dedicated | 1.605m | 1.361m | ↓%15.2 |
| **Hybrid** | **1.820m** | **1.491m** | **↓%18.1** |
| Random | 2.072m | 1.793m | ↓%13.5 |
| Class-Based | 2.082m | 1.822m | ↓%12.5 |

---

## 🚀 Kurulum & Çalıştırma

### Gereksinimler
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) paket yöneticisi

```bash
pip install uv
```

### 1. Bağımlılıkları Kur
```bash
cd warehouse_optimization
uv add flask flask-cors reportlab matplotlib numpy scikit-learn mlxtend scipy seaborn
```

### 2. Ana Pipeline'ı Çalıştır (İlk Seferde Zorunlu)
```bash
uv run src/warehouse_optimization_full.py
```
Bu komut `outputs/` klasörünü oluşturur:
- `association_rules.csv` — Apriori kuralları
- `rf_model.pkl` — Random Forest modeli
- `optimal_params.json` — En iyi hiperparametreler
- `faz1_eda.png` ... `faz8_storage_policy.png`

> ⏱️ Süre: ~10-20 dakika

### 3. Uygulamayı Başlat
```bash
# Windows
start.bat

# Manuel
uv run python backend/app.py
```

### 4. Web Arayüzü
`frontend/index.html` dosyasını tarayıcıda aç.

---

## 🖥️ Web Dashboard — 5 Sekme

| Sekme | İçerik |
|-------|--------|
| **Dashboard** | KPI kartları, ABC pasta grafik, wave mesafe dağılımı |
| **Ürün Yerleşim** | ABC Pareto sınıflandırma, IO mesafe sıralaması |
| **Rota Optimizasyonu** | ABC yakınsama eğrisi, SVG depo haritası |
| **Apriori Kuralları** | Top 20 birliktelik kuralı (max lift: 85.81) |
| **Wave Sorgula** | Gerçek wave verisi + ABC optimize (33168-43175) |

---

## ⚡ n8n Otomasyon Workflow

```
Yeni Wave Bildirimi (Webhook)
        ↓
Flask API → Apriori + ABC Optimizasyon
        ↓
RF Modeli → Mesafe Tahmini + Anomali Tespiti (>%30 sapma)
        ↓
Gemini AI → Türkçe Rota Açıklaması
        ↓
Slack Bildirimi (>%5 iyileşmede)
```

**Test:**
```bash
curl -X POST http://localhost:5678/webhook/warehouse-new-wave \
  -H "Content-Type: application/json" \
  -d "{\"wave_id\": \"33293\"}"
```

---

## 🛠️ Teknoloji Stack

**Backend:** Python · Flask · Flask-CORS  
**ML/AI:** scikit-learn · mlxtend · Random Forest · Apriori  
**Algoritma:** ABC Arı Kolonisi (Karaboğa 2005) · abc.erciyes.edu.tr  
**Otomasyon:** n8n · Gemini API · Slack  
**Frontend:** HTML5 · CSS3 · JavaScript · Chart.js  
**Rapor:** ReportLab  
**Paket Yönetimi:** uv  

---

## 📚 Kaynak

> Karaboga, D. (2005). *An idea based on honey bee swarm for numerical optimization*. Technical Report TR06, Erciyes University, Engineering Faculty, Computer Engineering Department.  
> 🔗 [abc.erciyes.edu.tr](https://abc.erciyes.edu.tr)
**Veri Seti:** PMC12269467 — Gerçek Ayakkabı Fabrikası Deposu

---

## 👥 Ekip

| İsim |
|------|
| Berke Beşli |
| Muhammet Necati Çetinkaya |
| Ali Orhan |
| Gökay Bıçkıcı |
| Muhammet Safa Tekin |

---

## 📄 Lisans

MIT License — Detaylar için [LICENSE](LICENSE) dosyasına bakın.
