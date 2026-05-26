"""Mevsimsellik Analizi sayfası."""

from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Mevsimsellik Analizi", page_icon="📅", layout="wide")

ROOT = Path(__file__).parents[1]
SEA = ROOT / "outputs" / "seasonality"

st.title("📅 Mevsimsellik Analizi")
st.caption("ODD piyasa verisi ve segment verisinden türetilen aylık talep indeksleri")


def show_image(path: Path, caption: str = "") -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"Görsel bulunamadı: {path.name}")


def show_csv(path: Path, label: str = "") -> None:
    if path.exists():
        df = pd.read_csv(path, encoding="utf-8-sig")
        if label:
            st.markdown(f"**{label}**")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(f"Veri bulunamadı: {path.name}")


# ---------------------------------------------------------------------------
# Ağırlık bilgisi
# ---------------------------------------------------------------------------
weight_path = SEA / "09_agirlik_analizi.csv"
if weight_path.exists():
    df_w = pd.read_csv(weight_path, encoding="utf-8-sig")
    st.info(
        f"**Veri Kaynağı Ağırlıkları** — "
        + " | ".join(
            f"{row.iloc[0]}: **{row.iloc[2]:.1%}**"
            for _, row in df_w.iterrows()
        ),
        icon="ℹ️",
    )

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "Piyasa İndeksleri",
    "Bayi Mevsimselliği",
    "Model & Renk",
    "Northstar vs Piyasa",
])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        show_image(SEA / "01_piyasa_hiyerarsisi.png", "Piyasa Hiyerarşisi Mevsimsel İndeks")
    with c2:
        show_image(SEA / "02_final_indeks_bar.png", "Final Mevsimsel İndeks (Bar)")

    show_image(SEA / "03_final_indeks_polar.png", "Final Mevsimsel İndeks (Polar)")

    col1, col2 = st.columns(2)
    with col1:
        show_csv(SEA / "01_mevsimsel_indeksler.csv", "Piyasa Mevsimsel İndeksler")
    with col2:
        show_csv(SEA / "04_FINAL_si.csv", "Final Mevsimsel İndeks (Ağırlıklı)")

with tab2:
    show_image(SEA / "04_bayi_heatmap.png", "Bayi × Ay Mevsimsellik Isı Haritası")
    _si_path = SEA / "05_bayi_si.csv"
    if _si_path.exists():
        _df_si = pd.read_csv(_si_path, encoding="utf-8-sig")
        _df_si = _df_si.loc[:, ~_df_si.columns.str.startswith("Unnamed")]
        _non_d = [c for c in _df_si.columns if not c.startswith("DEALER")]
        _dealer_cols = sorted(
            [c for c in _df_si.columns if c.startswith("DEALER")],
            key=lambda x: int(x.split()[-1]),
        )
        _df_si = _df_si[_non_d + _dealer_cols]
        st.markdown("**Bayi Bazında Mevsimsel İndeks**")
        st.dataframe(_df_si, use_container_width=True, hide_index=True)
    else:
        st.info("Veri bulunamadı: 05_bayi_si.csv")

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        show_image(SEA / "05_model_heatmap.png", "Model × Ay Mevsimsellik")
    with c2:
        show_image(SEA / "06_renk_heatmap.png", "Renk × Ay Mevsimsellik")

    c3, c4 = st.columns(2)
    with c3:
        show_csv(SEA / "06_model_si.csv", "Model Mevsimsel İndeks")
    with c4:
        show_csv(SEA / "07_renk_si.csv", "Renk Mevsimsel İndeks")

    show_csv(SEA / "02_rakip_mevsimsel_indeksler.csv", "Rakip Marka Bazında Mevsimsel İndeks")

with tab4:
    show_image(SEA / "05_northstar_vs_piyasa.png", "Northstar vs Piyasa Mevsimsel Profili")
    show_image(SEA / "07_aylik_plan.png", "Aylık Dağıtım Planı")

    if (SEA / "mevsimsellik_raporu.txt").exists():
        with st.expander("📄 Mevsimsellik Raporu"):
            st.text((SEA / "mevsimsellik_raporu.txt").read_text(encoding="utf-8"))
