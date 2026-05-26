"""CSV çıktılarını Next.js için JSON'a dönüştürür.

Kullanım: python scripts/export_json.py
Çıktı:    web/public/data/*.json
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
OUT  = ROOT / "outputs"
RAW  = ROOT / "data" / "raw"
DEST = ROOT / "web" / "public" / "data"
DEST.mkdir(parents=True, exist_ok=True)

_ABBR = {
    "JAN": "Oca", "FEB": "Şub", "MAR": "Mar", "APR": "Nis",
    "MAY": "May", "JUN": "Haz", "JUL": "Tem", "AUG": "Ağu",
    "SEP": "Eyl", "OCT": "Eki", "NOV": "Kas", "DEC": "Ara",
}
_NUM = {1:"Oca",2:"Şub",3:"Mar",4:"Nis",5:"May",6:"Haz",
        7:"Tem",8:"Ağu",9:"Eyl",10:"Eki",11:"Kas",12:"Ara"}


def save(data: object, name: str) -> None:
    path = DEST / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {name}")


def fmt_abbr(val: str, show_year: bool = False) -> str:
    parts = str(val).split("'")
    tr = _ABBR.get(parts[0][:3].upper(), parts[0])
    if show_year and len(parts) > 1:
        yr = parts[1][-2:]
        return f"20{yr} {tr}"
    return tr


def fmt_ym(val: str, show_year: bool = True) -> str:
    try:
        y, m = str(val).split("-")
        tr = _NUM.get(int(m), m)
        return f"{y} {tr}" if show_year else tr
    except Exception:
        return str(val)


def read(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def sort_dealers(lst: list[dict], key: str = "dealer") -> list[dict]:
    def num(d: dict) -> int:
        m = re.search(r"(\d+)$", str(d.get(key, "")))
        return int(m.group(1)) if m else 0
    return sorted(lst, key=num)


# ---------------------------------------------------------------------------
# 1. Satış verileri: 2024 / 2025 / all
# ---------------------------------------------------------------------------
print("Satış verileri export ediliyor...")

for year in ["2024", "2025", "all"]:
    d = OUT / year
    show_year = (year == "all")

    model_df   = read(d / "01_model_satislari.csv")
    renk_df    = read(d / "03_renk_satislari.csv")
    bayi_df    = read(d / "04_bayi_toplam_satis.csv")
    trend_df   = read(d / "08_aylik_trend.csv")

    model_rows = model_df[["model","total_sales","share_pct"]].rename(
        columns={"model":"model","total_sales":"satis","share_pct":"pay"}
    ).to_dict("records") if model_df is not None else []

    renk_rows = renk_df.rename(
        columns={"Exterior Color":"renk","total_sales":"satis","share_pct":"pay"}
    ).to_dict("records") if renk_df is not None else []

    bayi_rows = bayi_df.rename(
        columns={"Dealer Name":"dealer","total_sales":"satis"}
    ).to_dict("records") if bayi_df is not None else []
    bayi_rows = sort_dealers(bayi_rows)

    trend_rows: list[dict] = []
    if trend_df is not None:
        for _, row in trend_df.iterrows():
            period = fmt_ym(row["year_month"], show_year=show_year)
            trend_rows.append({
                "period": period,
                "satis": int(row["sales_qty"]),
                "year_month": str(row["year_month"]),
            })

    # Bayi × Renk (stacked bar için)
    raw_df = None
    try:
        raw_df = pd.read_csv(
            RAW / "2024&2025-ALL-SALES-CSV-FILE.csv",
            sep=";", encoding="utf-8-sig",
            usecols=["Dealer Name", "Exterior Color", "Sales Date"],
        )
        raw_df["_year"] = raw_df["Sales Date"].str[:4]
    except Exception:
        pass

    bayi_renk_rows: list[dict] = []
    top3_rows: list[dict] = []
    if raw_df is not None:
        sub = raw_df if year == "all" else raw_df[raw_df["_year"] == year]
        grp = sub.groupby(["Dealer Name", "Exterior Color"]).size().reset_index(name="n")
        bayi_renk_rows = [
            {"dealer": r["Dealer Name"], "renk": r["Exterior Color"], "n": int(r["n"])}
            for _, r in grp.iterrows()
        ]

        # Top 3 per dealer
        grp["rank"] = grp.groupby("Dealer Name")["n"].rank(method="first", ascending=False)
        top3_sub = grp[grp["rank"] <= 3].sort_values(["Dealer Name","rank"])
        for dealer, ddf in top3_sub.groupby("Dealer Name"):
            ddf = ddf.reset_index(drop=True)
            row: dict = {"dealer": dealer}
            for i in range(3):
                if i < len(ddf):
                    row[f"renk{i+1}"] = ddf.loc[i, "Exterior Color"]
                    row[f"adet{i+1}"] = int(ddf.loc[i, "n"])
                else:
                    row[f"renk{i+1}"] = "-"
                    row[f"adet{i+1}"] = 0
            top3_rows.append(row)
        top3_rows = sort_dealers(top3_rows)

    save({
        "model": model_rows,
        "renk":  renk_rows,
        "bayi":  bayi_rows,
        "aylik": trend_rows,
        "bayi_renk": sort_dealers(bayi_renk_rows),
        "top3_renk": top3_rows,
    }, f"sales-{year}.json")


# ---------------------------------------------------------------------------
# 2. Hedef gerçekleşme (B2C)
# ---------------------------------------------------------------------------
print("Hedef verileri export ediliyor...")

def load_hedef(year_key: str) -> list[dict]:
    if year_key == "all":
        frames = []
        for yk in ["2024", "2025"]:
            df = read(OUT / yk / "12_hedef_gerceklestirme_long.csv")
            if df is not None:
                frames.append(df)
        if not frames:
            return []
        df = pd.concat(frames, ignore_index=True)
        df["period"] = df["month"].apply(lambda v: fmt_abbr(v, show_year=True))
    else:
        df = read(OUT / year_key / "12_hedef_gerceklestirme_long.csv")
        if df is None:
            return []
        df["period"] = df["month"].apply(lambda v: fmt_abbr(v, show_year=False))

    b2c = df[df["channel"] == "B2C"].copy()
    targets   = b2c[b2c["metric_type"] == "target"][["period","value"]].rename(columns={"value":"hedef"})
    achieves  = b2c[b2c["metric_type"] == "achievement"][["period","value"]].rename(columns={"value":"gercek"})
    merged    = targets.merge(achieves, on="period", how="inner")
    merged["pct"] = (merged["gercek"] / merged["hedef"] * 100).round(1)
    return merged.to_dict("records")

hedef_data = {
    "2024": load_hedef("2024"),
    "2025": load_hedef("2025"),
    "all":  load_hedef("all"),
}
save(hedef_data, "hedef.json")


# ---------------------------------------------------------------------------
# 3. Rakip karşılaştırma
# ---------------------------------------------------------------------------
print("Rakip verileri export ediliyor...")

rakip_df = read(OUT / "all" / "15_rakip_satislar.csv")
rakip_rows: list[dict] = []
if rakip_df is not None:
    rakip_df = rakip_df.loc[:, ~rakip_df.columns.str.startswith("Unnamed")]
    for _, row in rakip_df.iterrows():
        rakip_rows.append({
            "marka":      str(row["brand"]),
            "year_month": str(row["year_month"]),
            "period":     fmt_ym(row["year_month"], show_year=True),
            "satis":      int(row["sales_qty"]),
        })
save(rakip_rows, "rakip.json")


# ---------------------------------------------------------------------------
# 4. Mevsimsellik
# ---------------------------------------------------------------------------
print("Mevsimsellik verileri export ediliyor...")

SEA = OUT / "seasonality"

final_df = read(SEA / "04_FINAL_si.csv")
final_rows = final_df.to_dict("records") if final_df is not None else []

bayi_si_df = read(SEA / "05_bayi_si.csv")
bayi_si_rows: list[dict] = []
if bayi_si_df is not None:
    bayi_si_df = bayi_si_df.loc[:, ~bayi_si_df.columns.str.startswith("Unnamed")]
    dealer_cols = sorted(
        [c for c in bayi_si_df.columns if c.startswith("DEALER")],
        key=lambda x: int(re.search(r"(\d+)$", x).group(1)),
    )
    non_d = [c for c in bayi_si_df.columns if not c.startswith("DEALER")]
    bayi_si_df = bayi_si_df[non_d + dealer_cols]
    bayi_si_rows = bayi_si_df.to_dict("records")

model_si_df = read(SEA / "06_model_si.csv")
model_si_rows = model_si_df.to_dict("records") if model_si_df is not None else []

renk_si_df = read(SEA / "07_renk_si.csv")
renk_si_rows = renk_si_df.to_dict("records") if renk_si_df is not None else []

save({
    "final":   final_rows,
    "bayi_si": bayi_si_rows,
    "model_si": model_si_rows,
    "renk_si":  renk_si_rows,
}, "mevsimsellik.json")


# ---------------------------------------------------------------------------
# 5. Bayi konumları + aktiflik + kodlar + hedefler
# ---------------------------------------------------------------------------
print("Bayi konumları export ediliyor...")

import csv as _csv

REGION_MAP = {
    "ICA": "İç Anadolu", "EGE": "Ege", "AKD": "Akdeniz",
    "MAR": "Marmara",    "GDA": "Güneydoğu Anadolu",
    "KAR": "Karadeniz",  "DOA": "Doğu Anadolu",
}

def region_from_code(code: str) -> str:
    parts = code.split("-")
    return REGION_MAP.get(parts[2] if len(parts) > 2 else "", "Bilinmiyor")

# Kodlar
codes: dict[str, str] = {}
with open(RAW / "Bayi-Adi-Kodu.csv", encoding="utf-8-sig") as f:
    for row in _csv.reader(f, delimiter=";"):
        if len(row) >= 2 and row[0].startswith("DEALER"):
            codes[row[0].strip()] = row[1].strip()

# Konumlar
locations: dict[str, dict] = {}
with open(RAW / "Bayi-Konum-Bilgisi.csv", encoding="utf-8-sig") as f:
    for row in _csv.reader(f, delimiter=";"):
        if len(row) >= 2 and row[0].startswith("DEALER"):
            lat, lon = map(float, row[1].strip().split(","))
            locations[row[0].strip()] = {"lat": lat, "lon": lon}

# Aktiflik durumu
activity_months: list[str] = []
activity: dict[str, dict] = {}
with open(RAW / "Bayi-Aktiflik-Durumu.csv", encoding="utf-8-sig") as f:
    reader = _csv.reader(f, delimiter=";")
    header = next(reader)
    activity_months = [h.strip() for h in header[1:] if h.strip()]
    for row in reader:
        if len(row) >= 2 and row[0].startswith("DEALER"):
            dealer = row[0].strip()
            activity[dealer] = {
                activity_months[i]: row[i + 1].strip()
                for i in range(len(activity_months))
                if i + 1 < len(row)
            }

dealer_rows = []
for dealer in sorted(codes.keys(), key=lambda x: int(x.split()[-1])):
    code = codes[dealer]
    loc  = locations.get(dealer, {"lat": 0.0, "lon": 0.0})
    act  = activity.get(dealer, {})
    default_active = act.get("Oca.26", "AKTİF DEĞİL") == "AKTİF"
    dealer_rows.append({
        "name":     dealer,
        "code":     code,
        "lat":      loc["lat"],
        "lon":      loc["lon"],
        "region":   region_from_code(code),
        "active":   default_active,
        "activity": act,
    })

save(dealer_rows, "dealers.json")

# Bayi hedefleri
print("Bayi hedefleri export ediliyor...")
TARGET_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs"]
bayi_hedef: dict[str, list] = {m: [] for m in TARGET_MONTHS}
with open(RAW / "Bayi-Hedefleri.csv", encoding="utf-8-sig") as f:
    reader = _csv.reader(f, delimiter=";")
    next(reader)
    for row in reader:
        if not row or not row[0].startswith("DEALER"):
            continue
        dealer = row[0].strip()
        code   = row[1].strip() if len(row) > 1 else ""
        for i, month in enumerate(TARGET_MONTHS):
            col     = i + 2
            val_str = row[col].strip() if col < len(row) else ""
            target  = int(val_str) if val_str.isdigit() else None
            bayi_hedef[month].append({"dealer": dealer, "code": code, "target": target})

save(bayi_hedef, "bayi-hedefleri.json")
print("  ✓ bayi-hedefleri.json")

print(f"\nToplam {len(list(DEST.glob('*.json')))} JSON dosyası oluşturuldu → {DEST}")
