"""NORTHSTAR Marka Aylik Hedef Planlaycisi.

NORTHSTAR markasinin yillik hedefini mevsimsel indekslerle aylik bazda dagitir.
Granüler breakdown secenekleriyle bayi, model ve renk bazinda mevsimsel analiz
de sunar.

Kullanim:
    python -m src.analysis.northstar_monthly_target
    python -m src.analysis.northstar_monthly_target --target 3600
    python -m src.analysis.northstar_monthly_target --target 3600 --breakdown dealer
    python -m src.analysis.northstar_monthly_target --target 3600 --breakdown model
    python -m src.analysis.northstar_monthly_target --target 3600 --breakdown color
    python -m src.analysis.northstar_monthly_target --target 3600 --breakdown all

--breakdown secenekleri:
    none    (varsayilan) — yalnizca marka duzeyinde plan
    dealer  — bayi mevsimsel agirliklar + tahmini kota
    model   — model mevsimsel paternler
    color   — renk mevsimsel paternler
    all     — tum breakdown'lar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Proje kok dizini (src/analysis/ alti)
_REPO_ROOT = Path(__file__).parents[2]
_DATA_DIR = _REPO_ROOT / "data" / "raw"
_OUTPUTS_DIR = _REPO_ROOT / "outputs" / "seasonality"

# Ay isimleri (Turkce)
_MONTH_TR = [
    "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
    "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik",
]

_MONTH_EN = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# Geçerli breakdown seçenekleri
_BREAKDOWN_OPTIONS = ("none", "dealer", "model", "color", "all")


# ---------------------------------------------------------------------------
# Yardimci fonksiyonlar
# ---------------------------------------------------------------------------

def _load_final_si() -> pd.Series:
    """Nihai SI serisini onceden hesaplanmis CSV'den veya canli hesaplayarak yukler.

    Returns:
        1-12 indeksli nihai SI serisi.
    """
    csv_path = _OUTPUTS_DIR / "04_FINAL_si.csv"
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            if "final_si" in df.columns:
                vals = df["final_si"].values[:12]
                print(f"  Nihai SI yuklendi: {csv_path}")
                return pd.Series(vals, index=range(1, 13), dtype=float)
        except Exception as exc:
            print(f"  [UYARI] CSV okunamadi ({exc}), hesaplanacak...")

    # Canli hesaplama
    print("  Nihai SI hesaplaniyor (veri dosyalarindan)...")
    sys.path.insert(0, str(_REPO_ROOT))
    from src.analysis.seasonality import (
        compute_odd_si,
        compute_segment_si,
        compute_northstar_si,
        compute_final_si,
    )
    from src.analysis.data_loader import load_sales, load_competitors

    odd_si  = compute_odd_si(_DATA_DIR)
    seg_si  = compute_segment_si(load_competitors(_DATA_DIR))
    ns_si   = compute_northstar_si(load_sales(_DATA_DIR))
    return compute_final_si(odd_si, seg_si, ns_si)


def _load_granular_si(breakdown: str) -> pd.DataFrame:
    """Granüler SI pivot tablosunu onceden hesaplanmis CSV'den veya canli hesaplayarak yukler.

    Args:
        breakdown: "dealer", "model" veya "color".

    Returns:
        Pivot DataFrame: satir=ay (1-12), sutun=kategori.
    """
    file_map = {
        "dealer": "05_bayi_si.csv",
        "model":  "06_model_si.csv",
        "color":  "07_renk_si.csv",
    }
    fname = file_map.get(breakdown)
    if not fname:
        return pd.DataFrame()

    csv_path = _OUTPUTS_DIR / fname
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig", index_col="month")
            print(f"  {breakdown.capitalize()} SI yuklendi: {csv_path}")
            return df
        except Exception as exc:
            print(f"  [UYARI] {fname} okunamadi ({exc}), hesaplanacak...")

    # Canli hesaplama
    print(f"  {breakdown.capitalize()} SI hesaplaniyor...")
    sys.path.insert(0, str(_REPO_ROOT))
    from src.analysis.data_loader import load_sales
    from src.analysis.seasonality import (
        compute_dealer_si,
        compute_model_si,
        compute_color_si,
    )

    df_sales = load_sales(_DATA_DIR)
    compute_map = {
        "dealer": compute_dealer_si,
        "model":  compute_model_si,
        "color":  compute_color_si,
    }
    return compute_map[breakdown](df_sales)


def _load_sales_shares(breakdown: str) -> pd.Series:
    """Her kategori (bayi/model/renk) icin tarihi satis payi hesaplar.

    Paya gore tahmini yillik kota belirlenmesinde kullanilir.

    Args:
        breakdown: "dealer", "model" veya "color".

    Returns:
        Kategori → satis payi (0-1) serisi.
    """
    sys.path.insert(0, str(_REPO_ROOT))
    from src.analysis.data_loader import load_sales

    df = load_sales(_DATA_DIR)

    col_map = {
        "dealer": "Dealer Name",
        "model":  "Model Description",
        "color":  "Exterior Color",
    }
    col = col_map.get(breakdown)
    if not col or col not in df.columns:
        return pd.Series(dtype=float)

    counts = df[col].value_counts()
    return (counts / counts.sum()).round(4)


# ---------------------------------------------------------------------------
# Tablo yazici fonksiyonlar
# ---------------------------------------------------------------------------

def _print_header(title: str, subtitle: str = "") -> None:
    """Ustun cizgili baslik kutusu yazdirir.

    Args:
        title:    Ana baslik metni.
        subtitle: Alt baslik (bos olabilir).
    """
    width = max(len(title), len(subtitle)) + 6
    print("\n" + "=" * width)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print("=" * width)


def _print_brand_plan(plan: pd.DataFrame, annual_target: int) -> None:
    """Marka duzeyinde aylik plan tablosunu yazdirir.

    Args:
        plan:          monthly_plan() citkisi.
        annual_target: Yillik araç adedi.
    """
    _print_header(
        f"NORTHSTAR AYLIK HEDEF PLANI — {annual_target:,} arac",
        "Nihai SI = 0.50xODD + 0.30xSegment + 0.20xNORTHSTAR",
    )
    print(f"\n  {'Ay':<10} {'SI':>7} {'Plan':>8} {'Pay%':>7} {'Kumulatif':>12} {'Kumul%':>8}  Bar")
    print("  " + "-" * 68)

    max_qty = plan["planned_qty"].max()
    for _, row in plan.iterrows():
        bar_len = int(row["share_pct"] / 1.5)
        bar = "█" * bar_len
        print(
            f"  {row['month_name']:<10} {row['si']:>7.4f} "
            f"{int(row['planned_qty']):>8,} {row['share_pct']:>6.2f}% "
            f"{int(row['cumulative_qty']):>12,} {row['cumulative_pct']:>7.2f}%  {bar}"
        )

    print("  " + "-" * 68)
    print(f"  {'TOPLAM':<10} {'—':>7} {int(plan['planned_qty'].sum()):>8,} {'100.00%':>7}")


def _print_granular_breakdown(
    breakdown: str,
    granular_si: pd.DataFrame,
    brand_si: pd.Series,
    annual_target: int,
    shares: pd.Series,
) -> None:
    """Granüler breakdown tablosunu (bayi/model/renk) yazdirir.

    Her kategorinin:
    - Kendi SI profili (marka SI ile karsilastirma)
    - Peak / dip aylari
    - Tarihi paya gore tahmini yillik + aylik kota

    Args:
        breakdown:   "dealer", "model" veya "color".
        granular_si: Pivot DataFrame (satir=ay 1-12, sutun=kategori).
        brand_si:    Marka duzeyinde SI serisi (karsilastirma referansi).
        annual_target: Yillik araç adedi.
        shares:      Kategori → tarihi satis payi serisi.
    """
    label_map = {"dealer": "BAYİ", "model": "MODEL", "color": "RENK"}
    label = label_map.get(breakdown, breakdown.upper())

    _print_header(
        f"NORTHSTAR — {label} BAZINDA MEVSİYSEL PROFIL",
        f"Marka SI ile karsilastirmali | Yillik hedef: {annual_target:,} arac",
    )

    if granular_si.empty:
        print("  (Yeterli veri yok)")
        return

    for category in granular_si.columns:
        cat_si = granular_si[category]

        # Tarihi pay ve tahmini kota
        share = shares.get(category, 0.0) if not shares.empty else 0.0
        est_annual = round(annual_target * share)

        # Peak ve dip aylar (kategorinin kendi SI'si bazinda)
        peak_months = cat_si.nlargest(3).index.tolist()
        dip_months  = cat_si.nsmallest(3).index.tolist()
        peak_names  = " / ".join(_MONTH_TR[m - 1] for m in sorted(peak_months))
        dip_names   = " / ".join(_MONTH_TR[m - 1] for m in sorted(dip_months))

        print(f"\n  [{label}] {category}")
        print(f"  Tarihi Pay: {share*100:.1f}%  |  Tahmini Yillik Kota: {est_annual:,} arac")
        print(f"  Peak Aylar: {peak_names}")
        print(f"  Dip  Aylar: {dip_names}")

        # SI karsilastirma tablosu
        print(f"\n    {'Ay':<10} {'Kat SI':>8} {'Marka SI':>10} {'Fark':>8}  Yorum")
        print("    " + "-" * 52)

        for m in range(1, 13):
            c_val = cat_si.get(m, 0.0)
            b_val = brand_si.get(m, 1.0)
            diff = c_val - b_val
            if diff > 0.10:
                yorum = "Markadan guclu"
            elif diff < -0.10:
                yorum = "Markadan zayif"
            else:
                yorum = "Markayla paralel"

            # Tahmini aylik kota (kategorinin kendi SI'sini kullan)
            if est_annual > 0:
                est_monthly = round(est_annual * c_val / 12)
                qty_str = f"~{est_monthly:,}"
            else:
                qty_str = "—"

            print(
                f"    {_MONTH_TR[m-1]:<10} {c_val:>8.4f} {b_val:>10.4f} "
                f"{diff:>+8.4f}  {yorum}  ({qty_str})"
            )


# ---------------------------------------------------------------------------
# Sonuc kaydetme
# ---------------------------------------------------------------------------

def _save_results(
    plan: pd.DataFrame,
    annual_target: int,
    breakdown: str,
    granular_si: pd.DataFrame | None = None,
    shares: pd.Series | None = None,
    brand_si: pd.Series | None = None,
) -> None:
    """Plan ve breakdown sonuclarini CSV olarak kaydeder.

    Args:
        plan:          Aylik plan DataFrame'i.
        annual_target: Yillik hedef.
        breakdown:     Breakdown secenegi.
        granular_si:   Granüler SI pivot (varsa).
        shares:        Tarihi satis paylari (varsa).
        brand_si:      Marka SI serisi (varsa).
    """
    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # Ana plan CSV
    plan_path = _OUTPUTS_DIR / f"northstar_plan_{annual_target}_{breakdown}.csv"
    plan.to_csv(plan_path, index=False, encoding="utf-8-sig")
    print(f"\n  Plan kaydedildi: {plan_path}")

    # Granüler breakdown CSV (varsa)
    if granular_si is not None and not granular_si.empty and breakdown != "none":
        # Her kategori icin tahmini aylik plan hesapla
        rows: list[dict] = []
        for category in granular_si.columns:
            cat_si = granular_si[category]
            share = (shares.get(category, 0.0) if shares is not None else 0.0)
            est_annual = round(annual_target * share)

            for m in range(1, 13):
                c_val = float(cat_si.get(m, 0.0))
                b_val = float(brand_si.get(m, 1.0)) if brand_si is not None else 1.0
                est_monthly = round(est_annual * c_val / 12) if est_annual > 0 else 0
                rows.append({
                    "breakdown_type":     breakdown,
                    "category":           category,
                    "month":              m,
                    "month_name":         _MONTH_TR[m - 1],
                    "category_si":        round(c_val, 4),
                    "brand_si":           round(b_val, 4),
                    "si_diff":            round(c_val - b_val, 4),
                    "historical_share":   share,
                    "estimated_annual":   est_annual,
                    "estimated_monthly":  est_monthly,
                })

        detail_df = pd.DataFrame(rows)
        detail_path = _OUTPUTS_DIR / f"northstar_plan_{annual_target}_{breakdown}_detail.csv"
        detail_df.to_csv(detail_path, index=False, encoding="utf-8-sig")
        print(f"  Detay kaydedildi: {detail_path}")


# ---------------------------------------------------------------------------
# Ana calisma akisi
# ---------------------------------------------------------------------------

def run(annual_target: int = 3_600, breakdown: str = "none") -> None:
    """NORTHSTAR aylik hedef planlamasini calistirir.

    Args:
        annual_target: Yillik araç hedefi.
        breakdown:     Granüler analiz secenegi: "none", "dealer", "model",
                       "color" veya "all".
    """
    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nNORTHSTAR Aylik Hedef Planlayicisi")
    print(f"Yillik Hedef: {annual_target:,} araç | Breakdown: {breakdown}")
    print("-" * 50)

    # 1) Nihai SI yukle
    print("\n[1] Nihai SI yukleniyor...")
    final_si = _load_final_si()

    # 2) Aylik plan olustur
    print("\n[2] Aylik plan hesaplaniyor...")
    sys.path.insert(0, str(_REPO_ROOT))
    from src.analysis.seasonality import monthly_plan
    plan = monthly_plan(annual_target, final_si, label="final")

    # 3) Marka duzeyinde tabloyu yazdir
    _print_brand_plan(plan, annual_target)

    # 4) Granüler breakdown
    breakdown_list: list[str] = []
    if breakdown == "all":
        breakdown_list = ["dealer", "model", "color"]
    elif breakdown != "none":
        breakdown_list = [breakdown]

    granular_si_map: dict[str, pd.DataFrame] = {}
    shares_map: dict[str, pd.Series] = {}

    for bd in breakdown_list:
        print(f"\n[3/{bd}] {bd.capitalize()} bazinda mevsimsel analiz yukleniyor...")
        g_si = _load_granular_si(bd)
        shares = _load_sales_shares(bd)
        granular_si_map[bd] = g_si
        shares_map[bd] = shares

        _print_granular_breakdown(
            breakdown=bd,
            granular_si=g_si,
            brand_si=final_si,
            annual_target=annual_target,
            shares=shares,
        )

    # 5) Sonuclari kaydet
    print(f"\n[4] Sonuclar kaydediliyor...")
    for bd in (breakdown_list if breakdown_list else ["none"]):
        g_si = granular_si_map.get(bd)
        shares = shares_map.get(bd)
        _save_results(
            plan=plan,
            annual_target=annual_target,
            breakdown=bd if bd != "none" else breakdown,
            granular_si=g_si,
            shares=shares,
            brand_si=final_si,
        )

    # Eger hic breakdown yoksa yalnizca ana plani kaydet
    if not breakdown_list:
        _save_results(
            plan=plan,
            annual_target=annual_target,
            breakdown="none",
        )

    print(f"\nTamamlandi. Ciktilar: {_OUTPUTS_DIR}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """Komut satiri argumanlarini parse eder.

    Returns:
        Parsed argparse Namespace nesnesi.
    """
    parser = argparse.ArgumentParser(
        description="NORTHSTAR Aylik Hedef Planlayicisi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--target",
        type=int,
        default=3_600,
        metavar="N",
        help="Yillik araç hedefi (varsayilan: 3600)",
    )
    parser.add_argument(
        "--breakdown",
        choices=_BREAKDOWN_OPTIONS,
        default="none",
        help="Granüler analiz secenegi (varsayilan: none)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(annual_target=args.target, breakdown=args.breakdown)
