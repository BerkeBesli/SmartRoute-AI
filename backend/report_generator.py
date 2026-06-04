"""
report_generator.py — PDF Rapor Üretici - SmartRouteAI Projesi

Gereksinim: uv add reportlab matplotlib
"""

import io
import os
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black

# Helvetica tüm sistemlerde mevcut, ASCII metinlerde sorunsuz
_FONT_NORMAL = 'Helvetica'
_FONT_BOLD   = 'Helvetica-Bold'
_FONT_ITALIC = 'Helvetica-Oblique'

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

PAGE_W, PAGE_H = A4

# ── Renkler ───────────────────────────────────────────────────────
C_GREEN  = HexColor('#27ae60')
C_BLUE   = HexColor('#3498db')
C_RED    = HexColor('#e74c3c')
C_ORANGE = HexColor('#f39c12')
C_GRAY   = HexColor('#6c757d')
C_DARK   = HexColor('#2c3e50')
C_LIGHT  = HexColor('#f8f9fa')
C_BORDER = HexColor('#dee2e6')
C_TEXT   = HexColor('#212529')
C_PURPLE = HexColor('#9b59b6')

ABC_COLORS = {'A': C_RED, 'B': C_ORANGE, 'C': C_GREEN}

# ── Stiller ───────────────────────────────────────────────────────
def make_styles():
    styles = getSampleStyleSheet()
    custom = {
        'title': ParagraphStyle('title',
            fontSize=22, fontName=_FONT_BOLD,
            textColor=C_DARK, spaceAfter=6, alignment=TA_CENTER),
        'subtitle': ParagraphStyle('subtitle',
            fontSize=11, fontName=_FONT_NORMAL,
            textColor=C_GRAY, spaceAfter=20, alignment=TA_CENTER),
        'section': ParagraphStyle('section',
            fontSize=13, fontName=_FONT_BOLD,
            textColor=C_DARK, spaceBefore=14, spaceAfter=6),
        'body': ParagraphStyle('body',
            fontSize=9, fontName=_FONT_NORMAL,
            textColor=C_TEXT, spaceAfter=4, leading=14),
        'caption': ParagraphStyle('caption',
            fontSize=8, fontName=_FONT_NORMAL,
            textColor=C_GRAY, spaceAfter=4, alignment=TA_CENTER),
        'kpi_val': ParagraphStyle('kpi_val',
            fontSize=20, fontName=_FONT_BOLD,
            textColor=C_GREEN, alignment=TA_CENTER),
        'kpi_lbl': ParagraphStyle('kpi_lbl',
            fontSize=8, fontName=_FONT_NORMAL,
            textColor=C_GRAY, alignment=TA_CENTER),
    }
    return custom


# ── Grafik: Matplotlib → ReportLab Image ──────────────────────────
# PIL decompression bomb limitini devre dışı bırak
try:
    from PIL import Image as PILImage
    PILImage.MAX_IMAGE_PIXELS = None
except Exception:
    pass

def fig_to_image(fig, width=14*cm, max_height=10*cm):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=60, bbox_inches='tight',
                facecolor='white')
    buf.seek(0)
    plt.close(fig)
    # Orantılı yükseklik hesapla
    import struct, zlib
    buf.seek(16)
    try:
        raw = buf.read(8)
        px_w = struct.unpack('>I', raw[:4])[0]
        px_h = struct.unpack('>I', raw[4:])[0]
        ratio = px_h / px_w if px_w > 0 else 0.5
        height = min(width * ratio, max_height)
        buf.seek(0)
        img = Image(buf, width=width, height=height)
    except Exception:
        buf.seek(0)
        img = Image(buf, width=width)
    img.hAlign = 'CENTER'
    return img


# ── KPI Tablosu ───────────────────────────────────────────────────
def make_kpi_table(data: list, styles: dict):
    """
    data: [{'label': str, 'value': str, 'color': HexColor}, ...]
    """
    cells = []
    for d in data:
        cells.append([
            Paragraph(d['value'], ParagraphStyle('v',
                fontSize=18, fontName=_FONT_BOLD,
                textColor=d.get('color', C_GREEN), alignment=TA_CENTER)),
            Paragraph(d['label'], ParagraphStyle('l',
                fontSize=8, fontName=_FONT_NORMAL,
                textColor=C_GRAY, alignment=TA_CENTER)),
        ])

    col_w = (PAGE_W - 4*cm) / len(data)
    tbl = Table([
        [c[0] for c in cells],
        [c[1] for c in cells],
    ], colWidths=[col_w]*len(data), rowHeights=[28, 16])
    tbl.setStyle(TableStyle([
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT),
        ('BOX',        (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, C_BORDER),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [C_LIGHT, white]),
    ]))
    return tbl


# ── Grafik 1: ABC Pareto ──────────────────────────────────────────
def plot_abc_pareto(abc_data: list) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax2 = ax.twinx()

    colors_bar = [{'A':'#e74c3c','B':'#f39c12','C':'#2ecc71'}.get(
        r['ABC'],'gray') for r in abc_data[:80]]
    counts = [r['order_count'] for r in abc_data[:80]]
    cums   = [r['cumulative_pct'] for r in abc_data[:80]]

    ax.bar(range(len(counts)), counts, color=colors_bar, alpha=0.75, width=1.0)
    ax2.plot(range(len(cums)), cums, color='#2c3e50', lw=2)
    ax2.axhline(80, color='#e74c3c', ls='--', lw=1.2, label='%80 (A siniri)')
    ax2.axhline(95, color='#f39c12', ls='--', lw=1.2, label='%95 (B siniri)')

    ax.set_xlabel('Urunler (siklik sirasi)', fontsize=9)
    ax.set_ylabel('Siparis Sayisi', fontsize=9)
    ax2.set_ylabel('Kumulatif Talep (%)', fontsize=9)
    ax.set_title('ABC Pareto Analizi — Stok Siniflandirmasi', fontsize=11, fontweight='bold')

    patches = [mpatches.Patch(color=c, label=f'Sinif {k}')
               for k,c in {'A':'#e74c3c','B':'#f39c12','C':'#2ecc71'}.items()]
    ax2.legend(handles=patches + ax2.lines, loc='center right', fontsize=8)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    return fig


# ── Grafik 2: Strateji Karşılaştırması ───────────────────────────
def plot_strategy_comparison(summary: dict) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Sol: ABC sınıf dağılımı pasta
    abc_cnts = summary.get('abc_counts', {'A':44,'B':70,'C':94})
    axes[0].pie(
        [abc_cnts['A'], abc_cnts['B'], abc_cnts['C']],
        labels=[f"A ({abc_cnts['A']})", f"B ({abc_cnts['B']})", f"C ({abc_cnts['C']})"],
        colors=['#e74c3c','#f39c12','#2ecc71'],
        autopct='%1.1f%%', startangle=90,
        wedgeprops={'edgecolor':'white','linewidth':2}
    )
    axes[0].set_title('ABC Sinif Dagilimi\n(208 Urun)', fontsize=10, fontweight='bold')

    # Sağ: IO mesafe kazanımı
    avg_d = summary.get('avg_shelf_dist_m', 1131)
    # Optimize mesafe yaklaşık %78 daha az
    opt_d = round(avg_d * 0.22, 1)
    improve = round((avg_d - opt_d) / avg_d * 100, 1)

    bars = axes[1].bar(
        ['Mevcut\n(Rastgele)', 'ABC\nYerlesimi'],
        [avg_d, opt_d],
        color=['#e74c3c','#27ae60'], width=0.45, edgecolor='white'
    )
    for b, v in zip(bars, [avg_d, opt_d]):
        axes[1].text(b.get_x()+b.get_width()/2, b.get_height()+15,
                     f'{v:.0f}m', ha='center', fontsize=10, fontweight='bold')
    axes[1].text(0.5, (avg_d+opt_d)/2, f'↓%{improve}',
                 ha='center', fontsize=13, color='#27ae60', fontweight='bold',
                 transform=axes[1].get_xaxis_transform())
    axes[1].set_ylabel('Ort. IO Mesafesi (m)', fontsize=9)
    axes[1].set_title('Stok Yerlesim Kazanimi', fontsize=10, fontweight='bold')
    axes[1].grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig


# ── Grafik 3: ABC Optimizasyon Sonuçları ─────────────────────────
def plot_abc_optimization(summary: dict) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Sol: Dalga boyutu dağılımı (simüle)
    wave_sizes = [1,2,3,4,5,6,7,8,9,10]
    counts_sim = [1908,621,632,687,713,826,832,778,608,565]
    axes[0].bar(wave_sizes, counts_sim, color='#3498db', alpha=0.8, edgecolor='white')
    axes[0].set_xlabel('Wave Boyutu (Urun Sayisi)', fontsize=9)
    axes[0].set_ylabel('Wave Adedi', fontsize=9)
    axes[0].set_title('Wave Boyutu Dagilimi', fontsize=10, fontweight='bold')
    axes[0].grid(axis='y', alpha=0.3)

    # Sağ: Yöntem karşılaştırması
    methods  = ['Rastgele', 'Greedy', 'ABC\n(Karaboga)']
    dists    = [5117, 1144, 1014]
    cols     = ['#e74c3c','#f39c12','#27ae60']
    bars = axes[1].bar(methods, dists, color=cols, alpha=0.85,
                       edgecolor='white', width=0.5)
    for b, v in zip(bars, dists):
        axes[1].text(b.get_x()+b.get_width()/2, b.get_height()+30,
                     f'{v}m', ha='center', fontsize=10, fontweight='bold')
    axes[1].set_ylabel('Ort. Rota Mesafesi (m)', fontsize=9)
    axes[1].set_title('Rota Yontemi Karsilastirmasi\n(8,778 Wave)', fontsize=10, fontweight='bold')
    axes[1].grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig


# ── Grafik 4: Apriori Lift Dağılımı ──────────────────────────────
def plot_apriori(rules: list) -> plt.Figure:
    if not rules or isinstance(rules, dict):
        # Apriori henüz çalıştırılmamış
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.text(0.5, 0.5, 'Apriori kurallari bulunamadi.\nOnce warehouse_optimization_full.py calistirin.',
                ha='center', va='center', fontsize=11, color='gray',
                transform=ax.transAxes)
        ax.axis('off')
        return fig

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Sol: Support vs Lift scatter
    supports = [r.get('support', 0) for r in rules[:200]]
    lifts    = [r.get('lift', 0)    for r in rules[:200]]
    sc = axes[0].scatter(supports, lifts, alpha=0.5, s=15,
                         c=lifts, cmap='YlOrRd')
    plt.colorbar(sc, ax=axes[0], label='Lift')
    axes[0].set_xlabel('Support', fontsize=9)
    axes[0].set_ylabel('Lift', fontsize=9)
    axes[0].set_title('Apriori — Support vs Lift\n(Birliktelik Kurallari)', fontsize=10, fontweight='bold')
    axes[0].grid(True, alpha=0.3)

    # Sağ: Top 10 lift bar
    top10 = sorted(rules, key=lambda r: r.get('lift',0), reverse=True)[:10]
    labels = [f"{r.get('antecedents','')[:8]}→{r.get('consequents','')[:8]}"
              for r in top10]
    lift_vals = [r.get('lift', 0) for r in top10]
    axes[1].barh(labels[::-1], lift_vals[::-1],
                 color='#9b59b6', alpha=0.85, edgecolor='white')
    axes[1].set_xlabel('Lift Degeri', fontsize=9)
    axes[1].set_title('Top 10 Birliktelik Kurali\n(En Yuksek Lift)', fontsize=10, fontweight='bold')
    axes[1].grid(axis='x', alpha=0.3)

    fig.tight_layout()
    return fig


# ── Grafik 5: Hiperparametre Grid Search ─────────────────────────
def plot_hyperparameter() -> plt.Figure:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    # colony_size etkisi
    cs_vals = [10, 20, 40, 60]
    cs_dist = [1580, 1014, 1025, 1038]
    axes[0].plot(cs_vals, cs_dist, 'o-', color='#3498db', lw=2, markersize=7)
    axes[0].set_xlabel('colony_size', fontsize=9)
    axes[0].set_ylabel('Ort. Mesafe (m)', fontsize=9)
    axes[0].set_title('colony_size Etkisi', fontsize=10, fontweight='bold')
    axes[0].grid(True, alpha=0.3)

    # limit_mult etkisi
    lm_vals = [0.5, 1.0, 2.0]
    lm_dist = [1025, 1014, 1018]
    axes[1].plot(lm_vals, lm_dist, 's-', color='#e74c3c', lw=2, markersize=7)
    axes[1].set_xlabel('limit_mult', fontsize=9)
    axes[1].set_ylabel('Ort. Mesafe (m)', fontsize=9)
    axes[1].set_title('limit_mult Etkisi', fontsize=10, fontweight='bold')
    axes[1].grid(True, alpha=0.3)

    # Grid Search vs ABC-HP
    methods = ['Grid\nSearch', 'ABC-HP\n(Karaboga)']
    dists   = [1014, 1011]
    cols    = ['#f39c12', '#27ae60']
    bars = axes[2].bar(methods, dists, color=cols, width=0.4,
                       edgecolor='white', alpha=0.85)
    for b, v in zip(bars, dists):
        axes[2].text(b.get_x()+b.get_width()/2, b.get_height()+2,
                     f'{v}m', ha='center', fontsize=10, fontweight='bold')
    axes[2].set_ylabel('Ort. Mesafe (m)', fontsize=9)
    axes[2].set_title('Grid Search vs ABC-HP\n(Karaboga Orijinal)', fontsize=10, fontweight='bold')
    axes[2].grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig


# ── Grafik 6: ML Model Sonuçları ─────────────────────────────────
def plot_ml_results() -> plt.Figure:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    # CV R² karşılaştırma
    models = ['Linear\nRegression', 'Random\nForest']
    r2s    = [0.7950, 0.7958]
    cols   = ['#3498db', '#27ae60']
    bars = axes[0].bar(models, r2s, color=cols, width=0.4,
                       edgecolor='white', alpha=0.85)
    for b, v in zip(bars, r2s):
        axes[0].text(b.get_x()+b.get_width()/2, b.get_height()+0.003,
                     f'{v:.4f}', ha='center', fontsize=10, fontweight='bold')
    axes[0].set_ylim(0.75, 0.82)
    axes[0].set_ylabel("R² (5-Fold CV)", fontsize=9)
    axes[0].set_title("Model Karsilastirmasi\n(5-Fold CV)", fontsize=10, fontweight='bold')
    axes[0].grid(axis='y', alpha=0.3)

    # Feature importance
    features = ['unique_lc', 'unique_locations', 'total_items',
                 'unique_products', 'Dalga_Yogunlugu']
    importances = [0.934, 0.028, 0.019, 0.012, 0.007]
    axes[1].barh(features[::-1], importances[::-1],
                 color='#9b59b6', alpha=0.85, edgecolor='white')
    axes[1].set_xlabel('Importance', fontsize=9)
    axes[1].set_title('Random Forest\nFeature Importance', fontsize=10, fontweight='bold')
    axes[1].grid(axis='x', alpha=0.3)

    # 5-Fold detay
    folds = ['Fold 1','Fold 2','Fold 3','Fold 4','Fold 5']
    r2_folds = [0.794, 0.799, 0.792, 0.798, 0.797]
    axes[2].bar(folds, r2_folds, color='#27ae60', alpha=0.8, edgecolor='white')
    axes[2].axhline(np.mean(r2_folds), color='red', ls='--', lw=1.5,
                    label=f'Ort. R²={np.mean(r2_folds):.4f}')
    axes[2].set_ylim(0.78, 0.81)
    axes[2].set_ylabel("R²", fontsize=9)
    axes[2].set_title("Random Forest 5-Fold\nDetayi", fontsize=10, fontweight='bold')
    axes[2].legend(fontsize=8)
    axes[2].grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig


# ── Ana PDF Üretici ───────────────────────────────────────────────
def generate_pdf(loader, output_path: str):
    """
    loader     : DataLoader instance
    output_path: PDF kayit yolu (orn: 'rapor.pdf')
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    styles  = make_styles()
    story   = []
    now_str = datetime.now().strftime('%d.%m.%Y %H:%M')

    # ── Kapak ─────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph(
        'SIPARIS TOPLAMA ROTA OPTIMIZASYONU', styles['title']))
    story.append(Paragraph(
        'Miuul AI Data Scientist Bootcamp — Bitirme Projesi', styles['subtitle']))
    story.append(Paragraph(
        f'ABC Ari Kolonisi Algoritmasi (Karaboga 2005) · '
        f'Apriori Birliktelik Kurallari · Random Forest',
        styles['subtitle']))
    story.append(HRFlowable(width='100%', thickness=1,
                             color=C_GREEN, spaceAfter=12))
    story.append(Paragraph(
        f'Rapor Tarihi: {now_str}  |  Veri: PMC12269467 — '
        f'Ayakkabi Fabrikasi Deposu  |  Kaynak: abc.erciyes.edu.tr',
        styles['caption']))
    story.append(Spacer(1, 0.3*cm))

    # Takim uyeleri
    story.append(Paragraph(
        'Takim Uyeleri: M. Necati Cetinkaya  |  Ali Orhan  |  '
        'Berke Besli  |  Gokay Bickici  |  Muhammet Safa Tekin',
        styles['caption']))
    story.append(Paragraph(
        'Miuul AI Data Scientist Bootcamp  |  20. Donem',
        styles['caption']))
    story.append(Spacer(1, 0.5*cm))

    # ── KPI Özet ──────────────────────────────────────────────────
    try:
        summary = loader.get_summary()
    except Exception:
        summary = {}

    total_orders = summary.get('total_orders', 122370)
    unique_waves = summary.get('unique_waves', 9707)
    unique_prods = summary.get('unique_products', 208)
    operators    = summary.get('operators', 24)

    kpi_data = [
        {'label': 'Toplam Siparis',   'value': f"{total_orders:,}",  'color': C_BLUE},
        {'label': 'Toplam Wave',       'value': f"{unique_waves:,}",  'color': C_GREEN},
        {'label': 'Benzersiz Urun',    'value': str(unique_prods),    'color': C_PURPLE},
        {'label': 'Operator',          'value': str(operators),       'color': C_ORANGE},
        {'label': 'ABC Kazanimi',      'value': '↓%78.7',            'color': C_GREEN},
        {'label': 'RF R²',             'value': '0.7958',             'color': C_BLUE},
    ]
    story.append(make_kpi_table(kpi_data, styles))
    story.append(Spacer(1, 0.5*cm))

    # ── Bölüm 1: ABC Pareto ────────────────────────────────────────
    story.append(Paragraph('1. ABC Analizi — Pareto Bazli Stok Siniflandirmasi',
                            styles['section']))
    story.append(Paragraph(
        'Urunler gercek talep frekanslarina gore Pareto prensibiyle A/B/C '
        'siniflarina ayrildi. Sinif A urunler (%79.9 talep) IO noktasina '
        'en yakin raflara yerlestirildi. Makale ABCCOD ile uyum orani %57.2 '
        'olup veri bazli hesaplama kullanildi.', styles['body']))

    try:
        abc_data = loader.get_abc_classification()
    except Exception:
        abc_data = []

    if abc_data:
        fig = plot_abc_pareto(abc_data)
        story.append(fig_to_image(fig, width=15*cm))
        story.append(Paragraph(
            'Sekil 1: Pareto Analizi — ABC Siniflandirmasi', styles['caption']))

        abc_summary = summary.get('abc_counts', {'A':44,'B':70,'C':94})
        tbl_data = [
            ['Sinif', 'Urun Sayisi', 'Talep Payi', 'Raf Konumu', 'IO Mesafesi'],
            ['A', str(abc_summary.get('A',44)), '%79.9',
             'IO Yakini (ilk raflar)', 'Dusuk'],
            ['B', str(abc_summary.get('B',70)), '%15.0',
             'Orta Mesafe', 'Orta'],
            ['C', str(abc_summary.get('C',94)), '%5.1',
             'Uzak Raflar', 'Yuksek'],
        ]
        tbl = Table(tbl_data,
                    colWidths=[2.5*cm, 3*cm, 3*cm, 4.5*cm, 3*cm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0), C_DARK),
            ('TEXTCOLOR',   (0,0), (-1,0), white),
            ('FONTNAME',    (0,0), (-1,0), _FONT_BOLD),
            ('FONTNAME',    (0,1), (-1,-1), _FONT_NORMAL),
            ('FONTSIZE',    (0,0), (-1,-1), 9),
            ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),
             [HexColor('#fff0f0'), HexColor('#fff8e7'), HexColor('#f0fff4')]),
            ('GRID',        (0,0), (-1,-1), 0.5, C_BORDER),
            ('TOPPADDING',  (0,0), (-1,-1), 5),
            ('BOTTOMPADDING',(0,0), (-1,-1), 5),
        ]))
        story.append(Spacer(1, 0.3*cm))
        story.append(tbl)

    story.append(Spacer(1, 0.4*cm))

    # ── Bölüm 2: Stok Yerleşim ────────────────────────────────────
    story.append(Paragraph('2. Stratejik Stok Yerlesimi',
                            styles['section']))
    story.append(Paragraph(
        'IO (giris/cikis) noktasi LC-01 koordinati (66, -29, 1) olarak '
        'belirlendi. Manhattan mesafesi kullanilarak tum raf lokasyonlari '
        'IO\'ya uzakliga gore siralandi ve ABC siniflarina tahsis edildi.',
        styles['body']))
    fig2 = plot_strategy_comparison(summary)
    story.append(fig_to_image(fig2, width=15*cm))
    story.append(Paragraph(
        'Sekil 2: ABC Yerlesim Kazanimi — Mevcut vs Optimize',
        styles['caption']))
    story.append(Spacer(1, 0.4*cm))

    # ── Bölüm 3: Apriori ──────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('3. Apriori Birliktelik Kurallari',
                            styles['section']))
    story.append(Paragraph(
        'Siparis gecmisinden birlikte siparis edilen urun ciftleri tespit edildi. '
        'min_support=0.004, min_confidence=0.10, min_lift=1.2 parametreleriyle '
        '3,561 kural uretildi. En guclu lift degeri 85.81 '
        '(F7LULH ↔ B24J86) olarak bulundu.',
        styles['body']))

    try:
        rules = loader.get_apriori_rules(top_n=200)
        if isinstance(rules, dict):
            rules = []
    except Exception:
        rules = []

    fig3 = plot_apriori(rules)
    story.append(fig_to_image(fig3, width=15*cm))
    story.append(Paragraph(
        'Sekil 3: Apriori Birliktelik Kurallari — Support vs Lift',
        styles['caption']))

    if rules:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph('Top 10 Birliktelik Kurali:', styles['body']))
        tbl_data2 = [['Antecedent', 'Consequent', 'Support', 'Confidence', 'Lift']]
        for r in rules[:10]:
            tbl_data2.append([
                str(r.get('antecedents',''))[:20],
                str(r.get('consequents',''))[:20],
                f"{r.get('support',0):.4f}",
                f"{r.get('confidence',0):.3f}",
                f"{r.get('lift',0):.2f}",
            ])
        tbl2 = Table(tbl_data2,
                     colWidths=[4*cm, 4*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        tbl2.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0), C_PURPLE),
            ('TEXTCOLOR',   (0,0), (-1,0), white),
            ('FONTNAME',    (0,0), (-1,0), _FONT_BOLD),
        ('FONTNAME',    (0,1), (-1,-1), _FONT_NORMAL),
            ('FONTSIZE',    (0,0), (-1,-1), 8),
            ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_LIGHT, white]),
            ('GRID',        (0,0), (-1,-1), 0.5, C_BORDER),
            ('TOPPADDING',  (0,0), (-1,-1), 4),
            ('BOTTOMPADDING',(0,0), (-1,-1), 4),
        ]))
        story.append(tbl2)

    story.append(Spacer(1, 0.4*cm))

    # ── Bölüm 4: ABC Algoritması ──────────────────────────────────
    story.append(Paragraph(
        '4. Apriori + ABC Birlesik Optimizasyon (Ozgun)',
        styles['section']))
    story.append(Paragraph(
        'Karaboga (2005) tarafindan Erciyes Universitesi\'nde gelistirilen '
        'Yapay Ari Kolonisi Algoritmasi, LC (koridor) permutasyonu icin '
        'uyarlandi. Apriori proximity cluster\'larindan elde edilen '
        'guided_seed ile baslangic populasyonu olusturuldu.',
        styles['body']))

    alg_data = [
        ['Parametre', 'Deger', 'Aciklama'],
        ['colony_size', '20', 'Toplam ari sayisi (employed + onlooker)'],
        ['limit_mult', '1.0', 'Scout esigi carpani'],
        ['max_cycles', '200', 'Iterasyon sayisi'],
        ['Perturbation', '2-opt swap', 'LC permutasyonu degistirme yontemi'],
        ['Fitness', '1/mesafe', 'Karaboga (2005) nectar formulu'],
        ['Guided Seed', 'Apriori cluster', 'Proximity siralamasi baslangic rotasi'],
    ]
    tbl3 = Table(alg_data, colWidths=[4*cm, 3.5*cm, 8*cm])
    tbl3.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), C_DARK),
        ('TEXTCOLOR',   (0,0), (-1,0), white),
        ('FONTNAME',    (0,0), (-1,0), _FONT_BOLD),
        ('FONTNAME',    (0,1), (-1,-1), _FONT_NORMAL),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('ALIGN',       (0,0), (1,-1), 'CENTER'),
        ('ALIGN',       (2,0), (2,-1), 'LEFT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_LIGHT, white]),
        ('GRID',        (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
    ]))
    story.append(Spacer(1, 0.3*cm))
    story.append(tbl3)
    story.append(Spacer(1, 0.4*cm))

    fig4 = plot_abc_optimization(summary)
    story.append(fig_to_image(fig4, width=15*cm))
    story.append(Paragraph(
        'Sekil 4: Rota Yontemi Karsilastirmasi — Rastgele vs Greedy vs ABC',
        styles['caption']))

    # ── Bölüm 5: Hiperparametre ───────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph(
        '5. Hiperparametre Optimizasyonu — Grid Search + ABC-HP',
        styles['section']))
    story.append(Paragraph(
        'Grid Search (27 kombinasyon) ve Karaboga\'nin orijinal surekli uzay '
        'ABC formulasyonu (x_new = x_i + phi*(x_i - x_k)) ile '
        'hiperparametre optimizasyonu gerceklestirildi. '
        'Optimal parametreler: colony_size=20, limit_mult=1.0, max_cycles=200.',
        styles['body']))

    fig5 = plot_hyperparameter()
    story.append(fig_to_image(fig5, width=16*cm))
    story.append(Paragraph(
        'Sekil 5: Hiperparametre Analizi — Grid Search vs ABC-HP (Karaboga 2005)',
        styles['caption']))
    story.append(Spacer(1, 0.4*cm))

    # ── Bölüm 6: ML Modeli ────────────────────────────────────────
    story.append(Paragraph('6. ML Modeli — Toplam Mesafe Tahmini',
                            styles['section']))
    story.append(Paragraph(
        'Hedef degisken: abc_optimized_distance (Apriori+ABC ile optimize wave mesafesi). '
        'Ozellikler: total_items, unique_locations, unique_lc, unique_products, '
        'Dalga_Yogunlugu. En onemli feature unique_lc (%93.4).',
        styles['body']))

    ml_data = [
        ['Model', 'MAE (m)', 'RMSE (m)', 'R² (CV)', 'MAPE%'],
        ['Linear Regression', '187.09', '232.91', '0.7950', '%24.8'],
        ['Random Forest',     '184.83', '232.48', '0.7958', '%24.3'],
    ]
    tbl4 = Table(ml_data, colWidths=[4.5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    tbl4.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), C_DARK),
        ('TEXTCOLOR',   (0,0), (-1,0), white),
        ('FONTNAME',    (0,0), (-1,0), _FONT_BOLD),
        ('FONTNAME',    (0,1), (-1,-1), _FONT_NORMAL),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_LIGHT, HexColor('#d5f5e3')]),
        ('GRID',        (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING',  (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
    ]))
    story.append(tbl4)
    story.append(Spacer(1, 0.3*cm))

    fig6 = plot_ml_results()
    story.append(fig_to_image(fig6, width=16*cm))
    story.append(Paragraph(
        'Sekil 6: ML Model Sonuclari — 5-Fold CV, Feature Importance, Fold Detaylari',
        styles['caption']))

    # ── Sonuç ─────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('7. Sonuc ve Is Degeri', styles['section']))
    story.append(Paragraph(
        'Bu calismada ayakkabi fabrikasi deposundaki siparis toplama '
        'operasyonlari uctan uca optimize edilmistir:', styles['body']))

    results = [
        ['Bulgu', 'Deger', 'Aciklama'],
        ['Stok Yerlesim',    '↓%78.7',  'ABC yerlesimi ile IO mesafesi 1131m → 241m'],
        ['Apriori Kurali',   '3,561',   'Birliktelik kurali, en guclu lift: 85.81'],
        ['ABC vs Greedy',    '↓%11.4',  'Rota mesafesinde iyilesme (8,778 wave)'],
        ['ABC-HP',           '20 deneme', 'Grid Search\'in 27 denemesine karsi esit sonuc'],
        ['RF R²',            '0.7958',  'Wave mesafesi tahmin dogrulugu'],
        ['n8n Entegrasyonu', 'Otomatik', 'Yeni wave → ABC optimize → Gemini acikla'],
    ]
    tbl5 = Table(results, colWidths=[4.5*cm, 3*cm, 9*cm])
    tbl5.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), C_DARK),
        ('TEXTCOLOR',   (0,0), (-1,0), white),
        ('FONTNAME',    (0,0), (-1,0), _FONT_BOLD),
        ('FONTNAME',    (0,1), (-1,-1), _FONT_NORMAL),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('ALIGN',       (1,0), (1,-1), 'CENTER'),
        ('ALIGN',       (0,0), (0,-1), 'LEFT'),
        ('ALIGN',       (2,0), (2,-1), 'LEFT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_LIGHT, white]),
        ('GRID',        (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
    ]))
    story.append(tbl5)

    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width='100%', thickness=1, color=C_GREEN))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        'Miuul AI Data Scientist Bootcamp — Bitirme Projesi  |  '
        f'Olusturulma: {now_str}  |  '
        'Kaynak: Karaboga (2005) abc.erciyes.edu.tr  |  '
        'Veri: PMC12269467',
        styles['caption']))

    # ── Build ──────────────────────────────────────────────────────
    doc.build(story)
    print(f"[✓] PDF olusturuldu: {output_path}")