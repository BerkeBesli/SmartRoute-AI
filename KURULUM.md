# Siparis Toplama Rota Optimizasyonu
## Miuul AI Data Scientist Bootcamp — 20. Donem Bitirme Projesi

**Takim:**  Berke Besli | Gokay Bickici | Muhammet Safa Tekin | M. Necati Cetinkaya | Ali Orhan |
**Algoritma:** ABC Ari Kolonisi (Karaboga 2005) — abc.erciyes.edu.tr  
**Veri:** PMC12269467 — Ayakkabi Fabrikasi Deposu

---

## Proje Yapisi

```
warehouse_optimization/
├── backend/
│   ├── app.py                  ← Flask API
│   ├── data_loader.py          ← Veri yukleme
│   ├── optimizer.py            ← ABC algoritma
│   ├── report_generator.py     ← PDF rapor
│   └── requirements.txt
├── data/                       ← 9 CSV dosyasi (degistirme)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── outputs/                    ← Pipeline ciktilari (Step 1 ile olusur)
├── src/
│   └── warehouse_optimization_full.py  ← Ana pipeline
├── n8n_warehouse_workflow.json
└── start.bat
```

---

## Kurulum

### Gereksinimler
- Python 3.10+
- Node.js LTS (n8n icin): https://nodejs.org
- uv paket yoneticisi: `pip install uv`

### Paketleri Kur

```bash
cd warehouse_optimization
uv add flask flask-cors reportlab matplotlib numpy scikit-learn mlxtend scipy seaborn
```

Veya pip ile:
```bash
pip install flask flask-cors reportlab matplotlib numpy scikit-learn mlxtend scipy seaborn
```

---

## Calistirma

### Adim 1 — Ana Pipeline (ilk seferde zorunlu)

```bash
uv run src/warehouse_optimization_full.py
```

Bu komut `outputs/` klasorunu doldurur:
- `association_rules.csv` — Apriori kurallari
- `proximity_pairs.csv`
- `optimal_params.json`
- `rf_model.pkl` — Random Forest modeli (Flask API kullanir)
- `faz1_eda.png` ... `faz8_storage_policy.png`

> Süre: ~10-20 dakika (Faz 5 tüm wave'leri optimize eder)

### Adim 2 — start.bat ile Basla

```
start.bat dosyasina cift tikla
```

Bu dosya:
1. Flask API'yi baslatir → http://localhost:5000
2. Web arayuzunu acar → frontend/index.html

### Adim 3 — Web Arayuzu

Tarayicide `frontend/index.html` dosyasini ac.

**5 sekme:**
- **Dashboard** — KPI'lar, ABC dagilimi, wave grafigi
- **Urun Yerlesim** — ABC Pareto siniflandirma
- **Rota Optimizasyonu** — ABC Ari Kolonisi ile rota
- **Apriori Kurallari** — Top 20 birliktelik kurali (lift=85.81)
- **Wave Sorgula** — Gercek veri + ABC optimize

---

## API Endpoint Referansi

| Endpoint | Metod | Aciklama |
|---|---|---|
| `/api/health` | GET | Sistem durumu |
| `/api/analytics` | GET | Dashboard istatistikler |
| `/api/abc-classification` | GET | Pareto ABC siniflandirma |
| `/api/apriori-rules` | GET | Birliktelik kurallari |
| `/api/wave/<id>` | GET | Wave detayi |
| `/api/optimize-wave/<id>` | GET | ABC rota optimizasyonu |
| `/api/optimize-placement` | POST | Urun yerlesim |
| `/api/optimize-route` | POST | Manuel rota |
| `/api/report` | GET | PDF rapor indir |
| `/webhook/new-wave` | POST | n8n baglantisi |

---

## n8n Kurulumu (Opsiyonel)

```bash
npm install -g n8n
n8n start
```

1. http://localhost:5678 ac
2. **Import from file** → `n8n_warehouse_workflow.json`
3. **3. Gemini AI** node'unda API key gir: https://aistudio.google.com/apikey
4. **Activate** et

**Test:**
```bash
curl -X POST http://localhost:5678/webhook/warehouse-new-wave \
  -H "Content-Type: application/json" \
  -d "{\"wave_id\": \"33293\"}"
```

**Beklenen yanit:**
```json
{
  "wave_id": "33293",
  "algorithm": "Apriori + ABC Ari Kolonisi (Karaboga 2005)",
  "total_distance": 1847.3,
  "improvement_pct": 12.4,
  "rf_prediction": 1920.1,
  "anomaly": false,
  "ai_explanation": "Wave 33293 icin 8 urun optimize edildi..."
}
```

---

## Sonuclar

| Bulgu | Deger |
|---|---|
| Stok Yerlesim Kazanimi | Asagi %78.7 (1131m → 241m) |
| Apriori Birliktelik Kurali | 3,561 (max lift: 85.81) |
| ABC vs Greedy Iyilesme | Asagi %8.96 ortalama |
| Random Forest R² | 0.7958 (5-Fold CV) |
| En Iyi Storage Policy Kazanimi | Asagi %18.1 (Hybrid) |

**Kaynak:** D. Karaboga (2005), abc.erciyes.edu.tr  
**Veri:** PMC12269467