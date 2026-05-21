"""Veri yükleme ve temizleme modülü.

Ham CSV dosyalarını okur, temizler ve analize hazır hale getirir.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parents[2] / "data" / "raw"

MONTH_ORDER = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]

MONTH_TR_MAP = {
    "Oca": "Jan", "Şub": "Feb", "Mar": "Mar", "Nis": "Apr",
    "May": "May", "Haz": "Jun", "Tem": "Jul", "Ağu": "Aug",
    "Eyl": "Sep", "Eki": "Oct", "Kas": "Nov", "Ara": "Dec",
}


def load_sales(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Ana satış dosyasını yükler ve temizler.

    Returns:
        Her satırın bir araç satışını temsil ettiği DataFrame.
        Yeni sütunlar: year, month, year_month, model_version
    """
    path = data_dir / "2024&2025-ALL-SALES-CSV-FILE.csv"
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")

    # Tarih dönüşümü
    df["Sales Date"] = pd.to_datetime(df["Sales Date"], errors="coerce")
    df["year"] = df["Sales Date"].dt.year
    df["month"] = df["Sales Date"].dt.month
    df["year_month"] = df["Sales Date"].dt.to_period("M")

    # Model + versiyon birleşik sütun
    df["model_version"] = df["Model Description"].fillna("?") + " / " + df["Vehicle Version"].fillna("?")

    # NaN model satırlarını çıkar
    df = df.dropna(subset=["Model Description", "Dealer Name"])

    return df


def load_monthly_performance(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Tüm aylık hedef-gerçekleşme dosyalarını birleştirir.

    Her dosya üç bölümden oluşur:
    - Satır 0-22:  Bayi bazlı hedefler (Northstar Dealers' Target)
    - Satır 31-53: B2C model bazlı gerçekleşmeler
    - Satır 57-80: B2B model bazlı gerçekleşmeler

    Returns:
        Uzun formatlı DataFrame: month, dealer, channel, model, actual_qty
    """
    records: list[dict] = []

    for month_name in MONTH_ORDER:
        fname = (
            f"NORTHSTAR_2025_{month_name}_Bayinin_Aylık_Model_Bazlı_"
            "Araç_Satışı_Hedef_Gerçekleştirmesi.csv"
        )
        path = data_dir / fname
        if not path.exists():
            continue

        # Apostrofun pandas'ı karıştırmaması için text olarak oku, csv ile parse et
        content = path.read_text(encoding="utf-8-sig")
        reader = csv.reader(
            io.StringIO(content), delimiter=";",
            quoting=csv.QUOTE_NONE, escapechar="\\"
        )
        rows = list(reader)
        raw = pd.DataFrame(rows)

        # --- Hedef bölümü (satır 1-22) ---
        target_section = raw.iloc[1:23, [0, 1, 2]].copy()
        target_section.columns = ["dealer_code", "dealer_name", "monthly_target"]
        target_section = target_section.dropna(subset=["dealer_code"])
        target_section["monthly_target"] = pd.to_numeric(
            target_section["monthly_target"], errors="coerce"
        )
        target_section["month"] = month_name

        # --- B2C gerçekleşme bölümü ---
        b2c_header_row = None
        b2b_header_row = None
        for i, val in enumerate(raw.iloc[:, 0]):
            if str(val).strip() == "BRAND-A CLOSING B2C":
                b2c_header_row = i + 1
            if str(val).strip() == "BRAND-A CLOSING B2B":
                b2b_header_row = i + 1

        for channel, header_row in [("B2C", b2c_header_row), ("B2B", b2b_header_row)]:
            if header_row is None:
                continue
            cols = raw.iloc[header_row, :].tolist()
            data_rows = raw.iloc[header_row + 1 : header_row + 23].copy()
            data_rows.columns = range(len(data_rows.columns))

            model_cols = {
                i: str(cols[i]).strip()
                for i in range(2, len(cols))
                if str(cols[i]).startswith("Model") or str(cols[i]) == "TOTAL"
            }

            for _, row in data_rows.iterrows():
                dealer_code = str(row[0]).strip()
                dealer_name = str(row[1]).strip()
                if not dealer_code.startswith("BA-"):
                    continue
                for col_idx, model_name in model_cols.items():
                    if model_name == "TOTAL":
                        continue
                    qty = pd.to_numeric(row[col_idx], errors="coerce")
                    if pd.isna(qty):
                        qty = 0
                    records.append(
                        {
                            "month": month_name,
                            "dealer_code": dealer_code,
                            "dealer_name": dealer_name,
                            "channel": channel,
                            "model_group": model_name,
                            "actual_qty": int(qty),
                        }
                    )

    if not records:
        return pd.DataFrame()

    perf = pd.DataFrame(records)
    month_order_map = {m: i for i, m in enumerate(MONTH_ORDER)}
    perf["month_num"] = perf["month"].map(month_order_map)
    perf = perf.sort_values(["month_num", "dealer_name", "channel"])
    return perf


def load_competitors(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Rakip marka aylık satış verilerini yükler.

    Returns:
        Uzun formatlı DataFrame: brand, year_month, sales_qty
    """
    path = data_dir / "2024-2025-Competitors-Sales-Months.csv"
    raw = pd.read_csv(path, sep=";", encoding="utf-8-sig", header=None)

    # İlk satır boş, ikinci satır marka isimleri
    brand_col = raw.iloc[:, 0]
    month_cols = raw.iloc[0, 1:].tolist()

    records: list[dict] = []
    for _, row in raw.iterrows():
        brand = str(row.iloc[0]).strip()
        if brand in ("", "nan", "NaN") or brand.startswith("Unnamed"):
            continue
        for col_idx, month_label in enumerate(month_cols, start=1):
            month_str = str(month_label).strip()
            if month_str in ("", "nan"):
                continue
            # "Oca.24" → "2024-01" formatına çevir
            parts = month_str.split(".")
            if len(parts) != 2:
                continue
            tr_abbr, yr_short = parts[0].strip(), parts[1].strip()
            en_abbr = MONTH_TR_MAP.get(tr_abbr, tr_abbr)
            year = int("20" + yr_short)
            month_num = pd.to_datetime(f"{en_abbr} {year}", format="%b %Y").month
            year_month = f"{year}-{month_num:02d}"

            raw_val = str(row.iloc[col_idx]).replace(".", "").replace(",", ".").strip()
            qty = pd.to_numeric(raw_val, errors="coerce")
            if pd.isna(qty):
                continue
            records.append({"brand": brand, "year_month": year_month, "sales_qty": qty})

    return pd.DataFrame(records)
