"""Generic Monthly Target Planner with Seasonality.

Herhangi bir marka için yıllık hedefi aylık mevsimsel ağırlıklarla dağıtır.
Marka ismi hardcode edilmemiştir; ortam değişkeni veya config'den okunur.

Kullanim:
    python find_your_brand_monthly_target_w_seasonality.py
    python find_your_brand_monthly_target_w_seasonality.py --target 4000
    python find_your_brand_monthly_target_w_seasonality.py --target 4000 --si-source northstar
    python find_your_brand_monthly_target_w_seasonality.py --target 4000 --si-source odd
    python find_your_brand_monthly_target_w_seasonality.py --target 4000 --si-source segment
    python find_your_brand_monthly_target_w_seasonality.py --target 4000 --si-source final
    python find_your_brand_monthly_target_w_seasonality.py --target 4000 --si-file path/to/custom_si.csv

SI kaynakları:
    final     (varsayilan) — 50% ODD + 30% Segment + 20% NORTHSTAR (onerilen)
    odd       — Turkiye ithal piyasasi
    segment   — Rekabet segmenti (9 rakip)
    northstar — Yalnizca NORTHSTAR marka verisi

--target verilmezse kullanicidan interaktif olarak istenir.
CSV dosyalari bulunamazsa otomatik olarak hesaplanir.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Proje kok dizini: bu dosya repo rootunda
_REPO_ROOT = Path(__file__).parent
_OUTPUTS_DIR = _REPO_ROOT / "outputs" / "seasonality"
_DATA_DIR = _REPO_ROOT / "data" / "raw"

# Ay isimleri (Turkce)
_MONTH_TR = [
    "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
    "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik",
]

# SI kaynak dosya haritasi
_SI_FILE_MAP: dict[str, str] = {
    "final":     "04_FINAL_si.csv",
    "odd":       "01_odd_si.csv",
    "segment":   "02_segment_si.csv",
    "northstar": "03_northstar_si.csv",
}

# SI kaynak → DataFrame sutun adi haritasi
_SI_COL_MAP: dict[str, str] = {
    "final":     "final_si",
    "odd":       "odd_si",
    "segment":   "segment_si",
    "northstar": "northstar_si",
}


# ---------------------------------------------------------------------------
# Yardimci fonksiyonlar
# ---------------------------------------------------------------------------

def _get_brand_name() -> str:
    """Marka adini config'den veya ortam degiskeninden okur.

    Hata durumunda genel bir etiket doner.

    Returns:
        Marka etiketi (str).
    """
    try:
        # Oncelikle src.config'den oku
        sys.path.insert(0, str(_REPO_ROOT))
        # Config dosyasi yoksa veya import edilemezse generic etiket kullan
        import importlib
        cfg = importlib.import_module("src.config") if (_REPO_ROOT / "src" / "config.py").exists() else None
        if cfg and hasattr(cfg, "BRAND_NAME"):
            return str(cfg.BRAND_NAME)
    except Exception:
        pass

    import os
    return os.environ.get("BRAND_NAME", "NORTHSTAR")


def _load_si_from_csv(source: str) -> pd.Series | None:
    """Onceden hesaplanmis SI'yi CSV dosyasindan yukler.

    Args:
        source: "final", "odd", "segment" veya "northstar".

    Returns:
        1-12 indeksli SI serisi veya dosya bulunamazsa None.
    """
    fname = _SI_FILE_MAP.get(source)
    if not fname:
        return None
    path = _OUTPUTS_DIR / fname
    if not path.exists():
        return None

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        col = _SI_COL_MAP[source]
        if col not in df.columns:
            # Alternatif sutun: tek degerli CSV'de ilk sayisal sutun
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            # "month" ve "year" disinda kalan ilk sutun
            numeric_cols = [c for c in numeric_cols if c not in ("month",)]
            if not numeric_cols:
                return None
            col = numeric_cols[0]
        si_vals = df[col].values[:12]
        series = pd.Series(si_vals, index=range(1, len(si_vals) + 1), dtype=float)
        return series
    except Exception as exc:
        print(f"  [UYARI] SI CSV okunamadi ({path}): {exc}")
        return None


def _load_si_from_file(filepath: str) -> pd.Series | None:
    """Kullanicinin belirttigi ozel SI CSV dosyasindan yukler.

    Dosya bicimi: en az bir "month" (1-12) sutunu ve bir SI deger sutunu
    icermeli. Ilk sayisal sutun (month disinda) SI olarak alinir.

    Args:
        filepath: Ozel SI CSV dosyasinin yolu.

    Returns:
        1-12 indeksli SI serisi veya hata durumunda None.
    """
    path = Path(filepath)
    if not path.exists():
        print(f"  [HATA] Dosya bulunamadi: {path}")
        return None
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        numeric_cols = [c for c in df.select_dtypes(include="number").columns if c != "month"]
        if not numeric_cols:
            print(f"  [HATA] SI sutunu bulunamadi: {path}")
            return None
        col = numeric_cols[0]
        si_vals = df[col].values[:12]
        series = pd.Series(si_vals, index=range(1, len(si_vals) + 1), dtype=float)
        print(f"  Ozel SI dosyasindan yuklendi: {path} (sutun: {col})")
        return series
    except Exception as exc:
        print(f"  [HATA] SI dosyasi okunamadi: {exc}")
        return None


def _compute_si(source: str) -> pd.Series:
    """SI'yi hesaplayarak dondurur (CSV bulunamazsa hesaplama yapar).

    Args:
        source: SI kaynagi ("final", "odd", "segment", "northstar").

    Returns:
        1-12 indeksli SI serisi.
    """
    print(f"  SI hesaplaniyor (kaynak: {source})...")

    # Importlari burada yap (calisma dizininden bagimsiz)
    sys.path.insert(0, str(_REPO_ROOT))
    from src.analysis.seasonality import (
        compute_odd_si,
        compute_segment_si,
        compute_northstar_si,
        compute_final_si,
    )
    from src.analysis.data_loader import load_sales, load_competitors

    if source == "odd":
        return compute_odd_si(_DATA_DIR)

    df_comp = load_competitors(_DATA_DIR)
    if source == "segment":
        return compute_segment_si(df_comp)

    df_sales = load_sales(_DATA_DIR)
    if source == "northstar":
        return compute_northstar_si(df_sales)

    # final (varsayilan)
    odd_si  = compute_odd_si(_DATA_DIR)
    seg_si  = compute_segment_si(df_comp)
    ns_si   = compute_northstar_si(df_sales)
    return compute_final_si(odd_si, seg_si, ns_si)


def _get_si(source: str, si_file: str | None) -> pd.Series:
    """SI serisini uygun kaynaktan dondurur.

    Oncelik sirasi:
        1. Kullanicinin belirttigi ozel dosya (--si-file)
        2. Onceden hesaplanmis CSV (outputs/seasonality/)
        3. Canli hesaplama (veri dosyalarindan)

    Args:
        source:  SI kaynagi ("final", "odd", "segment", "northstar").
        si_file: Ozel SI dosya yolu (None ise kullanilmaz).

    Returns:
        1-12 indeksli SI serisi.
    """
    if si_file:
        result = _load_si_from_file(si_file)
        if result is not None:
            return result

    result = _load_si_from_csv(source)
    if result is not None:
        print(f"  Onceden hesaplanmis SI yuklendi: outputs/seasonality/{_SI_FILE_MAP[source]}")
        return result

    # Hesapla
    return _compute_si(source)


def _build_plan(annual_target: int, si: pd.Series) -> pd.DataFrame:
    """Yillik hedefe gore aylik plan DataFrame'i olusturur.

    Args:
        annual_target: Yillik araç adedi.
        si:            1-12 indeksli mevsimsel indeks serisi.

    Returns:
        Aylik plan DataFrame'i.
    """
    sys.path.insert(0, str(_REPO_ROOT))
    from src.analysis.seasonality import monthly_plan
    return monthly_plan(annual_target, si)


def _bar(value: float, max_val: float, width: int = 10) -> str:
    """Ilerleme cubugu karakteri olusturur.

    Args:
        value:   Gosterilecek deger.
        max_val: Maksimum deger (tam cubuk).
        width:   Toplam cubuk genisligi (karakter).

    Returns:
        Unicode blok karakterlerinden olusan cubuk str.
    """
    if max_val <= 0:
        return ""
    ratio = min(value / max_val, 1.0)
    filled = int(ratio * width)
    partial = ratio * width - filled
    # Yarim blok karakterleri
    blocks = ["", "░", "▒", "▓", "█"]
    partial_char = blocks[int(partial * 4)]
    return "█" * filled + partial_char


def _print_plan_table(
    plan: pd.DataFrame,
    annual_target: int,
    brand: str,
    source: str,
) -> None:
    """Aylik hedef planini gozel formatli tablo olarak yazdirir.

    Args:
        plan:          monthly_plan() citkisi.
        annual_target: Yillik araç adedi.
        brand:         Marka adi.
        source:        SI kaynagi etiketi.
    """
    # Baslik genisligi
    title = f"AYLIK HEDEF PLANI — {brand} — Yillik Hedef: {annual_target:,} arac"
    source_label = f"SI Kaynagi: {source.upper()}"
    box_w = max(len(title), len(source_label)) + 6

    def hline(left: str = "╠", mid: str = "═", right: str = "╣") -> str:
        return left + mid * (box_w - 2) + right

    print("\n" + "╔" + "═" * (box_w - 2) + "╗")
    print("║" + title.center(box_w - 2) + "║")
    print("║" + source_label.center(box_w - 2) + "║")
    print(hline())

    # Sutun basliği
    col_header = (
        f"  {'Ay':<10} {'SI':>6}  {'Plan':>7}  {'Pay%':>6}  "
        f"{'Kumutatif':>11}  {'Kumul%':>7}  {'Bar':<10}  "
    )
    print("║" + col_header + " " * max(0, box_w - 2 - len(col_header)) + "║")
    print(hline())

    max_qty = plan["planned_qty"].max()

    for _, row in plan.iterrows():
        bar_str = _bar(row["planned_qty"], max_qty, width=12)
        line = (
            f"  {row['month_name']:<10} {row['si']:>6.3f}  "
            f"{int(row['planned_qty']):>7,}  {row['share_pct']:>5.1f}%  "
            f"{int(row['cumulative_qty']):>11,}  {row['cumulative_pct']:>6.1f}%  "
            f"{bar_str:<12}  "
        )
        # Satiri kutu genisligine gore pad'le
        padded = line + " " * max(0, box_w - 2 - len(line))
        print("║" + padded + "║")

    print(hline())
    # Toplam satiri
    total_line = (
        f"  {'TOPLAM':<10} {'—':>6}  "
        f"{int(plan['planned_qty'].sum()):>7,}  {'100.0%':>6}  "
        f"{'':>11}  {'':>7}  "
    )
    padded = total_line + " " * max(0, box_w - 2 - len(total_line))
    print("║" + padded + "║")
    print("╚" + "═" * (box_w - 2) + "╝")


def _save_plan_csv(plan: pd.DataFrame, annual_target: int, source: str) -> None:
    """Plani CSV olarak kaydeder.

    Args:
        plan:          Aylik plan DataFrame'i.
        annual_target: Yillik hedef.
        source:        SI kaynagi etiketi.
    """
    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"user_plan_{annual_target}_{source}.csv"
    path = _OUTPUTS_DIR / fname
    plan.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"\n  Plan kaydedildi: {path}")


# ---------------------------------------------------------------------------
# CLI giris noktasi
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """Komut satiri argumanlarini parse eder.

    Returns:
        Parsed argparse Namespace nesnesi.
    """
    parser = argparse.ArgumentParser(
        description="Generic Monthly Target Planner with Seasonality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--target",
        type=int,
        default=None,
        metavar="N",
        help="Yillik araç hedefi (verilmezse interaktif sorulur)",
    )
    parser.add_argument(
        "--si-source",
        dest="si_source",
        choices=["final", "odd", "segment", "northstar"],
        default="final",
        help="Mevsimsel indeks kaynagi (varsayilan: final)",
    )
    parser.add_argument(
        "--si-file",
        dest="si_file",
        default=None,
        metavar="PATH",
        help="Ozel SI CSV dosyasi yolu (--si-source yerine gecerli)",
    )
    return parser.parse_args()


def main() -> None:
    """Ana program akisi: arguman parse, SI yukle, plan uret, tablo yazdir."""
    args = _parse_args()
    brand = _get_brand_name()
    source = args.si_source

    # SI yukle (once CSV, yoksa hesapla)
    print(f"\n[1/3] Mevsimsel indeks yukleniyor (kaynak: {source})...")
    si = _get_si(source, args.si_file)
    print(f"  SI serisi hazir. Ortalama: {si.mean():.4f} (beklenen: ~1.0000)")

    # Ilk hedef
    if args.target is not None:
        annual_target = args.target
    else:
        print("\nYillik araç hedefinizi girin (örn. 3600):")
        while True:
            try:
                inp = input("  Hedef: ").strip().replace(",", "").replace(".", "")
                annual_target = int(inp)
                if annual_target <= 0:
                    raise ValueError("Hedef pozitif olmali")
                break
            except ValueError as exc:
                print(f"  [HATA] Gecersiz giris: {exc}. Lutfen bir sayi girin.")

    # Interaktif dongu
    while True:
        print(f"\n[2/3] {annual_target:,} araçlik plan hesaplaniyor...")
        plan = _build_plan(annual_target, si)

        print("\n[3/3] Sonuc:")
        _print_plan_table(plan, annual_target, brand, source)

        # Kaydetme sorusu (yalnizca interaktif modda)
        if sys.stdin.isatty():
            save_ans = input("\nCSV olarak kaydetmek istiyor musunuz? [e/H]: ").strip().lower()
            if save_ans in ("e", "evet", "y", "yes"):
                _save_plan_csv(plan, annual_target, source)

            again_ans = input("\nFarkli bir hedefle tekrar denemek istiyor musunuz? [e/H]: ").strip().lower()
            if again_ans not in ("e", "evet", "y", "yes"):
                break

            while True:
                try:
                    inp = input("  Yeni hedef: ").strip().replace(",", "").replace(".", "")
                    annual_target = int(inp)
                    if annual_target <= 0:
                        raise ValueError("Pozitif olmali")
                    break
                except ValueError as exc:
                    print(f"  [HATA] {exc}")
        else:
            # Non-interaktif mod (CI/pipe): yalnizca bir kez calistir, cik
            break

    print("\nCikis yapiliyor. Gule gule!\n")


if __name__ == "__main__":
    main()
