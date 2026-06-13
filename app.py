"""Satış Destek Sistemi — Ana Sayfa."""

from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Satış Destek Sistemi",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Stil
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%);
        border-radius: 12px;
        padding: 20px 24px;
        color: white;
        margin-bottom: 8px;
    }
    .metric-card .label { font-size: 13px; opacity: 0.85; margin-bottom: 4px; }
    .metric-card .value { font-size: 32px; font-weight: 700; line-height: 1; }
    .metric-card .sub   { font-size: 12px; opacity: 0.75; margin-top: 4px; }

    .section-header {
        font-size: 18px; font-weight: 700; color: #1565C0;
        border-left: 4px solid #1565C0; padding-left: 10px;
        margin: 24px 0 12px 0;
    }
    .nav-card {
        background: #F0F4F8; border-radius: 10px; padding: 16px 20px;
        border: 1px solid #E2E8F0; cursor: pointer;
    }
    .nav-card:hover { border-color: #1565C0; }
    .nav-title { font-weight: 700; font-size: 15px; color: #1A1A2E; }
    .nav-desc  { font-size: 13px; color: #64748B; margin-top: 4px; }
    div[data-testid="stSidebar"] { background-color: #0D47A1; }
    div[data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Metrikleri hesapla
# ---------------------------------------------------------------------------
@st.cache_data
def load_metrics() -> dict:
    metrics = {
        "toplam_bayi": 22,
        "toplam_arac_ocak": 250,
        "fill_rate": "100%",
        "aktif_model": 3,
    }

    alloc_path = ROOT / "outputs" / "allocation" / "2026_01" / "dealer_summary.csv"
    if alloc_path.exists():
        df = pd.read_csv(alloc_path, sep=";", encoding="utf-8-sig")
        metrics["toplam_bayi"] = len(df)
        metrics["toplam_arac_ocak"] = int(df["allocated"].sum())
        metrics["fill_rate"] = f"{(df['allocated'].sum() / df['target'].sum() * 100):.0f}%"

    inv_path = ROOT / "outputs" / "allocation" / "2026_01" / "inventory_usage.csv"
    if inv_path.exists():
        df_inv = pd.read_csv(inv_path, sep=";", encoding="utf-8-sig")
        metrics["aktif_model"] = df_inv["model"].nunique()

    return metrics


metrics = load_metrics()

# ---------------------------------------------------------------------------
# Başlık
# ---------------------------------------------------------------------------
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("## 🚗")
with col_title:
    st.markdown("# Satış Destek Sistemi")
    st.caption("Otomotiv Bayi Araç Dağıtım Optimizasyon Platformu · Ocak 2026")

st.divider()

# ---------------------------------------------------------------------------
# KPI Kartları
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Aktif Bayi</div>
        <div class="value">{metrics['toplam_bayi']}</div>
        <div class="sub">Ocak 2026</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Dağıtılan Araç</div>
        <div class="value">{metrics['toplam_arac_ocak']:,}</div>
        <div class="sub">Ocak 2026 hedefi</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Hedef Doluluk</div>
        <div class="value">{metrics['fill_rate']}</div>
        <div class="sub">Tüm bayiler karşılandı</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Aktif Model</div>
        <div class="value">{metrics['aktif_model']}</div>
        <div class="sub">SUV segmenti</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Navigasyon Kartları
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Bölümler</div>', unsafe_allow_html=True)

nav1, nav2, nav3, nav4 = st.columns(4)

with nav1:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-title">📊 Geçmiş Satış Analizi</div>
        <div class="nav-desc">2024–2025 model, versiyon, renk ve bayi bazlı satış grafikleri</div>
    </div>
    """, unsafe_allow_html=True)

with nav2:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-title">📅 Mevsimsellik</div>
        <div class="nav-desc">Aylık talep indeksleri, bayi ve model bazlı mevsimsel profiller</div>
    </div>
    """, unsafe_allow_html=True)

with nav3:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-title">🎯 Ocak 2026 Dağıtımı</div>
        <div class="nav-desc">Mevcut ay dağıtım sonuçları, skor analizi ve envanter kullanımı</div>
    </div>
    """, unsafe_allow_html=True)

with nav4:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-title">⚡ Yeni Dağıtım</div>
        <div class="nav-desc">Yeni envanter ve hedef dosyası yükleyerek dağıtım hesapla</div>
    </div>
    """, unsafe_allow_html=True)

st.caption("Sol menüden ilgili bölüme gidin.")

# ---------------------------------------------------------------------------
# Sistem Hakkında
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<div class="section-header">Sistem Hakkında</div>', unsafe_allow_html=True)

info1, info2 = st.columns([3, 2])

with info1:
    st.markdown("""
    Bu sistem, otomotiv markasının 22 bayisine aylık araç dağıtımını otomatize eden
    bir karar destek aracıdır. Üç ana bileşenden oluşur:

    **1. Çok Kriterli Skorlama (MCDM)**
    - **P — Performans (%25):** Son aylık satış gerçekleşme oranı (EWMA)
    - **LP — Ürün Uyumu (%35):** Bayinin geçmiş satış profiliyle cosine benzerliği
    - **S — Mevsimsellik (%20):** Bayinin o aya özgü mevsimsel indeksi
    - **H — Hedef Yakınlık (%20):** Aylık hedef büyüklüğü önceliği

    **2. MILP Optimizasyonu**
    Karar değişkeni `x[bayi, araç_tipi]`; PuLP/CBC solver ile
    bileşik skor maksimize edilirken envanter ve bayi hedef kısıtları sağlanır.

    **3. Mevsimsellik Modelleme**
    ODD ve segment piyasa verisiyle veri-odaklı ağırlıklandırma
    (YoY Pearson r kararlılık analizi).
    """)

with info2:
    score_path = ROOT / "outputs" / "allocation" / "2026_01" / "dealer_scores.csv"
    if score_path.exists():
        df_scores = pd.read_csv(score_path, sep=";", encoding="utf-8-sig")
        df_top = df_scores.nlargest(5, "composite_score")[
            ["dealer_name", "composite_score"]
        ].rename(columns={"dealer_name": "Bayi", "composite_score": "Bileşik Skor"})
        df_top["Bileşik Skor"] = df_top["Bileşik Skor"].map("{:.3f}".format)
        st.markdown("**En Yüksek Skorlu 5 Bayi**")
        st.dataframe(df_top, hide_index=True, use_container_width=True)
