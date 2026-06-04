"""
optimizer.py — SmartRouteAI Backend
Ekibin, ABC + Apriori algoritmaları burada.

Karaboğa (2005) — abc.erciyes.edu.tr
"""

import math
import random
import time


class WarehouseOptimizer:
    """
    Gerçek depo koordinatları ve LC (koridor) sistemi kullanarak
    ABC Arı Algoritması ile rota optimizasyonu.
    """

    IO = (66, -29, 1)   # Giriş/Çıkış noktası (LC-01)

    # ABC Hiperparametreleri (warehouse_optimization_full.py'den)
    COLONY_SIZE = 20
    MAX_CYCLES  = 150
    LIMIT_MULT  = 1.0

    def __init__(self, lc_coords: dict, storage_map: dict):
        """
        lc_coords  : {'LC-01': {'x_nav': 66, 'y_nav': -29}, ...}
        storage_map: {'H-10-22': {'x':..., 'y':..., 'z':...}, ...}
        """
        self.lc_coords   = lc_coords
        self.storage_map = storage_map

    # ── Mesafe Fonksiyonları ──────────────────────────────────────

    def _lc_dist(self, lc1: str, lc2: str) -> float:
        p1 = self.lc_coords.get(lc1, {})
        p2 = self.lc_coords.get(lc2, {})
        if not p1 or not p2:
            return 0.0
        return math.sqrt((p1['x_nav']-p2['x_nav'])**2 +
                         (p1['y_nav']-p2['y_nav'])**2)

    def _route_dist(self, lc_list: list) -> float:
        if len(lc_list) <= 1:
            return 0.0
        total = 0.0
        for i in range(len(lc_list)-1):
            total += self._lc_dist(lc_list[i], lc_list[i+1])
        return total

    def _manhattan_to_io(self, x, y, z) -> float:
        return (abs(x - self.IO[0]) + abs(y - self.IO[1]) +
                abs(z - self.IO[2]))

    def _find_nearest_lc(self, x: float, y: float) -> str:
        best_lc, best_d = None, float('inf')
        for lbl, c in self.lc_coords.items():
            d = math.sqrt((c['x_nav']-x)**2 + (c['y_nav']-y)**2)
            if d < best_d:
                best_d, best_lc = d, lbl
        return best_lc

    # ── Greedy (En Yakın Komşu) ───────────────────────────────────

    def _greedy_route(self, lc_list: list) -> list:
        lc_list = list(dict.fromkeys(lc_list))
        if len(lc_list) <= 1:
            return lc_list
        route   = [lc_list[0]]
        rem     = lc_list[1:]
        current = lc_list[0]
        while rem:
            nearest = min(rem, key=lambda l: self._lc_dist(current, l))
            route.append(nearest)
            rem.remove(nearest)
            current = nearest
        return route

    # ── ABC Algoritması (Karaboğa 2005) ──────────────────────────

    def _two_opt(self, route: list) -> list:
        r = route[:]
        i, j = sorted(random.sample(range(len(r)), 2))
        r[i:j+1] = reversed(r[i:j+1])
        return r

    def abc_optimize(self, lc_list: list,
                     colony_size: int = None,
                     max_cycles:  int = None,
                     limit_mult: float = None,
                     guided_seed: list = None) -> dict:
        """
        ABC Algoritması ile LC permütasyonu optimizasyonu.
        Kaynak: Karaboga (2005), abc.erciyes.edu.tr

        Döndürür:
          best_dist  : float  — optimize edilmiş rota mesafesi
          best_route : list   — LC sırası
          greedy_dist: float  — greedy baseline
          improvement: float  — % iyileşme
          history    : list   — convergence
          time_sec   : float  — çalışma süresi
        """
        colony_size = colony_size or self.COLONY_SIZE
        max_cycles  = max_cycles  or self.MAX_CYCLES
        limit_mult  = limit_mult  or self.LIMIT_MULT

        lc_list = list(dict.fromkeys(lc_list))
        n       = len(lc_list)

        # Greedy baseline
        greedy_r    = self._greedy_route(lc_list)
        greedy_dist = self._route_dist(greedy_r)

        if n <= 2:
            return {
                'best_dist':   greedy_dist,
                'best_route':  greedy_r,
                'greedy_dist': greedy_dist,
                'improvement': 0.0,
                'history':     [greedy_dist],
                'time_sec':    0.0,
            }

        food_n = colony_size // 2
        limit  = max(1, int(food_n * n * limit_mult))

        def fit(r):
            d = self._route_dist(r)
            return 1.0 / d if d > 0 else 0

        # Başlatma
        foods = []
        for i in range(food_n):
            if i == 0 and guided_seed:
                g   = [x for x in guided_seed if x in lc_list]
                rem = [x for x in lc_list if x not in g]
                r   = g + rem
            else:
                r = lc_list[:]
                random.shuffle(r)
            foods.append(r)

        fits   = [fit(r) for r in foods]
        trial  = [0] * food_n
        best_r = foods[int(max(range(food_n), key=lambda i: fits[i]))][:]
        best_d = self._route_dist(best_r)
        history = [best_d]

        t0 = time.time()

        for _ in range(max_cycles):
            # Employed bees
            for i in range(food_n):
                nr = self._two_opt(foods[i])
                nf = fit(nr)
                if nf > fits[i]:
                    foods[i] = nr; fits[i] = nf; trial[i] = 0
                else:
                    trial[i] += 1

            # Onlooker bees
            total = sum(fits)
            probs = [f/total for f in fits] if total > 0 \
                    else [1/food_n]*food_n
            for _ in range(food_n):
                i  = random.choices(range(food_n), weights=probs, k=1)[0]
                nr = self._two_opt(foods[i])
                nf = fit(nr)
                if nf > fits[i]:
                    foods[i] = nr; fits[i] = nf; trial[i] = 0
                else:
                    trial[i] += 1

            # Memorize best
            bi = max(range(food_n), key=lambda i: fits[i])
            if fits[bi] > (1.0/best_d if best_d > 0 else 0):
                best_r = foods[bi][:]; best_d = self._route_dist(best_r)

            # Scout bees
            for i in range(food_n):
                if trial[i] > limit:
                    r = lc_list[:]; random.shuffle(r)
                    foods[i] = r; fits[i] = fit(r); trial[i] = 0

            history.append(best_d)

        elapsed    = time.time() - t0
        improvement = round((greedy_dist - best_d) / greedy_dist * 100, 2) \
                      if greedy_dist > 0 else 0.0

        return {
            'best_dist':   round(best_d, 1),
            'best_route':  best_r,
            'greedy_dist': round(greedy_dist, 1),
            'improvement': improvement,
            'history':     [round(h, 1) for h in history],
            'time_sec':    round(elapsed, 2),
        }

    # ── Ürün Yerleşimi (ABC Sınıflandırması) ──────────────────────

    def place_products(self, products: list, abc_classification: list) -> dict:
        """
        Ürünleri ABC sınıfına göre IO noktasına yakınlık esasıyla yerleştirir.

        products          : [{'name', 'frequency'}, ...]
        abc_classification: DataLoader.get_abc_classification() çıktısı
        """
        if not products:
            return {'error': 'Ürün listesi boş'}

        abc_map = {r['reference']: r['ABC'] for r in abc_classification}

        sorted_storage = sorted(
            self.storage_map.items(),
            key=lambda kv: self._manhattan_to_io(
                kv[1]['x'], kv[1]['y'], kv[1]['z'])
        )

        sorted_prods = sorted(
            products,
            key=lambda p: float(p.get('frequency', 1)),
            reverse=True
        )
        n = len(sorted_prods)

        placements = []
        for i, p in enumerate(sorted_prods):
            ref  = p.get('name', f'Ürün-{i+1}')
            abc  = abc_map.get(ref, 'A' if i < n*0.23 else ('B' if i < n*0.48 else 'C'))
            freq = float(p.get('frequency', 1))

            # En yakın uygun rafı seç
            if i < len(sorted_storage):
                loc, coords = sorted_storage[i]
                dist_io = round(self._manhattan_to_io(
                    coords['x'], coords['y'], coords['z']), 1)
                lc = self._find_nearest_lc(coords['x'], coords['y'])
            else:
                loc, coords, dist_io, lc = '—', {}, 0, '—'

            # Zone etiket (A→Hızlı Erişim, B→Yakın, C→Uzak)
            zone_map = {
                'A': {'label': 'Bölge A', 'desc': 'Hızlı Erişim', 'color': '#3fb950'},
                'B': {'label': 'Bölge B', 'desc': 'Yakın Bölge',  'color': '#58a6ff'},
                'C': {'label': 'Bölge C', 'desc': 'Uzak Bölge',   'color': '#d29922'},
            }
            zone_info = zone_map.get(abc, zone_map['C'])

            placements.append({
                'product':             ref,
                'frequency':           freq,
                'abc_class':           abc,
                'zone':                abc,
                'shelf':               i + 1,
                'location':            loc,
                'coords':              [coords.get('x',0), coords.get('y',0)],
                'distance_from_entry': dist_io,
                'nearest_lc':         lc,
                'zone_label':          zone_info['label'],
                'zone_desc':           zone_info['desc'],
                'zone_color':          zone_info['color'],
            })

        return {
            'placements':     placements,
            'total_products': n,
            'strategy':       'ABC Pareto (Karaboğa Destekli)',
            'zone_breakdown': self._zone_breakdown(placements),
        }

    def _zone_breakdown(self, placements):
        bd = {}
        for p in placements:
            z = p['zone']
            if z not in bd:
                bd[z] = {
                    'count': 0, 'products': [],
                    'zone_label': p['zone_label'],
                    'zone_color': p['zone_color'],
                }
            bd[z]['count'] += 1
            bd[z]['products'].append(p['product'])
        return bd

    # ── Rota Optimizasyonu (wave_id ile) ─────────────────────────

    def optimize_route_from_wave(self, wave_detail: dict) -> dict:
        """
        DataLoader.get_wave_detail() çıktısından ABC rota optimizasyonu.
        """
        products = wave_detail.get('products', [])
        if not products:
            return {'error': 'Wave boş'}

        # LC listesi oluştur
        lc_list = []
        lc_to_prod = {}
        for p in products:
            lc = p.get('nearest_lc')
            if lc and lc in self.lc_coords:
                if lc not in lc_list:
                    lc_list.append(lc)
                lc_to_prod[lc] = p['reference']

        if not lc_list:
            return {'error': 'LC koordinatları bulunamadı'}

        result = self.abc_optimize(lc_list, guided_seed=lc_list)

        # Route adımlarını oluştur
        route_steps = []
        cum_dist    = 0.0
        best_route  = result['best_route']

        for step_i, lc in enumerate(best_route):
            c     = self.lc_coords.get(lc, {})
            prev  = best_route[step_i-1] if step_i > 0 else None
            step_d = self._lc_dist(prev, lc) if prev else 0
            cum_dist += step_d
            route_steps.append({
                'order':               step_i + 1,
                'product':             lc_to_prod.get(lc, lc),
                'lc':                  lc,
                'coords':              [c.get('x_nav',0), c.get('y_nav',0)],
                'step_distance':       round(step_d, 1),
                'cumulative_distance': round(cum_dist, 1),
                'zone_color':          '#58a6ff',
            })

        return {
            'route':           route_steps,
            'total_distance':  result['best_dist'],
            'greedy_distance': result['greedy_dist'],
            'improvement_pct': result['improvement'],
            'product_count':   len(lc_list),
            'algorithm':       'ABC Arı Kolonisi (Karaboğa 2005)',
            'abc_source':      'abc.erciyes.edu.tr',
            'history':         result['history'],
            'time_sec':        result['time_sec'],
        }

    # ── Apriori Proximity Cluster → Guided Seed ──────────────────
    def build_apriori_guided_seed(self,
                                   lc_list: list,
                                   rules: list,
                                   lc_to_prod: dict,
                                   prod_locations: dict) -> list:
        """
        Apriori birliktelik kurallarından proximity cluster oluşturur
        ve LC listesi için guided_seed üretir.

        Faz 5'teki Union-Find + centroid sıralama mantığı:
          1. Yüksek lift (≥3) çiftleri Union-Find ile cluster'la
          2. Her cluster'ın centroid IO mesafesini hesapla
          3. IO'ya yakın cluster önce → guided_seed LC sırası

        rules       : [{'antecedents','consequents','lift'}, ...]
        lc_to_prod  : {lc_label: product_ref}
        prod_locations: {product_ref: {'x','y'}}
        """
        if not rules or not lc_to_prod:
            return lc_list  # Apriori yoksa orijinal sıra

        IO_X, IO_Y = self.IO[0], self.IO[1]
        LIFT_THRESHOLD = 3.0

        # Ürün → LC eşlemesi (ters)
        prod_to_lc = {v: k for k, v in lc_to_prod.items()}

        # Union-Find
        parent = {}

        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            parent[find(x)] = find(y)

        # Güçlü kurallardan cluster oluştur
        for r in rules:
            if float(r.get('lift', 0)) < LIFT_THRESHOLD:
                continue
            ants = r.get('antecedents', '')
            cons = r.get('consequents', '')
            # Virgülle ayrılmış olabilir
            items = [i.strip() for i in (ants + ',' + cons).split(',') if i.strip()]
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    union(items[i], items[j])

        # Wave'deki LC'leri cluster'a göre grupla
        from collections import defaultdict
        lc_clusters = defaultdict(list)
        for lc in lc_list:
            prod = lc_to_prod.get(lc, lc)
            cid  = find(prod) if prod in parent else prod
            lc_clusters[cid].append(lc)

        # Her cluster için IO mesafesini hesapla
        cluster_dists = []
        for cid, lcs in lc_clusters.items():
            xs = [self.lc_coords.get(lc, {}).get('x_nav', IO_X) for lc in lcs]
            ys = [self.lc_coords.get(lc, {}).get('y_nav', IO_Y) for lc in lcs]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            dist = math.sqrt((cx - IO_X)**2 + (cy - IO_Y)**2)
            cluster_dists.append((dist, lcs))

        # IO'ya yakın cluster önce gelsin
        cluster_dists.sort(key=lambda x: x[0])

        # Guided seed: cluster sırasına göre LC listesi
        guided = []
        for _, lcs in cluster_dists:
            for lc in lcs:
                if lc not in guided:
                    guided.append(lc)

        # Wave'deki ama cluster'a girmeyen LC'leri sona ekle
        for lc in lc_list:
            if lc not in guided:
                guided.append(lc)

        return guided

    # ── Ürün listesiyle rota (frontend'den gelecek) ───────────────

    def optimize_route(self, products: list) -> dict:
        """
        Frontend'den gelen [{'name', 'zone', 'shelf'}, ...] listesiyle rota.
        Koordinatları storage_map'ten bulur, ABC çalıştırır.
        """
        if not products:
            return {'error': 'Ürün listesi boş'}

        lc_list     = []
        prod_lc_map = {}

        for p in products:
            name = p.get('name', '')
            # storage_map'te ürün adına yakın lokasyon bul
            # Frontend zone+shelf ile gönderir — mock koordinat kullan
            zone_x = {'A':15,'B':35,'C':55,'D':75,'E':95}.get(
                p.get('zone','C'), 55)
            shelf_y = (int(p.get('shelf', 1)) - 1) * 90  # ~90 birim aralık
            lc = self._find_nearest_lc(zone_x * 6, shelf_y)  # ölçek
            if lc and lc not in lc_list:
                lc_list.append(lc)
            prod_lc_map[lc] = name

        if not lc_list:
            return {'error': 'Koordinat bulunamadı'}

        result = self.abc_optimize(lc_list)
        route_steps = []
        cum_dist    = 0.0

        for i, lc in enumerate(result['best_route']):
            c      = self.lc_coords.get(lc, {})
            prev   = result['best_route'][i-1] if i > 0 else None
            step_d = self._lc_dist(prev, lc) if prev else 0
            cum_dist += step_d
            route_steps.append({
                'order':               i + 1,
                'product':             prod_lc_map.get(lc, lc),
                'zone':                lc,
                'shelf':               i + 1,
                'zone_label':          lc,
                'zone_color':          '#58a6ff',
                'coords':              [c.get('x_nav',0), c.get('y_nav',0)],
                'step_distance':       round(step_d, 1),
                'cumulative_distance': round(cum_dist, 1),
            })

        return_d    = self._lc_dist(result['best_route'][-1],
                                    result['best_route'][0]) \
                      if result['best_route'] else 0

        return {
            'route':           route_steps,
            'total_distance':  result['best_dist'],
            'greedy_distance': result['greedy_dist'],
            'improvement_pct': result['improvement'],
            'return_distance': round(return_d, 1),
            'product_count':   len(products),
            'algorithm':       'ABC Arı Kolonisi (Karaboğa 2005)',
            'history':         result['history'],
            'time_sec':        result['time_sec'],
        }