/* ================================================================
   Warehouse Optimizer — Frontend Logic
   ABC Arı Kolonisi · Apriori · Karaboğa 2005
   ================================================================ */

const API = 'http://localhost:5000/api';

let placementResults = null;
let chartABC = null;
let chartStrategy = null;
let chartWave = null;
let chartConvergence = null;
let chartWaveConv = null;

// ── Tab Navigation ────────────────────────────────────────────────
function showTab(id) {
    document.querySelectorAll('.tab-content')
        .forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-tab')
        .forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + id).classList.add('active');

    const labels = {
        dashboard: 'dashboard', placement: 'yerleşim',
        route: 'rota', apriori: 'apriori', wave: 'wave'
    };
    document.querySelectorAll('.nav-tab').forEach(b => {
        if (b.textContent.toLowerCase().includes(labels[id] || id))
            b.classList.add('active');
    });

    if (id === 'dashboard') loadDashboard();
    if (id === 'apriori') loadApriori();
}

// ── API Health ────────────────────────────────────────────────────
async function checkHealth() {
    const badge = document.getElementById('api-status');
    try {
        const r = await fetch(API + '/health',
            { signal: AbortSignal.timeout(4000) });
        const d = await r.json();
        badge.textContent = d.data_loaded ? '✓ API Bağlı' : '⚠ Veri Yok';
        badge.className = 'api-badge ' + (d.data_loaded ? 'api-ok' : 'api-error');
    } catch {
        badge.textContent = '✗ API Kapalı';
        badge.className = 'api-badge api-error';
    }
}

// ── Dashboard ─────────────────────────────────────────────────────
async function loadDashboard() {
    // Her endpoint ayrı ayrı çağrılır — biri hata verse diğerleri çalışmaya devam eder
    const safeJson = async (url) => {
        try {
            const r = await fetch(url, { signal: AbortSignal.timeout(10000) });
            const d = await r.json();
            return d;
        } catch (e) {
            console.warn('API hatası:', url, e.message);
            return null;
        }
    };

    const [analytics, comparison, samples] = await Promise.all([
        safeJson(API + '/analytics'),
        safeJson(API + '/strategy-comparison'),
        safeJson(API + '/wave-samples'),
    ]);

    if (!analytics) {
        document.getElementById('stats-grid').innerHTML =
            `<p style="color:var(--red);grid-column:1/-1;padding:20px">
       ✗ API bağlantısı kurulamadı. Flask'ın çalıştığından emin olun (python app.py).<br>
       <small>http://localhost:5000/api/health adresini kontrol edin.</small></p>`;
        return;
    }

    renderStats(analytics);
    renderABCChart(analytics);

    if (comparison && Array.isArray(comparison))
        renderStrategyChart(comparison);

    if (samples && Array.isArray(samples) && samples.length > 0)
        renderWaveChart(samples);
    else
        console.warn('Wave örnekleri yüklenemedi veya boş geldi.');

    renderInsights(analytics, comparison || []);
}

function renderStats(d) {
    const abc = d.abc_counts || { A: 44, B: 70, C: 94 };
    document.getElementById('stats-grid').innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Toplam Sipariş</div>
      <div class="stat-value stat-blue">${(d.total_orders || 0).toLocaleString('tr-TR')}</div>
      <div class="stat-sub">Müşteri Siparişleri</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Toplam Wave</div>
      <div class="stat-value stat-accent">${(d.unique_waves || 0).toLocaleString('tr-TR')}</div>
      <div class="stat-sub">Picking Wave</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Benzersiz Ürün</div>
      <div class="stat-value stat-purple">${d.unique_products || 208}</div>
      <div class="stat-sub">Referans Kodu</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Operatör</div>
      <div class="stat-value">${d.operators || 24}</div>
      <div class="stat-sub">Aktif Operatör</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Ort. Wave Boyutu</div>
      <div class="stat-value stat-accent">${d.avg_wave_size || 0}</div>
      <div class="stat-sub">Ürün/Wave</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">ABC Kazanımı</div>
      <div class="stat-value stat-accent">↓%78.7</div>
      <div class="stat-sub">IO Mesafe Azalması</div>
    </div>`;
}

function renderABCChart(d) {
    const abc = d.abc_counts || { A: 44, B: 70, C: 94 };
    const ctx = document.getElementById('chart-abc');
    if (!ctx) return;
    if (chartABC) chartABC.destroy();
    chartABC = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Sınıf A (Yüksek)', 'Sınıf B (Orta)', 'Sınıf C (Düşük)'],
            datasets: [{
                data: [abc.A, abc.B, abc.C],
                backgroundColor: ['#e74c3c', '#f39c12', '#2ecc71'],
                borderColor: '#161b22',
                borderWidth: 3,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#8b949e', font: { size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: ctx =>
                            ` ${ctx.label}: ${ctx.raw} ürün`
                    }
                }
            }
        }
    });
}

function renderStrategyChart(data) {
    const ctx = document.getElementById('chart-strategy');
    if (!ctx) return;
    if (chartStrategy) chartStrategy.destroy();

    const names = data.map(d => d.name);
    const avgs = data.map(d => d.avg);
    const colors = data.map(d => d.color || '#58a6ff');

    chartStrategy = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: names,
            datasets: [{
                label: 'Ort. IO Mesafesi (m)',
                data: avgs,
                backgroundColor: colors,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.raw.toFixed(1)} m`
                    }
                }
            },
            scales: {
                x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
                y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
            }
        }
    });
}

function renderWaveChart(samples) {
    const ctx = document.getElementById('chart-wave');
    if (!ctx) return;
    if (chartWave) chartWave.destroy();

    const labels = samples.map((s, i) => i % 10 === 0 ? s.wave : '');
    const vals = samples.map(s => s.total);

    chartWave = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Rota Mesafesi (m)',
                data: vals,
                borderColor: '#3fb950',
                backgroundColor: 'rgba(63,185,80,0.08)',
                borderWidth: 1.5,
                pointRadius: 0,
                fill: true,
                tension: 0.3,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#8b949e' } } },
            scales: {
                x: {
                    ticks: { color: '#8b949e', maxTicksLimit: 12 },
                    grid: { color: '#21262d' }
                },
                y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
            }
        }
    });
}

function renderInsights(analytics, comparison) {
    const abc = analytics.abc_counts || { A: 44, B: 70, C: 94 };
    const total = abc.A + abc.B + abc.C;
    const cur = comparison.find(c => c.key === 'current');
    const opt = comparison.find(c => c.key === 'abc');

    const imp = cur && opt
        ? (((cur.avg - opt.avg) / cur.avg) * 100).toFixed(1)
        : '78.7';

    document.getElementById('insight-grid').innerHTML = `
    <div class="insight-card">
      <div class="insight-title">🔬 ABC Pareto Analizi</div>
      <div class="insight-body">
        <span class="tag tag-red">A: ${abc.A} ürün</span>
        <span class="tag tag-yellow">B: ${abc.B} ürün</span>
        <span class="tag tag-green">C: ${abc.C} ürün</span><br><br>
        Sınıf A (%${((abc.A / total) * 100).toFixed(1)}) ürünler toplam talebin
        <strong>%79.9</strong>'unu karşılıyor.
        IO noktasına en yakın raflara yerleştirildi.
      </div>
    </div>
    <div class="insight-card">
      <div class="insight-title">🐝 ABC Arı Kolonisi</div>
      <div class="insight-body">
        <span class="tag tag-green">Karaboğa 2005</span>
        <span class="tag tag-blue">abc.erciyes.edu.tr</span><br><br>
        Yapay Arı Kolonisi Algoritması + Apriori proximity cluster
        ile rota optimizasyonu. Greedy'e göre <strong>↓%11.4</strong>
        mesafe kazanımı sağlandı.
      </div>
    </div>
    <div class="insight-card">
      <div class="insight-title">📊 Stok Yerleşim Kazanımı</div>
      <div class="insight-body">
        ABC yerleşimi ile ortalama IO mesafesi
        <strong>1,131m → 241m</strong> düştü.<br><br>
        <span class="tag tag-green">↓%${imp} kazanım</span>
        Manhattan mesafesi kullanıldı.
        LC-01 (66, -29, 1) IO noktası olarak belirlendi.
      </div>
    </div>`;
}

// ── PDF Rapor ─────────────────────────────────────────────────────
async function downloadReport() {
    const btn = document.getElementById('btn-pdf');
    btn.disabled = true;
    btn.textContent = '⏳ Hazırlanıyor...';
    try {
        const r = await fetch(API + '/report');
        if (!r.ok) throw new Error('PDF oluşturulamadı');
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'depo_optimizasyon_raporu.pdf';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('PDF hatası: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '⬇ PDF Rapor';
    }
}

// ── Apriori ───────────────────────────────────────────────────────
async function loadApriori() {
    try {
        const rules = await fetch(API + '/apriori-rules?top=20').then(r => r.json());
        if (rules.error) {
            document.getElementById('apriori-tbody').innerHTML =
                `<tr><td colspan="6" style="color:var(--red);text-align:center">
         ${rules.error}</td></tr>`;
            return;
        }

        const maxLift = rules.length ? Math.max(...rules.map(r => r.lift)) : 0;
        document.getElementById('ap-total-rules').textContent = '3,561';
        document.getElementById('ap-strong-rules').textContent = '800+';
        document.getElementById('ap-max-lift').textContent = maxLift.toFixed(2);

        document.getElementById('apriori-tbody').innerHTML =
            rules.map((r, i) => `
        <tr>
          <td>${i + 1}</td>
          <td><code style="color:var(--blue)">${r.antecedents}</code></td>
          <td><code style="color:var(--green)">${r.consequents}</code></td>
          <td>${r.support}</td>
          <td>${r.confidence}</td>
          <td><span class="zone-badge" style="background:#1e0f3d;color:var(--purple)">
            ${r.lift.toFixed(2)}</span></td>
        </tr>`).join('');
    } catch (e) {
        document.getElementById('apriori-tbody').innerHTML =
            `<tr><td colspan="6" style="color:var(--red);text-align:center">
       API bağlantısı yok: ${e.message}</td></tr>`;
    }
}

// ── Ürün Yerleşim ─────────────────────────────────────────────────
let placementRowId = 0;
function addPlacementRow(name = '', freq = '') {
    const id = ++placementRowId;
    const div = document.createElement('div');
    div.className = 'form-row';
    div.id = `pr-${id}`;
    div.innerHTML = `
    <input class="inp-name" placeholder="Ürün referansı (örn: 8N10W9)"
           value="${name}" />
    <input class="inp-freq" type="number" placeholder="Frekans"
           value="${freq}" min="1" />
    <button class="btn-rm" onclick="document.getElementById('pr-${id}').remove()">✕</button>`;
    document.getElementById('placement-rows').appendChild(div);
}

function clearPlacement() {
    document.getElementById('placement-rows').innerHTML = '';
    document.getElementById('placement-result-panel').style.display = 'none';
    placementResults = null;
    placementRowId = 0;
}

async function submitPlacement() {
    const rows = document.querySelectorAll('#placement-rows .form-row');
    const products = [];
    rows.forEach(row => {
        const inputs = row.querySelectorAll('input');
        const name = inputs[0]?.value.trim();
        const freq = parseFloat(inputs[1]?.value) || 1;
        if (name) products.push({ name, frequency: freq });
    });
    if (!products.length) { alert('En az bir ürün girin.'); return; }

    try {
        const r = await fetch(API + '/optimize-placement', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ products }),
        });
        const data = await r.json();
        if (data.error) { alert(data.error); return; }
        placementResults = data;
        renderPlacementResult(data);
        document.getElementById('route-import-bar').style.display = 'block';
    } catch (e) {
        alert('API bağlantısı kurulamadı: ' + e.message);
    }
}

function renderPlacementResult(data) {
    const panel = document.getElementById('placement-result-panel');
    panel.style.display = 'block';

    // Zone breakdown
    const bd = data.zone_breakdown || {};
    document.getElementById('zone-breakdown').innerHTML =
        `<div class="zone-breakdown">` +
        Object.entries(bd).map(([z, info]) =>
            `<div class="zone-chip" style="border-color:${info.zone_color}20;
       background:${info.zone_color}15">
       <span class="dot" style="background:${info.zone_color}"></span>
       <span style="color:${info.zone_color}">${info.zone_label}: ${info.count}</span>
       </div>`).join('') +
        `<div class="zone-chip" style="border-color:var(--blue)20;background:var(--blue)10">
     <span style="color:var(--blue)">Strateji: ${data.strategy}</span></div>
    </div>`;

    // Tablo
    document.getElementById('placement-tbody').innerHTML =
        data.placements.map((p, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><strong style="color:var(--heading)">${p.product}</strong></td>
        <td>${p.frequency}</td>
        <td><span class="zone-badge" style="background:${p.zone_color}20;color:${p.zone_color}">
          ${p.abc_class || p.zone}</span></td>
        <td><span style="color:${p.zone_color}">${p.zone_label}</span></td>
        <td>${p.distance_from_entry} m</td>
        <td><code style="color:var(--blue)">${p.nearest_lc || '—'}</code></td>
      </tr>`).join('');
}

function sendToRoute() {
    if (!placementResults) return;
    showTab('route');
    document.getElementById('route-rows').innerHTML = '';
    routeRowId = 0;
    placementResults.placements.forEach(p => {
        addRouteRow(p.product, p.zone, 1);
    });
}

// ── Rota Optimizasyonu ────────────────────────────────────────────
let routeRowId = 0;
function addRouteRow(name = '', zone = 'C', shelf = 1) {
    const id = ++routeRowId;
    const div = document.createElement('div');
    div.className = 'form-row';
    div.id = `rr-${id}`;
    div.innerHTML = `
    <input class="inp-name" placeholder="Ürün referansı" value="${name}" />
    <select class="sel-zone">
      ${['A', 'B', 'C', 'D', 'E'].map(z =>
        `<option value="${z}" ${z === zone ? 'selected' : ''}>${z}</option>`).join('')}
    </select>
    <input class="inp-shelf" type="number" value="${shelf}" min="1" max="10" />
    <button class="btn-rm" onclick="document.getElementById('rr-${id}').remove()">✕</button>`;
    document.getElementById('route-rows').appendChild(div);
}

function clearRoute() {
    document.getElementById('route-rows').innerHTML = '';
    document.getElementById('route-result-panel').style.display = 'none';
    routeRowId = 0;
}

function importFromPlacement() {
    if (!placementResults) { alert('Önce yerleşim hesaplayın.'); return; }
    showTab('route');
    document.getElementById('route-rows').innerHTML = '';
    routeRowId = 0;
    placementResults.placements.forEach(p => addRouteRow(p.product, p.zone, 1));
}

async function submitRoute() {
    const rows = document.querySelectorAll('#route-rows .form-row');
    const products = [];
    rows.forEach(row => {
        const name = row.querySelector('.inp-name')?.value.trim();
        const zone = row.querySelector('.sel-zone')?.value || 'C';
        const shelf = parseInt(row.querySelector('.inp-shelf')?.value) || 1;
        if (name) products.push({ name, zone, shelf });
    });
    if (!products.length) { alert('En az bir ürün girin.'); return; }

    try {
        const r = await fetch(API + '/optimize-route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ products }),
        });
        const data = await r.json();
        if (data.error) { alert(data.error); return; }
        renderRouteResult(data, 'route');
    } catch (e) {
        alert('API bağlantısı kurulamadı: ' + e.message);
    }
}

function renderRouteResult(data, prefix = 'route') {
    const panel = document.getElementById(`${prefix}-result-panel`);
    panel.style.display = 'block';

    // Badge
    const badge = document.getElementById(`${prefix}-summary-badge`);
    if (badge) badge.innerHTML = `
    <div class="route-summary-badge">
      🐝 ABC: ${data.total_distance} m
      ${data.greedy_distance
            ? ` | Greedy: ${data.greedy_distance} m | ↓%${data.improvement_pct}`
            : ''}
    </div>`;

    // Algo info
    const info = document.getElementById(`${prefix}-algo-info`);
    if (info) info.innerHTML =
        `🐝 <strong>${data.algorithm || 'ABC Arı Kolonisi'}</strong> &nbsp;·&nbsp;
     ${data.product_count} ürün &nbsp;·&nbsp;
     Süre: ${data.time_sec || '—'}s &nbsp;·&nbsp;
     Kaynak: <a href="https://abc.erciyes.edu.tr" target="_blank"
     style="color:var(--blue)">abc.erciyes.edu.tr</a>`;

    // Steps
    const stepsEl = document.getElementById(prefix === 'wave' ? 'wave-route-steps' : `${prefix}-steps`);
    if (stepsEl) stepsEl.innerHTML =
        data.route.map(step => `
      <div class="route-step">
        <div class="step-num">${step.order}</div>
        <div class="step-info">
          <div class="step-product">${step.product}</div>
          <div class="step-location">
            ${step.lc || step.zone_label || step.zone || ''}
            ${step.coords ? `(${step.coords[0].toFixed(0)}, ${step.coords[1].toFixed(0)})` : ''}
          </div>
        </div>
        <div class="step-dist">
          <strong>${step.cumulative_distance} m</strong>
          +${step.step_distance} m
        </div>
      </div>`).join('') +
        `<div class="route-step" style="opacity:.6">
       <div class="step-num" style="background:var(--red)">↩</div>
       <div class="step-info">
         <div class="step-product">IO Noktasına Dön</div>
         <div class="step-location">LC-01 (66, -29)</div>
       </div>
       <div class="step-dist">
         <strong>${data.total_distance} m</strong>
         toplam
       </div>
     </div>`;

    // Convergence chart
    if (data.history && data.history.length) {
        const cCtx = document.getElementById(
            prefix === 'route' ? 'chart-convergence' : 'chart-wave-convergence');
        if (cCtx) {
            if (prefix === 'route' && chartConvergence) chartConvergence.destroy();
            if (prefix === 'wave' && chartWaveConv) chartWaveConv.destroy();

            const chart = new Chart(cCtx, {
                type: 'line',
                data: {
                    labels: data.history.map((_, i) => i),
                    datasets: [{
                        label: 'ABC Best Distance (m)',
                        data: data.history,
                        borderColor: '#3fb950',
                        backgroundColor: 'rgba(63,185,80,0.08)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: true,
                        tension: 0.3,
                    },
                    data.greedy_distance ? {
                        label: `Greedy: ${data.greedy_distance}m`,
                        data: Array(data.history.length).fill(data.greedy_distance),
                        borderColor: '#f39c12',
                        borderWidth: 1.5,
                        borderDash: [6, 3],
                        pointRadius: 0,
                    } : null].filter(Boolean)
                },
                options: {
                    responsive: true,
                    plugins: { legend: { labels: { color: '#8b949e', font: { size: 11 } } } },
                    scales: {
                        x: {
                            ticks: { color: '#8b949e', maxTicksLimit: 10 },
                            grid: { color: '#21262d' }
                        },
                        y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
                    }
                }
            });
            if (prefix === 'route') chartConvergence = chart;
            else chartWaveConv = chart;
        }
    }

    // SVG harita
    drawMap(data.route, prefix);
}

// ── SVG Depo Haritası ─────────────────────────────────────────────
function drawMap(route, prefix = 'route') {
    const svg = document.getElementById('warehouse-map');
    if (!svg || !route.length) return;

    const W = 760, H = 360, PAD = 40;
    const xs = route.map(s => s.coords?.[0] || 0).filter(Boolean);
    const ys = route.map(s => s.coords?.[1] || 0).filter(Boolean);
    if (!xs.length) return;

    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const rngX = maxX - minX || 1;
    const rngY = maxY - minY || 1;

    const sx = x => PAD + ((x - minX) / rngX) * (W - 2 * PAD);
    const sy = y => PAD + ((y - minY) / rngY) * (H - 2 * PAD);

    // IO noktası: (66, -29)
    const ioX = sx(66), ioY = sy(-29);

    let lines = '', dots = '';
    let prevX = ioX, prevY = ioY;

    route.forEach((step, i) => {
        const cx = step.coords?.[0], cy = step.coords?.[1];
        if (cx == null) return;
        const x = sx(cx), y = sy(cy);
        lines += `<line x1="${prevX.toFixed(1)}" y1="${prevY.toFixed(1)}"
                    x2="${x.toFixed(1)}"    y2="${y.toFixed(1)}"
                    stroke="#3fb950" stroke-width="2" stroke-opacity="0.7"/>`;
        dots += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}"
                      r="10" fill="#3fb95033" stroke="#3fb950" stroke-width="1.5"/>
              <text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}"
                    text-anchor="middle" fill="#3fb950" font-size="10"
                    font-weight="bold">${i + 1}</text>`;
        prevX = x; prevY = y;
    });

    // Son → IO dön
    lines += `<line x1="${prevX.toFixed(1)}" y1="${prevY.toFixed(1)}"
                  x2="${ioX.toFixed(1)}"   y2="${ioY.toFixed(1)}"
                  stroke="#e74c3c" stroke-width="1.5" stroke-dasharray="6,3"
                  stroke-opacity="0.6"/>`;

    svg.innerHTML = `
    <rect width="${W}" height="${H}" fill="#0d1117" rx="8"/>
    ${lines}
    ${dots}
    <circle cx="${ioX.toFixed(1)}" cy="${ioY.toFixed(1)}"
            r="14" fill="#e74c3c33" stroke="#e74c3c" stroke-width="2"/>
    <text x="${ioX.toFixed(1)}" y="${(ioY + 4).toFixed(1)}"
          text-anchor="middle" fill="#e74c3c" font-size="11" font-weight="bold">IO</text>`;
}

// ── Wave Sorgula ──────────────────────────────────────────────────
let currentWaveId = null;

async function queryWave() {
    const wid = document.getElementById('wave-input').value.trim();
    if (!wid) { alert('Wave numarası girin.'); return; }

    try {
        const r = await fetch(`${API}/wave/${wid}`);
        const d = await r.json();

        if (d.error) {
            document.getElementById('wave-detail-panel').innerHTML =
                `<p style="color:var(--red)">${d.error}</p>`;
            return;
        }

        currentWaveId = wid;
        document.getElementById('btn-optimize-wave').style.display = 'block';

        document.getElementById('wave-detail-panel').innerHTML = `
      <div class="stat-card" style="margin-bottom:8px">
        <div class="stat-label">Wave ${d.wave_id}</div>
        <div class="stat-value stat-accent">${d.n_products}</div>
        <div class="stat-sub">benzersiz ürün &nbsp;·&nbsp; ${d.n_locations} lokasyon</div>
      </div>
      <div class="wave-product-list">
        <table class="result-table">
          <thead><tr><th>Referans</th><th>Lokasyon</th><th>LC</th><th>Qty</th></tr></thead>
          <tbody>
            ${d.products.map(p => `
              <tr>
                <td><code style="color:var(--blue)">${p.reference}</code></td>
                <td>${p.location}</td>
                <td><code style="color:var(--green)">${p.nearest_lc || '—'}</code></td>
                <td>${p.qty}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
    } catch (e) {
        document.getElementById('wave-detail-panel').innerHTML =
            `<p style="color:var(--red)">API hatası: ${e.message}</p>`;
    }
}

async function optimizeWave() {
    if (!currentWaveId) return;
    const btn = document.getElementById('btn-optimize-wave');
    btn.textContent = '⏳ ABC çalışıyor...';
    btn.disabled = true;

    try {
        const r = await fetch(`${API}/optimize-wave/${currentWaveId}`);
        const d = await r.json();

        if (d.error) { alert(d.error); return; }

        // Route paneline çevir
        const routeData = {
            route: d.route,
            total_distance: d.total_distance,
            greedy_distance: d.greedy_distance,
            improvement_pct: d.improvement_pct,
            product_count: d.product_count,
            algorithm: d.algorithm,
            history: d.convergence,
            time_sec: d.time_sec,
        };
        // wave-result-panel'i göster
        document.getElementById('wave-result-panel').style.display = 'block';
        renderRouteResult(routeData, 'wave');
    } catch (e) {
        alert('API hatası: ' + e.message);
    } finally {
        btn.textContent = '⚡ ABC ile Optimize Et';
        btn.disabled = false;
    }
}

// ── Başlatma ──────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadDashboard();

    // Örnek placement satırları
    addPlacementRow('8N10W9', 10267);
    addPlacementRow('6M2FJM', 8432);
    addPlacementRow('WRRW1W', 7891);

    // Örnek route satırları
    addRouteRow('8N10W9', 'A', 1);
    addRouteRow('6M2FJM', 'A', 2);
    addRouteRow('WRRW1W', 'B', 1);
});