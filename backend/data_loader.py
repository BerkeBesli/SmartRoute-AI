"""
data_loader.py - SmartRouteAI Veri Yükleyici
"""
import csv, ast, math, os


class DataLoader:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.orders   = []
        self.waves    = []
        self.storage  = []
        self.products = []
        self.nav      = []
        self.lc_coords = {}
        self._load_all()

    def _read_csv(self, filename, delimiter=','):
        path = os.path.join(self.data_dir, filename)
        with open(path, newline='', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f, delimiter=delimiter))

    def _load_all(self):
        self.orders   = self._read_csv('Customer_Order.csv',            ';')
        self.waves    = self._read_csv('Picking_Wave.csv',              ';')
        self.storage  = self._read_csv('Storage_Location.csv',         ',')
        self.products = self._read_csv('Product.csv',                   ';')
        self.nav      = self._read_csv('Support_Points_Navigation.csv', ';')

        for r in self.waves:
            r['waveNumber'] = str(r.get('waveNumber', '')).strip()
            r['locations']  = r.get('locations', '').strip()
            r['reference']  = r.get('reference', '').strip()
        for r in self.orders:
            r['Reference'] = r.get('Reference', '').strip()
        for r in self.storage:
            r['originalLocation'] = r.get('originalLocation', '').strip()
        for r in self.products:
            r['Reference'] = r.get('Reference', '').strip()
            r['ABCCOD']    = r.get('ABCCOD', '').strip()
        for r in self.nav:
            try:
                coords = ast.literal_eval(r['points_specified'])
                self.lc_coords[r['labels']] = {
                    'x_nav': float(coords[0]),
                    'y_nav': float(coords[1]),
                }
            except Exception:
                pass

    def _storage_map(self):
        m = {}
        for r in self.storage:
            try:
                m[r['originalLocation']] = {
                    'x': float(r['x']), 'y': float(r['y']), 'z': float(r['z']),
                }
            except Exception:
                pass
        return m

    def _find_nearest_lc(self, x, y):
        best_lc, best_d = None, float('inf')
        for label, c in self.lc_coords.items():
            d = math.sqrt((c['x_nav'] - x)**2 + (c['y_nav'] - y)**2)
            if d < best_d:
                best_d, best_lc = d, label
        return best_lc

    def get_abc_classification(self):
        freq = {}
        for r in self.orders:
            ref = r.get('Reference', '').strip()
            if ref:
                freq[ref] = freq.get(ref, 0) + 1
        total = sum(freq.values()) or 1
        sorted_refs = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        result, cum = [], 0.0
        for ref, cnt in sorted_refs:
            cum += cnt / total * 100
            abc = 'A' if cum <= 80 else ('B' if cum <= 95 else 'C')
            result.append({'reference': ref, 'order_count': cnt,
                           'order_pct': round(cnt/total*100, 3),
                           'cumulative_pct': round(cum, 2), 'ABC': abc})
        return result

    def get_summary(self):
        abc_data = self.get_abc_classification()
        n_a = sum(1 for r in abc_data if r['ABC'] == 'A')
        n_b = sum(1 for r in abc_data if r['ABC'] == 'B')
        n_c = sum(1 for r in abc_data if r['ABC'] == 'C')
        IO_X, IO_Y, IO_Z = 66, -29, 1
        dists = []
        for r in self.storage:
            try:
                dists.append(abs(float(r['x'])-IO_X)+abs(float(r['y'])-IO_Y)+abs(float(r['z'])-IO_Z))
            except Exception:
                pass
        avg_dist = round(sum(dists)/len(dists), 1) if dists else 0
        unique_waves = len(set(r['waveNumber'] for r in self.waves if r['waveNumber']))
        wave_size = {}
        for r in self.waves:
            wid = r['waveNumber']
            if wid:
                wave_size.setdefault(wid, set())
                if r['reference']:
                    wave_size[wid].add(r['reference'])
        sizes = [len(v) for v in wave_size.values()]
        return {
            'total_orders':     len(self.orders),
            'unique_waves':     unique_waves,
            'unique_products':  len(set(r['Reference'] for r in self.orders if r['Reference'])),
            'operators':        len(set(r.get('operator','') for r in self.orders)),
            'abc_counts':       {'A': n_a, 'B': n_b, 'C': n_c},
            'avg_shelf_dist_m': avg_dist,
            'avg_wave_size':    round(sum(sizes)/len(sizes), 1) if sizes else 0,
            'total_locations':  len(self.storage),
            'io_point':         [IO_X, IO_Y, IO_Z],
        }

    def get_strategy_comparison(self):
        IO_X, IO_Y, IO_Z = 66, -29, 1
        dists = []
        for r in self.storage:
            try:
                dists.append(abs(float(r['x'])-IO_X)+abs(float(r['y'])-IO_Y)+abs(float(r['z'])-IO_Z))
            except Exception:
                pass
        avg_current = round(sum(dists)/len(dists), 1) if dists else 1
        abc_data = self.get_abc_classification()
        n_a = sum(1 for r in abc_data if r['ABC'] == 'A')
        n_b = sum(1 for r in abc_data if r['ABC'] == 'B')
        sorted_storage = sorted(self.storage, key=lambda r: (
            abs(float(r.get('x',0) or 0)-IO_X)+abs(float(r.get('y',0) or 0)-IO_Y)+abs(float(r.get('z',0) or 0)-IO_Z)))
        abc_dists = []
        for r in sorted_storage[:n_a+n_b]:
            try:
                abc_dists.append(abs(float(r['x'])-IO_X)+abs(float(r['y'])-IO_Y)+abs(float(r['z'])-IO_Z))
            except Exception:
                pass
        avg_abc = round(sum(abc_dists)/max(len(abc_dists),1), 1) if abc_dists else avg_current
        improve = round((avg_current - avg_abc) / avg_current * 100, 1)
        return [
            {'key':'current','name':'Mevcut Sistem','avg':avg_current,'change_pct':0,'color':'#6e7681'},
            {'key':'abc','name':'ABC Yerlesimi','avg':avg_abc,'change_pct':-improve,'improvement_pct':improve,'color':'#3fb950'},
        ]

    def get_wave_samples(self, limit=120):
        storage_map = self._storage_map()
        wave_lc = {}
        for r in self.waves[:30000]:
            wid = r.get('waveNumber', '')
            loc = r.get('locations', '').strip()
            if not wid or not loc or loc not in storage_map:
                continue
            coords = storage_map[loc]
            lc = self._find_nearest_lc(coords['x'], coords['y'])
            if lc:
                wave_lc.setdefault(wid, [])
                if lc not in wave_lc[wid]:
                    wave_lc[wid].append(lc)

        def calc_dist(lc_list):
            t = 0.0
            for i in range(len(lc_list)-1):
                p1 = self.lc_coords.get(lc_list[i], {})
                p2 = self.lc_coords.get(lc_list[i+1], {})
                if p1 and p2:
                    t += math.sqrt((p1['x_nav']-p2['x_nav'])**2+(p1['y_nav']-p2['y_nav'])**2)
            return round(t, 1)

        results = []
        for wid, lc_list in wave_lc.items():
            if len(lc_list) < 2:
                continue
            d = calc_dist(lc_list)
            if d > 0:
                results.append({'wave': str(wid), 'total': float(d), 'lc_count': int(len(lc_list))})
        if not results:
            return []
        step = max(1, len(results) // limit)
        return results[::step][:limit]

    def get_wave_detail(self, wave_id):
        wave_id = str(wave_id).strip()
        wave_rows = [r for r in self.waves if r.get('waveNumber','').strip() == wave_id]
        if not wave_rows:
            return None
        storage_map = self._storage_map()
        products_in_wave, seen = [], set()
        for r in wave_rows:
            ref = r.get('reference', '').strip()
            loc = r.get('locations', '').strip()
            key = (ref, loc)
            if key in seen:
                continue
            seen.add(key)
            coords = storage_map.get(loc, {})
            lc = self._find_nearest_lc(coords['x'], coords['y']) if coords else None
            try:
                qty = int(float(r.get('quantityToPick (units)', 1) or 1))
            except Exception:
                qty = 1
            products_in_wave.append({
                'reference': ref, 'location': loc, 'qty': qty,
                'operator': r.get('operator', '').strip(),
                'x': coords.get('x'), 'y': coords.get('y'), 'z': coords.get('z'),
                'nearest_lc': lc,
            })
        unique_refs = set(r.get('reference','').strip() for r in wave_rows if r.get('reference'))
        unique_locs = set(r.get('locations','').strip() for r in wave_rows if r.get('locations'))
        return {
            'wave_id': wave_id, 'products': products_in_wave,
            'n_products': len(unique_refs), 'n_locations': len(unique_locs),
        }

    def get_apriori_rules(self, top_n=20):
        candidates = [
            os.path.join(self.data_dir, '..', 'outputs', 'association_rules.csv'),
            os.path.join(self.data_dir, 'outputs', 'association_rules.csv'),
            os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(self.data_dir))), 'outputs', 'association_rules.csv'),
        ]
        rules_path = None
        for c in candidates:
            norm = os.path.normpath(c)
            if os.path.exists(norm):
                rules_path = norm
                break
        if not rules_path:
            print("[!] association_rules.csv bulunamadi.")
            return []
        try:
            with open(rules_path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    reader.fieldnames = [x.strip() for x in reader.fieldnames]
                rows = list(reader)
            def sf(r, *keys):
                for k in keys:
                    try:
                        v = r.get(k, '')
                        if v: return float(v)
                    except Exception:
                        pass
                return 0.0
            rows_sorted = sorted(rows, key=lambda r: sf(r,'lift','Lift'), reverse=True)[:top_n]
            return [{'antecedents': (r.get('antecedents') or r.get('Antecedents') or '').strip(),
                     'consequents': (r.get('consequents') or r.get('Consequents') or '').strip(),
                     'support':    round(sf(r,'support','Support'), 4),
                     'confidence': round(sf(r,'confidence','Confidence'), 3),
                     'lift':       round(sf(r,'lift','Lift'), 2)} for r in rows_sorted]
        except Exception as e:
            print(f"[!] Apriori okunamadi: {e}")
            return []