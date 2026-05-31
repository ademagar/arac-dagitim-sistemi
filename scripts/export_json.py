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

_MONTH_TR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
             "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]


def _long_to_nested(df: pd.DataFrame | None, cat_col: str) -> dict[str, list[dict]]:
    """Long-format SI CSV'sini bayi→[aylık kayıt] dict yapısına çevirir."""
    if df is None:
        return {}
    result: dict[str, list[dict]] = {}
    for dealer, grp in df.groupby("dealer"):
        month_names = {
            int(r["month"]): r["month_name"]
            for _, r in grp[["month", "month_name"]].drop_duplicates().iterrows()
        }
        pivot = grp.pivot_table(
            index="month", columns=cat_col, values="si", aggfunc="first"
        ).reset_index()
        pivot.columns.name = None
        records: list[dict] = []
        for _, row in pivot.iterrows():
            m = int(row["month"])
            rec: dict = {"month": m, "month_name": month_names.get(m, _MONTH_TR[m - 1])}
            for col in pivot.columns:
                if col == "month":
                    continue
                val = row[col]
                if not (isinstance(val, float) and pd.isna(val)):
                    rec[str(col)] = round(float(val), 4)
            records.append(rec)
        result[str(dealer)] = records
    return result


bayi_model_si_dict = _long_to_nested(read(SEA / "08_bayi_model_si.csv"), "model")
bayi_renk_si_dict  = _long_to_nested(read(SEA / "10_bayi_renk_si.csv"),  "color")

save({
    "final":         final_rows,
    "bayi_si":       bayi_si_rows,
    "model_si":      model_si_rows,
    "renk_si":       renk_si_rows,
    "bayi_model_si": bayi_model_si_dict,
    "bayi_renk_si":  bayi_renk_si_dict,
}, "mevsimsellik.json")


# ---------------------------------------------------------------------------
# 5. Bayi konumları
# ---------------------------------------------------------------------------
print("Bayi konumları export ediliyor...")

INACTIVE_FROM = 23

def classify(lat: float, lon: float) -> str:
    if lat >= 40.0 and lon < 32.0:   return "Marmara"
    if lat >= 40.5 and lon >= 32.0:  return "Karadeniz"
    if lon < 30.5 and lat < 40.0:    return "Ege"
    if lat < 37.5 and lon >= 37.0:   return "Güneydoğu Anadolu"
    if lat < 37.5:                   return "Akdeniz"
    if lon >= 38.0 and lat < 40.5:   return "Doğu Anadolu"
    return "İç Anadolu"

dealer_rows: list[dict] = []
loc_path = RAW / "Dealer-Location.csv"
if loc_path.exists():
    with open(loc_path, encoding="utf-8-sig") as f:
        lines = f.readlines()
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(";")
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        try:
            lat, lon = map(float, parts[1].strip().split(","))
        except Exception:
            continue
        try:
            num = int(name.split()[-1])
            active = num < INACTIVE_FROM
        except ValueError:
            active = True
        dealer_rows.append({
            "name":   name,
            "lat":    lat,
            "lon":    lon,
            "region": classify(lat, lon),
            "active": active,
        })

save(dealer_rows, "dealers.json")

print(f"\nToplam {len(list(DEST.glob('*.json')))} JSON dosyası oluşturuldu → {DEST}")
