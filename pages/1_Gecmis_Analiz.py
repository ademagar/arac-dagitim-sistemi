"""Geçmiş Satış Analizi sayfası."""

from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Geçmiş Satış Analizi", page_icon="📊", layout="wide")

ROOT = Path(__file__).parents[1]
IMG = ROOT / "outputs" / "images"
OUT = ROOT / "outputs"

# ---------------------------------------------------------------------------
# Sabitler: sütun yeniden adlandırma ve ay çevirileri
# ---------------------------------------------------------------------------
_RENAME: dict[str, str] = {
    "model":          "Model",
    "total_sales":    "Toplam Satış",
    "share_pct":      "Pay (%)",
    "version":        "Versiyon",
    "Exterior Color": "Renk",
    "Dealer Name":    "Bayi",
    "dealer_name":    "Bayi",
    "year":           "Yıl",
    "month":          "Ay",
    "sales_qty":      "Satış",
    "year_month":     "Dönem",
    "channel":        "Kanal",
    "metric_type":    "Metrik",
    "value":          "Değer",
    "actual_qty":     "Gerçekleşen",
    "brand":          "Marka",
}

_EN_FULL: dict[str, str] = {
    "JANUARY": "Ocak", "FEBRUARY": "Şubat", "MARCH": "Mart",
    "APRIL": "Nisan", "MAY": "Mayıs", "JUNE": "Haziran",
    "JULY": "Temmuz", "AUGUST": "Ağustos", "SEPTEMBER": "Eylül",
    "OCTOBER": "Ekim", "NOVEMBER": "Kasım", "DECEMBER": "Aralık",
}

_ABBR: dict[str, str] = {
    "JAN": "Oca", "FEB": "Şub", "MAR": "Mar", "APR": "Nis",
    "MAY": "May", "JUN": "Haz", "JUL": "Tem", "AUG": "Ağu",
    "SEP": "Eyl", "OCT": "Eki", "NOV": "Kas", "DEC": "Ara",
}

_NUM: dict[int, str] = {
    1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
    7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara",
}


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------
def _fmt_abbr(val: str, show_year: bool = False) -> str:
    """'JAN'24' → 'Oca' veya '2024 Oca'."""
    parts = str(val).split("'")
    tr = _ABBR.get(parts[0][:3].upper(), parts[0])
    if show_year and len(parts) > 1:
        return f"20{parts[1]} {tr}"
    return tr


def _fmt_ym(val: str, show_year: bool = True) -> str:
    """'2024-01' → '2024 Oca' veya 'Oca'."""
    try:
        y, m = str(val).split("-")
        tr = _NUM.get(int(m), m)
        return f"{y} {tr}" if show_year else tr
    except (ValueError, AttributeError):
        return str(val)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Unnamed sütunları ve month_num'u sil, sütunları Türkçeleştir."""
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    if "month_num" in df.columns:
        df = df.drop(columns=["month_num"])
    return df.rename(columns={k: v for k, v in _RENAME.items() if k in df.columns})


def _load(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def show_image(path: Path, caption: str = "") -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"Görsel henüz oluşturulmamış: {path.name}")


def show_df(df: pd.DataFrame, label: str = "") -> None:
    if label:
        st.markdown(f"**{label}**")
    st.dataframe(df, use_container_width=True, hide_index=True)


def show_csv(path: Path, label: str = "") -> None:
    df = _load(path)
    if df is None:
        st.info(f"Veri henüz oluşturulmamış: {path.name}")
        return
    show_df(_clean(df), label)


def _load_hedef_long(year_key: str) -> pd.DataFrame | None:
    """Hedef gerçekleşme verisini yükler; 'all' modunda iki yılı birleştirir."""
    if year_key == "all":
        parts = [
            _load(OUT / "2024" / "12_hedef_gerceklestirme_long.csv"),
            _load(OUT / "2025" / "12_hedef_gerceklestirme_long.csv"),
        ]
        frames = [x for x in parts if x is not None]
        if not frames:
            return None
        df = pd.concat(frames, ignore_index=True)
        df = _clean(df)
        if "Ay" in df.columns:
            df["Ay"] = df["Ay"].apply(lambda v: _fmt_abbr(v, show_year=True))
        # Yıl kolonu artık Ay içinde gömülü
        if "Yıl" in df.columns:
            df = df.drop(columns=["Yıl"])
    else:
        df = _load(OUT / year_key / "12_hedef_gerceklestirme_long.csv")
        if df is None:
            return None
        df = _clean(df)
        if "Ay" in df.columns:
            df["Ay"] = df["Ay"].apply(lambda v: _fmt_abbr(v, show_year=False))
        if "Yıl" in df.columns:
            df = df.drop(columns=["Yıl"])
    return df


def _load_rakip(year_key: str) -> pd.DataFrame | None:
    """Rakip satış verisini yükler; tek yıl modunda filtreler."""
    df = _load(OUT / "all" / "15_rakip_satislar.csv")
    if df is None:
        return None
    df = _clean(df)
    if "Dönem" not in df.columns:
        return df
    if year_key != "all":
        df = df[df["Dönem"].str.startswith(year_key)].copy()
        df["Dönem"] = df["Dönem"].apply(lambda v: _fmt_ym(v, show_year=False))
    else:
        df["Dönem"] = df["Dönem"].apply(lambda v: _fmt_ym(v, show_year=True))
    return df


# ---------------------------------------------------------------------------
# Sayfa başlığı ve dönem seçimi
# ---------------------------------------------------------------------------
st.title("📊 Geçmiş Satış Analizi")
st.caption("2024 ve 2025 yıllarına ait model, versiyon, renk ve bayi bazlı satış verileri")

year = st.radio(
    "Dönem seçin",
    ["2024", "2025", "Tümü (2024–2025)"],
    horizontal=True,
)
year_key = {"2024": "2024", "2025": "2025", "Tümü (2024–2025)": "all"}[year]
img_dir = IMG / year_key
out_dir = OUT / year_key

st.divider()

# ---------------------------------------------------------------------------
# Sekmeler
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Model & Versiyon", "Renk & Bayi", "Aylık Trend",
    "Hedef Gerçekleşme", "Rakip Karşılaştırma",
])

# ---------- Tab 1: Model & Versiyon ----------
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
        show_csv(out_dir / "01_model_satislari.csv", "Model Satışları")
    with col_t2:
        show_csv(out_dir / "02_versiyon_satislari.csv", "Versiyon Satışları")

# ---------- Tab 2: Renk & Bayi ----------
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
        show_csv(out_dir / "03_renk_satislari.csv", "Renk Satışları")

    show_csv(out_dir / "04_bayi_toplam_satis.csv", "Bayi Toplam Satışları")

# ---------- Tab 3: Aylık Trend ----------
with tab3:
    show_image(img_dir / "05_aylik_trend.png", "Aylık Satış Trendi")

    if year_key == "all":
        c1, c2 = st.columns(2)
        with c1:
            show_image(img_dir / "09_model_aylik_trend.png", "Model × Aylık Trend")
        with c2:
            show_image(img_dir / "10_yoy_karsilastirma.png", "YoY Karşılaştırma")
        show_image(img_dir / "12_model_ay_heatmap.png", "Model × Ay Isı Haritası")
    else:
        if year_key == "2025":
            show_image(img_dir / "12_model_ay_heatmap.png", "Model × Ay Isı Haritası")

    df_trend = _load(out_dir / "08_aylik_trend.csv")
    if df_trend is not None:
        df_trend = _clean(df_trend)
        if "Dönem" in df_trend.columns:
            df_trend["Dönem"] = df_trend["Dönem"].apply(
                lambda v: _fmt_ym(v, show_year=(year_key == "all"))
            )
            for col in ["Yıl", "Ay"]:
                if col in df_trend.columns:
                    df_trend = df_trend.drop(columns=[col])
        show_df(df_trend, "Aylık Trend Verileri")
    else:
        st.info("Aylık trend verisi henüz oluşturulmamış.")

# ---------- Tab 4: Hedef Gerçekleşme ----------
with tab4:
    show_image(img_dir / "08_hedef_gerceklestirme.png", "Hedef Gerçekleşme Analizi")

    df_hedef = _load_hedef_long(year_key)
    if df_hedef is not None:
        lbl = "Aylık Hedef Gerçekleşme (2024–2025)" if year_key == "all" else "Aylık Hedef Gerçekleşme"
        show_df(df_hedef, lbl)
    else:
        st.info("Hedef gerçekleşme verisi henüz oluşturulmamış.")

    if year_key == "all":
        df_bayi = _load(OUT / "all" / "13_bayi_2025_performansi.csv")
        if df_bayi is not None:
            show_df(_clean(df_bayi), "Bayi Performansı")

        df_perf = _load(OUT / "all" / "12_aylik_hedef_performansi.csv")
        if df_perf is not None:
            df_perf = _clean(df_perf)
            if "Ay" in df_perf.columns:
                df_perf["Ay"] = df_perf["Ay"].map(
                    lambda v: _EN_FULL.get(str(v).upper(), v)
                )
            show_df(df_perf, "Aylık Gerçekleşen Adetler")

# ---------- Tab 5: Rakip Karşılaştırma ----------
with tab5:
    if year_key == "all":
        show_image(IMG / "all" / "11_rakip_karsilastirma.png", "Rakip Marka Satış Trendi")

    df_rakip = _load_rakip(year_key)
    if df_rakip is not None:
        lbl = "Rakip Marka Satışları (2024–2025)" if year_key == "all" else f"Rakip Marka Satışları ({year})"
        show_df(df_rakip, lbl)
    else:
        st.info("Rakip satış verisi henüz oluşturulmamış.")
