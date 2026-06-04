"""
app.py - SmartRouteAI Flask API
ABC Ari Kolonisi (Karaboga 2005) - abc.erciyes.edu.tr
"""
import os, csv, math, tempfile, pickle
import numpy as np
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from data_loader import DataLoader
from optimizer import WarehouseOptimizer
from report_generator import generate_pdf

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'data'))
OUT_DIR  = os.path.abspath(os.path.join(BASE_DIR, '..', 'outputs'))

# ── Veri Yukle ────────────────────────────────────────────────────
try:
    loader = DataLoader(DATA_DIR)
    optimizer = WarehouseOptimizer(
        lc_coords=loader.lc_coords,
        storage_map={r['originalLocation']: {
            'x': float(r['x']), 'y': float(r['y']), 'z': float(r['z'])}
            for r in loader.storage if r.get('x') and r.get('y') and r.get('z')}
    )
    data_loaded = True
    print(f"[✓] Veri yüklendi: {len(loader.orders):,} sipariş, {len(loader.waves):,} wave satırı")
    print(f"[✓] LC noktaları : {len(loader.lc_coords)}")
    print(f"[✓] Raf lokasyonu: {len(loader.storage)}")
except Exception as e:
    loader = optimizer = None
    data_loaded = False
    print(f"[✗] Veri yüklenemedi: {e}")

# ── Apriori Cache ─────────────────────────────────────────────────
apriori_rules_cache = []
try:
    rules_path = os.path.join(OUT_DIR, 'association_rules.csv')
    with open(rules_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            reader.fieldnames = [x.strip() for x in reader.fieldnames]
        apriori_rules_cache = list(reader)
    print(f"[✓] Apriori kuralları: {len(apriori_rules_cache):,} kural yüklendi")
except Exception as e:
    print(f"[!] Apriori kuralları yüklenemedi: {e}")

# ── RF Model ──────────────────────────────────────────────────────
rf_model = None
try:
    with open(os.path.join(OUT_DIR, 'rf_model.pkl'), 'rb') as f:
        rf_model = pickle.load(f)
    print(f"[✓] RF modeli yüklendi")
except Exception:
    print(f"[!] RF modeli bulunamadı")


def err(msg, code=500):
    return jsonify({'error': msg}), code


# ════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'data_loaded': data_loaded,
                    'algorithm': 'ABC Ari Kolonisi - Karaboga (2005)'})


@app.route('/api/analytics')
def analytics():
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        return jsonify(loader.get_summary())
    except Exception as e:
        return err(str(e))


@app.route('/api/strategy-comparison')
def strategy_comparison():
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        return jsonify(loader.get_strategy_comparison())
    except Exception as e:
        return err(str(e))


@app.route('/api/wave-samples')
def wave_samples():
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        data = loader.get_wave_samples()
        return jsonify(data if isinstance(data, list) else [])
    except Exception as e:
        return err(str(e))


@app.route('/api/abc-classification')
def abc_classification():
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        data = loader.get_abc_classification()
        summary = {'A': sum(1 for r in data if r['ABC']=='A'),
                   'B': sum(1 for r in data if r['ABC']=='B'),
                   'C': sum(1 for r in data if r['ABC']=='C')}
        return jsonify({'classification': data[:50], 'summary': summary, 'total': len(data)})
    except Exception as e:
        return err(str(e))


@app.route('/api/apriori-rules')
def apriori_rules():
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        top_n = int(request.args.get('top', 20))
        return jsonify(loader.get_apriori_rules(top_n=top_n))
    except Exception as e:
        return err(str(e))


@app.route('/api/wave/<wave_id>')
def wave_detail(wave_id):
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        detail = loader.get_wave_detail(wave_id)
        if not detail:
            return err(f'Wave {wave_id} bulunamadı. Geçerli aralık: 33168 - 43175', 404)
        return jsonify(detail)
    except Exception as e:
        return err(str(e))


@app.route('/api/optimize-wave/<wave_id>', methods=['GET','POST'])
def optimize_wave(wave_id):
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        body = request.get_json(silent=True) or {}
        colony_size = body.get('colony_size', 20)
        max_cycles  = body.get('max_cycles', 150)

        detail = loader.get_wave_detail(wave_id)
        if not detail:
            return err(f'Wave {wave_id} bulunamadı', 404)

        lc_list, lc_prod_map = [], {}
        for p in detail['products']:
            lc = p.get('nearest_lc')
            if lc and lc in loader.lc_coords:
                if lc not in lc_list:
                    lc_list.append(lc)
                lc_prod_map[lc] = p['reference']

        if not lc_list:
            return err('Bu wave için LC koordinatı bulunamadı', 400)

        result = optimizer.abc_optimize(lc_list, colony_size=colony_size,
                                        max_cycles=max_cycles, guided_seed=lc_list)

        route_steps, cum_dist = [], 0.0
        for i, lc in enumerate(result['best_route']):
            c = loader.lc_coords.get(lc, {})
            prev = result['best_route'][i-1] if i > 0 else None
            step_d = optimizer._lc_dist(prev, lc) if prev else 0.0
            cum_dist += step_d
            route_steps.append({
                'order': i+1, 'product': lc_prod_map.get(lc, lc), 'lc': lc,
                'coords': [c.get('x_nav', 0), c.get('y_nav', 0)],
                'step_distance': round(step_d, 1),
                'cumulative_distance': round(cum_dist, 1),
                'zone_color': '#58a6ff', 'zone_label': lc,
            })

        return jsonify({
            'wave_id': wave_id, 'route': route_steps,
            'total_distance': result['best_dist'],
            'greedy_distance': result['greedy_dist'],
            'improvement_pct': result['improvement'],
            'product_count': len(lc_list),
            'algorithm': 'ABC Ari Kolonisi - Karaboga (2005)',
            'convergence': result['history'],
            'time_sec': result['time_sec'],
        })
    except Exception as e:
        return err(str(e))


@app.route('/api/optimize-placement', methods=['POST'])
def optimize_placement():
    if not data_loaded: return err('Veri yüklenemedi')
    body = request.get_json(silent=True) or {}
    products = body.get('products', [])
    if not products: return err('En az bir ürün girin', 400)
    try:
        abc_data = loader.get_abc_classification()
        return jsonify(optimizer.place_products(products, abc_data))
    except Exception as e:
        return err(str(e))


@app.route('/api/optimize-route', methods=['POST'])
def optimize_route():
    if not data_loaded: return err('Veri yüklenemedi')
    body = request.get_json(silent=True) or {}
    products = body.get('products', [])
    if not products: return err('En az bir ürün girin', 400)
    try:
        return jsonify(optimizer.optimize_route(products))
    except Exception as e:
        return err(str(e))


@app.route('/api/report')
def generate_report():
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.close()
        generate_pdf(loader, tmp.name)
        return send_file(tmp.name, as_attachment=True,
                         download_name='depo_optimizasyon_raporu.pdf',
                         mimetype='application/pdf')
    except Exception as e:
        return err(f'PDF olusturulamadi: {str(e)}')


@app.route('/webhook/new-wave', methods=['POST'])
def webhook_new_wave():
    body = request.get_json(silent=True) or {}
    wave_id = str(body.get('wave_id', '')).strip()
    if not wave_id: return err('wave_id gerekli', 400)
    if not data_loaded: return err('Veri yüklenemedi')
    try:
        detail = loader.get_wave_detail(wave_id)
        if not detail: return err(f'Wave {wave_id} bulunamadı', 404)

        lc_list, lc_map, prod_loc_map = [], {}, {}
        for p in detail['products']:
            lc  = p.get('nearest_lc')
            ref = p.get('reference', '')
            if lc and lc in loader.lc_coords:
                if lc not in lc_list: lc_list.append(lc)
                lc_map[lc] = ref
                prod_loc_map[ref] = {'x': p.get('x',0) or 0, 'y': p.get('y',0) or 0}

        if not lc_list: return err('LC bulunamadı', 400)

        if apriori_rules_cache:
            guided_seed = optimizer.build_apriori_guided_seed(
                lc_list, apriori_rules_cache, lc_map, prod_loc_map)
            algo_name = 'Apriori + ABC Ari Kolonisi (Karaboga 2005)'
        else:
            guided_seed = lc_list
            algo_name = 'ABC Ari Kolonisi (Karaboga 2005)'

        result = optimizer.abc_optimize(lc_list, guided_seed=guided_seed)
        best_dist = result['best_dist']
        greedy_dist = result['greedy_dist']
        improvement = result['improvement']
        route_text = ' -> '.join(lc_map.get(lc, lc) for lc in result['best_route'])

        rf_prediction, anomaly, anomaly_msg = None, False, ''
        if rf_model is not None:
            try:
                n_products  = detail['n_products']
                n_locations = detail['n_locations']
                n_lc        = len(set(lc_list))
                total_items = sum(int(p.get('qty', 1) or 1) for p in detail['products'])
                dalga_yog   = total_items / max(n_products, 1)
                X = np.array([[total_items, n_locations, n_lc, n_products, dalga_yog]])
                rf_prediction = float(rf_model.predict(X)[0])
                if rf_prediction > 0:
                    sapma = abs(best_dist - rf_prediction) / rf_prediction * 100
                    if sapma > 30:
                        anomaly = True
                        anomaly_msg = f"Anomali: Gercek {best_dist:.0f}m, Tahmin {rf_prediction:.0f}m, Sapma %{sapma:.1f}"
            except Exception:
                pass

        summary_text = (
            f"Wave {wave_id} icin {detail['n_products']} urun optimize edildi. "
            f"Toplam mesafe: {best_dist:.0f}m (Greedy'den %{improvement:.1f} kisa). "
            f"Rota: {route_text}."
        )

        return jsonify({
            'wave_id': wave_id, 'optimal_route': route_text,
            'total_distance': round(best_dist, 1), 'greedy_distance': round(greedy_dist, 1),
            'improvement': round(improvement, 2), 'n_products': detail['n_products'],
            'algorithm': algo_name, 'apriori_used': len(apriori_rules_cache) > 0,
            'rf_prediction': round(rf_prediction, 1) if rf_prediction else None,
            'anomaly': anomaly, 'anomaly_message': anomaly_msg,
            'summary_for_ai': summary_text,
        })
    except Exception as e:
        return err(str(e))


if __name__ == '__main__':
    print("=" * 55)
    print("  Warehouse Optimizer API - ABC Ari Kolonisi")
    print("  http://localhost:5000")
    print("=" * 55)
    app.run(debug=False, port=5000, host='0.0.0.0')