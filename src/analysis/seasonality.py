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
    1. ODD SI       — Türkiye ithal otomobil piyasası, 53 marka, toplam hacim
    2. Segment SI   — 9 rakip marka toplamı, rekabetçi bağlam
    3. NORTHSTAR SI — Sadece NORTHSTAR işlem verisi, marka özgül

Nihai SI (final_si):
    final_si = w_odd × odd_si + w_seg × segment_si + w_ns × northstar_si

Ağırlıklandırma yöntemi — Yıllar arası tutarlılık (Year-over-Year Stability):
    Her kaynağın 2024 ve 2025 SI profilleri ayrı hesaplanır; Pearson korelasyonu
    ile yıllar arası tutarlılık (r) ölçülür. Tutarlı kaynak → düşük gürültü →
    güvenilir → daha yüksek ağırlık.

        stability_i = Pearson_r(SI_i_2024, SI_i_2025)  [0, 1]'e kırpılır
        w_i = stability_i / Σ stability

    - ODD ve Segment büyük örneklem → düşük çökelme gürültüsü → yüksek r
    - NORTHSTAR n≈6,400 → daha yüksek örnekleme gürültüsü → düşük r → düşük w
    - Sonuç: veriden otomatik hesaplanır, keyfi değildir.

    compute_optimal_weights() ile hesaplanır; run() her çalışmada günceller.
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

from src.analysis.data_loader import MONTH_TR_MAP, load_competitors, load_sales

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
# İkili kombinasyon (bayi×model / bayi×renk) için düşürülmüş eşik
MIN_COMBO_THRESHOLD = 8


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


def _year_si(df: pd.DataFrame, value_col: str) -> pd.Series:
    """Tek bir yıla ait veriyle normalize aylık profil (stability hesabı için).

    Args:
        df:         "month" ve value_col sütunlarını içeren DataFrame (tek yıl).
        value_col:  Sayısal değer sütunu.

    Returns:
        1-12 indeksli normalize seri (grand_mean=1 değil, o yılın ortalaması=1).
    """
    monthly = (
        df.groupby("month")[value_col]
        .sum()
        .reindex(range(1, 13), fill_value=0.0)
    )
    grand = monthly.mean()
    return (monthly / grand).round(6) if grand > 0 else monthly * 0


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


def compute_per_brand_si(df_comp: pd.DataFrame) -> pd.DataFrame:
    """Her rakip marka için ayrı mevsimsel indeks pivot tablosu.

    Args:
        df_comp: load_competitors() çıktısı.
            Sütunlar: brand, year_month (YYYY-MM), sales_qty

    Returns:
        Pivot DataFrame: satırlar = ay (1-12), sütunlar = marka isimleri.
        Alfabetik sıralı, indeks adı "month".
    """
    df = df_comp.copy()
    df["year"]  = df["year_month"].str[:4].astype(int)
    df["month"] = df["year_month"].str[5:7].astype(int)

    pivot_data: dict[str, list[float]] = {}
    for brand, grp in df.groupby("brand"):
        monthly = (
            grp.groupby(["year", "month"])["sales_qty"]
            .sum()
            .reset_index()
        )
        si = _ratio_to_mean(monthly, "sales_qty")
        pivot_data[str(brand)] = si.tolist()

    pivot = pd.DataFrame(pivot_data, index=range(1, 13))
    pivot.index.name = "month"
    # Alfabetik sırala
    pivot = pivot.reindex(sorted(pivot.columns), axis=1)
    return pivot


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
# 4. Veri tabanlı ağırlık hesabı
# ---------------------------------------------------------------------------

def compute_optimal_weights(
    data_dir: Path,
    df_comp: pd.DataFrame,
    df_sales: pd.DataFrame,
) -> tuple[float, float, float]:
    """Yıllar arası tutarlılık (YoY stability) tabanlı optimal ağırlık hesaplar.

    Yöntem (Year-over-Year Stability Weighting):
        Her kaynak için 2024 ve 2025 yılına ait aylık SI profili ayrı hesaplanır.
        Bu iki profilin Pearson korelasyonu = "tutarlılık skoru" (stability).
        Daha tutarlı kaynak → daha güvenilir mevsimsel sinyal → daha yüksek ağırlık.

        stability_i = max(0, corr(SI_i_2024, SI_i_2025))
        w_i = stability_i / Σ stability

    Akademik gerekçe:
        Yüksek YoY korelasyon → kaynağın mevsimsel örüntüsü gerçek mevsimselliği
        yansıtıyor (gürültü değil). Küçük örneklem (NORTHSTAR n≈6,400) daha fazla
        çökelme gürültüsü üretir → düşük r → düşük w. Büyük örneklem (ODD, Segment)
        daha stabil → yüksek r → yüksek w. Ağırlıklar veriden otomatik türetilir.

    Args:
        data_dir: data/raw/ klasörünün yolu.
        df_comp:  load_competitors() çıktısı.
        df_sales: load_sales() çıktısı.

    Returns:
        (w_odd, w_seg, w_ns) — normalize, toplamı = 1.0, 4 ondalık basamak.
    """
    # --- ODD: yıl bazlı aylık toplam ---
    odd_path = data_dir / "2024-2025-ODD-Otomobil-Satışlar-İthal).csv"
    raw_text = odd_path.read_text(encoding="utf-8-sig")
    lines_raw = raw_text.strip().splitlines()

    header_parts = lines_raw[0].split(";")
    month_keys: list[tuple[int, int]] = []
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

    monthly_odd: dict[tuple[int, int], float] = {k: 0.0 for k in month_keys}
    for line in lines_raw[1:]:
        if not line.strip():
            continue
        parts_l = line.split(";")
        brand_name = parts_l[0].strip()
        if not brand_name or brand_name.upper() == "TOTAL SALES":
            continue
        vals: list[float] = []
        for rv in parts_l[1: len(month_keys) + 1]:
            cleaned = rv.strip().replace(".", "").replace(",", ".")
            try:
                vals.append(float(cleaned))
            except ValueError:
                vals.append(0.0)
        if all(v == 0 for v in vals):
            continue
        for (yr, mn), val in zip(month_keys, vals):
            monthly_odd[(yr, mn)] += val

    df_odd = pd.DataFrame(
        [{"year": yr, "month": mn, "sales_qty": qty}
         for (yr, mn), qty in monthly_odd.items()]
    )

    odd_2024 = _year_si(df_odd[df_odd["year"] == 2024], "sales_qty")
    odd_2025 = _year_si(df_odd[df_odd["year"] == 2025], "sales_qty")
    stab_odd = max(0.0, float(odd_2024.corr(odd_2025)))

    # --- Segment: yıl bazlı aylık toplam ---
    df_c = df_comp.copy()
    df_c["year"]  = df_c["year_month"].str[:4].astype(int)
    df_c["month"] = df_c["year_month"].str[5:7].astype(int)
    seg_monthly = df_c.groupby(["year", "month"])["sales_qty"].sum().reset_index()

    seg_2024 = _year_si(seg_monthly[seg_monthly["year"] == 2024], "sales_qty")
    seg_2025 = _year_si(seg_monthly[seg_monthly["year"] == 2025], "sales_qty")
    stab_seg = max(0.0, float(seg_2024.corr(seg_2025)))

    # --- NORTHSTAR: yıl bazlı aylık toplam ---
    ns_monthly = (
        df_sales
        .groupby(["year", "month"])
        .size()
        .reset_index(name="sales_qty")
    )
    ns_2024 = _year_si(ns_monthly[ns_monthly["year"] == 2024], "sales_qty")
    ns_2025 = _year_si(ns_monthly[ns_monthly["year"] == 2025], "sales_qty")
    stab_ns = max(0.0, float(ns_2024.corr(ns_2025)))

    total = stab_odd + stab_seg + stab_ns
    if total == 0:
        # Veri yoksa eşit ağırlık
        return (round(1/3, 4), round(1/3, 4), round(1/3, 4))

    w_odd = round(stab_odd / total, 4)
    w_seg = round(stab_seg / total, 4)
    w_ns  = round(1.0 - w_odd - w_seg, 4)   # toplam = 1 garantisi

    return w_odd, w_seg, w_ns


def _stability_detail(
    data_dir: Path,
    df_comp: pd.DataFrame,
    df_sales: pd.DataFrame,
) -> dict[str, float]:
    """compute_optimal_weights() hesabında kullanılan ham stability skorlarını döndürür.

    Raporlama ve doğrulama amacıyla kullanılır.

    Returns:
        {"odd": r_odd, "seg": r_seg, "ns": r_ns}
    """
    # ODD
    odd_path = data_dir / "2024-2025-ODD-Otomobil-Satışlar-İthal).csv"
    raw_text = odd_path.read_text(encoding="utf-8-sig")
    lines_raw = raw_text.strip().splitlines()
    header_parts = lines_raw[0].split(";")
    month_keys: list[tuple[int, int]] = []
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
    monthly_odd: dict[tuple[int, int], float] = {k: 0.0 for k in month_keys}
    for line in lines_raw[1:]:
        if not line.strip():
            continue
        parts_l = line.split(";")
        brand_name = parts_l[0].strip()
        if not brand_name or brand_name.upper() == "TOTAL SALES":
            continue
        vals: list[float] = []
        for rv in parts_l[1: len(month_keys) + 1]:
            cleaned = rv.strip().replace(".", "").replace(",", ".")
            try:
                vals.append(float(cleaned))
            except ValueError:
                vals.append(0.0)
        if all(v == 0 for v in vals):
            continue
        for (yr, mn), val in zip(month_keys, vals):
            monthly_odd[(yr, mn)] += val
    df_odd = pd.DataFrame(
        [{"year": yr, "month": mn, "sales_qty": qty}
         for (yr, mn), qty in monthly_odd.items()]
    )
    odd_2024 = _year_si(df_odd[df_odd["year"] == 2024], "sales_qty")
    odd_2025 = _year_si(df_odd[df_odd["year"] == 2025], "sales_qty")
    r_odd = max(0.0, float(odd_2024.corr(odd_2025)))

    # Segment
    df_c = df_comp.copy()
    df_c["year"]  = df_c["year_month"].str[:4].astype(int)
    df_c["month"] = df_c["year_month"].str[5:7].astype(int)
    seg_monthly = df_c.groupby(["year", "month"])["sales_qty"].sum().reset_index()
    seg_2024 = _year_si(seg_monthly[seg_monthly["year"] == 2024], "sales_qty")
    seg_2025 = _year_si(seg_monthly[seg_monthly["year"] == 2025], "sales_qty")
    r_seg = max(0.0, float(seg_2024.corr(seg_2025)))

    # NORTHSTAR
    ns_monthly = df_sales.groupby(["year", "month"]).size().reset_index(name="sales_qty")
    ns_2024 = _year_si(ns_monthly[ns_monthly["year"] == 2024], "sales_qty")
    ns_2025 = _year_si(ns_monthly[ns_monthly["year"] == 2025], "sales_qty")
    r_ns = max(0.0, float(ns_2024.corr(ns_2025)))

    return {"odd": r_odd, "seg": r_seg, "ns": r_ns}


# ---------------------------------------------------------------------------
# 5. Granüler NORTHSTAR indeksleri (bayi / model / renk)
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


def compute_dealer_model_si(df_sales: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Bayi × Model kombinasyonu bazında mevsimsel indeks.

    Sadece NORTHSTAR (Marka X) 2024-2025 kendi satış verisi kullanılır;
    piyasa veya rakip verisi dahil edilmez.
    Her bayi için, o bayinin sattığı her model bazında ayrı SI hesaplanır.
    İkili kombinasyon için veri eşiği MIN_COMBO_THRESHOLD olarak düşürülür.

    Args:
        df_sales: load_sales() çıktısı.

    Returns:
        Dict: bayi adı → DataFrame (satır=ay 1-12, sütun=model adları).
    """
    result: dict[str, pd.DataFrame] = {}

    for dealer, dealer_grp in df_sales.groupby("Dealer Name"):
        if len(dealer_grp) < MIN_SALES_THRESHOLD:
            continue

        model_sis: dict[str, list[float]] = {}
        for model, model_grp in dealer_grp.groupby("Model Description"):
            if len(model_grp) < MIN_COMBO_THRESHOLD:
                continue
            monthly = (
                model_grp
                .groupby(["year", "month"])
                .size()
                .reset_index(name="sales_qty")
            )
            si_series = _ratio_to_mean(monthly, "sales_qty")
            model_sis[str(model)] = si_series.tolist()

        if model_sis:
            df = pd.DataFrame(model_sis, index=range(1, 13))
            df.index.name = "month"
            result[str(dealer)] = df

    return result


def compute_dealer_color_si(df_sales: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Bayi × Renk kombinasyonu bazında mevsimsel indeks.

    Sadece NORTHSTAR (Marka X) 2024-2025 kendi satış verisi kullanılır;
    piyasa veya rakip verisi dahil edilmez.
    Her bayi için, en çok satılan ilk 5 renk bazında SI hesaplanır.
    İkili kombinasyon için veri eşiği MIN_COMBO_THRESHOLD olarak düşürülür.

    Args:
        df_sales: load_sales() çıktısı.

    Returns:
        Dict: bayi adı → DataFrame (satır=ay 1-12, sütun=renk adları).
    """
    result: dict[str, pd.DataFrame] = {}

    for dealer, dealer_grp in df_sales.groupby("Dealer Name"):
        if len(dealer_grp) < MIN_SALES_THRESHOLD:
            continue

        # Bu bayinin en çok sattığı 5 renk
        top_colors = (
            dealer_grp["Exterior Color"]
            .value_counts()
            .head(5)
            .index
            .tolist()
        )

        color_sis: dict[str, list[float]] = {}
        for color in top_colors:
            color_grp = dealer_grp[dealer_grp["Exterior Color"] == color]
            if len(color_grp) < MIN_COMBO_THRESHOLD:
                continue
            monthly = (
                color_grp
                .groupby(["year", "month"])
                .size()
                .reset_index(name="sales_qty")
            )
            si_series = _ratio_to_mean(monthly, "sales_qty")
            color_sis[str(color)] = si_series.tolist()

        if color_sis:
            df = pd.DataFrame(color_sis, index=range(1, 13))
            df.index.name = "month"
            result[str(dealer)] = df

    return result


def _dict_si_to_long(
    si_dict: dict[str, pd.DataFrame],
    key_col: str,
) -> pd.DataFrame:
    """Bayi→DataFrame(ay×kategori) yapısını long format CSV için düzleştirir.

    Args:
        si_dict:  compute_dealer_model_si() veya compute_dealer_color_si() çıktısı.
        key_col:  Kategori sütun adı ("model" veya "color").

    Returns:
        Long format DataFrame: dealer, key_col, month, month_name, si.
    """
    rows: list[dict] = []
    for dealer, df in si_dict.items():
        for cat in df.columns:
            for month_no, si_val in zip(range(1, 13), df[cat].tolist()):
                rows.append({
                    "dealer":     dealer,
                    key_col:      cat,
                    "month":      month_no,
                    "month_name": MONTH_ABBR_TR[month_no - 1],
                    "si":         round(float(si_val), 4),
                })
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["dealer", key_col, "month", "month_name", "si"])


# ---------------------------------------------------------------------------
# 6. Nihai ağırlıklı SI
# ---------------------------------------------------------------------------

def compute_final_si(
    odd_si: pd.Series,
    segment_si: pd.Series,
    northstar_si: pd.Series,
    w_odd: float,
    w_seg: float,
    w_ns: float,
) -> pd.Series:
    """Üç katmanı ağırlıklı ortalama ile birleştirir.

    Ağırlıkların compute_optimal_weights() ile hesaplanması önerilir.

    Args:
        odd_si:       ODD piyasa SI serisi (index 1-12).
        segment_si:   Segment SI serisi (index 1-12).
        northstar_si: NORTHSTAR SI serisi (index 1-12).
        w_odd:        ODD ağırlığı.
        w_seg:        Segment ağırlığı.
        w_ns:         NORTHSTAR ağırlığı.

    Returns:
        1-12 indeksli nihai SI serisi (4 basamak yuvarlama).
    """
    final = (w_odd * odd_si + w_seg * segment_si + w_ns * northstar_si).round(4)
    final.index = range(1, 13)
    return final


# ---------------------------------------------------------------------------
# 7. Planlama fonksiyonu
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
# 8. Görselleştirmeler
# ---------------------------------------------------------------------------

def plot_market_hierarchy(
    odd_si: pd.Series,
    seg_si: pd.Series,
    ns_si: pd.Series,
    final_si: pd.Series,
    output_dir: Path,
    weights: tuple[float, float, float] = (0.50, 0.30, 0.20),
) -> None:
    """Dört SI katmanını tek grafikte (çizgi + bar) gösterir.

    Args:
        odd_si:     ODD piyasa SI serisi.
        seg_si:     Segment SI serisi.
        ns_si:      NORTHSTAR SI serisi.
        final_si:   Nihai ağırlıklı SI serisi.
        output_dir: Çıktı klasörü.
        weights:    (w_odd, w_seg, w_ns) tuple.
    """
    w_odd, w_seg, w_ns = weights
    x = np.arange(12)
    labels = MONTH_ABBR_EN

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(
        "Mevsimsel İndeks — Piyasa Hiyerarşisi\n"
        f"(ODD×{w_odd:.2f} + Segment×{w_seg:.2f} + NORTHSTAR×{w_ns:.2f}  "
        "| YoY Stability Weighting)",
        fontsize=14, fontweight="bold",
    )

    # Üst: çizgi grafik
    ax1.plot(x, odd_si.values,   "o-",  color="#1565C0", lw=2, ms=6, label=f"ODD (w={w_odd:.2f})")
    ax1.plot(x, seg_si.values,   "s--", color="#43A047", lw=2, ms=6, label=f"Segment (w={w_seg:.2f})")
    ax1.plot(x, ns_si.values,    "^:",  color="#FB8C00", lw=2, ms=6, label=f"NORTHSTAR (w={w_ns:.2f})")
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


def plot_final_si_bar(
    final_si: pd.Series,
    output_dir: Path,
    weights: tuple[float, float, float] = (0.50, 0.30, 0.20),
) -> None:
    """Nihai SI'ı renklendirilmiş bar grafik olarak gösterir.

    Args:
        final_si:   Nihai ağırlıklı SI serisi (index 1-12).
        output_dir: Çıktı klasörü.
        weights:    (w_odd, w_seg, w_ns) tuple.
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
    w_odd, w_seg, w_ns = weights
    ax.text(
        0.99, 0.02,
        f"final_si = {w_odd:.2f}×ODD + {w_seg:.2f}×Segment + {w_ns:.2f}×NORTHSTAR  "
        "(YoY Stability)",
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


def plot_dealer_model_heatmap(
    dealer_model_si: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    """Model bazında Bayi × Ay mevsimsel indeks ısı haritası.

    Başlıkta açıkça belirtilir: Marka X 2024-2025 kendi satış verisi bazlıdır.
    Her model için ayrı bir heatmap üretilir: satırlar=bayiler, sütunlar=aylar.

    Args:
        dealer_model_si: compute_dealer_model_si() çıktısı.
        output_dir:      Çıktı klasörü.
    """
    if not dealer_model_si:
        return

    all_models: set[str] = set()
    for df in dealer_model_si.values():
        all_models.update(df.columns.tolist())

    for model in sorted(all_models):
        dealer_rows: dict[str, list[float]] = {}
        for dealer, df in sorted(dealer_model_si.items()):
            if model in df.columns:
                dealer_rows[dealer] = df[model].tolist()

        if len(dealer_rows) < 2:
            continue

        pivot = pd.DataFrame(dealer_rows, index=range(1, 13)).T
        pivot.columns = MONTH_ABBR_EN

        n_dealers = pivot.shape[0]
        fig_h = max(4, n_dealers * 0.45)
        fig, ax = plt.subplots(figsize=(14, fig_h))

        sns.heatmap(
            pivot,
            annot=True, fmt=".2f",
            cmap="RdYlGn", center=1.0,
            vmin=0.4, vmax=1.8,
            linewidths=0.4, linecolor="white",
            ax=ax,
            cbar_kws={"label": "Mevsimsel İndeks (1.0 = ortalama)"},
            annot_kws={"size": 8},
        )
        ax.set_title(
            f"Marka X 2024-2025 Kendi Satış Verisi Bazlı\n"
            f"{model} — Bayi Bazında Aylık Mevsimsel İndeks",
            fontsize=12, fontweight="bold",
        )
        ax.set_xlabel("Ay")
        ax.set_ylabel("Bayi")
        fig.tight_layout()

        safe = model.replace("/", "_").replace(" ", "_")
        _save_fig(fig, output_dir / f"10_bayi_model_{safe}_heatmap.png")


def plot_dealer_color_heatmap(
    dealer_color_si: dict[str, pd.DataFrame],
    output_dir: Path,
    top_n: int = 4,
) -> None:
    """Renk bazında Bayi × Ay mevsimsel indeks ısı haritası.

    Başlıkta açıkça belirtilir: Marka X 2024-2025 kendi satış verisi bazlıdır.
    En yaygın top_n renk için ayrı heatmap üretilir.

    Args:
        dealer_color_si: compute_dealer_color_si() çıktısı.
        output_dir:      Çıktı klasörü.
        top_n:           Kaç renk için heatmap üretileceği.
    """
    if not dealer_color_si:
        return

    color_counts: dict[str, int] = {}
    for df in dealer_color_si.values():
        for color in df.columns:
            color_counts[color] = color_counts.get(color, 0) + 1
    top_colors = sorted(color_counts, key=lambda x: -color_counts[x])[:top_n]

    for color in top_colors:
        dealer_rows: dict[str, list[float]] = {}
        for dealer, df in sorted(dealer_color_si.items()):
            if color in df.columns:
                dealer_rows[dealer] = df[color].tolist()

        if len(dealer_rows) < 2:
            continue

        pivot = pd.DataFrame(dealer_rows, index=range(1, 13)).T
        pivot.columns = MONTH_ABBR_EN

        n_dealers = pivot.shape[0]
        fig_h = max(4, n_dealers * 0.45)
        fig, ax = plt.subplots(figsize=(14, fig_h))

        sns.heatmap(
            pivot,
            annot=True, fmt=".2f",
            cmap="RdYlGn", center=1.0,
            vmin=0.4, vmax=1.8,
            linewidths=0.4, linecolor="white",
            ax=ax,
            cbar_kws={"label": "Mevsimsel İndeks (1.0 = ortalama)"},
            annot_kws={"size": 8},
        )
        ax.set_title(
            f"Marka X 2024-2025 Kendi Satış Verisi Bazlı\n"
            f"{color} Rengi — Bayi Bazında Aylık Mevsimsel İndeks",
            fontsize=12, fontweight="bold",
        )
        ax.set_xlabel("Ay")
        ax.set_ylabel("Bayi")
        fig.tight_layout()

        safe = color.replace("/", "_").replace(" ", "_")
        _save_fig(fig, output_dir / f"11_bayi_renk_{safe}_heatmap.png")


def plot_monthly_plan(
    plan_df: pd.DataFrame,
    annual_target: int,
    output_dir: Path,
    weights: tuple[float, float, float] = (0.50, 0.30, 0.20),
) -> None:
    """Aylık dağıtım planını 2 panelli grafik olarak gösterir.

    Üst panel: bars (aylık adet) + çizgi (SI), Alt panel: kümülatif ilerleme.

    Args:
        plan_df:       monthly_plan() çıktısı.
        annual_target: Yıllık hedef adedi.
        output_dir:    Çıktı klasörü.
        weights:       (w_odd, w_seg, w_ns) tuple.
    """
    w_odd, w_seg, w_ns = weights
    x = np.arange(12)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9))
    fig.suptitle(
        f"Aylık Dağıtım Planı — Yıllık Hedef: {annual_target:,} araç\n"
        f"(Nihai SI: {w_odd:.2f}×ODD + {w_seg:.2f}×Segment + {w_ns:.2f}×NORTHSTAR"
        "  | YoY Stability)",
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


def plot_northstar_vs_market(
    ns_si: pd.Series,
    final_si: pd.Series,
    output_dir: Path,
    weights: tuple[float, float, float] = (0.50, 0.30, 0.20),
) -> None:
    """NORTHSTAR SI ile nihai piyasa SI'ını karşılaştıran grafik.

    İki SI serisini yan yana çubuk + fark çizgisiyle gösterir. Her ay için
    NORTHSTAR'ın piyasadan ne kadar saptığı görsel olarak vurgulanır.

    Args:
        ns_si:      NORTHSTAR SI serisi (index 1-12).
        final_si:   Nihai piyasa SI serisi (index 1-12).
        output_dir: Çıktı klasörü.
        weights:    (w_odd, w_seg, w_ns) tuple — başlıkta gösterilir.
    """
    w_odd, w_seg, w_ns = weights
    x = np.arange(12)
    width = 0.38

    # Fark: NORTHSTAR - piyasa
    diff = ns_si.values - final_si.values

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(
        "NORTHSTAR SI vs Piyasa SI Karşılaştırması\n"
        f"(Piyasa = {w_odd:.2f}×ODD + {w_seg:.2f}×Segment | YoY Stability Weighting)",
        fontsize=14, fontweight="bold",
    )

    # --- Üst panel: yan yana bar ---
    bars_ns = ax1.bar(x - width / 2, ns_si.values, width,
                      color="#FB8C00", alpha=0.82, label="NORTHSTAR SI", edgecolor="white")
    bars_mkt = ax1.bar(x + width / 2, final_si.values, width,
                       color="#1565C0", alpha=0.82, label="Piyasa SI (FINAL)", edgecolor="white")

    for bar, val in zip(bars_ns, ns_si.values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=7.5,
                 color="#FB8C00", fontweight="bold")
    for bar, val in zip(bars_mkt, final_si.values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=7.5,
                 color="#1565C0", fontweight="bold")

    ax1.axhline(1.0, color="gray", linestyle="--", lw=1.2, label="Ortalama (1.0)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(MONTH_ABBR_EN, fontsize=9)
    ax1.set_ylabel("Mevsimsel İndeks")
    ax1.set_title("NORTHSTAR vs Piyasa — Aylık SI")
    ax1.legend(fontsize=9)
    ax1.set_ylim(0, max(ns_si.max(), final_si.max()) * 1.22)

    # --- Alt panel: fark ---
    diff_colors = ["#43A047" if d >= 0 else "#E53935" for d in diff]
    diff_bars = ax2.bar(x, diff, color=diff_colors, alpha=0.85, edgecolor="white")
    for bar, val in zip(diff_bars, diff):
        va = "bottom" if val >= 0 else "top"
        offset = 0.005 if val >= 0 else -0.005
        ax2.text(bar.get_x() + bar.get_width() / 2, val + offset,
                 f"{val:+.3f}", ha="center", va=va, fontsize=8, fontweight="bold")
    ax2.axhline(0, color="gray", linestyle="--", lw=1.2)
    ax2.set_xticks(x)
    ax2.set_xticklabels(MONTH_ABBR_EN, fontsize=9)
    ax2.set_ylabel("Fark (NORTHSTAR − Piyasa)")
    ax2.set_title(
        "Sapma: yeşil = NORTHSTAR peak > piyasa, kırmızı = NORTHSTAR dip < piyasa"
    )

    # Sapmayı açıklayan not
    ax2.text(
        0.01, 0.97,
        f"Not: NORTHSTAR YoY stability r≈{w_ns:.4f} → piyasa ağırlığı daha yüksek",
        transform=ax2.transAxes, ha="left", va="top",
        fontsize=8, color="gray", style="italic",
    )

    fig.tight_layout()
    _save_fig(fig, output_dir / "05_northstar_vs_piyasa.png")


# ---------------------------------------------------------------------------
# 9. Metin raporu
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
    weights: tuple[float, float, float] = (0.50, 0.30, 0.20),
    stabilities: dict[str, float] | None = None,
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
        weights:      (w_odd, w_seg, w_ns) — compute_optimal_weights() çıktısı.
        stabilities:  {"odd": r, "seg": r, "ns": r} — ham YoY korelasyonları.

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

    w_odd, w_seg, w_ns = weights

    # Başlık
    h1("MEVSİMSELLİK ANALİZİ RAPORU — NORTHSTAR 2024-2025")

    stab_block = ""
    if stabilities:
        r_odd = stabilities.get("odd", float("nan"))
        r_seg = stabilities.get("seg", float("nan"))
        r_ns  = stabilities.get("ns",  float("nan"))
        total = r_odd + r_seg + r_ns
        stab_block = textwrap.dedent(f"""
        Ağırlık Hesabı — YoY Stability (yıllar arası Pearson korelasyonu):
          ODD stability     r = {r_odd:.4f}  →  w_odd = {r_odd/total:.4f}
          Segment stability r = {r_seg:.4f}  →  w_seg = {r_seg/total:.4f}
          NORTHSTAR stab.   r = {r_ns:.4f}  →  w_ns  = {r_ns/total:.4f}
          (stability ∝ YoY r; daha stabil kaynak daha yüksek ağırlık alır)
        """).rstrip()

    lines.append(textwrap.dedent(f"""
        Metodoloji: Klasik oran-ortalaması (ratio-to-mean)
          SI[ay] = 2 yıllık_aylık_ortalama[ay] / grand_mean
          grand_mean = toplam_satış / 24   (2 yıl × 12 ay)
          SI > 1.0 → Peak (ortalama üstü talep)
          SI < 1.0 → Dip  (ortalama altı talep)

        Üç piyasa katmanı ve hesaplanan ağırlıkları:
          ODD (Türkiye ithal piyasası)  w = {w_odd:.4f}
          Segment (9 rakip marka)       w = {w_seg:.4f}
          NORTHSTAR                     w = {w_ns:.4f}
        {stab_block}
        Nihai SI = {w_odd:.4f} × ODD + {w_seg:.4f} × Segment + {w_ns:.4f} × NORTHSTAR
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
    lines.append(
        f"    (final_si = {w_odd:.4f}×ODD + {w_seg:.4f}×Segment + {w_ns:.4f}×NORTHSTAR"
        "  | YoY Stability Weighting)\n"
    )
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
    lines.append(textwrap.dedent(f"""
        Bu modülü başka scriptlerden kullanmak için:

            from src.analysis.seasonality import (
                compute_odd_si, compute_segment_si, compute_northstar_si,
                compute_optimal_weights, compute_final_si, monthly_plan,
            )
            from src.analysis.data_loader import load_sales, load_competitors
            from pathlib import Path

            data_dir = Path("data/raw")
            df_sales = load_sales(data_dir)
            df_comp  = load_competitors(data_dir)
            odd_si   = compute_odd_si(data_dir)
            seg_si   = compute_segment_si(df_comp)
            ns_si    = compute_northstar_si(df_sales)
            # Veri tabanlı ağırlıklar (YoY stability):
            w_odd, w_seg, w_ns = compute_optimal_weights(data_dir, df_comp, df_sales)
            final_si = compute_final_si(odd_si, seg_si, ns_si, w_odd, w_seg, w_ns)
            plan     = monthly_plan(3_600, final_si)
            print(plan)

        Bu çalışmada hesaplanan ağırlıklar:
            ODD={w_odd:.4f}, Segment={w_seg:.4f}, NORTHSTAR={w_ns:.4f}

        Çıktı dosyaları (outputs/seasonality/):
            01_mevsimsel_indeksler.csv      → Tüm katmanlar + plan özeti
            02_rakip_mevsimsel_indeksler.csv → Rakip marka bazında SI
            04_FINAL_si.csv                → Planlama için kullanılacak indeks
            05_bayi_si.csv                 → Bayi bazında SI pivot
            09_agirlik_analizi.csv         → YoY stability skorları ve ağırlıklar
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
# 10. Ana çalıştırma
# ---------------------------------------------------------------------------

def run(annual_target: int = 3_600) -> None:
    """Tüm mevsimsellik analizini çalıştırır ve çıktıları üretir.

    Adımlar:
        1. Veriler yüklenir (ODD CSV, rakip, NORTHSTAR satışları)
        2. ODD / Segment / NORTHSTAR SI hesaplanır; marka bazlı rakip SI'ı da üretilir
        3. Optimal ağırlıklar YoY stability yöntemiyle hesaplanır
        4. Nihai ağırlıklı SI hesaplanır
        5. Granüler SI'lar hesaplanır (bayi, model, renk)
        6. Aylık plan oluşturulur
        7. Eski/geçersiz dosyalar temizlenir
        8. CSV çıktıları kaydedilir
        9. Metin raporu kaydedilir
       10. 8 görsel üretilir

    Çıktı dosyaları (outputs/seasonality/):
        CSVler:
            01_odd_si.csv                  — ODD pazar aylık SI
            01_mevsimsel_indeksler.csv      — Tüm katmanlar + plan özeti
            02_rakip_mevsimsel_indeksler.csv — Rakip marka bazında SI (geniş)
            03_northstar_si.csv            — NORTHSTAR marka SI
            04_FINAL_si.csv                — Nihai ağırlıklı SI + ağırlıklar
            05_bayi_si.csv                 — Bayi bazında SI pivot
            06_model_si.csv                — Model bazında SI pivot
            07_renk_si.csv                 — Renk bazında SI pivot (top 10)
            09_agirlik_analizi.csv         — YoY stability skorları ve ağırlıklar
        Görseller:
            01_piyasa_hiyerarsisi.png      — 4 katman çizgi + nihai bar
            02_final_indeks_bar.png        — Nihai SI renkli bar
            03_final_indeks_polar.png      — Yıl döngüsü polar
            04_bayi_heatmap.png            — Bayi × ay ısı haritası
            05_northstar_vs_piyasa.png     — NORTHSTAR vs piyasa karşılaştırması
            05_model_heatmap.png           — Model × ay ısı haritası
            06_renk_heatmap.png            — Renk × ay ısı haritası
            07_aylik_plan.png              — Aylık dağıtım planı
        Rapor:
            mevsimsellik_raporu.txt

    Args:
        annual_target: Plan tablosu için yıllık araç hedefi.
    """
    OUTPUT_DIR = Path(__file__).parents[2] / "outputs" / "seasonality"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    DATA_DIR = Path(__file__).parents[2] / "data" / "raw"

    print("\n[1/7] Veriler yükleniyor...")
    df_sales = load_sales(DATA_DIR)
    df_comp  = load_competitors(DATA_DIR)
    print(f"  NORTHSTAR: {len(df_sales):,} işlem")
    print(f"  Rakip: {df_comp['brand'].nunique()} marka, {len(df_comp):,} kayıt")

    print("\n[2/7] Mevsimsel indeksler hesaplanıyor...")
    odd_si      = compute_odd_si(DATA_DIR)
    seg_si      = compute_segment_si(df_comp)
    ns_si       = compute_northstar_si(df_sales)
    per_brand   = compute_per_brand_si(df_comp)
    dealer_si   = compute_dealer_si(df_sales)
    model_si    = compute_model_si(df_sales)
    color_si    = compute_color_si(df_sales)
    # Marka X 2024-2025 kendi verisi bazlı çapraz boyutlu SI'lar
    dealer_model_si = compute_dealer_model_si(df_sales)
    dealer_color_si = compute_dealer_color_si(df_sales)
    print(f"  Bayi×Model kombinasyonu: {sum(len(v.columns) for v in dealer_model_si.values())} çift")
    print(f"  Bayi×Renk kombinasyonu:  {sum(len(v.columns) for v in dealer_color_si.values())} çift")

    print("\n[3/7] Optimal ağırlıklar hesaplanıyor (YoY stability)...")
    stabilities = _stability_detail(DATA_DIR, df_comp, df_sales)
    r_odd = stabilities["odd"]
    r_seg = stabilities["seg"]
    r_ns  = stabilities["ns"]
    print(f"  ODD stability (r 2024-2025):        {r_odd:.4f}")
    print(f"  Segment stability (r 2024-2025):    {r_seg:.4f}")
    print(f"  NORTHSTAR stability (r 2024-2025):  {r_ns:.4f}")

    w_odd, w_seg, w_ns = compute_optimal_weights(DATA_DIR, df_comp, df_sales)
    weights = (w_odd, w_seg, w_ns)
    print("\n  → Hesaplanan ağırlıklar:")
    print(f"    ODD={w_odd:.4f}  Segment={w_seg:.4f}  NORTHSTAR={w_ns:.4f}")

    final_si = compute_final_si(odd_si, seg_si, ns_si, w_odd, w_seg, w_ns)
    plan = monthly_plan(annual_target, final_si, label="final")

    # ------------------------------------------------------------------
    # Eski / geçersiz dosyaları temizle
    # ------------------------------------------------------------------
    print("\n[4/7] Eski dosyalar temizleniyor...")
    obsolete = [
        "02_segment_si.csv",
        "08_aylik_plan_3600.csv",
        "03_aylik_plan_3600.csv",
        "04_aylik_hedef_plani.png",
        "01_mevsimsel_indeks_karsilastirma.png",
        "02_mevsimsel_indeks_polar.png",
        "03_rakip_mevsimsel_heatmap.png",
    ]
    for fname in obsolete:
        p = OUTPUT_DIR / fname
        if p.exists():
            p.unlink()
            print(f"  Silindi: {p.name}")

    # ------------------------------------------------------------------
    # CSV çıktıları
    # ------------------------------------------------------------------
    print("\n[5/7] CSV çıktıları kaydediliyor...")

    # 01 — ODD pazar SI
    odd_df = pd.DataFrame({
        "month": range(1, 13), "month_name": MONTH_ABBR_TR,
        "odd_si": odd_si.values,
    })

    # 01 — Tüm katmanlar + plan özeti (combined)
    combined_df = pd.DataFrame({
        "month":         range(1, 13),
        "month_name":    MONTH_ABBR_TR,
        "odd_si":        odd_si.values,
        "segment_si":    seg_si.values,
        "northstar_si":  ns_si.values,
        "final_si":      final_si.values,
        "planned_qty":   plan["planned_qty"].values,
        "share_pct":     plan["share_pct"].values,
        "cumulative_qty": plan["cumulative_qty"].values,
        "cumulative_pct": plan["cumulative_pct"].values,
    })

    # 02 — Rakip marka bazında SI (per-brand pivot, long-friendly with month_name)
    per_brand_out = per_brand.copy()
    per_brand_out.index.name = "month"
    per_brand_out.insert(0, "month_name", MONTH_ABBR_TR)

    # 03 — NORTHSTAR SI
    ns_df = pd.DataFrame({
        "month": range(1, 13), "month_name": MONTH_ABBR_TR,
        "northstar_si": ns_si.values,
    })

    # 04 — FINAL SI + ağırlıklar
    final_df = pd.DataFrame({
        "month":        range(1, 13),
        "month_name":   MONTH_ABBR_TR,
        "odd_si":       odd_si.values,
        "segment_si":   seg_si.values,
        "northstar_si": ns_si.values,
        "final_si":     final_si.values,
        "w_odd":        [w_odd] * 12,
        "w_seg":        [w_seg] * 12,
        "w_ns":         [w_ns]  * 12,
    })

    # 09 — Ağırlık analizi
    weight_df = pd.DataFrame({
        "source":          ["ODD", "Segment", "NORTHSTAR"],
        "yoy_stability_r": [r_odd, r_seg, r_ns],
        "weight":          [w_odd, w_seg, w_ns],
        "weight_pct":      [f"{w_odd*100:.1f}%", f"{w_seg*100:.1f}%", f"{w_ns*100:.1f}%"],
        "n_approx":        [1_417_938, 720_805, len(df_sales)],
        "method":          ["YoY Stability"] * 3,
    })

    dealer_model_long = _dict_si_to_long(dealer_model_si, "model")
    dealer_color_long = _dict_si_to_long(dealer_color_si, "color")

    csv_outputs: list[tuple] = [
        (odd_df,                       "01_odd_si.csv"),
        (combined_df,                  "01_mevsimsel_indeksler.csv"),
        (per_brand_out.reset_index(),  "02_rakip_mevsimsel_indeksler.csv"),
        (ns_df,                        "03_northstar_si.csv"),
        (final_df,                     "04_FINAL_si.csv"),
        (dealer_si.reset_index(),      "05_bayi_si.csv"),
        (model_si.reset_index(),       "06_model_si.csv"),
        (color_si.reset_index(),       "07_renk_si.csv"),
        (dealer_model_long,            "08_bayi_model_si.csv"),
        (dealer_color_long,            "10_bayi_renk_si.csv"),
        (weight_df,                    "09_agirlik_analizi.csv"),
    ]
    for df_out, fname in csv_outputs:
        path = OUTPUT_DIR / fname
        df_out.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  Kaydedildi: {path.name}")

    # ------------------------------------------------------------------
    # Metin raporu
    # ------------------------------------------------------------------
    print("\n[6/7] Metin raporu oluşturuluyor...")
    report = generate_report(
        odd_si, seg_si, ns_si, final_si,
        dealer_si, model_si, color_si,
        plan, annual_target,
        weights=weights,
        stabilities=stabilities,
    )
    rpath = OUTPUT_DIR / "mevsimsellik_raporu.txt"
    rpath.write_text(report, encoding="utf-8")
    print(f"  Kaydedildi: {rpath.name}")

    # ------------------------------------------------------------------
    # Görseller
    # ------------------------------------------------------------------
    print("\n[7/7] Görseller oluşturuluyor...")
    plot_market_hierarchy(odd_si, seg_si, ns_si, final_si, OUTPUT_DIR, weights=weights)
    plot_final_si_bar(final_si, OUTPUT_DIR, weights=weights)
    plot_final_si_polar(final_si, OUTPUT_DIR)
    plot_dealer_heatmap(dealer_si, OUTPUT_DIR)
    plot_northstar_vs_market(ns_si, final_si, OUTPUT_DIR, weights=weights)
    plot_model_heatmap(model_si, OUTPUT_DIR)
    plot_color_heatmap(color_si, OUTPUT_DIR)
    plot_monthly_plan(plan, annual_target, OUTPUT_DIR, weights=weights)
    # Marka X 2024-2025 kendi verisi bazlı çapraz boyutlu görseller
    plot_dealer_model_heatmap(dealer_model_si, OUTPUT_DIR)
    plot_dealer_color_heatmap(dealer_color_si, OUTPUT_DIR)

    print(f"\nTamamlandi → {OUTPUT_DIR}")
    png_count = len(list(OUTPUT_DIR.glob("*.png")))
    csv_count = len(list(OUTPUT_DIR.glob("*.csv")))
    print(f"  {csv_count} CSV  |  {png_count} PNG  |  mevsimsellik_raporu.txt")
    print(f"\n{report}")


if __name__ == "__main__":
    import sys
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 3_600)
