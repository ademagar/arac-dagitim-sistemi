"""Geçmiş Satış Analizi sayfası."""

from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Geçmiş Satış Analizi", page_icon="📊", layout="wide")

ROOT = Path(__file__).parents[1]
IMG = ROOT / "outputs" / "images"
OUT = ROOT / "outputs"

st.title("📊 Geçmiş Satış Analizi")
st.caption("2024 ve 2025 yıllarına ait model, versiyon, renk ve bayi bazlı satış verileri")

# ---------------------------------------------------------------------------
# Yıl seçimi
# ---------------------------------------------------------------------------
year = st.radio(
    "Dönem seçin",
    ["2024", "2025", "Tümü (2024–2025)"],
    horizontal=True,
)
year_key = {"2024": "2024", "2025": "2025", "Tümü (2024–2025)": "all"}[year]
img_dir = IMG / year_key
out_dir = OUT / year_key

st.divider()


def show_image(path: Path, caption: str = "") -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"Görsel henüz oluşturulmamış: {path.name}")


def show_csv(path: Path, label: str = "") -> None:
    if path.exists():
        df = pd.read_csv(path, encoding="utf-8-sig")
        if label:
            st.markdown(f"**{label}**")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(f"Veri henüz oluşturulmamış: {path.name}")


# ---------------------------------------------------------------------------
# İçerik
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Model & Versiyon", "Renk & Bayi", "Aylık Trend", "Hedef Gerçekleşme"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        show_image(img_dir / "01_model_satislari.png", "Model Bazında Satışlar")
    with c2:
        show_image(img_dir / "02_versiyon_satislari.png", "Versiyon Bazında Satışlar")

    st.markdown("---")
    show_image(img_dir / "06_bayi_model_heatmap.png", "Bayi × Model Satış Isı Haritası")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        show_csv(out_dir / "01_model_satislari.csv", "Model Satış Verileri")
    with col_t2:
        show_csv(out_dir / "02_versiyon_satislari.csv", "Versiyon Satış Verileri")

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        show_image(img_dir / "03_renk_dagilimi.png", "Renk Dağılımı")
    with c2:
        show_image(img_dir / "04_bayi_toplam_satis.png", "Bayi Toplam Satış")

    c3, c4 = st.columns(2)
    with c3:
        show_image(img_dir / "07_kanal_dagilimi.png", "Kanal Dağılımı (B2C / B2B)")
    with c4:
        show_csv(out_dir / "03_renk_satislari.csv", "Renk Satış Verileri")

    show_csv(out_dir / "04_bayi_toplam_satis.csv", "Bayi Toplam Satış Verileri")

with tab3:
    show_image(img_dir / "05_aylik_trend.png", "Aylık Satış Trendi")

    if year_key == "all":
        c1, c2 = st.columns(2)
        with c1:
            show_image(img_dir / "09_model_aylik_trend.png", "Model × Aylık Trend")
        with c2:
            show_image(img_dir / "10_yoy_karsilastirma.png", "YoY Karşılaştırma")
        show_image(img_dir / "12_model_ay_heatmap.png", "Model × Ay Isı Haritası")
        show_csv(out_dir / "08_aylik_trend.csv", "Aylık Trend Verileri")
    else:
        if year_key == "2025":
            show_image(img_dir / "12_model_ay_heatmap.png", "Model × Ay Isı Haritası")
        show_csv(out_dir / "08_aylik_trend.csv", "Aylık Trend Verileri")

with tab4:
    show_image(img_dir / "08_hedef_gerceklestirme.png", "Hedef Gerçekleşme Analizi")

    if year_key == "all":
        show_image(img_dir / "11_rakip_karsilastirma.png", "Rakip Karşılaştırma")
        show_csv(out_dir / "12_aylik_hedef_performansi.csv", "Aylık Hedef Performansı")
        show_csv(out_dir / "13_bayi_2025_performansi.csv", "Bayi 2025 Performansı")
    else:
        show_csv(out_dir / "12_hedef_gerceklestirme_long.csv", "Hedef Gerçekleşme (Uzun Format)")
