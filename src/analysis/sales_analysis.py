"""Satış analizi fonksiyonları.

Model/versiyon ve bayi bazında geçmiş satış verilerini analiz eder.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Optional

import pandas as pd

from src.analysis.data_loader import (
    load_competitors,
    load_monthly_performance,
    load_sales,
)

OUTPUT_DIR = Path(__file__).parents[2] / "outputs"


# ---------------------------------------------------------------------------
# 1. MODEL / VERSİYON ANALİZİ
# ---------------------------------------------------------------------------

def model_version_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Model ve versiyon bazında toplam satış sıralaması.

    Args:
        df: load_sales() çıktısı

    Returns:
        Sıralanmış DataFrame: model, version, total_sales, share_pct
    """
    grp = (
        df.groupby(["Model Description", "Vehicle Version"], dropna=True)
        .size()
        .reset_index(name="total_sales")
        .sort_values("total_sales", ascending=False)
    )
    grp["share_pct"] = (grp["total_sales"] / grp["total_sales"].sum() * 100).round(1)
    grp = grp.rename(columns={"Model Description": "model", "Vehicle Version": "version"})
    return grp.reset_index(drop=True)


def model_only_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Sadece model bazında toplam satış sıralaması."""
    grp = (
        df.groupby("Model Description", dropna=True)
        .size()
        .reset_index(name="total_sales")
        .sort_values("total_sales", ascending=False)
    )
    grp["share_pct"] = (grp["total_sales"] / grp["total_sales"].sum() * 100).round(1)
    grp = grp.rename(columns={"Model Description": "model"})
    return grp.reset_index(drop=True)


def color_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Renk bazında satış sıralaması."""
    grp = (
        df.groupby("Exterior Color", dropna=True)
        .size()
        .reset_index(name="total_sales")
        .sort_values("total_sales", ascending=False)
    )
    grp["share_pct"] = (grp["total_sales"] / grp["total_sales"].sum() * 100).round(1)
    return grp.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. BAYİ ANALİZİ
# ---------------------------------------------------------------------------

def dealer_total_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Bayi bazında toplam satış."""
    grp = (
        df.groupby("Dealer Name")
        .size()
        .reset_index(name="total_sales")
        .sort_values("total_sales", ascending=False)
    )
    return grp.reset_index(drop=True)


def dealer_model_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Bayi × Model pivot tablosu (adet)."""
    pivot = (
        df.groupby(["Dealer Name", "Model Description"], dropna=True)
        .size()
        .unstack(fill_value=0)
    )
    pivot["TOPLAM"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("TOPLAM", ascending=False)
    return pivot


def dealer_version_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Bayi × Versiyon pivot tablosu (adet)."""
    pivot = (
        df.groupby(["Dealer Name", "Vehicle Version"], dropna=True)
        .size()
        .unstack(fill_value=0)
    )
    pivot["TOPLAM"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("TOPLAM", ascending=False)
    return pivot


def dealer_top_model(df: pd.DataFrame) -> pd.DataFrame:
    """Her bayinin en çok sattığı model ve versiyon."""
    rows = []
    for dealer, sub in df.groupby("Dealer Name"):
        top_model = sub["Model Description"].value_counts().idxmax()
        top_version = sub["Vehicle Version"].value_counts().idxmax()
        top_color = sub["Exterior Color"].value_counts().idxmax()
        total = len(sub)
        rows.append(
            {
                "dealer": dealer,
                "top_model": top_model,
                "top_version": top_version,
                "top_color": top_color,
                "total_sales": total,
            }
        )
    return pd.DataFrame(rows).sort_values("total_sales", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. ZAMAN SERİSİ ANALİZİ
# ---------------------------------------------------------------------------

def monthly_sales_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Aylık toplam satış trendi (2024-2025)."""
    trend = (
        df.groupby(["year", "month"])
        .size()
        .reset_index(name="sales_qty")
    )
    trend["year_month"] = pd.to_datetime(
        trend["year"].astype(str) + "-" + trend["month"].astype(str).str.zfill(2)
    ).dt.to_period("M")
    return trend.sort_values("year_month").reset_index(drop=True)


def monthly_model_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Modele göre aylık satış trendi."""
    trend = (
        df.groupby(["year", "month", "Model Description"], dropna=True)
        .size()
        .reset_index(name="sales_qty")
    )
    trend["year_month"] = pd.to_datetime(
        trend["year"].astype(str) + "-" + trend["month"].astype(str).str.zfill(2)
    ).dt.to_period("M")
    return trend.sort_values(["year_month", "Model Description"]).reset_index(drop=True)


def channel_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """B2C vs B2B satış kanalı dağılımı."""
    ch = (
        df.groupby(["Channel Group", "year"])
        .size()
        .reset_index(name="sales_qty")
    )
    total = df.groupby("year").size().reset_index(name="year_total")
    ch = ch.merge(total, on="year")
    ch["share_pct"] = (ch["sales_qty"] / ch["year_total"] * 100).round(1)
    return ch


def yoy_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """2024 vs 2025 yıllık karşılaştırma (aynı ay aralığı için)."""
    trend = monthly_sales_trend(df)
    y2024 = trend[trend["year"] == 2024]["sales_qty"].sum()
    y2025 = trend[trend["year"] == 2025]["sales_qty"].sum()
    growth = ((y2025 - y2024) / y2024 * 100) if y2024 else 0
    return pd.DataFrame(
        {
            "year": [2024, 2025],
            "total_sales": [y2024, y2025],
            "yoy_growth_pct": [None, round(growth, 1)],
        }
    )


# ---------------------------------------------------------------------------
# 4. AYLIK HEDEF PERFORMANSI
# ---------------------------------------------------------------------------

def monthly_performance_summary(perf: pd.DataFrame) -> pd.DataFrame:
    """Aylık toplam satış (gerçekleşen), tüm bayiler."""
    return (
        perf.groupby(["month", "month_num", "channel"])["actual_qty"]
        .sum()
        .reset_index()
        .sort_values("month_num")
    )


def dealer_annual_performance(perf: pd.DataFrame) -> pd.DataFrame:
    """Bayi bazında 2025 yıllık toplam gerçekleşen satışlar."""
    return (
        perf.groupby(["dealer_name", "channel"])["actual_qty"]
        .sum()
        .reset_index()
        .sort_values("actual_qty", ascending=False)
    )


def model_monthly_heatmap_data(perf: pd.DataFrame) -> pd.DataFrame:
    """Model grubu × Ay ısı haritası verisi."""
    pivot = (
        perf.groupby(["model_group", "month_num", "month"])["actual_qty"]
        .sum()
        .reset_index()
        .pivot(index="model_group", columns="month", values="actual_qty")
        .fillna(0)
        .astype(int)
    )
    month_order = [
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
    ]
    existing = [m for m in month_order if m in pivot.columns]
    return pivot[existing]


# ---------------------------------------------------------------------------
# 5. YORUMLAYıCı RAPOR
# ---------------------------------------------------------------------------

def generate_text_report(
    df: pd.DataFrame,
    perf: pd.DataFrame,
    comp: Optional[pd.DataFrame] = None,
) -> str:
    """Tüm analizleri metin formatında özetleyen rapor üretir.

    Args:
        df:   Ana satış DataFrame (load_sales çıktısı)
        perf: Aylık performans DataFrame (load_monthly_performance çıktısı)
        comp: Rakip satış DataFrame (isteğe bağlı)

    Returns:
        Okunabilir metin raporu.
    """
    lines: list[str] = []

    def h(title: str) -> None:
        lines.append("\n" + "=" * 60)
        lines.append(f"  {title}")
        lines.append("=" * 60)

    def sub(title: str) -> None:
        lines.append(f"\n--- {title} ---")

    # ---- Genel bakış ----
    h("GENEL BAKIŞ (2024-2025 Satış Verisi)")
    total = len(df)
    y2024 = (df["year"] == 2024).sum()
    y2025 = (df["year"] == 2025).sum()
    lines.append(f"Toplam satış adedi      : {total:,}")
    lines.append(f"  2024                  : {y2024:,}")
    lines.append(f"  2025                  : {y2025:,}")
    growth = (y2025 - y2024) / y2024 * 100 if y2024 else 0
    lines.append(f"  YoY büyüme            : %{growth:+.1f}")
    lines.append(f"Toplam bayi sayısı      : {df['Dealer Name'].nunique()}")
    lines.append(f"Farklı model sayısı     : {df['Model Description'].nunique()}")
    lines.append(f"Farklı versiyon sayısı  : {df['Vehicle Version'].nunique()}")

    # ---- Model sıralaması ----
    h("MODEL BAZINDA SATIŞLAR")
    model_rank = model_only_ranking(df)
    for _, row in model_rank.iterrows():
        bar = "█" * int(row["share_pct"] / 2)
        lines.append(f"  {row['model']:<8} {row['total_sales']:>5,} adet  %{row['share_pct']:>5.1f}  {bar}")

    # ---- Versiyon sıralaması ----
    h("VERSİYON BAZINDA SATIŞLAR (Top 10)")
    ver_rank = model_version_ranking(df).head(10)
    for _, row in ver_rank.iterrows():
        bar = "█" * int(row["share_pct"] / 2)
        lines.append(
            f"  {row['model']}/{row['version']:<10} "
            f"{row['total_sales']:>5,} adet  %{row['share_pct']:>5.1f}  {bar}"
        )

    # ---- Renk sıralaması ----
    h("RENK BAZINDA SATIŞLAR (Top 8)")
    col_rank = color_ranking(df).head(8)
    for _, row in col_rank.iterrows():
        bar = "█" * int(row["share_pct"] / 2)
        lines.append(
            f"  {str(row['Exterior Color']):<15} "
            f"{row['total_sales']:>5,} adet  %{row['share_pct']:>5.1f}  {bar}"
        )

    # ---- Kanal dağılımı ----
    h("SATIŞ KANALI (B2C vs B2B)")
    ch = channel_breakdown(df)
    for _, row in ch.iterrows():
        lines.append(
            f"  {row['year']}  {str(row['Channel Group']):<15} "
            f"{row['sales_qty']:>5,} adet  %{row['share_pct']:>5.1f}"
        )

    # ---- Bayi sıralaması ----
    h("BAYİ BAZINDA TOPLAM SATIŞLAR")
    d_total = dealer_total_sales(df)
    for _, row in d_total.iterrows():
        bar = "█" * int(row["total_sales"] / 30)
        lines.append(f"  {row['Dealer Name']:<12} {row['total_sales']:>5,} adet  {bar}")

    # ---- Bayi top model ----
    h("BAYİ BAZINDA EN ÇOK SATAN MODEL / VERSİYON")
    top_model = dealer_top_model(df)
    lines.append(
        f"  {'Bayi':<12} {'Top Model':<10} {'Top Versiyon':<12} "
        f"{'Top Renk':<12} {'Toplam':>7}"
    )
    lines.append("  " + "-" * 56)
    for _, row in top_model.iterrows():
        lines.append(
            f"  {row['dealer']:<12} {row['top_model']:<10} "
            f"{row['top_version']:<12} {row['top_color']:<12} {row['total_sales']:>7,}"
        )

    # ---- Aylık trend ----
    h("AYLIK SATIŞ TRENDİ")
    mt = monthly_sales_trend(df)
    for _, row in mt.iterrows():
        bar = "█" * int(row["sales_qty"] / 15)
        lines.append(f"  {str(row['year_month']):<8}  {row['sales_qty']:>4,} adet  {bar}")

    # ---- 2025 aylık hedef performansı ----
    if not perf.empty:
        h("2025 AYLIK HEDEF PERFORMANSI (Gerçekleşen Satış)")
        perf_summary = monthly_performance_summary(perf)
        b2c = perf_summary[perf_summary["channel"] == "B2C"].set_index("month")["actual_qty"]
        b2b = perf_summary[perf_summary["channel"] == "B2B"].set_index("month")["actual_qty"]
        month_order = [
            "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
            "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
        ]
        lines.append(f"  {'Ay':<12} {'B2C':>6} {'B2B':>6} {'TOPLAM':>8}")
        lines.append("  " + "-" * 36)
        for m in month_order:
            c = b2c.get(m, 0)
            b = b2b.get(m, 0)
            lines.append(f"  {m:<12} {int(c):>6,} {int(b):>6,} {int(c+b):>8,}")

    # ---- Rakip karşılaştırma ----
    if comp is not None and not comp.empty:
        h("RAKİP MARKA SATIŞ KARŞILAŞTIRMASI (2024-2025 Aylık Toplam)")
        brand_totals = (
            comp.groupby("brand")["sales_qty"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        northstar_total = len(df)
        lines.append(f"  {'Marka':<20} {'Toplam Satış':>14}")
        lines.append("  " + "-" * 36)
        lines.append(f"  {'NORTHSTAR':<20} {northstar_total:>14,}  ← Bizim marka")
        for brand, qty in brand_totals.items():
            lines.append(f"  {str(brand):<20} {int(qty):>14,}")

    # ---- Özet yorumlar ----
    h("YÖNETİCİ ÖZET VE YORUMLAR")
    best_model = model_rank.iloc[0]
    best_dealer = d_total.iloc[0]
    worst_dealer = d_total.iloc[-1]
    top_ver = ver_rank.iloc[0]

    lines.append(textwrap.dedent(f"""
  1. EN POPÜLER MODEL:
     {best_model['model']} modeli tüm satışların %{best_model['share_pct']:.1f}'ini oluşturuyor
     ({best_model['total_sales']:,} adet). Dağıtım planlamasında bu modele öncelik verilmeli.

  2. EN POPÜLER VERSİYON:
     {top_ver['model']}/{top_ver['version']} versiyonu {top_ver['total_sales']:,} adet ile
     en çok satan paket. Envanter planı bu versiyona yönelik yapılmalı.

  3. BAYİ PERFORMANSI:
     En yüksek satış: {best_dealer['Dealer Name']} ({best_dealer['total_sales']:,} adet)
     En düşük satış:  {worst_dealer['Dealer Name']} ({worst_dealer['total_sales']:,} adet)
     Bayiler arası kapasite farkı optimizasyon modelinde kısıt olarak kullanılmalı.

  4. BÜYÜME TRENDI:
     2024'ten 2025'e YoY büyüme: %{growth:+.1f}
     {"Pozitif büyüme, dağıtım hacmi artacak demektir." if growth > 0 else "Düşüş var, temkinli planlama gerekiyor."}

  5. KANAL STRATEJİSİ:
     B2C satışlar baskın. B2B kanalı nispeten düşük ama istikrarlı.
     Optimizasyon modelinde kanal bazlı kısıtlar gözetilmeli.
    """).strip())

    return "\n".join(lines)
