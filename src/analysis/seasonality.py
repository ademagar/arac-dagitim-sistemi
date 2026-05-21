"""Mevsimsellik analizi modülü — üç piyasa katmanlı hiyerarşik yöntem.

2024-2025 verilerinden (ODD ithal piyasası + rakipler + NORTHSTAR) aylık
mevsimsel indeksler hesaplar ve yıllık hedef bazlı aylık dağıtım planı üretir.

Metodoloji
----------
Klasik oran-ortalaması yöntemi (ratio-to-mean):
    SI[m] = mean_over_years(monthly_sales[m]) / grand_mean
    grand_mean = sum(monthly_sales) / 24   (2 yıl × 12 ay)
    → mean(SI) = 1.0, SI > 1 = peak, SI < 1 = dip

Üç piyasa katmanı:
    1. ODD SI      — Türkiye ithal otomobil piyasası, 53 marka, toplam hacim
    2. Segment SI  — 9 rakip marka toplamı, rekabetçi bağlam
    3. NORTHSTAR SI — Sadece NORTHSTAR işlem verisi, marka özgül

Nihai önerilen SI (final_si):
    final_si = 0.50 × odd_si + 0.30 × segment_si + 0.20 × northstar_si

Ağırlıklandırma gerekçesi:
    - ODD: En geniş veri tabanı (53 marka), piyasa gürültüsüne karşı robust
    - Segment: Doğrudan rekabet ortamı, stratejik bağlam
    - NORTHSTAR: Marka özgül ama sınırlı örneklem (n≈6,400)
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

from src.analysis.data_loader import load_competitors, load_sales, MONTH_TR_MAP

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

MONTH_ABBR_TR = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]
MONTH_ABBR_EN = [calendar.month_abbr[m] for m in range(1, 13)]

# Seaborn/matplotlib tema ayarları
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({
    "figure.dpi": 150,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
})

# Yetersiz veri eşiği: 2 yıllık toplam bu sayının altındaysa atlana
MIN_SALES_THRESHOLD = 24


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _ratio_to_mean(year_month_sales: pd.DataFrame, value_col: str) -> pd.Series:
    """Oran-ortalaması yöntemiyle mevsimsel indeks serisi döndürür.

    Args:
        year_month_sales: "month" ve value_col sütunlarını içeren DataFrame.
            Her satır bir (yıl, ay) gözlemini temsil etmeli.
        value_col: Sayısal değer sütununun adı.

    Returns:
        1-12 indeksli SI serisi. grand_mean > 0 değilse sıfır serisi döner.
    """
    # Her ay için 2 yıllık ortalama
    avg = (
        year_month_sales
        .groupby("month")[value_col]
        .mean()
        .reindex(range(1, 13), fill_value=0)
    )
    grand = avg.mean()
    if grand > 0:
        return (avg / grand).round(4)
    return avg * 0


def _save_fig(fig: plt.Figure, path: Path) -> None:
    """Figürü diske kaydeder ve kapatır."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Kaydedildi: {path}")


# ---------------------------------------------------------------------------
# 1. ODD piyasa mevsimsel indeksi
# ---------------------------------------------------------------------------

def compute_odd_si(data_dir: Path) -> pd.Series:
    """ODD ithal otomobil verisiyle toplam piyasa SI'ını hesaplar.

    Tüm markaların aylık satışları toplanarak tek bir piyasa serisi elde
    edilir. "TOTAL SALES" satırı ve tüm değerleri sıfır olan markalar atlanır.

    Args:
        data_dir: data/raw/ klasörünün yolu.

    Returns:
        1-12 indeksli mevsimsel indeks serisi (float, yuvarlama: 4 basamak).
    """
    odd_path = data_dir / "2024-2025-ODD-Otomobil-Satışlar-İthal).csv"

    # Dosyayı metin olarak oku; encoding: UTF-8 BOM
    raw_text = odd_path.read_text(encoding="utf-8-sig")
    lines = raw_text.strip().splitlines()

    # İlk satır başlık (sütun adları: boş + 24 ay etiketi)
    header_parts = lines[0].split(";")
    # Ay etiketlerini YYYY-MM formatına çevir (örn. "Oca.24" → 2024-01)
    month_keys: list[tuple[int, int]] = []  # (yıl, ay_no) listesi
    for raw_lbl in header_parts[1:]:
        raw_lbl = raw_lbl.strip()
        if not raw_lbl:
            continue
        parts = raw_lbl.split(".")
        if len(parts) != 2:
            continue
        tr_abbr, yr_short = parts[0].strip(), parts[1].strip()
        en_abbr = MONTH_TR_MAP.get(tr_abbr, tr_abbr)
        year = int("20" + yr_short)
        month_num = pd.to_datetime(f"{en_abbr} {year}", format="%b %Y").month
        month_keys.append((year, month_num))

    # Aylık toplam piyasa satışı (tüm markalar)
    monthly_totals: dict[tuple[int, int], float] = {k: 0.0 for k in month_keys}

    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(";")
        brand_name = parts[0].strip()
        # "TOTAL SALES" satırını atla
        if brand_name.upper() == "TOTAL SALES":
            continue
        if not brand_name:
            continue

        values: list[float] = []
        for raw_val in parts[1: len(month_keys) + 1]:
            # Binlik nokta → kaldır, ondalık virgül → nokta
            cleaned = raw_val.strip().replace(".", "").replace(",", ".")
            try:
                values.append(float(cleaned))
            except ValueError:
                values.append(0.0)

        # Tüm sıfır olan markaları atla
        if all(v == 0 for v in values):
            continue

        for (yr, mn), val in zip(month_keys, values):
            monthly_totals[(yr, mn)] += val

    # DataFrame oluştur: year, month, sales_qty
    rows = [
        {"year": yr, "month": mn, "sales_qty": qty}
        for (yr, mn), qty in monthly_totals.items()
    ]
    df_odd = pd.DataFrame(rows)

    return _ratio_to_mean(df_odd, "sales_qty")


# ---------------------------------------------------------------------------
# 2. Rekabet segmenti mevsimsel indeksi
# ---------------------------------------------------------------------------

def compute_segment_si(df_comp: pd.DataFrame) -> pd.Series:
    """9 rakip markanın toplamından segment SI hesaplar.

    Args:
        df_comp: load_competitors() çıktısı.
            Sütunlar: brand, year_month (YYYY-MM), sales_qty

    Returns:
        1-12 indeksli mevsimsel indeks serisi.
    """
    df = df_comp.copy()
    df["year"]  = df["year_month"].str[:4].astype(int)
    df["month"] = df["year_month"].str[5:7].astype(int)

    # Tüm rakipleri toplayarak tek bir segment serisi oluştur
    seg_monthly = (
        df.groupby(["year", "month"])["sales_qty"]
        .sum()
        .reset_index()
    )
    return _ratio_to_mean(seg_monthly, "sales_qty")


# ---------------------------------------------------------------------------
# 3. NORTHSTAR marka mevsimsel indeksi
# ---------------------------------------------------------------------------

def compute_northstar_si(df_sales: pd.DataFrame) -> pd.Series:
    """NORTHSTAR işlem verisinden marka SI hesaplar.

    Args:
        df_sales: load_sales() çıktısı.
            Sütunlar: year (int), month (int), ...

    Returns:
        1-12 indeksli mevsimsel indeks serisi.
    """
    ns_monthly = (
        df_sales
        .groupby(["year", "month"])
        .size()
        .reset_index(name="sales_qty")
    )
    return _ratio_to_mean(ns_monthly, "sales_qty")


# ---------------------------------------------------------------------------
# 4. Granüler NORTHSTAR indeksleri (bayi / model / renk)
# ---------------------------------------------------------------------------

def compute_dealer_si(df_sales: pd.DataFrame) -> pd.DataFrame:
    """Bayi bazında mevsimsel indeks pivot tablosu.

    Her bayi için kendi ratio-to-mean hesabı yapılır. 2 yıllık toplam
    MIN_SALES_THRESHOLD altındaki bayiler atlanır.

    Args:
        df_sales: load_sales() çıktısı.

    Returns:
        Pivot DataFrame: satırlar = ay (1-12), sütunlar = bayi adları.
    """
    pivot_data: dict[str, list[float]] = {}

    for dealer, grp in df_sales.groupby("Dealer Name"):
        # Yetersiz veri kontrolü
        if len(grp) < MIN_SALES_THRESHOLD:
            continue
        monthly = (
            grp.groupby(["year", "month"])
            .size()
            .reset_index(name="sales_qty")
        )
        si_series = _ratio_to_mean(monthly, "sales_qty")
        pivot_data[str(dealer)] = si_series.tolist()

    pivot = pd.DataFrame(pivot_data, index=range(1, 13))
    pivot.index.name = "month"
    return pivot


def compute_model_si(df_sales: pd.DataFrame) -> pd.DataFrame:
    """Model bazında mevsimsel indeks pivot tablosu.

    Args:
        df_sales: load_sales() çıktısı.

    Returns:
        Pivot DataFrame: satırlar = ay (1-12), sütunlar = model adları.
    """
    pivot_data: dict[str, list[float]] = {}

    for model, grp in df_sales.groupby("Model Description"):
        if len(grp) < MIN_SALES_THRESHOLD:
            continue
        monthly = (
            grp.groupby(["year", "month"])
            .size()
            .reset_index(name="sales_qty")
        )
        si_series = _ratio_to_mean(monthly, "sales_qty")
        pivot_data[str(model)] = si_series.tolist()

    pivot = pd.DataFrame(pivot_data, index=range(1, 13))
    pivot.index.name = "month"
    return pivot


def compute_color_si(df_sales: pd.DataFrame) -> pd.DataFrame:
    """Renk bazında mevsimsel indeks pivot tablosu (ilk 10 renk hacme göre).

    Args:
        df_sales: load_sales() çıktısı.

    Returns:
        Pivot DataFrame: satırlar = ay (1-12), sütunlar = renk adları (top 10).
    """
    # Hacme göre ilk 10 renk
    top_colors = (
        df_sales["Exterior Color"]
        .value_counts()
        .head(10)
        .index
        .tolist()
    )

    pivot_data: dict[str, list[float]] = {}

    for color in top_colors:
        grp = df_sales[df_sales["Exterior Color"] == color]
        if len(grp) < MIN_SALES_THRESHOLD:
            continue
        monthly = (
            grp.groupby(["year", "month"])
            .size()
            .reset_index(name="sales_qty")
        )
        si_series = _ratio_to_mean(monthly, "sales_qty")
        pivot_data[str(color)] = si_series.tolist()

    pivot = pd.DataFrame(pivot_data, index=range(1, 13))
    pivot.index.name = "month"
    return pivot


# ---------------------------------------------------------------------------
# 5. Nihai ağırlıklı SI
# ---------------------------------------------------------------------------

def compute_final_si(
    odd_si: pd.Series,
    segment_si: pd.Series,
    northstar_si: pd.Series,
    w_odd: float = 0.50,
    w_seg: float = 0.30,
    w_ns: float = 0.20,
) -> pd.Series:
    """Üç katmanı ağırlıklı ortalama ile birleştirir.

    Args:
        odd_si:       ODD piyasa SI serisi (index 1-12).
        segment_si:   Segment SI serisi (index 1-12).
        northstar_si: NORTHSTAR SI serisi (index 1-12).
        w_odd:        ODD ağırlığı (varsayılan 0.50).
        w_seg:        Segment ağırlığı (varsayılan 0.30).
        w_ns:         NORTHSTAR ağırlığı (varsayılan 0.20).

    Returns:
        1-12 indeksli nihai SI serisi (4 basamak yuvarlama).
    """
    final = (w_odd * odd_si + w_seg * segment_si + w_ns * northstar_si).round(4)
    final.index = range(1, 13)
    return final


# ---------------------------------------------------------------------------
# 6. Planlama fonksiyonu
# ---------------------------------------------------------------------------

def monthly_plan(
    annual_target: int,
    si_series: pd.Series,
    label: str = "combined",
) -> pd.DataFrame:
    """Yıllık hedefi aylık mevsimsel ağırlıklarla dağıtır.

    Formül:
        planned_qty[m] = round(annual_target × si[m] / 12)
        Aralık ayına yuvarlama düzeltmesi uygulanır → toplam = annual_target

    Args:
        annual_target: Planlanan yıllık araç adedi.
        si_series:     1-12 indeksli mevsimsel indeks serisi.
        label:         Hangi SI kaynağının kullanıldığını gösteren etiket.

    Returns:
        DataFrame sütunları:
            month, month_name, si, planned_qty, share_pct,
            cumulative_qty, cumulative_pct
    """
    si_aligned = si_series.reindex(range(1, 13), fill_value=0)

    # Aylık planlama: hedef × SI / 12
    planned = (annual_target * si_aligned / 12).round(0).astype(int)

    # Yuvarlama farkını Aralık'a ekle → toplam kesin olarak annual_target
    diff = annual_target - planned.sum()
    planned.iloc[-1] += diff

    cumulative = planned.cumsum()

    df_plan = pd.DataFrame({
        "month":          range(1, 13),
        "month_name":     MONTH_ABBR_TR,
        "si":             si_aligned.values.round(4),
        "planned_qty":    planned.values,
        "share_pct":      (planned.values / annual_target * 100).round(2),
        "cumulative_qty": cumulative.values,
        "cumulative_pct": (cumulative.values / annual_target * 100).round(2),
    })
    df_plan.attrs["label"] = label
    df_plan.attrs["annual_target"] = annual_target
    return df_plan


# ---------------------------------------------------------------------------
# 7. Görselleştirmeler
# ---------------------------------------------------------------------------

def plot_market_hierarchy(
    odd_si: pd.Series,
    seg_si: pd.Series,
    ns_si: pd.Series,
    final_si: pd.Series,
    output_dir: Path,
) -> None:
    """Dört SI katmanını tek grafikte (çizgi + bar) gösterir.

    Args:
        odd_si:     ODD piyasa SI serisi.
        seg_si:     Segment SI serisi.
        ns_si:      NORTHSTAR SI serisi.
        final_si:   Nihai ağırlıklı SI serisi.
        output_dir: Çıktı klasörü.
    """
    x = np.arange(12)
    labels = MONTH_ABBR_EN

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(
        "Mevsimsel İndeks — Piyasa Hiyerarşisi\n"
        "(ODD × 0.50 + Segment × 0.30 + NORTHSTAR × 0.20)",
        fontsize=14, fontweight="bold",
    )

    # Üst: çizgi grafik
    ax1.plot(x, odd_si.values,   "o-",  color="#1565C0", lw=2, ms=6, label="ODD (Piyasa w=0.50)")
    ax1.plot(x, seg_si.values,   "s--", color="#43A047", lw=2, ms=6, label="Segment (w=0.30)")
    ax1.plot(x, ns_si.values,    "^:",  color="#FB8C00", lw=2, ms=6, label="NORTHSTAR (w=0.20)")
    ax1.plot(x, final_si.values, "D-",  color="#E53935", lw=2.5, ms=7, label="FINAL (önerilen)")
    ax1.axhline(1.0, color="gray", linestyle="--", lw=1.2, label="Ortalama (1.0)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel("Mevsimsel İndeks")
    ax1.set_title("Katman Karşılaştırması")
    ax1.legend(fontsize=9, ncol=2)
    ax1.set_ylim(0, max(odd_si.max(), seg_si.max(), ns_si.max(), final_si.max()) * 1.20)

    # Alt: bar grafik (final SI)
    colors = ["#E53935" if v < 0.9 else "#FDD835" if v < 1.1 else "#43A047"
              for v in final_si.values]
    bars = ax2.bar(x, final_si.values, color=colors, alpha=0.85, edgecolor="white")
    for bar, val in zip(bars, final_si.values):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.015,
            f"{val:.2f}",
            ha="center", va="bottom", fontsize=8, fontweight="bold",
        )
    ax2.axhline(1.0, color="gray", linestyle="--", lw=1.2)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_ylabel("Nihai Mevsimsel İndeks")
    ax2.set_title("Nihai SI (kırmızı=dip <0.90, sarı=normal, yeşil=peak >1.10)")
    ax2.set_ylim(0, final_si.max() * 1.22)

    fig.tight_layout()
    _save_fig(fig, output_dir / "01_piyasa_hiyerarsisi.png")


def plot_final_si_bar(final_si: pd.Series, output_dir: Path) -> None:
    """Nihai SI'ı renklendirilmiş bar grafik olarak gösterir.

    Args:
        final_si:   Nihai ağırlıklı SI serisi (index 1-12).
        output_dir: Çıktı klasörü.
    """
    x = np.arange(12)
    # Renklendirme: kırmızı <0.9, sarı 0.9-1.1, yeşil >1.1
    colors = [
        "#E53935" if v < 0.9 else "#FDD835" if v <= 1.1 else "#43A047"
        for v in final_si.values
    ]

    fig, ax = plt.subplots(figsize=(13, 6))
    bars = ax.bar(x, final_si.values, color=colors, alpha=0.88, edgecolor="white", width=0.7)
    for bar, val in zip(bars, final_si.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.012,
            f"{val:.3f}",
            ha="center", va="bottom", fontsize=9, fontweight="bold",
        )
    ax.axhline(1.0, color="gray", linestyle="--", lw=1.5, label="Ortalama (1.0)")
    ax.set_xticks(x)
    ax.set_xticklabels(MONTH_ABBR_EN, fontsize=10)
    ax.set_ylabel("Mevsimsel İndeks (1.0 = ortalama)")
    ax.set_title("Nihai Mevsimsel İndeks — FINAL SI\n(kırmızı=dip, sarı=normal, yeşil=peak)")
    ax.legend(fontsize=10)
    ax.set_ylim(0, final_si.max() * 1.20)

    # Açıklama notu
    ax.text(
        0.99, 0.02,
        "final_si = 0.50×ODD + 0.30×Segment + 0.20×NORTHSTAR",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=8, color="gray", style="italic",
    )
    fig.tight_layout()
    _save_fig(fig, output_dir / "02_final_indeks_bar.png")


def plot_final_si_polar(final_si: pd.Series, output_dir: Path) -> None:
    """Nihai SI'ı polar/radar grafik olarak gösterir.

    Args:
        final_si:   Nihai ağırlıklı SI serisi (index 1-12).
        output_dir: Çıktı klasörü.
    """
    vals = final_si.tolist() + [final_si.iloc[0]]  # grafiği kapat
    angles = np.linspace(0, 2 * np.pi, 12, endpoint=False).tolist()
    angles += [angles[0]]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
    ax.plot(angles, vals, "o-", lw=2.5, color="#E53935", markersize=7)
    ax.fill(angles, vals, alpha=0.18, color="#E53935")
    # Referans daire: SI = 1.0
    ax.plot(angles, [1.0] * 13, "--", lw=1.2, color="gray", alpha=0.7, label="SI = 1.0")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(MONTH_ABBR_EN, fontsize=10)
    ax.set_ylim(0, max(vals) * 1.15)
    ax.set_title("Nihai Mevsimsel İndeks — Yıl Döngüsü", pad=22, fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1.1), fontsize=9)

    # Değerleri grafik üzerine yaz
    for angle, val, lbl in zip(angles[:-1], vals[:-1], MONTH_ABBR_EN):
        ax.text(angle, val + 0.055, f"{val:.2f}", ha="center", fontsize=8, color="#E53935")

    fig.tight_layout()
    _save_fig(fig, output_dir / "03_final_indeks_polar.png")


def _heatmap(
    pivot: pd.DataFrame,
    title: str,
    output_path: Path,
) -> None:
    """Genel amaçlı SI heatmap yardımcısı.

    Args:
        pivot:       Satır=ay (1-12), sütun=kategori (bayi/model/renk) DataFrame.
        title:       Grafik başlığı.
        output_path: Kaydedilecek dosya yolu.
    """
    # Ay kısaltmalarını satır etiketlerine ekle
    data = pivot.copy()
    data.index = MONTH_ABBR_EN

    n_cols = data.shape[1]
    fig_w = max(10, n_cols * 1.2)
    fig, ax = plt.subplots(figsize=(fig_w, 7))

    sns.heatmap(
        data,
        annot=True,
        fmt=".2f",
        cmap="RdYlGn",
        center=1.0,
        vmin=0.4,
        vmax=1.8,
        linewidths=0.4,
        linecolor="white",
        ax=ax,
        cbar_kws={"label": "Mevsimsel İndeks (1.0 = ortalama)"},
        annot_kws={"size": 8},
    )
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Ay")
    fig.tight_layout()
    _save_fig(fig, output_path)


def plot_dealer_heatmap(dealer_si_pivot: pd.DataFrame, output_dir: Path) -> None:
    """Bayi × ay mevsimsel indeks ısı haritası.

    Args:
        dealer_si_pivot: compute_dealer_si() çıktısı.
        output_dir:      Çıktı klasörü.
    """
    _heatmap(
        dealer_si_pivot,
        title="Bayi Bazında Mevsimsel İndeks Isı Haritası",
        output_path=output_dir / "04_bayi_heatmap.png",
    )


def plot_model_heatmap(model_si_pivot: pd.DataFrame, output_dir: Path) -> None:
    """Model × ay mevsimsel indeks ısı haritası.

    Args:
        model_si_pivot: compute_model_si() çıktısı.
        output_dir:     Çıktı klasörü.
    """
    _heatmap(
        model_si_pivot,
        title="Model Bazında Mevsimsel İndeks Isı Haritası",
        output_path=output_dir / "05_model_heatmap.png",
    )


def plot_color_heatmap(color_si_pivot: pd.DataFrame, output_dir: Path) -> None:
    """Renk × ay mevsimsel indeks ısı haritası.

    Args:
        color_si_pivot: compute_color_si() çıktısı.
        output_dir:     Çıktı klasörü.
    """
    _heatmap(
        color_si_pivot,
        title="Renk Bazında Mevsimsel İndeks Isı Haritası (Top 10)",
        output_path=output_dir / "06_renk_heatmap.png",
    )


def plot_monthly_plan(plan_df: pd.DataFrame, annual_target: int, output_dir: Path) -> None:
    """Aylık dağıtım planını 2 panelli grafik olarak gösterir.

    Üst panel: bars (aylık adet) + çizgi (SI), Alt panel: kümülatif ilerleme.

    Args:
        plan_df:       monthly_plan() çıktısı.
        annual_target: Yıllık hedef adedi.
        output_dir:    Çıktı klasörü.
    """
    x = np.arange(12)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9))
    fig.suptitle(
        f"Aylık Dağıtım Planı — Yıllık Hedef: {annual_target:,} araç\n"
        f"(Nihai SI: 0.50×ODD + 0.30×Segment + 0.20×NORTHSTAR)",
        fontsize=13, fontweight="bold",
    )

    # --- Üst panel: aylık adet + SI ---
    bar_colors = [
        "#E53935" if v < 0.9 else "#FDD835" if v <= 1.1 else "#43A047"
        for v in plan_df["si"]
    ]
    bars = ax1.bar(x, plan_df["planned_qty"], color=bar_colors, alpha=0.85, edgecolor="white")
    for bar, qty in zip(bars, plan_df["planned_qty"]):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{qty:,}",
            ha="center", va="bottom", fontsize=8.5, fontweight="bold",
        )

    # İkincil eksen: SI çizgisi
    ax1b = ax1.twinx()
    ax1b.plot(x, plan_df["si"], "o--", color="#1565C0", lw=2, ms=6, label="Mevsimsel İndeks (SI)")
    ax1b.axhline(1.0, color="gray", linestyle=":", lw=1.2)
    ax1b.set_ylabel("Mevsimsel İndeks", color="#1565C0")
    ax1b.tick_params(axis="y", labelcolor="#1565C0")
    ax1b.legend(loc="upper left", fontsize=9)
    ax1b.set_ylim(0, plan_df["si"].max() * 1.30)

    ax1.set_xticks(x)
    ax1.set_xticklabels(MONTH_ABBR_EN, fontsize=9)
    ax1.set_ylabel("Planlanan Araç Adedi")
    ax1.set_title("Aylık Hedef Dağılımı")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))

    # --- Alt panel: kümülatif ---
    ax2.fill_between(x, plan_df["cumulative_qty"], alpha=0.15, color="#1565C0")
    ax2.plot(x, plan_df["cumulative_qty"], "o-", color="#1565C0", lw=2.2, ms=6)
    ax2.axhline(annual_target, color="#E53935", linestyle="--", lw=1.5,
                label=f"Yıllık Hedef: {annual_target:,}")
    for xi, cum, pct in zip(x, plan_df["cumulative_qty"], plan_df["cumulative_pct"]):
        if xi % 2 == 0 or xi == 11:
            ax2.annotate(
                f"%{pct:.0f}", (xi, cum),
                textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=8, color="#1565C0",
            )
    ax2.set_xticks(x)
    ax2.set_xticklabels(MONTH_ABBR_EN, fontsize=9)
    ax2.set_ylabel("Kümülatif Araç Adedi")
    ax2.set_title("Kümülatif Hedef İlerlemesi")
    ax2.legend(fontsize=9)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))

    fig.tight_layout()
    _save_fig(fig, output_dir / "07_aylik_plan.png")


# ---------------------------------------------------------------------------
# 8. Metin raporu
# ---------------------------------------------------------------------------

def generate_report(
    odd_si: pd.Series,
    seg_si: pd.Series,
    ns_si: pd.Series,
    final_si: pd.Series,
    dealer_si: pd.DataFrame,
    model_si: pd.DataFrame,
    color_si: pd.DataFrame,
    plan: pd.DataFrame,
    annual_target: int,
) -> str:
    """Kapsamlı mevsimsellik analiz raporu üretir.

    Args:
        odd_si:       ODD piyasa SI (index 1-12).
        seg_si:       Segment SI (index 1-12).
        ns_si:        NORTHSTAR SI (index 1-12).
        final_si:     Nihai ağırlıklı SI (index 1-12).
        dealer_si:    Bayi SI pivot tablosu.
        model_si:     Model SI pivot tablosu.
        color_si:     Renk SI pivot tablosu.
        plan:         monthly_plan() çıktısı.
        annual_target: Yıllık hedef adedi.

    Returns:
        Metin raporu (str).
    """
    lines: list[str] = []

    def h1(title: str) -> None:
        lines.append("\n" + "=" * 70)
        lines.append(f"  {title}")
        lines.append("=" * 70)

    def h2(title: str) -> None:
        lines.append(f"\n  --- {title} ---")

    # Başlık
    h1("MEVSİMSELLİK ANALİZİ RAPORU — NORTHSTAR 2024-2025")
    lines.append(textwrap.dedent("""
        Metodoloji: Klasik oran-ortalaması (ratio-to-mean)
          SI[ay] = 2 yıllık_aylık_ortalama[ay] / grand_mean
          grand_mean = toplam_satış / 24   (2 yıl × 12 ay)
          SI > 1.0 → Peak (ortalama üstü talep)
          SI < 1.0 → Dip  (ortalama altı talep)

        Üç piyasa katmanı ve ağırlıkları:
          ODD (Türkiye ithal piyasası)  w = 0.50  → en geniş veri tabanı
          Segment (9 rakip marka)       w = 0.30  → rekabetçi bağlam
          NORTHSTAR                     w = 0.20  → marka özgül

        Nihai SI = 0.50 × ODD + 0.30 × Segment + 0.20 × NORTHSTAR
    """).strip())

    # ODD SI tablosu
    h1("1. ODD PAZAR SI (Türkiye İthal Otomobil Toplam Piyasası)")
    lines.append(f"\n  {'Ay':<10} {'ODD SI':>8}  {'Yorum'}")
    lines.append("  " + "-" * 38)
    for m, val in odd_si.items():
        yorum = _si_comment(val)
        lines.append(f"  {MONTH_ABBR_TR[m-1]:<10} {val:>8.4f}  {yorum}")

    # Segment SI tablosu
    h1("2. SEGMENT SI (9 Rakip Marka Toplamı)")
    lines.append(f"\n  {'Ay':<10} {'Seg SI':>8}  {'Yorum'}")
    lines.append("  " + "-" * 38)
    for m, val in seg_si.items():
        yorum = _si_comment(val)
        lines.append(f"  {MONTH_ABBR_TR[m-1]:<10} {val:>8.4f}  {yorum}")

    # NORTHSTAR SI tablosu
    h1("3. NORTHSTAR SI (Marka Satış İşlemleri)")
    lines.append(f"\n  {'Ay':<10} {'NS SI':>8}  {'Yorum'}")
    lines.append("  " + "-" * 38)
    for m, val in ns_si.items():
        yorum = _si_comment(val)
        lines.append(f"  {MONTH_ABBR_TR[m-1]:<10} {val:>8.4f}  {yorum}")

    # FINAL SI tablosu — en önemli bölüm
    h1("*** 4. NİHAİ ÖNERILEN SI — PLANLAMA İÇİN KULLANILACAK ***")
    lines.append("    (final_si = 0.50×ODD + 0.30×Segment + 0.20×NORTHSTAR)\n")
    lines.append(f"  {'Ay':<10} {'ODD SI':>8} {'Seg SI':>8} {'NS SI':>8} {'FINAL SI':>10}  {'Yorum'}")
    lines.append("  " + "-" * 60)
    for m in range(1, 13):
        f_val = final_si[m]
        lines.append(
            f"  {MONTH_ABBR_TR[m-1]:<10} {odd_si[m]:>8.4f} {seg_si[m]:>8.4f} "
            f"{ns_si[m]:>8.4f} {f_val:>10.4f}  {_si_comment(f_val)}"
        )

    # Peak/Dip analizi
    h1("5. PEAK / DİP AY ANALİZİ")
    top3 = final_si.nlargest(3)
    bot3 = final_si.nsmallest(3)
    lines.append("\n  PEAK (en yüksek talep dönemleri):")
    for m, val in top3.items():
        lines.append(
            f"    {MONTH_ABBR_TR[m-1]:<10} SI={val:.4f}  "
            f"ortalamanın {(val-1)*100:+.1f}% üstünde"
        )
    lines.append("\n  DİP (en düşük talep dönemleri):")
    for m, val in bot3.items():
        lines.append(
            f"    {MONTH_ABBR_TR[m-1]:<10} SI={val:.4f}  "
            f"ortalamanın {(val-1)*100:+.1f}% altında"
        )

    # Bayi SI pivot
    h1("6. BAYİ BAZINDA MEVSİMSEL İNDEKS")
    if not dealer_si.empty:
        _pivot_to_lines(dealer_si, lines)
    else:
        lines.append("\n  (Veri yok)")

    # Model SI pivot
    h1("7. MODEL BAZINDA MEVSİMSEL İNDEKS")
    if not model_si.empty:
        _pivot_to_lines(model_si, lines)
    else:
        lines.append("\n  (Veri yok)")

    # Renk SI pivot
    h1("8. RENK BAZINDA MEVSİMSEL İNDEKS (Top 10)")
    if not color_si.empty:
        _pivot_to_lines(color_si, lines)
    else:
        lines.append("\n  (Veri yok)")

    # Aylık plan tablosu
    h1(f"9. AYLIK DAĞITIM PLANI — {annual_target:,} ARAÇ YILLIK HEDEF")
    lines.append(
        f"\n  {'Ay':<10} {'SI':>7} {'Plan (adet)':>13} {'Pay %':>7} "
        f"{'Kümülatif':>12} {'Kümül %':>9}"
    )
    lines.append("  " + "-" * 62)
    for _, row in plan.iterrows():
        bar = "█" * int(row["share_pct"] / 1.0)
        lines.append(
            f"  {row['month_name']:<10} {row['si']:>7.4f} "
            f"{int(row['planned_qty']):>13,} {row['share_pct']:>7.2f}% "
            f"{int(row['cumulative_qty']):>12,} {row['cumulative_pct']:>8.2f}%  {bar}"
        )
    lines.append(f"\n  TOPLAM: {plan['planned_qty'].sum():,} araç")

    # Kullanım rehberi
    h1("10. KULLANIM REHBERİ")
    lines.append(textwrap.dedent("""
        Bu modülü başka scriptlerden kullanmak için:

            from src.analysis.seasonality import (
                compute_odd_si, compute_segment_si, compute_northstar_si,
                compute_final_si, monthly_plan,
            )
            from src.analysis.data_loader import load_sales, load_competitors
            from pathlib import Path

            data_dir = Path("data/raw")
            odd_si      = compute_odd_si(data_dir)
            seg_si      = compute_segment_si(load_competitors(data_dir))
            ns_si       = compute_northstar_si(load_sales(data_dir))
            final_si    = compute_final_si(odd_si, seg_si, ns_si)
            plan        = monthly_plan(3_600, final_si)
            print(plan)

        Çıktı dosyaları (outputs/seasonality/):
            04_FINAL_si.csv    → Planlama için kullanılacak indeks
            08_aylik_plan_*.csv → Aylık dağıtım planı
    """).strip())

    return "\n".join(lines)


def _si_comment(val: float) -> str:
    """SI değerine göre kısa yorum döndürür."""
    if val >= 1.30:
        return "Yüksek peak"
    if val >= 1.10:
        return "Peak"
    if val >= 0.90:
        return "Ortalama"
    if val >= 0.70:
        return "Dip"
    return "Derin dip"


def _pivot_to_lines(pivot: pd.DataFrame, lines: list[str]) -> None:
    """Pivot tabloyu metin satırları olarak lines listesine ekler."""
    cols = list(pivot.columns)
    col_width = 9
    header = f"  {'Ay':<8}" + "".join(f"{str(c)[:col_width]:>{col_width+1}}" for c in cols)
    lines.append("\n" + header)
    lines.append("  " + "-" * len(header))
    for m, row in pivot.iterrows():
        row_str = f"  {MONTH_ABBR_TR[int(m)-1]:<8}"
        for val in row.values:
            row_str += f"{val:>{col_width+1}.2f}"
        lines.append(row_str)


# ---------------------------------------------------------------------------
# 9. Ana çalıştırma
# ---------------------------------------------------------------------------

def run(annual_target: int = 3_600) -> None:
    """Tüm mevsimsellik analizini çalıştırır ve çıktıları üretir.

    Adımlar:
        1. Veriler yüklenir (ODD CSV, rakip, NORTHSTAR satışları)
        2. ODD / Segment / NORTHSTAR SI hesaplanır
        3. Nihai ağırlıklı SI hesaplanır (0.50 + 0.30 + 0.20)
        4. Granüler SI'lar hesaplanır (bayi, model, renk)
        5. Aylık plan oluşturulur
        6. CSV çıktıları kaydedilir
        7. Metin raporu kaydedilir
        8. 7 görsel üretilir

    Args:
        annual_target: Plan tablosu için yıllık araç hedefi.
    """
    OUTPUT_DIR = Path(__file__).parents[2] / "outputs" / "seasonality"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    DATA_DIR = Path(__file__).parents[2] / "data" / "raw"

    print("\n[1/5] Veriler yükleniyor...")
    df_sales = load_sales(DATA_DIR)
    df_comp  = load_competitors(DATA_DIR)
    print(f"  NORTHSTAR: {len(df_sales):,} işlem")
    print(f"  Rakip: {df_comp['brand'].nunique()} marka, {len(df_comp):,} kayıt")

    print("\n[2/5] Mevsimsel indeksler hesaplanıyor...")
    odd_si  = compute_odd_si(DATA_DIR)
    seg_si  = compute_segment_si(df_comp)
    ns_si   = compute_northstar_si(df_sales)
    final_si = compute_final_si(odd_si, seg_si, ns_si)

    dealer_si = compute_dealer_si(df_sales)
    model_si  = compute_model_si(df_sales)
    color_si  = compute_color_si(df_sales)

    plan = monthly_plan(annual_target, final_si, label="final")

    print("\n[3/5] CSV çıktıları kaydediliyor...")

    # Pazar katmanları
    odd_df = pd.DataFrame({"month": range(1, 13), "month_name": MONTH_ABBR_TR, "odd_si": odd_si.values})
    seg_df = pd.DataFrame({"month": range(1, 13), "month_name": MONTH_ABBR_TR, "segment_si": seg_si.values})
    ns_df  = pd.DataFrame({"month": range(1, 13), "month_name": MONTH_ABBR_TR, "northstar_si": ns_si.values})
    final_df = pd.DataFrame({
        "month":        range(1, 13),
        "month_name":   MONTH_ABBR_TR,
        "odd_si":       odd_si.values,
        "segment_si":   seg_si.values,
        "northstar_si": ns_si.values,
        "final_si":     final_si.values,
    })

    csv_outputs = [
        (odd_df,         "01_odd_si.csv"),
        (seg_df,         "02_segment_si.csv"),
        (ns_df,          "03_northstar_si.csv"),
        (final_df,       "04_FINAL_si.csv"),
        (dealer_si.reset_index(), "05_bayi_si.csv"),
        (model_si.reset_index(),  "06_model_si.csv"),
        (color_si.reset_index(),  "07_renk_si.csv"),
        (plan,           f"08_aylik_plan_{annual_target}.csv"),
    ]
    for df, fname in csv_outputs:
        path = OUTPUT_DIR / fname
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  Kaydedildi: {path}")

    print("\n[4/5] Metin raporu oluşturuluyor...")
    report = generate_report(
        odd_si, seg_si, ns_si, final_si,
        dealer_si, model_si, color_si,
        plan, annual_target,
    )
    rpath = OUTPUT_DIR / "mevsimsellik_raporu.txt"
    rpath.write_text(report, encoding="utf-8")
    print(f"  Kaydedildi: {rpath}")

    print("\n[5/5] Görseller oluşturuluyor...")
    plot_market_hierarchy(odd_si, seg_si, ns_si, final_si, OUTPUT_DIR)
    plot_final_si_bar(final_si, OUTPUT_DIR)
    plot_final_si_polar(final_si, OUTPUT_DIR)
    plot_dealer_heatmap(dealer_si, OUTPUT_DIR)
    plot_model_heatmap(model_si, OUTPUT_DIR)
    plot_color_heatmap(color_si, OUTPUT_DIR)
    plot_monthly_plan(plan, annual_target, OUTPUT_DIR)

    print(f"\nTamamlandi → {OUTPUT_DIR}")
    print(f"\n{report}")


if __name__ == "__main__":
    import sys
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 3_600)
