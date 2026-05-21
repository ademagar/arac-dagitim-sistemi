"""Mevsimsellik analizi modülü.

2024-2025 verilerinden (NORTHSTAR + rakipler) aylık mevsimsel indeksler
hesaplar ve yıllık hedef bazlı aylık dağıtım planı üretir.

Metodoloji
----------
Klasik oran-ortalaması yöntemi (ratio-to-mean):
    SI[m] = ortalama_2yil[m] / grand_mean
    grand_mean = toplam_satış / 24
    → SI ortalaması = 1.0, SI > 1 = peak, SI < 1 = dip

Üç ayrı endeks hesaplanır:
    1. northstar_si  — Sadece NORTHSTAR satışları (6,439 işlem)
    2. market_si     — 9 rakip toplamı (piyasa nabzı, daha büyük n)
    3. combined_si   — Hacme göre ağırlıklı ortalama (birincil öneri)

Planlama formülü:
    aylık_hedef[m] = yıllık_hedef × SI[m] / 12
    → Toplam = yıllık_hedef (∑SI/12 = 1 olduğundan)
"""

from __future__ import annotations

import calendar
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

from src.analysis.data_loader import load_competitors, load_sales

OUTPUT_DIR = Path(__file__).parents[2] / "outputs" / "seasonality"
MONTH_ABBR = [calendar.month_abbr[m] for m in range(1, 13)]
MONTH_FULL = [calendar.month_name[m] for m in range(1, 13)]

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"figure.dpi": 150, "font.family": "DejaVu Sans",
                     "axes.titlesize": 13, "axes.titleweight": "bold"})


# ---------------------------------------------------------------------------
# 1. Mevsimsel indeks hesaplama
# ---------------------------------------------------------------------------

def _monthly_avg(year_month_sales: pd.DataFrame, value_col: str) -> pd.Series:
    """Ay bazında 2 yıllık ortalama döndürür (index: 1-12)."""
    avg = (
        year_month_sales
        .groupby("month")[value_col]
        .mean()
        .reindex(range(1, 13), fill_value=0)
    )
    return avg


def compute_seasonal_indices(
    df_sales: pd.DataFrame,
    df_comp: pd.DataFrame,
) -> pd.DataFrame:
    """Üç mevsimsel indeks serisini hesaplar.

    Args:
        df_sales: load_sales() çıktısı (NORTHSTAR işlem verisi)
        df_comp:  load_competitors() çıktısı

    Returns:
        DataFrame with columns:
            month, month_name,
            northstar_si, market_si, combined_si,
            northstar_pct, market_pct, combined_pct
    """
    # --- NORTHSTAR ---
    ns_monthly = (
        df_sales.groupby(["year", "month"])
        .size()
        .reset_index(name="sales")
    )
    ns_avg = _monthly_avg(ns_monthly, "sales")
    ns_grand = ns_avg.mean()
    ns_si = ns_avg / ns_grand

    # --- Piyasa (rakip toplamı) ---
    df_comp = df_comp.copy()
    df_comp["year"]  = df_comp["year_month"].str[:4].astype(int)
    df_comp["month"] = df_comp["year_month"].str[5:7].astype(int)
    mkt_monthly = (
        df_comp.groupby(["year", "month"])["sales_qty"]
        .sum()
        .reset_index()
    )
    mkt_avg = _monthly_avg(mkt_monthly, "sales_qty")
    mkt_grand = mkt_avg.mean()
    mkt_si = mkt_avg / mkt_grand

    # --- Ağırlıklı birleşik indeks ---
    ns_total  = ns_avg.sum()
    mkt_total = mkt_avg.sum()
    w_ns  = ns_total  / (ns_total + mkt_total)
    w_mkt = mkt_total / (ns_total + mkt_total)
    comb_si = w_ns * ns_si + w_mkt * mkt_si

    result = pd.DataFrame({
        "month":        range(1, 13),
        "month_name":   MONTH_ABBR,
        "northstar_si": ns_si.values.round(4),
        "market_si":    mkt_si.values.round(4),
        "combined_si":  comb_si.values.round(4),
    })
    # Yüzde formatı (her ayın yıllık içindeki payı)
    result["northstar_pct"] = (result["northstar_si"] / 12 * 100).round(2)
    result["market_pct"]    = (result["market_si"]    / 12 * 100).round(2)
    result["combined_pct"]  = (result["combined_si"]  / 12 * 100).round(2)

    return result


# ---------------------------------------------------------------------------
# 2. Rakip bazında bireysel endeksler
# ---------------------------------------------------------------------------

def competitor_seasonal_indices(df_comp: pd.DataFrame) -> pd.DataFrame:
    """Her rakip + NORTHSTAR için ayrı mevsimsel indeks tablosu.

    Returns:
        Pivot: satırlar = aylar, sütunlar = marka adları
    """
    df_comp = df_comp.copy()
    df_comp["year"]  = df_comp["year_month"].str[:4].astype(int)
    df_comp["month"] = df_comp["year_month"].str[5:7].astype(int)

    rows = {}
    for brand, grp in df_comp.groupby("brand"):
        monthly = grp.groupby(["year", "month"])["sales_qty"].sum().reset_index()
        avg = _monthly_avg(monthly, "sales_qty")
        si = (avg / avg.mean()).round(4)
        rows[brand] = si.values

    pivot = pd.DataFrame(rows, index=range(1, 13))
    pivot.index.name = "month"
    pivot.insert(0, "month_name", MONTH_ABBR)
    return pivot


# ---------------------------------------------------------------------------
# 3. Yıllık hedef → Aylık plan
# ---------------------------------------------------------------------------

def annual_to_monthly_plan(
    annual_target: int,
    si: pd.DataFrame,
    si_col: str = "combined_si",
) -> pd.DataFrame:
    """Yıllık hedefi aylık dağıtım planına çevirir.

    Args:
        annual_target: Planlanan yıllık satış adedi
        si:            compute_seasonal_indices() çıktısı
        si_col:        Hangi indeks kullanılacak (varsayılan: combined_si)

    Returns:
        month, month_name, seasonal_index, planned_qty, planned_pct,
        cumulative_qty, cumulative_pct
    """
    plan = si[["month", "month_name", si_col]].copy()
    plan = plan.rename(columns={si_col: "seasonal_index"})

    # Aylık hedef: hedef × SI / 12  (toplam = annual_target)
    plan["planned_qty"]  = (annual_target * plan["seasonal_index"] / 12).round(0).astype(int)
    # Yuvarlama farkını son aya ekle
    diff = annual_target - plan["planned_qty"].sum()
    plan.loc[plan.index[-1], "planned_qty"] += diff

    plan["planned_pct"]    = (plan["planned_qty"] / annual_target * 100).round(1)
    plan["cumulative_qty"] = plan["planned_qty"].cumsum()
    plan["cumulative_pct"] = (plan["cumulative_qty"] / annual_target * 100).round(1)
    return plan


# ---------------------------------------------------------------------------
# 4. Görselleştirmeler
# ---------------------------------------------------------------------------

def _save(fig: plt.Figure, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Kaydedildi: {path.relative_to(Path.cwd())}")


def plot_seasonal_indices(si: pd.DataFrame) -> None:
    """Üç mevsimsel indeksi yan yana bar + çizgi grafiği."""
    x = np.arange(12)
    w = 0.28
    labels = si["month_name"].tolist()

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - w, si["northstar_si"], w, label="NORTHSTAR",  color="#1565C0", alpha=0.85)
    ax.bar(x,     si["market_si"],    w, label="Piyasa (9 rakip)", color="#43A047", alpha=0.85)
    ax.bar(x + w, si["combined_si"],  w, label="Birleşik (ağırlıklı)", color="#E65100", alpha=0.85)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1.2, label="Ortalama (1.0)")

    for xi, si_val in zip(x + w, si["combined_si"]):
        ax.text(xi, si_val + 0.02, f"{si_val:.2f}", ha="center", fontsize=7.5, color="#E65100")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Mevsimsel İndeks (1.0 = ortalama)")
    ax.set_title("Aylık Mevsimsel İndeksler — NORTHSTAR vs Piyasa vs Birleşik")
    ax.legend(fontsize=9)
    ax.set_ylim(0, si[["northstar_si", "market_si", "combined_si"]].max().max() * 1.2)
    fig.tight_layout()
    _save(fig, "01_mevsimsel_indeks_karsilastirma")


def plot_combined_index_polar(si: pd.DataFrame) -> None:
    """Birleşik mevsimsel indeksi polar (radar) grafik olarak gösterir."""
    vals = si["combined_si"].tolist()
    vals += [vals[0]]  # kapat
    angles = np.linspace(0, 2 * np.pi, 12, endpoint=False).tolist()
    angles += [angles[0]]
    labels = si["month_name"].tolist()

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
    ax.plot(angles, vals, "o-", linewidth=2, color="#E65100")
    ax.fill(angles, vals, alpha=0.2, color="#E65100")
    ax.plot(angles, [1.0] * 13, "--", linewidth=1, color="gray", alpha=0.6)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, max(vals) * 1.15)
    ax.set_title("Birleşik Mevsimsel İndeks — Yıl Döngüsü", pad=20, fontsize=13, fontweight="bold")

    for angle, val, lbl in zip(angles[:-1], vals[:-1], labels):
        ax.text(angle, val + 0.05, f"{val:.2f}", ha="center", fontsize=8, color="#E65100")
    fig.tight_layout()
    _save(fig, "02_mevsimsel_indeks_polar")


def plot_competitor_heatmap(comp_si: pd.DataFrame) -> None:
    """Rakip × Ay mevsimsel indeks ısı haritası."""
    data = comp_si.drop(columns=["month_name"]).T
    data.columns = MONTH_ABBR
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(data, annot=True, fmt=".2f", cmap="RdYlGn", center=1.0,
                linewidths=0.5, linecolor="white", ax=ax,
                cbar_kws={"label": "Mevsimsel İndeks (1.0 = ortalama)"})
    ax.set_title("Rakip Bazında Mevsimsel İndeks Isı Haritası")
    ax.set_xlabel("Ay")
    ax.set_ylabel("Marka")
    fig.tight_layout()
    _save(fig, "03_rakip_mevsimsel_heatmap")


def plot_monthly_plan(plan: pd.DataFrame, annual_target: int) -> None:
    """Aylık dağıtım planını görselleştirir."""
    x = np.arange(12)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9))
    fig.suptitle(f"Yıllık {annual_target:,} Hedef İçin Aylık Dağıtım Planı",
                 fontsize=14, fontweight="bold")

    # Üst: Aylık adet + indeks çizgisi
    colors = ["#E53935" if v < 1 else "#43A047" for v in plan["seasonal_index"]]
    bars = ax1.bar(x, plan["planned_qty"], color=colors, alpha=0.85, edgecolor="white")
    for bar, qty in zip(bars, plan["planned_qty"]):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 3,
                 f"{qty:,}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax1b = ax1.twinx()
    ax1b.plot(x, plan["seasonal_index"], "o--", color="#1565C0",
              linewidth=2, markersize=6, label="Mevsimsel İndeks")
    ax1b.axhline(1.0, color="gray", linestyle=":", linewidth=1)
    ax1b.set_ylabel("Mevsimsel İndeks", color="#1565C0")
    ax1b.tick_params(axis="y", labelcolor="#1565C0")
    ax1b.legend(loc="upper right", fontsize=9)
    ax1.set_xticks(x)
    ax1.set_xticklabels(plan["month_name"])
    ax1.set_ylabel("Planlanan Satış Adedi")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax1.set_title("Aylık Hedef Dağılımı (yeşil=peak, kırmızı=dip)")

    # Alt: Kümülatif ilerleme
    ax2.fill_between(x, plan["cumulative_qty"], alpha=0.15, color="#1565C0")
    ax2.plot(x, plan["cumulative_qty"], "o-", color="#1565C0", linewidth=2.2, markersize=6)
    ax2.axhline(annual_target, color="#E53935", linestyle="--", linewidth=1.5,
                label=f"Yıllık Hedef: {annual_target:,}")
    for xi, cum, pct in zip(x, plan["cumulative_qty"], plan["cumulative_pct"]):
        if xi % 2 == 0 or xi == 11:
            ax2.annotate(f"%{pct:.0f}", (xi, cum), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=8, color="#1565C0")
    ax2.set_xticks(x)
    ax2.set_xticklabels(plan["month_name"])
    ax2.set_ylabel("Kümülatif Satış")
    ax2.set_title("Kümülatif Hedef İlerlemesi")
    ax2.legend(fontsize=9)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    _save(fig, "04_aylik_hedef_plani")


def plot_northstar_vs_market(si: pd.DataFrame) -> None:
    """NORTHSTAR ile piyasa mevsimselliğini karşılaştıran çizgi grafiği."""
    x = np.arange(12)
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(x, si["northstar_si"], "o-", color="#1565C0", linewidth=2.2,
            markersize=7, label="NORTHSTAR")
    ax.plot(x, si["market_si"], "s--", color="#43A047", linewidth=2,
            markersize=6, label="Piyasa Ortalaması")
    ax.fill_between(x, si["northstar_si"], si["market_si"],
                    where=si["northstar_si"] >= si["market_si"],
                    alpha=0.15, color="#1565C0", label="NS > Piyasa")
    ax.fill_between(x, si["northstar_si"], si["market_si"],
                    where=si["northstar_si"] < si["market_si"],
                    alpha=0.15, color="#43A047", label="NS < Piyasa")
    ax.axhline(1.0, color="gray", linestyle=":", linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(si["month_name"], fontsize=10)
    ax.set_ylabel("Mevsimsel İndeks")
    ax.set_title("NORTHSTAR vs Piyasa Mevsimselliği — Sapma Analizi")
    ax.legend(fontsize=9)
    ax.set_ylim(0, max(si["northstar_si"].max(), si["market_si"].max()) * 1.2)
    fig.tight_layout()
    _save(fig, "05_northstar_vs_piyasa")


# ---------------------------------------------------------------------------
# 5. Metin raporu
# ---------------------------------------------------------------------------

def generate_seasonality_report(
    si: pd.DataFrame,
    comp_si: pd.DataFrame,
    plan: pd.DataFrame,
    annual_target: int,
) -> str:
    lines: list[str] = []

    def h(t: str) -> None:
        lines.append("\n" + "=" * 62)
        lines.append(f"  {t}")
        lines.append("=" * 62)

    h("MEVSİMSELLİK ANALİZİ RAPORU — NORTHSTAR 2024-2025")
    lines.append("""
Metodoloji: Klasik oran-ortalaması (ratio-to-mean)
  SI[ay] = 2 yıllık_aylık_ortalama[ay] / grand_mean
  grand_mean = toplam_satış / 24 (2 yıl × 12 ay)
  SI > 1.0 → Peak (ortalama üstü talep)
  SI < 1.0 → Dip  (ortalama altı talep)
  SI = 1.0 → Ortalama ay

Kaynaklar:
  - NORTHSTAR: 6,439 araç (2024-2025)
  - Piyasa: 9 rakip marka, aylık toplam (2024-2025)
  - Birleşik: hacme göre ağırlıklı (Piyasa ağırlığı baskın)
""".strip())

    h("AYLIK MEVSİMSEL İNDEKSLER")
    lines.append(f"\n  {'Ay':<6} {'NS İndeks':>11} {'Piyasa':>9} {'Birleşik':>10}  {'Yorum'}")
    lines.append("  " + "-" * 58)
    for _, row in si.iterrows():
        csi = row["combined_si"]
        if csi >= 1.20:
            yorum = "⬆⬆ Yüksek peak"
        elif csi >= 1.05:
            yorum = "⬆  Hafif peak"
        elif csi >= 0.95:
            yorum = "→  Ortalama"
        elif csi >= 0.80:
            yorum = "⬇  Hafif dip"
        else:
            yorum = "⬇⬇ Derin dip"
        lines.append(
            f"  {row['month_name']:<6} {row['northstar_si']:>11.4f} "
            f"{row['market_si']:>9.4f} {csi:>10.4f}  {yorum}"
        )

    h("PEAK / DİP AYLAR")
    top3 = si.nlargest(3, "combined_si")
    bot3 = si.nsmallest(3, "combined_si")
    lines.append("\n  PEAK (en yüksek talep):")
    for _, r in top3.iterrows():
        lines.append(f"    {r['month_name']}: SI={r['combined_si']:.3f} → "
                     f"ortalamanın %{(r['combined_si']-1)*100:+.1f} üstünde")
    lines.append("\n  DİP (en düşük talep):")
    for _, r in bot3.iterrows():
        lines.append(f"    {r['month_name']}: SI={r['combined_si']:.3f} → "
                     f"ortalamanın %{(r['combined_si']-1)*100:+.1f} altında")

    h(f"AYLIK DAĞITIM PLANI — {annual_target:,} ARAÇ YILLIK HEDEF")
    lines.append(f"\n  {'Ay':<6} {'Plan (adet)':>12} {'Pay %':>7} {'Kümülatif':>12} {'Kümül %':>8}")
    lines.append("  " + "-" * 50)
    for _, row in plan.iterrows():
        bar = "█" * int(row["planned_pct"] / 1.2)
        lines.append(
            f"  {row['month_name']:<6} {int(row['planned_qty']):>12,} "
            f"{row['planned_pct']:>7.1f}% {int(row['cumulative_qty']):>12,} "
            f"{row['cumulative_pct']:>7.1f}%  {bar}"
        )

    h("NORTHSTAR vs PİYASA SAPMA ANALİZİ")
    lines.append(f"\n  {'Ay':<6} {'NS SI':>7} {'Piyasa SI':>10} {'Fark':>7}  Yorum")
    lines.append("  " + "-" * 52)
    for _, row in si.iterrows():
        diff = row["northstar_si"] - row["market_si"]
        yorum = (
            "NS piyasanın üstünde" if diff > 0.05
            else "NS piyasanın altında" if diff < -0.05
            else "Piyasa ile paralel"
        )
        lines.append(
            f"  {row['month_name']:<6} {row['northstar_si']:>7.3f} "
            f"{row['market_si']:>10.3f} {diff:>+7.3f}  {yorum}"
        )

    h("KULLANIM REHBERİ")
    lines.append(textwrap.dedent(f"""
  Hedef senaryoları için annual_to_monthly_plan() fonksiyonunu kullanın:

    from src.analysis.seasonality import compute_seasonal_indices, annual_to_monthly_plan
    from src.analysis.data_loader import load_sales, load_competitors

    si = compute_seasonal_indices(load_sales(), load_competitors())
    plan = annual_to_monthly_plan(annual_target=3_600, si=si)
    print(plan)

  Farklı indeks tercihleri:
    si_col="northstar_si"  → Sadece kendi geçmiş verinize dayalı
    si_col="market_si"     → Piyasa mevsimselliği (daha güçlü veri)
    si_col="combined_si"   → Ağırlıklı birleşik (önerilen)
    """).strip())

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. Ana çalıştırma
# ---------------------------------------------------------------------------

def run(annual_target: int = 3_600) -> None:
    """Tüm mevsimsellik analizini çalıştırır.

    Args:
        annual_target: Plan tablosu için varsayılan yıllık hedef
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/4] Veriler yükleniyor...")
    df_sales = load_sales()
    df_comp  = load_competitors()
    print(f"  NORTHSTAR: {len(df_sales):,} işlem | Rakip: {df_comp['brand'].nunique()} marka")

    print("\n[2/4] Mevsimsel indeksler hesaplanıyor...")
    si       = compute_seasonal_indices(df_sales, df_comp)
    comp_si  = competitor_seasonal_indices(df_comp)
    plan     = annual_to_monthly_plan(annual_target, si)

    print("\n[3/4] CSV çıktıları kaydediliyor...")
    for df, name in [
        (si,      "01_mevsimsel_indeksler"),
        (comp_si, "02_rakip_mevsimsel_indeksler"),
        (plan,    f"03_aylik_plan_{annual_target}"),
    ]:
        path = OUTPUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  Kaydedildi: {path.relative_to(Path.cwd())}")

    # Rapor
    report = generate_seasonality_report(si, comp_si, plan, annual_target)
    rpath = OUTPUT_DIR / "mevsimsellik_raporu.txt"
    rpath.write_text(report, encoding="utf-8")
    print(f"  Kaydedildi: {rpath.relative_to(Path.cwd())}")

    print("\n[4/4] Görseller oluşturuluyor...")
    plot_seasonal_indices(si)
    plot_combined_index_polar(si)
    plot_competitor_heatmap(comp_si)
    plot_monthly_plan(plan, annual_target)
    plot_northstar_vs_market(si)

    print(f"\n✓ Tamamlandı → outputs/seasonality/")
    print(f"\n{report}")


if __name__ == "__main__":
    import sys
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 3_600
    run(annual_target=target)
