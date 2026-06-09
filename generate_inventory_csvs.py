"""
Demo envanter CSV dosyalarını üretir (Ocak-Temmuz 2026).
Çıktı: web/public/data/bulunurluk-{ay}.csv
"""
import math
import random
import os
from pathlib import Path
from datetime import date, timedelta

random.seed(42)

# ─── Çıktı dizini ────────────────────────────────────────────────────────────
OUT_DIR = Path("/home/user/arac-dagitim-sistemi/web/public/data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Aylık hedefler (A2, A3, B1) ─────────────────────────────────────────────
MONTHLY_TARGETS = {
    "January":  {"A2": 253, "A3": 84,  "B1": 156},
    "February": {"A2": 343, "A3": 116, "B1": 208},
    "March":    {"A2": 444, "A3": 147, "B1": 272},
    "April":    {"A2": 360, "A3": 120, "B1": 223},
    "May":      {"A2": 418, "A3": 138, "B1": 255},
    "June":     {"A2": 467, "A3": 155, "B1": 286},
    "July":     {"A2": 405, "A3": 136, "B1": 250},
}

# ─── Dosya adı eşlemeleri ─────────────────────────────────────────────────────
FILE_NAMES = {
    "January":  "bulunurluk-ocak.csv",
    "February": "bulunurluk-subat.csv",
    "March":    "bulunurluk-mart.csv",
    "April":    "bulunurluk-nisan.csv",
    "May":      "bulunurluk-mayis.csv",
    "June":     "bulunurluk-haziran.csv",
    "July":     "bulunurluk-temmuz.csv",
}

# ─── Üretim tarihi aralıkları (başlangıç, bitiş) ─────────────────────────────
DATE_RANGES = {
    "January":  (date(2026, 1, 12), date(2026, 1, 30)),
    "February": (date(2026, 2, 2),  date(2026, 2, 27)),
    "March":    (date(2026, 3, 2),  date(2026, 3, 27)),
    "April":    (date(2026, 4, 1),  date(2026, 4, 24)),
    "May":      (date(2026, 5, 4),  date(2026, 5, 29)),
    "June":     (date(2026, 6, 1),  date(2026, 6, 26)),
    "July":     (date(2026, 7, 1),  date(2026, 7, 25)),
}

# ─── Renk dağılımları ────────────────────────────────────────────────────────
COLOR_DIST = {
    "A2": [
        ("Black2", 22), ("Grey1", 18), ("White2", 16), ("Beige", 14),
        ("Grey3", 12), ("Blue4", 10), ("Grey6", 5), ("Red2", 2), ("White3", 1),
    ],
    "A3": [
        ("Grey3", 22), ("White2", 18), ("Beige", 16), ("Grey1", 14),
        ("Black2", 12), ("Yellow", 8), ("Red2", 6), ("Grey6", 4),
    ],
    "B1": [
        ("Black2", 25), ("Grey6", 20), ("White2", 18), ("Blue4", 15),
        ("Grey1", 12), ("Beige", 7), ("Red2", 3),
    ],
}

# ─── Model → (Vehicle Version, Vehicle Code) ─────────────────────────────────
MODEL_INFO = {
    "A2": ("A2V02", "L6"),
    "A3": ("A3V02", "M8"),
    "B1": ("B1V01", "N7"),
}

# ─── Fiziksel durum ve kota dağılımları ──────────────────────────────────────
PHYS_STATUS = [
    ("Locked order", 65),
    ("Partially modifiable order", 25),
    ("Ready for dispatch", 10),
]
QUOTA_STATUS = [
    ("Merkezi Kota", 70),
    ("Merkezi Rezerveli", 30),
]


def weighted_choice(choices: list[tuple[str, int]], rng: random.Random) -> str:
    """Ağırlıklı rastgele seçim."""
    items = [item for item, w in choices for _ in range(w)]
    return rng.choice(items)


def weekdays_in_range(start: date, end: date) -> list[date]:
    """Aralıktaki iş günlerini (Pzt-Cum) döndürür."""
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # 0=Pzt, 4=Cum
            days.append(cur)
        cur += timedelta(days=1)
    return days


def format_date(d: date) -> str:
    """DD.MM.YYYY formatı."""
    return d.strftime("%d.%m.%Y")


def format_week(d: date) -> str:
    """W{ww}/{mm}/{yyyy} formatı."""
    week_num = d.isocalendar()[1]
    return f"W{week_num:02d}/{d.month:02d}/{d.year}"


# Global chassis sayaçları (Ocak dosyası ~350 satır → 1001'den başla)
chassis_counters: dict[str, int] = {
    "A2": 1001,
    "A3": 1001,
    "B1": 1001,
}

# CSV başlık sütunları (orijinal dosyayla aynı sıra)
HEADER = [
    "Dealer Code Processing", "Dealer Name", "Long Chassis",
    "Model Description", "Vehicle Version", "Vehicle Code",
    "Model Year", "Color Type", "Exterior Color", "Interior Color",
    "Physical Status Description", "Estimated Production Day",
    "Estimated Production Week", "Sales Type", "Sales Type Description",
    "Have a Customer", "Invoiced?", "Dispatchable", "Quota Status",
    "Central / Dealer Quota", "Production Day", "Related Month Availability",
    "Status", "Month Number",
]

rng = random.Random(42)


def generate_rows(month_en: str) -> list[dict]:
    """Belirtilen ay için araç satırlarını üretir."""
    targets = MONTHLY_TARGETS[month_en]
    date_range = DATE_RANGES[month_en]
    weekdays = weekdays_in_range(*date_range)

    rows: list[dict] = []

    for model, base_target in targets.items():
        count = math.ceil(base_target * 1.15)
        version, vcode = MODEL_INFO[model]

        # Renk dağılımından renk listesi üret
        color_pool: list[str] = []
        for color, weight in COLOR_DIST[model]:
            color_pool.extend([color] * weight)

        for _ in range(count):
            prod_day = rng.choice(weekdays)
            chassis_num = chassis_counters[model]
            chassis_counters[model] += 1
            chassis = f"{version}MY26{vcode}{chassis_num:06d}"

            color = rng.choice(color_pool)
            phys_status = weighted_choice(PHYS_STATUS, rng)
            quota_status = weighted_choice(QUOTA_STATUS, rng)

            rows.append({
                "Dealer Code Processing": "CENT-STOCK",
                "Dealer Name": "CENTRAL STOCK",
                "Long Chassis": chassis,
                "Model Description": model,
                "Vehicle Version": version,
                "Vehicle Code": vcode,
                "Model Year": "2026",
                "Color Type": "Color",
                "Exterior Color": color,
                "Interior Color": "IG1a",
                "Physical Status Description": phys_status,
                "Estimated Production Day": format_date(prod_day),
                "Estimated Production Week": format_week(prod_day),
                "Sales Type": "RE",
                "Sales Type Description": "Perakende",
                "Have a Customer": "NO",
                "Invoiced?": "N",
                "Dispatchable": "Y",
                "Quota Status": quota_status,
                "Central / Dealer Quota": "Central",
                "Production Day": format_date(prod_day),
                "Related Month Availability": "Following Months",
                "Status": "To Be Produced",
                "Month Number": month_en,
            })

    rng.shuffle(rows)
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    """UTF-8 BOM, noktalı virgül sınırlayıcı ile CSV yazar."""
    lines = [";".join(HEADER)]
    for row in rows:
        lines.append(";".join(str(row[col]) for col in HEADER))
    content = "\n".join(lines) + "\n"
    # UTF-8 BOM prefix
    path.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))


# ─── Ana üretim döngüsü ───────────────────────────────────────────────────────
print(f"Çıktı dizini: {OUT_DIR}")
print()

for month_en, filename in FILE_NAMES.items():
    rows = generate_rows(month_en)
    out_path = OUT_DIR / filename
    write_csv(out_path, rows)

    targets = MONTHLY_TARGETS[month_en]
    total_target = sum(targets.values())
    expected = sum(math.ceil(v * 1.15) for v in targets.values())

    print(f"{month_en:10s} → {filename}")
    print(f"  Hedef: A2={targets['A2']}, A3={targets['A3']}, B1={targets['B1']} (toplam={total_target})")
    print(f"  Beklenen satır sayısı: {expected}, Gerçek: {len(rows)}")

    # Doğrulama
    assert len(rows) == expected, f"HATA: {len(rows)} != {expected}"
    assert all(r["Dispatchable"] == "Y" for r in rows), "Dispatchable hatası"
    assert all(r["Month Number"] == month_en for r in rows), "Month Number hatası"
    assert all(r["Dealer Code Processing"] == "CENT-STOCK" for r in rows), "Dealer Code hatası"
    print(f"  ✓ Doğrulama geçti\n")

print("Tüm dosyalar başarıyla oluşturuldu.")
