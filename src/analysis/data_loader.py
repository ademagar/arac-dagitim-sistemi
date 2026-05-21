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

# Rakip marka anonimleştirme — CSV'deki sıraya göre numaralandırılmıştır
COMPETITOR_ALIAS_MAP: dict[str, str] = {
    "CITROEN":    "Competitor 1",
    "KIA":        "Competitor 2",
    "NISSAN":     "Competitor 3",
    "OPEL":       "Competitor 4",
    "PEUGEOT":    "Competitor 5",
    "RENAULT":    "Competitor 6",
    "SKODA":      "Competitor 7",
    "TOYOTA":     "Competitor 8",
    "VOLKSWAGEN": "Competitor 9",
}
# TOPLAM: satırı rakip değil, toplam row — yükleme sırasında atlanır


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


def load_target_achievement(year: int, data_dir: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    """Yıllık hedef-gerçekleşme dosyasını iki formatta döndürür.

    Args:
        year: 2024 veya 2025

    Returns:
        {
          "wide":  metrik × ay pivot (ham tabloya yakın),
          "long":  uzun format: month, channel, metric, value
        }
    """
    path = data_dir / f"{year}-TARGET-vs-ACHIEVEMENT.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()

    # Ay başlıklarını içeren satırı bul (JAN veya FEB içeren)
    header_idx = next(
        i for i, l in enumerate(lines) if f"JAN'{str(year)[2:]}" in l
    )
    yr_short = str(year)[2:]
    month_labels = [
        c.strip().replace("AUG'", f"AUG'{yr_short}")  # 2024 dosyasındaki yazım hatasını düzelt
        for c in lines[header_idx].split(";") if c.strip()
    ]

    # Virgülü ondalık ayırıcı olarak normalize et
    def parse_val(s: str) -> float | None:
        s = s.strip().replace("%", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    # Metrik satırlarını oku (header_idx+1'den sonuna kadar boş olmayan satırlar)
    rows_wide: list[dict] = []
    rows_long: list[dict] = []

    for line in lines[header_idx + 1 :]:
        if not line.strip():
            continue
        parts = line.split(";")
        metric = parts[0].strip()
        if not metric:
            continue

        values = parts[2:]  # ilk iki sütun boş veya tekrar başlık
        row: dict = {"metric": metric}
        for i, lbl in enumerate(month_labels):
            val = parse_val(values[i]) if i < len(values) else None
            row[lbl] = val

            # Kanal ve tip çıkar (long format için)
            if "B2C" in metric and "B2B" not in metric:
                channel = "B2C"
            elif "B2B+B2C" in metric or "B2B+B2C" in metric:
                channel = "B2B+B2C"
            elif "B2B" in metric:
                channel = "B2B"
            else:
                channel = "ALL"

            if "TARGET" in metric and "ACHIEVEMENT" not in metric and "%" not in metric:
                mtype = "target"
            elif "ACHIEVEMENT" in metric and "%" not in metric:
                mtype = "achievement"
            elif "%" in metric or "Achievement" in metric:
                mtype = "achievement_pct"
            elif "Fark" in metric:
                mtype = "difference"
            else:
                mtype = metric.lower().replace(" ", "_")

            if val is not None and lbl != "TOTAL":
                rows_long.append(
                    {
                        "year": year,
                        "month": lbl,
                        "channel": channel,
                        "metric_type": mtype,
                        "value": val,
                    }
                )
        rows_wide.append(row)

    wide = pd.DataFrame(rows_wide).set_index("metric")
    long = pd.DataFrame(rows_long) if rows_long else pd.DataFrame()
    return {"wide": wide, "long": long}


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
        brand_raw = str(row.iloc[0]).strip()
        # Toplam ve boş satırları atla
        if brand_raw in ("", "nan", "NaN") or brand_raw.startswith("Unnamed"):
            continue
        if brand_raw not in COMPETITOR_ALIAS_MAP:
            continue  # TOPLAM: gibi rakip olmayan satırları atla
        brand = COMPETITOR_ALIAS_MAP[brand_raw]

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


def load_odd_market(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """ODD Türkiye ithal otomobil pazarı aylık satışlarını yükler.

    Dosya: 2024-2025-ODD-Otomobil-Satışlar-İthal).csv
    Format: marka × ay, nokta=bin ayırıcı, virgül=ondalık

    Returns:
        Uzun formatlı DataFrame: brand, year_month (YYYY-MM), sales_qty
        "TOTAL SALES" ve sıfır satırları çıkarılmış.
    """
    import glob
    matches = glob.glob(str(data_dir / "*ODD*"))
    if not matches:
        raise FileNotFoundError("ODD dosyası data/raw/ içinde bulunamadı.")
    path = Path(matches[0])

    lines = path.read_text(encoding="utf-8-sig").splitlines()

    # Ay başlıklarını ilk satırdan çek
    header_parts = lines[0].split(";")
    month_labels = [c.strip() for c in header_parts[1:] if c.strip()]

    skip_brands = {"TOTAL SALES", "TOPLAM", ""}
    records: list[dict] = []

    for line in lines[1:]:
        if not line.strip() or line.startswith(";"):
            continue
        parts = line.split(";")
        brand = parts[0].strip()
        if brand in skip_brands or not brand:
            continue

        values = parts[1:]
        monthly_total = 0.0
        row_records: list[dict] = []

        for i, lbl in enumerate(month_labels):
            if i >= len(values):
                break
            # "Oca.24" → YYYY-MM
            lbl_parts = lbl.split(".")
            if len(lbl_parts) != 2:
                continue
            tr_abbr, yr_short = lbl_parts[0].strip(), lbl_parts[1].strip()
            en_abbr = MONTH_TR_MAP.get(tr_abbr, tr_abbr)
            year = int("20" + yr_short)
            month_num = pd.to_datetime(f"{en_abbr} {year}", format="%b %Y").month
            year_month = f"{year}-{month_num:02d}"

            raw_val = values[i].strip().replace(".", "").replace(",", ".")
            qty = pd.to_numeric(raw_val, errors="coerce")
            if pd.isna(qty):
                qty = 0.0
            monthly_total += qty
            row_records.append({"brand": brand, "year_month": year_month, "sales_qty": qty})

        # Tüm ayları sıfır olan markaları atla (TOGG, SMART vb.)
        if monthly_total > 0:
            records.extend(row_records)

    return pd.DataFrame(records)
