"""Ocak 2026 Dağıtım Sonuçları sayfası."""

from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ocak 2026 Dağıtımı", page_icon="🎯", layout="wide")

ROOT = Path(__file__).parents[1]
ALLOC = ROOT / "outputs" / "allocation" / "2026_01"

# Henüz dağıtım yapılmadıysa yönlendir
alloc_csv = ALLOC / "allocation_january2026.csv"
if not alloc_csv.exists():
    st.title("🎯 Ocak 2026 Dağıtımı")
    st.info(
        "Ocak 2026 dağıtımı henüz yapılmadı.\n\n"
        "**⚡ Yeni Dağıtım** sayfasına giderek envanter dosyasını yükleyin "
        "ve bayi hedeflerini girerek dağıtımı oluşturun.",
        icon="ℹ️",
    )
    st.page_link("pages/4_Yeni_Dagitim.py", label="Yeni Dağıtım sayfasına git →", icon="⚡")
    st.stop()


def show_image(path: Path, caption: str = "") -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"Görsel bulunamadı: {path.name}")


@st.cache_data
def load_alloc() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    def read(name: str) -> pd.DataFrame:
        p = ALLOC / name
        return pd.read_csv(p, sep=";", encoding="utf-8-sig") if p.exists() else pd.DataFrame()

    return (
        read("allocation_january2026.csv"),
        read("dealer_summary.csv"),
        read("dealer_scores.csv"),
        read("inventory_usage.csv"),
    )


df_alloc, df_summary, df_scores, df_inv = load_alloc()

# ---------------------------------------------------------------------------
# Başlık + KPI
# ---------------------------------------------------------------------------
st.title("🎯 Ocak 2026 Dağıtım Sonuçları")

if not df_summary.empty:
    total_allocated = int(df_summary["allocated"].sum())
    total_target    = int(df_summary["target"].sum())
    fill_rate       = total_allocated / total_target * 100 if total_target > 0 else 0
    n_dealers       = len(df_summary)
    n_types         = df_alloc["vehicle_type"].nunique() if not df_alloc.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Atanan", f"{total_allocated:,}", f"/{total_target:,} hedef")
    m2.metric("Doluluk Oranı", f"{fill_rate:.0f}%")
    m3.metric("Aktif Bayi", n_dealers)
    m4.metric("Araç Tipi Çeşidi", n_types)

st.divider()

# ---------------------------------------------------------------------------
# Sekmeler
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dağıtım Haritası",
    "Bayi Özeti",
    "Model Dağılımı",
    "Skor Analizi",
    "Envanter Kullanımı",
])

with tab1:
    show_image(ALLOC / "01_allocation_heatmap.png", "Bayi × Model Atama Isı Haritası")

    if not df_alloc.empty:
        st.markdown("**Tam Dağıtım Tablosu**")

        # Filtre
        dealer_filter = st.multiselect(
            "Bayi filtrele",
            options=sorted(df_alloc["dealer_name"].unique()),
            default=[],
            key="alloc_dealer",
        )
        model_filter = st.multiselect(
            "Model filtrele",
            options=sorted(df_alloc["model"].unique()),
            default=[],
            key="alloc_model",
        )

        df_view = df_alloc.copy()
        if dealer_filter:
            df_view = df_view[df_view["dealer_name"].isin(dealer_filter)]
        if model_filter:
            df_view = df_view[df_view["model"].isin(model_filter)]

        st.dataframe(
            df_view.rename(columns={
                "dealer_name": "Bayi", "dealer_code": "Kod",
                "model": "Model", "version": "Versiyon",
                "color": "Renk", "allocated_qty": "Atanan",
                "composite_score": "Bileşik Skor",
                "lp_affinity_score": "LP Affinity",
            }),
            use_container_width=True,
            hide_index=True,
        )

        csv_data = df_alloc.to_csv(index=False, sep=";", encoding="utf-8-sig")
        st.download_button(
            "⬇️  CSV İndir",
            data=csv_data.encode("utf-8-sig"),
            file_name="allocation_january2026.csv",
            mime="text/csv",
        )

with tab2:
    show_image(ALLOC / "02_dealer_summary.png", "Bayi Hedef vs Atanan")

    if not df_summary.empty:
        df_sum_display = df_summary.copy()
        df_sum_display["fill_rate"] = df_sum_display["fill_rate"].map("{:.1f}%".format)
        df_sum_display = df_sum_display.sort_values("allocated", ascending=False)
        st.dataframe(
            df_sum_display.rename(columns={
                "dealer_name": "Bayi", "dealer_code": "Kod",
                "target": "Hedef", "allocated": "Atanan",
                "gap": "Fark", "fill_rate": "Doluluk",
            }),
            use_container_width=True,
            hide_index=True,
        )

with tab3:
    show_image(ALLOC / "03_model_distribution.png", "Bayi × Model Dağılımı (Stacked)")

with tab4:
    show_image(ALLOC / "04_score_breakdown.png", "Bayi Skor Bileşenleri")

    if not df_scores.empty:
        df_sc = df_scores.copy()
        for col in ["p_score", "s_score", "h_score", "composite_score"]:
            if col in df_sc.columns:
                df_sc[col] = df_sc[col].map("{:.3f}".format)
        st.dataframe(
            df_sc.rename(columns={
                "dealer_name": "Bayi",
                "p_score": "P (Performans)",
                "s_score": "S (Mevsim)",
                "h_score": "H (Hedef)",
                "composite_score": "Bileşik Skor",
            }),
            use_container_width=True,
            hide_index=True,
        )

with tab5:
    show_image(ALLOC / "05_inventory_usage.png", "Envanter Kullanım Oranı")

    if not df_inv.empty:
        df_inv_display = df_inv.copy()
        df_inv_display["usage_rate"] = df_inv_display["usage_rate"].map("{:.1f}%".format)
        st.dataframe(
            df_inv_display.rename(columns={
                "vehicle_type": "Araç Tipi", "model": "Model",
                "version": "Versiyon", "color": "Renk",
                "quantity": "Toplam", "used": "Atanan",
                "remaining": "Kalan", "usage_rate": "Kullanım",
            }),
            use_container_width=True,
            hide_index=True,
        )
