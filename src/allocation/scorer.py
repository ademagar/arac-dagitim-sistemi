"""Çok kriterli bayi ve araç-bayi uyum skorlama modülü.

Dört kriter:
    P  (Performans,         w=0.25) — Geçmiş aylık hedef gerçekleşme oranı
    LP (Lokasyon-Ürün Uyum, w=0.35) — Bayi geçmiş satış profili × envanter uyumu
    S  (Mevsimsel Uyum,     w=0.20) — Bayinin o aya özgü mevsimsel indeksi
    H  (Hedef Yakınlık,     w=0.20) — Aylık hedef büyüklüğü (Ocak 2026 = taze başlangıç)

Bileşik skor:
    score[d] = 0.25·P + 0.35·LP + 0.20·S + 0.20·H

LP, araç tipi bazında hesaplanır → affinity[d, vehicle_type] matrisini üretir.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Ağırlıklar
W_P  = 0.25
W_LP = 0.35
W_S  = 0.20
W_H  = 0.20

SEASONALITY_DIR = Path(__file__).parents[2] / "outputs" / "seasonality"


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _minmax(s: pd.Series) -> pd.Series:
    """Min-max normalizasyon; tüm değerler eşitse 0.5 döner."""
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


# ---------------------------------------------------------------------------
# P — Performans skoru
# ---------------------------------------------------------------------------

def compute_p_scores(df_perf: pd.DataFrame, dealer_names: list[str]) -> pd.Series:
    """Geçmiş aylık hedef gerçekleşme oranından performans skoru.

    Veri: load_monthly_performance() çıktısı.
    Yöntem: Her ay actual_qty / target_qty oranı; eksponansiyel ağırlıklı ortalama
    (son aylar daha önemli); ardından min-max normalizasyon → [0, 1].

    Verisi olmayan bayiler ortalama skor alır.

    Args:
        df_perf:      load_monthly_performance() çıktısı.
        dealer_names: Skoru hesaplanacak bayi listesi.

    Returns:
        pd.Series, index=dealer_name, values=[0,1].
    """
    if df_perf.empty:
        return pd.Series(0.5, index=dealer_names)

    # Ay sırası (EWMA için)
    month_order = {
        "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
        "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
        "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
    }

    # Toplam kanal bazlı bayi aylık actual_qty
    grp = (
        df_perf.groupby(["dealer_name", "month"])["actual_qty"]
        .sum()
        .reset_index()
    )
    grp["month_num"] = grp["month"].map(month_order).fillna(0)
    grp = grp.sort_values("month_num")

    # Her ay için hedef yoksa actual'den oranlamak mümkün değil;
    # toplam satış hacmini performans proxy'si olarak kullan
    dealer_scores: dict[str, float] = {}
    for dealer, sub in grp.groupby("dealer_name"):
        if len(sub) == 0:
            continue
        # EWMA: yakın aya daha fazla ağırlık (alpha=0.4)
        vals = sub.sort_values("month_num")["actual_qty"].values.astype(float)
        alpha = 0.4
        weights = np.array([alpha * (1 - alpha) ** i for i in range(len(vals) - 1, -1, -1)])
        weights /= weights.sum()
        dealer_scores[str(dealer)] = float(np.dot(vals, weights))

    score_series = pd.Series(dealer_scores)

    # Hedefsiz bayileri ortalama ile doldur
    result = pd.Series(index=dealer_names, dtype=float)
    for d in dealer_names:
        result[d] = score_series.get(d, np.nan)

    avg = result.dropna().mean() if result.dropna().shape[0] > 0 else 0.0
    result = result.fillna(avg)
    return _minmax(result)


# ---------------------------------------------------------------------------
# LP — Lokasyon-Ürün Uyum (affinity matrix)
# ---------------------------------------------------------------------------

def compute_lp_affinity(
    df_sales: pd.DataFrame,
    dealer_names: list[str],
    vehicle_types: list[str],
) -> pd.DataFrame:
    """Bayi × araç tipi uyum matrisi (cosine similarity tabanlı).

    Yöntem:
        1. Her bayi için geçmiş satışlardan model/versiyon profil vektörü çıkar.
        2. Her araç tipinin model/versiyon boyutundaki birim vektörüyle cosine sim hesapla.
        3. Renk tercihini ayrı çarp (bayinin tarihsel renk dağılımı).

    Args:
        df_sales:     load_sales() çıktısı.
        dealer_names: Satır listesi.
        vehicle_types: "Model / Version / Color" formatında sütun listesi.

    Returns:
        DataFrame: satır=dealer_name, sütun=vehicle_type, değer=[0,1].
    """
    # --- Bayi × model/versiyon geçmiş payı ---
    mv_counts = (
        df_sales.groupby(["Dealer Name", "Model Description", "Vehicle Version"])
        .size()
        .reset_index(name="cnt")
    )
    dealer_totals = mv_counts.groupby("Dealer Name")["cnt"].transform("sum")
    mv_counts["share"] = mv_counts["cnt"] / dealer_totals.where(dealer_totals > 0, 1)

    mv_pivot = mv_counts.pivot_table(
        index="Dealer Name",
        columns=["Model Description", "Vehicle Version"],
        values="share",
        fill_value=0.0,
    )

    # --- Bayi × renk geçmiş payı ---
    color_counts = (
        df_sales.groupby(["Dealer Name", "Exterior Color"])
        .size()
        .reset_index(name="cnt")
    )
    dealer_color_totals = color_counts.groupby("Dealer Name")["cnt"].transform("sum")
    color_counts["share"] = color_counts["cnt"] / dealer_color_totals.where(dealer_color_totals > 0, 1)

    color_pivot = color_counts.pivot_table(
        index="Dealer Name",
        columns="Exterior Color",
        values="share",
        fill_value=0.0,
    )

    # --- Araç tipi bazında affinity ---
    affinity: dict[str, dict[str, float]] = {d: {} for d in dealer_names}

    for vt in vehicle_types:
        parts = vt.split(" / ")
        if len(parts) != 3:
            for d in dealer_names:
                affinity[d][vt] = 0.0
            continue
        model, version, color = parts

        for dealer in dealer_names:
            # Model/versiyon payı
            mv_share = 0.0
            if dealer in mv_pivot.index:
                row = mv_pivot.loc[dealer]
                if (model, version) in mv_pivot.columns:
                    mv_share = float(row[(model, version)])
                elif model in [c[0] for c in mv_pivot.columns]:
                    # Versiyon yok ama model var → model toplamı
                    model_cols = [(c[0], c[1]) for c in mv_pivot.columns if c[0] == model]
                    mv_share = float(sum(row[c] for c in model_cols if c in mv_pivot.columns))

            # Renk payı
            c_share = 0.0
            if dealer in color_pivot.index:
                row_c = color_pivot.loc[dealer]
                if color in color_pivot.columns:
                    c_share = float(row_c[color])

            # Kombinasyon skoru: geometrik ortalama (her ikisi de önemli)
            affinity[dealer][vt] = float(np.sqrt(mv_share * c_share))

    df_affinity = pd.DataFrame(affinity).T  # satır=dealer, sütun=vehicle_type
    df_affinity = df_affinity.reindex(index=dealer_names, columns=vehicle_types, fill_value=0.0)

    # Satır bazında normalizasyon: her bayi için toplamı 1'e normalize
    row_sums = df_affinity.sum(axis=1).replace(0, 1)
    df_affinity = df_affinity.div(row_sums, axis=0)

    return df_affinity


# ---------------------------------------------------------------------------
# S — Mevsimsel Uyum skoru
# ---------------------------------------------------------------------------

def compute_s_scores(dealer_names: list[str], month: int = 1) -> pd.Series:
    """Bayinin o aya özgü mevsimsel indeksinden skor üretir.

    outputs/seasonality/05_bayi_si.csv dosyasını okur.
    Dosya yoksa tüm bayilere 0.5 verir.

    Args:
        dealer_names: Bayi listesi.
        month:        Ay numarası (1=Ocak, ..., 12=Aralık).

    Returns:
        pd.Series, index=dealer_name, values=[0,1].
    """
    si_path = SEASONALITY_DIR / "05_bayi_si.csv"
    if not si_path.exists():
        return pd.Series(0.5, index=dealer_names)

    try:
        df = pd.read_csv(si_path, encoding="utf-8-sig")
        # Satır = ay (1-12), sütun = bayi adı
        if "month" in df.columns:
            df = df.set_index("month")
        row = df.loc[month] if month in df.index else None
        if row is None:
            return pd.Series(0.5, index=dealer_names)

        result = pd.Series(index=dealer_names, dtype=float)
        for d in dealer_names:
            result[d] = float(row[d]) if d in row.index else np.nan
        avg = result.dropna().mean() if result.dropna().shape[0] > 0 else 0.5
        result = result.fillna(avg)
        return _minmax(result)
    except Exception:
        return pd.Series(0.5, index=dealer_names)


# ---------------------------------------------------------------------------
# H — Hedef Yakınlık skoru
# ---------------------------------------------------------------------------

def compute_h_scores(
    targets: pd.DataFrame,
    ytd_actual: pd.Series | None = None,
) -> pd.Series:
    """Aylık hedef büyüklüğüne göre skor.

    Taze ay başlangıcında (YTD verisi yok): büyük hedefli bayi → yüksek öncelik.
    YTD verisi varsa: hedefe kalan pay büyük olan → yüksek öncelik.

    Args:
        targets:    load_targets() çıktısı.
        ytd_actual: index=dealer_name, values=yılın başından bugüne satış.

    Returns:
        pd.Series, index=dealer_name, values=[0,1].
    """
    t = targets.set_index("dealer_name")["target"].astype(float)
    dealer_names = t.index.tolist()

    if ytd_actual is not None:
        remaining = t - ytd_actual.reindex(dealer_names, fill_value=0)
        remaining = remaining.clip(lower=0)
        score = remaining
    else:
        # Ocak 2026: taze başlangıç, hedef büyüklüğü = öncelik
        score = t

    return _minmax(score)


# ---------------------------------------------------------------------------
# Bileşik skor
# ---------------------------------------------------------------------------

def compute_composite_scores(
    p_scores: pd.Series,
    s_scores: pd.Series,
    h_scores: pd.Series,
    dealer_names: list[str],
) -> pd.Series:
    """P, S, H'ı birleştirerek bayi bazında bileşik skor üretir.

    LP affinity ayrı tutulur (araç tipi bazında); burada üç kriter birleşir.

    Args:
        p_scores, s_scores, h_scores: index=dealer_name, values=[0,1]
        dealer_names: Sıralama için kullanılır.

    Returns:
        pd.Series, index=dealer_name, values=[0,1].
    """
    df = pd.DataFrame({
        "P": p_scores,
        "S": s_scores,
        "H": h_scores,
    }, index=dealer_names)
    df = df.fillna(0.5)

    # LP hariç toplamı 1'e normalize: w_P+w_S+w_H = 0.65
    # LP terimi optimizasyon içinde affinity ile ağırlıklanır
    non_lp = W_P + W_S + W_H
    composite = (W_P * df["P"] + W_S * df["S"] + W_H * df["H"]) / non_lp

    return composite.clip(0, 1)
