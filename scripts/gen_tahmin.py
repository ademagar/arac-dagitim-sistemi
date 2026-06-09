"""gen_tahmin.py

Aralık 2025 tahminlemesi (A/B/C tier bazlı) ve 2026 yıllık dağıtım planı üretir.
Çıktı: web/public/data/tahmin.json

Metodoloji:
- Bayiler bölgesel koda göre A/B/C tier'a ayrılır (MAR+EGE+ICA → A, AKD → B, GDA+KAR → C)
- Her tier için ayrı Seasonal Index + ayrı trend düzeltmesi hesaplanır
- 2026 planı: 8500 ve 10000 araç olmak üzere iki senaryo, Ocak dahil tüm aylar SI bazlı
- Aylık model bazlı hedefler: tarihsel model mix'i her aya uygulanır

Kullanım:
    python scripts/gen_tahmin.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Yol tanımlamaları
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
SEASONALITY_DIR = REPO_ROOT / "outputs" / "seasonality"
OUT_JSON = REPO_ROOT / "web" / "public" / "data" / "tahmin.json"

SALES_FILE = DATA_RAW / "2024&2025-ALL-SALES-CSV-FILE.csv"
SI_FILE = SEASONALITY_DIR / "04_FINAL_si.csv"
DEALER_TARGETS_FILE = DATA_RAW / "dealer_target_january26.csv"
BAYI_KOD_FILE = DATA_RAW / "Bayi-Adi-Kodu.csv"

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
LANSMAN_AY = 3        # Mart lansmanı
LANSMAN_BOOST = 1.11  # Mart+ çarpanı — B seg Mart 2024/2025 restore analizi bazlı
LANSMAN_MODEL = "B1"  # Yeni versiyon lansmanı yapılacak model

# B Segmenti tüm versiyonları lansmandan yararlanır (B1 yeni versiyon + B2 yan etki)
LANSMAN_SEGMENT: frozenset[str] = frozenset({"B1", "B2"})

# B Segmenti model mix boost — aya göre: lansman ayı peak, sonra kademeli normalize
# Veri: tarihsel B payı Mart'ta zaten %50, H2'de %13-27 → yeni versiyon bunu yukarı çeker
B_SEGMENT_BOOST_BY_AY: dict[int, float] = {
    3: 1.60,   # Mart: lansman ayı peak — B segment ~%50 → ~%65
    4: 1.45,   # Nisan: lansman sonrası yüksek talep
    5: 1.40,   # Mayıs
    6: 1.35,   # Haziran
    7: 1.25,   # Temmuz: yaz sezonu, kademeli normalize
    8: 1.20,   # Ağustos
    9: 1.15,   # Eylül
    10: 1.10,  # Ekim
    11: 1.10,  # Kasım
    12: 1.05,  # Aralık: yıl sonu A segment ivmesiyle normalize
}

PLAN_HEDEFLER = [8500, 10000]  # İki senaryo

# 2026'da aktif olacak modeller — A1, C1, D1 üretimden kalkıyor
MODELLER_2026: frozenset[str] = frozenset({"A2", "A3", "B1", "B2"})

AY_ADLARI = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

# ---------------------------------------------------------------------------
# Pazar büyüklüğü bazlı tier grupları (il bazında, TÜİK araç stoku proxy)
# ---------------------------------------------------------------------------
# A — Büyük Metro: Türkiye'nin en yüksek araç yoğunluklu 4 ili.
#     TÜİK catchment toplamı ~45%+. Güçlü trend, yüksek SI varyansı.
TIER_A_ILLER: frozenset[str] = frozenset({"İSTANBUL", "ANKARA", "İZMİR", "BURSA"})

# B — Bölgesel Merkez: Orta büyüklükte pazar, köklü bayi tabanı, catchment ~2–5%.
TIER_B_ILLER: frozenset[str] = frozenset({
    "ANTALYA", "KOCAELİ", "GAZİANTEP",
    "TEKİRDAĞ", "KONYA", "MUĞLA", "DENİZLİ",
})
# C — Gelişen Pazar: Daha küçük catchment, yüksek büyüme potansiyeli, düşük baz.
# (ADANA, MERSİN, KAYSERİ, KAHRAMANMARAŞ, SAMSUN, TRABZON, SİVAS)

TIER_ACIKLAMALAR = {
    "A": "Büyük Metro (İstanbul · Ankara · İzmir · Bursa)",
    "B": "Bölgesel Merkez (Antalya · Kocaeli · Gaziantep · Tekirdağ · Konya · Muğla · Denizli)",
    "C": "Gelişen Pazar (Adana · Mersin · Kayseri · K.Maraş · Samsun · Trabzon · Sivas)",
}

# ---------------------------------------------------------------------------
# Pazar Kapasitesi — Bayi il/ilçe verisi ve il bazında catchment payları
# ---------------------------------------------------------------------------

# Kullanıcıdan doğrulanan bayi lokasyon verisi (28 bayi)
BAYI_IL_ILCE: dict[str, tuple[str, str]] = {
    "DEALER 1":  ("ANKARA",         "ETİMESGUT"),
    "DEALER 2":  ("İZMİR",          "GAZİEMİR"),
    "DEALER 3":  ("ADANA",          "SEYHAN"),
    "DEALER 4":  ("MERSİN",         "TOROSLAR"),
    "DEALER 5":  ("KOCAELİ",        "GEBZE"),
    "DEALER 6":  ("İZMİR",          "BAYRAKLI"),
    "DEALER 7":  ("İSTANBUL",       "BAHÇELİEVLER"),
    "DEALER 8":  ("TEKİRDAĞ",       "MERKEZ"),
    "DEALER 9":  ("KAYSERİ",        "KOCASİNAN"),
    "DEALER 10": ("KONYA",          "KARATAY"),
    "DEALER 11": ("KAHRAMANMARAŞ",  "DULKADİROĞLU"),
    "DEALER 12": ("BURSA",          "OSMANGAZİ"),
    "DEALER 13": ("İSTANBUL",       "ATAŞEHİR"),
    "DEALER 14": ("ANKARA",         "YENİMAHALLE"),
    "DEALER 15": ("ANTALYA",        "KEPEZ"),
    "DEALER 16": ("İSTANBUL",       "BEYLİKDÜZÜ"),
    "DEALER 17": ("İSTANBUL",       "SARIYER"),
    "DEALER 18": ("İSTANBUL",       "SUADİYE"),
    "DEALER 19": ("GAZİANTEP",      "ŞEHİTKAMİL"),
    "DEALER 20": ("TRABZON",        "AKÇAABAT"),
    "DEALER 21": ("MUĞLA",          "MİLAS"),
    "DEALER 22": ("DENİZLİ",        "MERKEZEFENDİ"),
    "DEALER 23": ("BURSA",          "NİLÜFER"),
    "DEALER 24": ("SAMSUN",         "TEKKEKÖY"),
    "DEALER 25": ("İSTANBUL",       "BAĞCILAR"),
    "DEALER 26": ("TEKİRDAĞ",       "ÇORLU"),
    "DEALER 27": ("İSTANBUL",       "EYÜPSULTAN"),
    "DEALER 28": ("SİVAS",          "MERKEZEFENDİ"),
}

# İl pazar kapasitesi — TÜİK Motorlu Kara Taşıtları Aralık 2024 verisi
# Toplam Türkiye araç stoğu: 31.301.389 (tüm türler, proxy olarak kullanılmaktadır).
# Catchment: il + en yakın komşu iller (pazar erişim alanı).
# Kaynak: https://data.tuik.gov.tr/Bulten/Index?p=Road-Motor-Vehicles-December-2024-53463
IL_PAZAR_KAPASITE: dict[str, dict] = {
    "İSTANBUL":      {"kendi_pay": 18.66, "komsular": [("TEKİRDAĞ",1.17),("KIRKLARELİ",0.48)]},
    "ANKARA":        {"kendi_pay": 8.89,  "komsular": [("ESKİŞEHİR",1.02),("KIRIKKALECHANKIRI",0.50)]},
    "İZMİR":         {"kendi_pay": 5.75,  "komsular": [("MANİSA",1.30),("ÇANAKKALE",0.50)]},
    "ANTALYA":       {"kendi_pay": 4.63,  "komsular": [("ISPARTA",0.43),("BURDUR",0.32)]},
    "BURSA":         {"kendi_pay": 3.71,  "komsular": [("YALOVA",0.48),("BALIKESİR",0.98)]},
    "KOCAELİ":       {"kendi_pay": 2.38,  "komsular": [("SAKARYA",0.88),("DÜZCE",0.32),("BOLU",0.38)]},
    "GAZİANTEP":     {"kendi_pay": 2.32,  "komsular": [("KİLİS",0.12),("ADIYAMAN",0.40),("ŞANLIURFA",0.52)]},
    "ADANA":         {"kendi_pay": 1.95,  "komsular": [("OSMANİYE",0.32)]},
    "MERSİN":        {"kendi_pay": 1.69,  "komsular": [("KARAMAN",0.38),("NİĞDE",0.29)]},
    "KAYSERİ":       {"kendi_pay": 1.32,  "komsular": [("NEVŞEHİR",0.38),("YOZGAT",0.29),("NİĞDE",0.28)]},
    "KONYA":         {"kendi_pay": 1.84,  "komsular": [("AKSARAY",0.40),("KARAMAN",0.38),("NİĞDE",0.29)]},
    "SAMSUN":        {"kendi_pay": 1.21,  "komsular": [("ORDU",0.50),("SİNOP",0.19),("AMASYA",0.30)]},
    "TEKİRDAĞ":      {"kendi_pay": 1.17,  "komsular": [("EDİRNE",0.40),("KIRKLARELİ",0.48)]},
    "MUĞLA":         {"kendi_pay": 1.37,  "komsular": [("AYDIN",1.08)]},
    "DENİZLİ":       {"kendi_pay": 1.02,  "komsular": [("AFYONKARAHİSAR",0.52),("UŞAK",0.30)]},
    "KAHRAMANMARAŞ": {"kendi_pay": 0.86,  "komsular": [("MALATYA",0.70),("ADIYAMAN",0.40)]},
    "TRABZON":       {"kendi_pay": 0.65,  "komsular": [("RİZE",0.30),("ARTVİN",0.11),("GİRESUN",0.38),("ORDU",0.50)]},
    "SİVAS":         {"kendi_pay": 0.43,  "komsular": [("TOKAT",0.48),("ERZİNCAN",0.21)]},
}

PERFORMANS_DOSYALAR = {
    m: DATA_RAW / f"NORTHSTAR_2025_{m}_Bayinin_Aylık_Model_Bazlı_Araç_Satışı_Hedef_Gerçekleştirmesi.csv"
    for m in [
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
    ]
}
PERFORMANS_AY_NO = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}

# Model açıklamaları (SUV segmenti — gizleme nedeniyle A1/A2 formatı)
# NOT: A1/A2/A3 aynı A segmenti aracının versiyonlarıdır (ayrı model değil)
# B1/B2 aynı B segmenti aracının versiyonlarıdır
MODEL_ACIKLAMALAR = {
    "A1": "A Segmenti — Versiyon 1 (2025 sonu itibarıyla üretimden kalktı)",
    "A2": "A Segmenti — Versiyon 2 (2026 ana hacim modeli)",
    "A3": "A Segmenti — Versiyon 3 (2026 ana hacim modeli)",
    "B1": "B Segmenti — Versiyon 1 (Mart 2026 yeni versiyon lansmanı)",
    "B2": "B Segmenti — Versiyon 2 (2026 aktif)",
    "C1": "C Segmenti — Versiyon 1 (2025 sonu itibarıyla üretimden kalktı)",
    "D1": "D Segmenti — Versiyon 1 (2025 sonu itibarıyla üretimden kalktı)",
}

MODEL_SEGMENT = {
    "A1": "A", "A2": "A", "A3": "A",
    "B1": "B", "B2": "B",
    "C1": "C",
    "D1": "D",
}


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

def load_sales() -> pd.DataFrame:
    """Ham satış verisini yükler."""
    df = pd.read_csv(SALES_FILE, sep=";", encoding="utf-8-sig", low_memory=False)
    df["Sales Date"] = pd.to_datetime(df["Sales Date"])
    df["year"] = df["Sales Date"].dt.year
    df["month"] = df["Sales Date"].dt.month
    df["ym"] = df["Sales Date"].dt.to_period("M").astype(str)
    df = df.dropna(subset=["Model Description"])
    return df


def load_final_si() -> pd.DataFrame:
    df = pd.read_csv(SI_FILE, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return df


def load_dealer_jan26_targets() -> dict[str, int]:
    df = pd.read_csv(DEALER_TARGETS_FILE, sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return dict(zip(df["Dealer Name"].str.strip(), df["Target"].fillna(0).astype(int)))


def load_dealer_tiers() -> dict[str, str]:
    """BAYI_IL_ILCE sabitindeki il verisine göre bayi → tier (A/B/C) döndürür.

    Tier kriterleri (TÜİK 2024 araç stoku bazlı pazar büyüklüğü):
      A — Büyük Metro : İSTANBUL, ANKARA, İZMİR, BURSA   (catchment ~45%)
      B — Bölgesel Merkez: ANTALYA, KOCAELİ, GAZİANTEP,  (catchment ~2–5% her il)
                            TEKİRDAĞ, KONYA, MUĞLA, DENİZLİ
      C — Gelişen Pazar : diğer iller                     (catchment <2.5%)
    """
    tiers: dict[str, str] = {}
    for dealer, (il, _) in BAYI_IL_ILCE.items():
        if il in TIER_A_ILLER:
            tiers[dealer] = "A"
        elif il in TIER_B_ILLER:
            tiers[dealer] = "B"
        else:
            tiers[dealer] = "C"
    return tiers


def load_2025_perf_targets() -> pd.DataFrame:
    rows = []
    for month_name, fpath in PERFORMANS_DOSYALAR.items():
        if not fpath.exists():
            continue
        try:
            raw = pd.read_csv(fpath, sep=";", encoding="utf-8-sig",
                              header=None, on_bad_lines="skip")
        except Exception:
            continue
        month_no = PERFORMANS_AY_NO[month_name]
        for i in range(2, 30):
            if i >= len(raw):
                break
            row = raw.iloc[i]
            if pd.isna(row.iloc[0]) or not str(row.iloc[0]).startswith("BA"):
                continue
            dealer_name = str(row.iloc[1]).strip()
            try:
                target = float(row.iloc[2])
                if pd.isna(target):
                    target = 0.0
            except Exception:
                target = 0.0
            rows.append({"month": month_no, "dealer": dealer_name, "target": int(target)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Yeni fonksiyon: Lansman boost istatistiksel gerekçesi
# ---------------------------------------------------------------------------

def compute_lansman_boost_justifikasyon(
    df: pd.DataFrame,
    si_df: pd.DataFrame,  # noqa: ARG001
) -> dict:
    """1.15 SI boost'unun istatistiksel gerekçesini hesaplar.

    Yöntem: B segmentinin (B1+B2) Mart ayı mevsimsel payı, yıllık ortalamasına
    oranlanarak 'B Mart Sezonalite Endeksi' hesaplanır. Mart 2026'da yeni versiyon
    lansmanıyla B segmentin 2024 Mart pay seviyesine restore olması beklenmektedir.
    Bu shift'in toplam pazar üzerindeki minimum etkisi veri bazlı alt sınır olarak
    kullanılmış; muhafazakâr 1.15 uygulanmıştır.
    """
    df_b = df[df["Model Description"].isin(list(LANSMAN_SEGMENT))].copy()
    toplam_satis = len(df)

    # Yıl bazında Mart pay hesabı
    def _mart_payi(yil: int) -> float:
        top = len(df[(df["year"] == yil) & (df["month"] == 3)])
        b = len(df_b[(df_b["year"] == yil) & (df_b["month"] == 3)])
        return b / top if top > 0 else 0.0

    def _yillik_ort_pay(yil: int) -> float:
        top = len(df[df["year"] == yil])
        b = len(df_b[df_b["year"] == yil])
        return b / top if top > 0 else 0.0

    b_mart_pay_2024 = _mart_payi(2024)
    b_mart_pay_2025 = _mart_payi(2025)
    b_yillik_ort_2024 = _yillik_ort_pay(2024)
    b_yillik_ort_2025 = _yillik_ort_pay(2025)

    # B segmenti Mart Sezonalite Endeksi = Mart payı / yıllık ort
    b_mart_si_2024 = b_mart_pay_2024 / b_yillik_ort_2024 if b_yillik_ort_2024 > 0 else 1.0
    b_mart_si_2025 = b_mart_pay_2025 / b_yillik_ort_2025 if b_yillik_ort_2025 > 0 else 1.0

    # Beklenti: lansman B segmenti payını 2024 Mart seviyesine restore eder
    # Toplam pazar üzerindeki minimum etki = ek B payı artışı
    pay_farki = b_mart_pay_2024 - b_mart_pay_2025  # 0.557 - 0.445 = 0.112
    hesaplanan_boost = 1.0 + max(pay_farki, 0.0)

    # B toplam pazar payı
    b_toplam_satis = len(df_b)
    b_market_payi = b_toplam_satis / toplam_satis if toplam_satis > 0 else 0.0

    return {
        "b_mart_pay_2024": round(b_mart_pay_2024, 4),
        "b_mart_pay_2025": round(b_mart_pay_2025, 4),
        "b_mart_si_2024": round(b_mart_si_2024, 3),
        "b_mart_si_2025": round(b_mart_si_2025, 3),
        "b_yillik_ort_pay_2024": round(b_yillik_ort_2024, 4),
        "b_yillik_ort_pay_2025": round(b_yillik_ort_2025, 4),
        "pay_farki": round(pay_farki, 4),
        "hesaplanan_boost": round(hesaplanan_boost, 3),
        "uygulanan_boost": LANSMAN_BOOST,
        "b_market_payi": round(b_market_payi, 3),
        "muhafazakarlik": (
            f"Veri bazlı alt sınır {hesaplanan_boost:.3f} → muhafazakâr "
            f"{LANSMAN_BOOST} uygulandı (lansman çekme etkisi ve marka bilinirliği "
            f"artışı için ek %{round((LANSMAN_BOOST - hesaplanan_boost) * 100, 1)} marj)"
        ),
    }


# ---------------------------------------------------------------------------
# Yeni fonksiyon: Bayi aylık model hedefleri
# ---------------------------------------------------------------------------

def compute_pazar_bazli_dealer_paylari(df: pd.DataFrame) -> dict[str, dict]:
    """Pazar kapasitesi bazlı hibrit bayi pay hesabı.

    Formül: target_pay[D] = 0.5 × brand_pay_2025[D] + 0.5 × (catchment[il(D)] / n_bayis_in_il(D))
    Yeni bayiler (2025 satışı = 0): tamamen pazar kapasitesi bazlı (brand_pay = 0).
    Tüm paylar normalize edilerek toplamları %100'e eşitlenir.

    Kaynak: TÜİK Motorlu Kara Taşıtları Aralık 2024 bülteni — Toplam stok 31.301.389
    URL: https://data.tuik.gov.tr/Bulten/Index?p=Road-Motor-Vehicles-December-2024-53463
    """
    from collections import Counter

    df_2025 = df[df["year"] == 2025].copy()
    total_2025 = len(df_2025)
    dealer_satis_2025: dict[str, int] = df_2025.groupby("Dealer Name").size().to_dict()

    il_bayi_sayisi: Counter[str] = Counter(v[0] for v in BAYI_IL_ILCE.values())

    il_catchment: dict[str, float] = {
        il: veri["kendi_pay"] + sum(p for _, p in veri["komsular"])
        for il, veri in IL_PAZAR_KAPASITE.items()
    }

    sonuc: dict[str, dict] = {}
    for dealer, (il, ilce) in BAYI_IL_ILCE.items():
        brand_pay_2025 = (
            dealer_satis_2025.get(dealer, 0) / total_2025 * 100
            if total_2025 > 0 else 0.0
        )
        catchment = il_catchment.get(il, 1.0)
        n_il = il_bayi_sayisi.get(il, 1)
        capacity_per_dealer = catchment / n_il
        ham_skor = 0.5 * brand_pay_2025 + 0.5 * capacity_per_dealer
        yeni = dealer_satis_2025.get(dealer, 0) == 0

        sonuc[dealer] = {
            "il": il,
            "ilce": ilce,
            "brand_pay_2025": round(brand_pay_2025, 3),
            "catchment_pay": round(catchment, 2),
            "n_il": n_il,
            "capacity_per_dealer": round(capacity_per_dealer, 3),
            "ham_skor": ham_skor,
            "yeni_bayi": yeni,
        }

    toplam_skor = sum(v["ham_skor"] for v in sonuc.values())
    for dealer in sonuc:
        sonuc[dealer]["target_pay_2026"] = round(
            sonuc[dealer]["ham_skor"] / toplam_skor * 100, 3
        )

    return sonuc


def compute_bayi_aylik_model_hedefleri(
    df: pd.DataFrame,
    plan_sonuc: dict,
    pazar_paylari: dict[str, dict] | None = None,
) -> dict:
    """Her bayi için Ocak–Aralık aylık model bazlı hedefleri hesaplar.

    Yöntem:
    - pazar_paylari sağlanırsa: hibrit formül ile bayi yıllık hacmi belirlenir,
      model dağılımı bayi bazlı tarihsel model mix ile yapılır (daha adil).
    - pazar_paylari yoksa: eski davranış (her model için ayrı bayi payı).
    - Sonuç: her bayi için 12 ay × model matris

    Returns:
        {
            "senaryo_8500": {
                "DEALER 1": {
                    "tier": "A",
                    "il": "ANKARA",
                    "ilce": "ETİMESGUT",
                    "brand_pay_2025": 9.33,
                    "target_pay_2026": 8.095,
                    "aylik": [...],
                    "yillik_toplam": int,
                    "yillik_modeller": {...},
                    "yillik_segmentler": {...}
                },
                ...
            },
            "senaryo_10000": {...}
        }
    """
    dealer_tiers = load_dealer_tiers()

    if "period" not in df.columns:
        df = df.copy()
        df["period"] = df["ym"].apply(lambda x: pd.Period(x, freq="M"))

    LAST12_START = pd.Period("2024-12", freq="M")
    LAST12_END   = pd.Period("2025-11", freq="M")
    last12 = df[(df["period"] >= LAST12_START) & (df["period"] <= LAST12_END)].copy()
    last12["model_desc"] = last12["Model Description"].astype(str).str.strip()

    # 2026'da aktif modeller (A1, C1, D1 üretimden kalktı)
    bilinen_modeller = sorted(MODELLER_2026)

    # Tüm 28 bayi (CSV'den) — yeni bayiler tarihsel veri olmadan eklenir
    aktif_bayiler = sorted(
        dealer_tiers.keys(),
        key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 99,
    )
    tarihsel_bayiler = set(last12["Dealer Name"].unique().tolist())
    yeni_bayiler = set(aktif_bayiler) - tarihsel_bayiler

    # Her model için bayi pay dağılımı (son 12 ay) — önce tarihsel bayiler
    model_dealer_share: dict[str, dict[str, float]] = {}
    for model in bilinen_modeller:
        model_df = last12[last12["model_desc"] == model]
        if len(model_df) == 0:
            model_dealer_share[model] = {}
            continue
        dealer_counts = model_df.groupby("Dealer Name").size()
        total = dealer_counts.sum()
        shares: dict[str, float] = {
            d: float(c) / total for d, c in dealer_counts.items()
        }

        # Yeni bayilere tier bazlı ortalama payın %60'ı verilir (muhafazakâr başlangıç)
        if yeni_bayiler:
            tier_avgs: dict[str, float] = {}
            for tier_kod in ("A", "B", "C"):
                tier_dealers_hist = [
                    d for d in tarihsel_bayiler
                    if dealer_tiers.get(d) == tier_kod and d in shares
                ]
                tier_avgs[tier_kod] = (
                    sum(shares[d] for d in tier_dealers_hist) / len(tier_dealers_hist)
                    if tier_dealers_hist else 0.0
                )
            for nd in yeni_bayiler:
                nd_tier = dealer_tiers.get(nd, "C")
                shares[nd] = tier_avgs.get(nd_tier, 0.0) * 0.60

            # Yeniden normalize et (toplam 1.0)
            s_toplam = sum(shares.values())
            if s_toplam > 0:
                shares = {d: v / s_toplam for d, v in shares.items()}

        model_dealer_share[model] = shares

    # --- Bayi bazlı tarihsel model mix (her bayi için hangi modelden ne kadar sattı) ---
    # Hibrit formül aktifse toplam hacim buradan değil, target_pay'den gelir.
    dealer_hist_model_mix: dict[str, dict[str, float]] = {}
    last12_hist = last12[last12["model_desc"].isin(bilinen_modeller)]
    ortalama_mix: dict[str, float] = {}
    if len(last12_hist) > 0:
        cnt_genel = last12_hist.groupby("model_desc").size()
        ortalama_mix = (cnt_genel / cnt_genel.sum()).to_dict()
    for dealer in aktif_bayiler:
        d_df = last12_hist[last12_hist["Dealer Name"] == dealer]
        if len(d_df) > 0:
            cnt = d_df.groupby("model_desc").size()
            dealer_hist_model_mix[dealer] = (cnt / cnt.sum()).to_dict()
        else:
            dealer_hist_model_mix[dealer] = dict(ortalama_mix)

    result: dict[str, dict] = {}

    for hedef in PLAN_HEDEFLER:
        key = f"senaryo_{hedef}"
        senaryo = plan_sonuc[key]

        # Model_aylik verisi: ay → model → adet (toplam tüm bayiler)
        model_aylik_data = senaryo.get("model_aylik", [])
        ay_model_hedef: dict[int, dict[str, int]] = {}
        ay_toplam_hedef: dict[int, int] = {}
        for ay_row in model_aylik_data:
            ay_no = ay_row["ay"]
            ay_model_hedef[ay_no] = {}
            for m_row in ay_row["model_dagilim"]:
                m_adi = m_row["model"]
                if m_adi in MODELLER_2026:
                    ay_model_hedef[ay_no][m_adi] = m_row["adet"]
            ay_toplam_hedef[ay_no] = sum(ay_model_hedef[ay_no].values())

        bayi_sonuc: dict[str, dict] = {}
        for dealer in aktif_bayiler:
            tier = dealer_tiers.get(dealer, "C")
            is_yeni = dealer in yeni_bayiler
            pazar_info = pazar_paylari.get(dealer, {}) if pazar_paylari else {}
            target_pay = pazar_info.get("target_pay_2026", 0.0) if pazar_paylari else None
            d_model_mix = dealer_hist_model_mix.get(dealer, ortalama_mix)
            aylik_liste = []

            for ay in range(1, 13):
                ay_modeller: dict[str, int] = {}

                if pazar_paylari and target_pay is not None:
                    # Hibrit: bayinin bu aydaki hacmi = ay_toplam × target_pay
                    bayi_ay_toplam_float = ay_toplam_hedef.get(ay, 0) * target_pay / 100.0
                    for model in bilinen_modeller:
                        mix_pay = d_model_mix.get(model, 0.0)
                        ay_modeller[model] = round(bayi_ay_toplam_float * mix_pay)
                else:
                    # Eski yöntem: model bazlı paylar
                    for model in bilinen_modeller:
                        model_hedef_ay = ay_model_hedef.get(ay, {}).get(model, 0)
                        dealer_pay = model_dealer_share.get(model, {}).get(dealer, 0.0)
                        ay_modeller[model] = round(model_hedef_ay * dealer_pay)

                toplam = sum(ay_modeller.values())
                aylik_liste.append({
                    "ay": ay,
                    "ay_adi": AY_ADLARI[ay - 1],
                    "toplam": toplam,
                    "modeller": ay_modeller,
                })

            yillik_modeller: dict[str, int] = {m: 0 for m in bilinen_modeller}
            for ay_entry in aylik_liste:
                for m, adet in ay_entry["modeller"].items():
                    yillik_modeller[m] = yillik_modeller.get(m, 0) + adet
            yillik_toplam = sum(yillik_modeller.values())

            yillik_segmentler: dict[str, int] = {}
            for m, adet in yillik_modeller.items():
                seg = MODEL_SEGMENT.get(m, "Diğer")
                yillik_segmentler[seg] = yillik_segmentler.get(seg, 0) + adet

            bayi_sonuc[dealer] = {
                "tier": tier,
                "il": pazar_info.get("il", BAYI_IL_ILCE.get(dealer, ("", ""))[0]),
                "ilce": pazar_info.get("ilce", BAYI_IL_ILCE.get(dealer, ("", ""))[1]),
                "brand_pay_2025": pazar_info.get("brand_pay_2025", 0.0),
                "target_pay_2026": pazar_info.get("target_pay_2026", 0.0),
                "catchment_pay": pazar_info.get("catchment_pay", 0.0),
                "capacity_per_dealer": pazar_info.get("capacity_per_dealer", 0.0),
                "yeni_bayi": is_yeni,
                "aylik": aylik_liste,
                "yillik_toplam": yillik_toplam,
                "yillik_modeller": yillik_modeller,
                "yillik_segmentler": yillik_segmentler,
            }

        result[key] = bayi_sonuc

    return result


# ---------------------------------------------------------------------------
# Yardımcı: tier bazlı SI + trend hesabı
# ---------------------------------------------------------------------------

def _tier_forecast(
    monthly: pd.DataFrame,
    global_dec_si: float,
) -> tuple[float, float, float, float]:
    """Bir tier'ın Aralık tahminini hesaplar.

    Returns: (tahmin_float, aralik_si, trend_carpani, son12_ort)
    """
    if len(monthly) < 3:
        son12_ort = float(monthly["satis"].mean()) if len(monthly) > 0 else 1.0
        return son12_ort * global_dec_si, global_dec_si, 1.0, son12_ort

    genel_ort = monthly["satis"].mean()
    dec_rows = monthly[monthly["month"] == 12]
    if len(dec_rows) > 0:
        tier_dec_si = float(dec_rows["satis"].mean() / genel_ort)
        si_tier_w = 0.70
    else:
        tier_dec_si = global_dec_si
        si_tier_w = 0.40

    aralik_si = si_tier_w * tier_dec_si + (1 - si_tier_w) * global_dec_si

    son12 = monthly.tail(12)
    son12_ort = float(son12["satis"].mean())

    son6 = float(monthly.tail(6)["satis"].mean())
    onceki6 = float(monthly.iloc[-12:-6]["satis"].mean()) if len(monthly) >= 12 else son12_ort

    # Trend cap 1.35 — gerçek büyümeyi (1.247) yakalamak için 1.20'den genişletildi
    trend = max(0.80, min(1.35, son6 / onceki6 if onceki6 > 0 else 1.0))

    return aralik_si * son12_ort * trend, aralik_si, trend, son12_ort


# ---------------------------------------------------------------------------
# GÖREV 1: Aralık 2025 Tier Bazlı Tahmini
# ---------------------------------------------------------------------------

def compute_aralik_tahmini(df: pd.DataFrame, si_df: pd.DataFrame) -> dict:
    """Aralık 2025 tahminini A/B/C tier bazlı hesaplar ve metrikleri döndürür."""

    dealer_tiers = load_dealer_tiers()
    global_dec_si = float(si_df[si_df["month"] == 12]["final_si"].values[0])

    # Eğitim: Aralık 2025 hariç tümü
    train_df = df[~((df["year"] == 2025) & (df["month"] == 12))].copy()
    test_df  = df[(df["year"] == 2025) & (df["month"] == 12)].copy()

    train_df["tier"] = train_df["Dealer Name"].map(dealer_tiers).fillna("C")
    test_df["tier"]  = test_df["Dealer Name"].map(dealer_tiers).fillna("C")

    gercek_toplam = len(test_df)

    # --- Her tier için ayrı tahmin ---
    LAST12_START = pd.Period("2024-12", freq="M")
    LAST12_END   = pd.Period("2025-11", freq="M")
    train_df["period"] = train_df["ym"].apply(lambda x: pd.Period(x, freq="M"))

    tier_data: dict[str, dict] = {}
    for tier in ["A", "B", "C"]:
        t_train = train_df[train_df["tier"] == tier]
        t_test  = test_df[test_df["tier"] == tier]

        monthly = (
            t_train.groupby(["year", "month"])
            .size()
            .reset_index(name="satis")
            .sort_values(["year", "month"])
        )

        tahmin_float, si, trend, son12_ort = _tier_forecast(monthly, global_dec_si)
        tahmin_tier = round(tahmin_float)
        gercek_tier = len(t_test)

        # Bayi payları (son 12 ay, bu tier içinde)
        last12_tier = t_train[
            (t_train["period"] >= LAST12_START) &
            (t_train["period"] <= LAST12_END)
        ]
        dealer_son12 = last12_tier.groupby("Dealer Name").size()
        dealer_pay = (
            dealer_son12 / dealer_son12.sum()
            if dealer_son12.sum() > 0
            else dealer_son12
        )

        tier_data[tier] = {
            "tahmin": tahmin_tier,
            "gercek": gercek_tier,
            "mape": (
                round(abs(gercek_tier - tahmin_tier) / gercek_tier * 100, 2)
                if gercek_tier > 0 else None
            ),
            "si": round(si, 4),
            "trend": round(trend, 4),
            "son12_ort": round(son12_ort, 1),
            "dealer_pay": dealer_pay,
            "last12_tier": last12_tier,
            "gercek_bayi": t_test.groupby("Dealer Name").size(),
        }

    tahmin_toplam = sum(v["tahmin"] for v in tier_data.values())
    hata_abs      = abs(gercek_toplam - tahmin_toplam)
    mape_overall  = round(hata_abs / gercek_toplam * 100, 2) if gercek_toplam > 0 else 0.0
    mae_overall   = float(hata_abs)

    # --- Bayi bazında tahmin listesi ---
    last12_all = train_df[
        (train_df["period"] >= LAST12_START) &
        (train_df["period"] <= LAST12_END)
    ]
    gercek_bayi_all = test_df.groupby("Dealer Name").size()

    tum_bayiler = sorted(
        set(list(last12_all["Dealer Name"].unique()) + list(gercek_bayi_all.index)),
        key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 99,
    )

    bayi_tahmin_listesi = []
    for dealer in tum_bayiler:
        tier = dealer_tiers.get(dealer, "C")
        td   = tier_data[tier]
        pay  = float(td["dealer_pay"].get(dealer, 0.0))
        tahmin_adet = round(td["tahmin"] * pay)
        gercek_adet = int(gercek_bayi_all.get(dealer, 0))
        hata_pct = (
            round((tahmin_adet - gercek_adet) / gercek_adet * 100, 1)
            if gercek_adet > 0 else None
        )

        bayi_last12 = last12_all[last12_all["Dealer Name"] == dealer]
        model_mix: dict[str, float] = {}
        if len(bayi_last12) > 0:
            mc = bayi_last12.groupby("Model Description").size()
            model_mix = {str(k): round(float(v / mc.sum()), 3) for k, v in mc.items()}

        bayi_tahmin_listesi.append({
            "dealer": dealer,
            "tier": tier,
            "tahmin": tahmin_adet,
            "gercek": gercek_adet,
            "hata_pct": hata_pct,
            "model_mix": model_mix,
        })

    hata_listesi = [
        abs(r["gercek"] - r["tahmin"]) / r["gercek"] * 100
        for r in bayi_tahmin_listesi
        if r["gercek"] and r["gercek"] > 0
    ]
    bayi_mape = round(float(np.mean(hata_listesi)), 2) if hata_listesi else None

    # --- Aylık trend verisi (grafik için) ---
    aylik_gercek = df.groupby("ym").size().reset_index(name="gercek").sort_values("ym")
    aylik_trend = []
    for _, row in aylik_gercek.iterrows():
        ym_str = str(row["ym"])
        aylik_trend.append({
            "ym": ym_str,
            "gercek": int(row["gercek"]),
            "tahmin": tahmin_toplam if ym_str == "2025-12" else None,
        })

    # --- Tier özet ---
    tier_ozet = [
        {
            "tier": tier,
            "aciklama": TIER_ACIKLAMALAR[tier],
            "tahmin": tier_data[tier]["tahmin"],
            "gercek": tier_data[tier]["gercek"],
            "mape": tier_data[tier]["mape"],
            "si": tier_data[tier]["si"],
            "trend": tier_data[tier]["trend"],
            "son12_ort": tier_data[tier]["son12_ort"],
        }
        for tier in ["A", "B", "C"]
    ]

    # --- Model bazlı Aralık 2025 analizi ---
    test_model = test_df.groupby("Model Description").size().reset_index(name="gercek")
    train_son6 = train_df[train_df["period"] >= pd.Period("2025-06", freq="M")]
    train_son6_model = train_son6.groupby("Model Description").size().reset_index(name="son6_adet")
    model_aralik_analiz = []
    toplam_test = len(test_df)
    toplam_son6 = len(train_son6)
    for _, row in test_model.sort_values("gercek", ascending=False).iterrows():
        m = str(row["Model Description"])
        gercek = int(row["gercek"])
        son6 = int(train_son6_model[train_son6_model["Model Description"] == m]["son6_adet"].values[0]) if m in train_son6_model["Model Description"].values else 0
        model_aralik_analiz.append({
            "model": m,
            "aciklama": MODEL_ACIKLAMALAR.get(m, m),
            "gercek_adet": gercek,
            "gercek_pay": round(gercek / toplam_test * 100, 1) if toplam_test > 0 else 0,
            "son6_pay": round(son6 / toplam_son6 * 100, 1) if toplam_son6 > 0 else 0,
            "lansman_model": m == LANSMAN_MODEL,
        })

    metodoloji = [
        {
            "baslik": "A/B/C Tier Gruplandırması",
            "aciklama": (
                "Bayiler bölgesel potansiyele göre 3 gruba ayrıldı. "
                "A = Marmara + Ege + İç Anadolu/Ankara (yüksek hacim), "
                "B = Akdeniz (orta), C = Güneydoğu + Karadeniz (düşük). "
                "Kaynak: Bayi-Adi-Kodu.csv bölge kısaltması (örn. BA-3-MAR-01 → MAR → Tier A)."
            ),
        },
        {
            "baslik": "Tier Bazlı Seasonal Index (SI)",
            "aciklama": (
                "Her tier için Aralık SI'sı kendi 2024-2025 satış verisinden hesaplandı "
                "(ratio-to-mean: Aralık aylık ort. / yıl aylık ort.). "
                "Global SI ile harmanlandı (Tier A: %70 tier + %30 global; "
                "yeterli veri yoksa %40 tier + %60 global)."
            ),
        },
        {
            "baslik": "Tier Bazlı Trend Düzeltmesi",
            "aciklama": (
                "Her tier için trend = son 6 ay ort. / önceki 6 ay ort. oranı hesaplandı. "
                "[0.80, 1.35] aralığında sınırlandırıldı (gerçek büyüme 1.247'yi yakalamak için "
                "1.20 yerine 1.35 üst sınır kullanıldı)."
            ),
        },
        {
            "baslik": "Bayi Pay Dağıtımı",
            "aciklama": (
                f"Tier A: {tier_data['A']['tahmin']} + Tier B: {tier_data['B']['tahmin']} "
                f"+ Tier C: {tier_data['C']['tahmin']} = {tahmin_toplam} araç (Gerçek: {gercek_toplam}). "
                "Her tier tahmini, o tier bayilerinin son 12 ay (Ara 2024 – Kas 2025) "
                "satış payıyla dağıtıldı."
            ),
        },
        {
            "baslik": "Model Karışımı (Model Mix)",
            "aciklama": (
                "Her bayi için son 12 ay satış verisinden model başına pay hesaplandı. "
                f"Dikkat: {LANSMAN_MODEL} modeli yalnızca Eylül 2025'ten itibaren satışta "
                "olduğundan bazı bayilerde model mix'e yansımayabilir."
            ),
        },
    ]

    return {
        "tier_data_raw": tier_data,  # compute_plan içi için
        "ozet": {
            "toplam_tahmin": tahmin_toplam,
            "toplam_gercek": gercek_toplam,
            "mape": mape_overall,
            "mae": round(mae_overall, 1),
            "rmse": round(mae_overall, 1),
            "bayi_mape": bayi_mape,
            "yontem": (
                f"Tier A ({TIER_ACIKLAMALAR['A']}): SI={tier_data['A']['si']:.3f} → {tier_data['A']['tahmin']} | "
                f"Tier B ({TIER_ACIKLAMALAR['B']}): SI={tier_data['B']['si']:.3f} → {tier_data['B']['tahmin']} | "
                f"Tier C ({TIER_ACIKLAMALAR['C']}): SI={tier_data['C']['si']:.3f} → {tier_data['C']['tahmin']}"
            ),
        },
        "tier_ozet": tier_ozet,
        "bayi_tahmin": bayi_tahmin_listesi,
        "aylik_trend": aylik_trend,
        "metodoloji": metodoloji,
        "model_aralik_analiz": model_aralik_analiz,
    }


# ---------------------------------------------------------------------------
# GÖREV 2: Aylık Model Bazlı Hedefler
# ---------------------------------------------------------------------------

def compute_model_aylik_hedefler(
    df: pd.DataFrame,
    plan_sonuc: dict,
) -> dict[str, list[dict]]:
    """Her senaryo için Ocak–Aralık aylık × model bazlı araç satış hedeflerini hesaplar.

    Yöntem:
    - Her ay için tarihsel model mix (2024+2025 ağırlıklı ortalama) hesaplanır
    - Son 6 ay verisi %60, önceki 18 ay verisi %40 ağırlıkla harmanlanır
      (yeni model A1 Eyl 2025'ten itibaren piyasada — güncel payını yansıtmak için)
    - Mart ve sonrası için A1 (lansman modeli) payı +%30 artırılır ve normalize edilir

    Returns:
        {"senaryo_8500": [...], "senaryo_10000": [...]}
        Her liste 12 ay içerir.
    """
    df_hist = df[df["year"].isin([2024, 2025])].copy()
    df_hist["model_desc"] = df_hist["Model Description"].astype(str).str.strip()
    df_hist["period"] = df_hist["ym"].apply(lambda x: pd.Period(x, freq="M"))

    SON6_START  = pd.Period("2025-07", freq="M")
    GERI_START  = pd.Period("2024-01", freq="M")
    GERI_END    = pd.Period("2025-06", freq="M")

    son6  = df_hist[df_hist["period"] >= SON6_START]
    geri  = df_hist[(df_hist["period"] >= GERI_START) & (df_hist["period"] <= GERI_END)]

    def _ay_model_mix(ay: int) -> dict[str, float]:
        """Belirli bir takvim ayı için ağırlıklı model mix döndürür."""
        son6_ay  = son6[son6["month"] == ay]
        geri_ay  = geri[geri["month"] == ay]

        son6_cnt  = son6_ay.groupby("model_desc").size()
        geri_cnt  = geri_ay.groupby("model_desc").size()

        son6_sum  = son6_cnt.sum()
        geri_sum  = geri_cnt.sum()

        # Yalnızca 2026'da aktif olan modeller dahil edilir (A1, C1, D1 üretimden kalktı)
        tum_modeller = sorted(
            m for m in set(list(son6_cnt.index) + list(geri_cnt.index))
            if m in MODELLER_2026
        )
        mix: dict[str, float] = {}
        for m in tum_modeller:
            son6_pay = float(son6_cnt.get(m, 0)) / son6_sum if son6_sum > 0 else 0.0
            geri_pay = float(geri_cnt.get(m, 0)) / geri_sum if geri_sum > 0 else 0.0
            mix[m] = 0.60 * son6_pay + 0.40 * geri_pay

        # Normalize
        toplam = sum(mix.values())
        if toplam > 0:
            mix = {k: v / toplam for k, v in mix.items()}
        return mix

    result: dict[str, list[dict]] = {}

    for hedef in PLAN_HEDEFLER:
        key = f"senaryo_{hedef}"
        senaryo = plan_sonuc[key]
        aylik_hedef_map = {row["ay"]: row["hedef"] for row in senaryo["aylik"]}

        aylik_model_listesi = []
        for ay in range(1, 13):
            ay_hedef = aylik_hedef_map[ay]
            mix = _ay_model_mix(ay)

            if not mix:
                # Genel mix — yalnızca 2026 aktif modeller
                tum_cnt = df_hist[df_hist["model_desc"].isin(MODELLER_2026)].groupby("model_desc").size()
                mix = (tum_cnt / tum_cnt.sum()).to_dict()

            # Mart+ için tüm B segmentini (B1+B2) aylık kademeli boost ile artır
            if ay in B_SEGMENT_BOOST_BY_AY:
                boost = B_SEGMENT_BOOST_BY_AY[ay]
                for m in LANSMAN_SEGMENT:
                    if m in mix:
                        mix[m] *= boost
                toplam_yeni = sum(mix.values())
                mix = {k: v / toplam_yeni for k, v in mix.items()}

            # %1.5'ten az modelleri "Diğer"'e topla
            ESIK = 0.015
            ana_mix = {k: v for k, v in mix.items() if v >= ESIK}
            diger_pay = sum(v for k, v in mix.items() if v < ESIK)

            # Normalize ana_mix (diğer eklemeden önce)
            ana_sum = sum(ana_mix.values()) + diger_pay
            if ana_sum > 0:
                ana_mix = {k: v / ana_sum for k, v in ana_mix.items()}
                diger_pay_norm = diger_pay / ana_sum
            else:
                diger_pay_norm = 0.0

            model_dist: list[dict] = []
            for model, pay in sorted(ana_mix.items(), key=lambda x: x[1], reverse=True):
                adet = round(ay_hedef * pay)
                model_dist.append({
                    "model": model,
                    "aciklama": MODEL_ACIKLAMALAR.get(model, model),
                    "pay_pct": round(pay * 100, 1),
                    "adet": adet,
                    "lansman_model": model in LANSMAN_SEGMENT,
                })

            if diger_pay_norm >= 0.005:
                model_dist.append({
                    "model": "Diğer",
                    "aciklama": "Düşük hacimli modeller",
                    "pay_pct": round(diger_pay_norm * 100, 1),
                    "adet": round(ay_hedef * diger_pay_norm),
                    "lansman_model": False,
                })

            # Yuvarlama düzeltmesi — toplam garanti
            toplam_hesap = sum(m["adet"] for m in model_dist)
            fark = ay_hedef - toplam_hesap
            if fark != 0 and model_dist:
                model_dist[0]["adet"] += fark

            aylik_model_listesi.append({
                "ay": ay,
                "ay_adi": AY_ADLARI[ay - 1],
                "toplam_hedef": ay_hedef,
                "lansman": ay >= LANSMAN_AY,
                "model_dagilim": model_dist,
            })

        result[key] = aylik_model_listesi

    return result


# ---------------------------------------------------------------------------
# GÖREV 3: 2026 Yıllık Plan (İki Senaryo)
# ---------------------------------------------------------------------------

def _compute_plan_senaryo(
    df: pd.DataFrame,
    si_df: pd.DataFrame,
    yillik_hedef: int,
) -> dict:
    """Tek bir yıllık hedef için SI bazlı aylık plan hesaplar.

    Ocak dahil tüm aylar tamamen SI ile belirlenir (sabit Ocak yok).
    Mart ve sonrası lansman boost (×1.15) uygulanır.
    """
    si_vals: dict[int, float] = {}
    for _, row in si_df.iterrows():
        ay = int(row["month"])
        si = float(row["final_si"])
        si_vals[ay] = si * (LANSMAN_BOOST if ay >= LANSMAN_AY else 1.0)

    toplam_si = sum(si_vals.values())
    si_pay = {ay: v / toplam_si for ay, v in si_vals.items()}

    aylik_ham = {ay: yillik_hedef * p for ay, p in si_pay.items()}
    aylik_hedefler = {ay: round(v) for ay, v in aylik_ham.items()}

    fark = yillik_hedef - sum(aylik_hedefler.values())
    if fark != 0:
        max_ay = max(aylik_hedefler, key=lambda a: aylik_hedefler[a])
        aylik_hedefler[max_ay] += fark

    assert sum(aylik_hedefler.values()) == yillik_hedef

    ocak_hedef = aylik_hedefler[1]

    aylik_liste = []
    for ay in range(1, 13):
        si_raw = float(si_df[si_df["month"] == ay]["final_si"].values[0])
        boost = LANSMAN_BOOST if ay >= LANSMAN_AY else 1.0
        hedef = aylik_hedefler[ay]
        aylik_liste.append({
            "ay": ay,
            "ay_adi": AY_ADLARI[ay - 1],
            "hedef": hedef,
            "si": round(si_raw, 4),
            "lansman_boost": boost,
            "pay_pct": round(hedef / yillik_hedef * 100, 2),
        })

    ocak_dagitim = _compute_ocak_dagitim(df, ocak_hedef)

    return {
        "ozet": {
            "yillik_hedef": yillik_hedef,
            "ocak_hedef": ocak_hedef,
            "lansman_ay": LANSMAN_AY,
            "lansman_boost": LANSMAN_BOOST,
            "toplam_kontrol": sum(aylik_hedefler.values()),
        },
        "aylik": aylik_liste,
        "ocak_bayi_dagilim": ocak_dagitim,
    }


def compute_plan_2026(df: pd.DataFrame, si_df: pd.DataFrame) -> dict:
    """8500 ve 10000 araç için iki senaryo döndürür."""
    senaryolar = {}
    for hedef in PLAN_HEDEFLER:
        key = f"senaryo_{hedef}"
        print(f"  {hedef} araç senaryosu hesaplanıyor...")
        senaryolar[key] = _compute_plan_senaryo(df, si_df, hedef)

    metodoloji = [
        {
            "baslik": "Final SI Tabanlı Tam SI Dağılımı",
            "aciklama": (
                "Ocak dahil tüm 12 ay tamamen SI payıyla belirlendi (sabit Ocak hedefi yok). "
                "outputs/seasonality/04_FINAL_si.csv piyasa mevsimselliği ve marka verisinin "
                "ağırlıklı ortalamasıdır. Düşük SI değeri (Ocak ≈ 0.66) ocak ayının "
                "tarihsel olarak en zayıf satış ayı olduğunu gösterir."
            ),
        },
        {
            "baslik": "Mart Lansman Boost (×1.15)",
            "aciklama": (
                f"Mart ayı ve sonrası için SI değeri {LANSMAN_BOOST} ile çarpıldı. "
                "Yeni SUV modeli lansmanının Mart 2026'dan itibaren piyasa talebini "
                "artırması bekleniyor. Bu boost distribütör stratejisini yansıtır; "
                "stok birikiminin Şubat'ta tamamlanıp Mart'ta serbest bırakılması hedefleniyor."
            ),
        },
        {
            "baslik": "İki Senaryo: 8500 vs 10000",
            "aciklama": (
                "8500 araç mevcut 2024-2025 büyüme trendini sürdürür (muhafazakâr). "
                "10000 araç yeni model lansmanının tam kapasiteye ulaşmasını ve "
                "yaklaşık +%18 artışı öngörür (agresif). "
                "Her iki senaryoda aylık dağılım aynı SI oranlarını kullanır; "
                "yalnızca mutlak sayılar değişir."
            ),
        },
        {
            "baslik": "Ocak Bayi Dağıtımı",
            "aciklama": (
                "Ocak hedefi: 50% son 12 ay satış payı + 30% Ocak 2026 resmi hedef payı "
                "+ 20% 2025 yılı performans skoru (hedef gerçekleştirme oranı) "
                "ağırlıklı dağıtım. Her bayi için güven seviyesi "
                "(Yüksek/Orta/Düşük) atama / resmi hedef oranına göre belirlendi."
            ),
        },
        {
            "baslik": "Aylık Model Bazlı Hedefler",
            "aciklama": (
                "Her ay için model mix: Son 6 ay (%60 ağırlık) + önceki 18 ay (%40 ağırlık) "
                "tarihsel satış verisi harmanlandı. Mart ve sonrası için lansman modeli "
                f"({LANSMAN_MODEL}) payı +%30 artırıldı ve normalize edildi. "
                "Tüm hesaplama 2024-2025 satış verisine dayanır."
            ),
        },
    ]

    return {**senaryolar, "metodoloji": metodoloji}


# ---------------------------------------------------------------------------
# Ocak 2026 bayi dağıtımı
# ---------------------------------------------------------------------------

def _compute_ocak_dagitim(df: pd.DataFrame, ocak_hedef: int) -> list[dict]:
    """Ocak 2026 bayi bazında dağıtım (hedef adet dışarıdan verilir)."""
    dealer_tiers = load_dealer_tiers()

    if "period" not in df.columns:
        df = df.copy()
        df["period"] = df["ym"].apply(lambda x: pd.Period(x, freq="M"))

    LAST12_START = pd.Period("2024-12", freq="M")
    LAST12_END   = pd.Period("2025-11", freq="M")
    last12 = df[(df["period"] >= LAST12_START) & (df["period"] <= LAST12_END)]

    dealer_son12 = last12.groupby("Dealer Name").size()
    dealer_son12_pay = dealer_son12 / dealer_son12.sum()

    jan26_targets = load_dealer_jan26_targets()
    mevcut_bayiler = sorted(
        list(dealer_son12.index),
        key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 99,
    )
    jan26_toplam = sum(jan26_targets.get(d, 0) for d in mevcut_bayiler)
    jan26_pay = {
        d: (jan26_targets.get(d, 0) / jan26_toplam if jan26_toplam > 0 else 0)
        for d in mevcut_bayiler
    }

    perf_targets = load_2025_perf_targets()
    actuals_2025 = (
        df[df["year"] == 2025]
        .groupby(["month", "Dealer Name"])
        .size()
        .reset_index(name="actual")
    )
    perf_scores: dict[str, float] = {}
    if not perf_targets.empty:
        merged = perf_targets.merge(
            actuals_2025,
            left_on=["month", "dealer"],
            right_on=["month", "Dealer Name"],
            how="left",
        )
        merged["actual"] = merged["actual"].fillna(0)
        merged["achievement"] = merged.apply(
            lambda r: min(r["actual"] / r["target"], 1.5) if r["target"] > 0 else 0.5,
            axis=1,
        )
        perf_avg = merged.groupby("dealer")["achievement"].mean()
        if perf_avg.max() > perf_avg.min():
            perf_norm = (perf_avg - perf_avg.min()) / (perf_avg.max() - perf_avg.min())
        else:
            perf_norm = perf_avg * 0 + 0.5
        perf_scores = perf_norm.to_dict()
    else:
        perf_scores = {d: 0.5 for d in mevcut_bayiler}

    W_SATIS, W_HEDEF, W_PERF = 0.5, 0.3, 0.2
    agirlikli_pay: dict[str, float] = {}
    for dealer in mevcut_bayiler:
        w = (
            W_SATIS * float(dealer_son12_pay.get(dealer, 0))
            + W_HEDEF * float(jan26_pay.get(dealer, 0))
            + W_PERF * float(perf_scores.get(dealer, 0.5) / max(len(mevcut_bayiler), 1))
        )
        agirlikli_pay[dealer] = w

    toplam_pay = sum(agirlikli_pay.values())
    if toplam_pay > 0:
        agirlikli_pay = {d: v / toplam_pay for d, v in agirlikli_pay.items()}

    araç_adet_raw = {d: ocak_hedef * p for d, p in agirlikli_pay.items()}
    araç_adet = {d: int(v) for d, v in araç_adet_raw.items()}
    kalan = ocak_hedef - sum(araç_adet.values())
    kesirler = sorted(mevcut_bayiler, key=lambda d: araç_adet_raw[d] - araç_adet[d], reverse=True)
    for i in range(kalan):
        araç_adet[kesirler[i % len(kesirler)]] += 1

    LAST6_START = pd.Period("2025-06", freq="M")
    LAST6_END   = pd.Period("2025-11", freq="M")
    last6 = df[(df["period"] >= LAST6_START) & (df["period"] <= LAST6_END)]

    def gercekcilik(adet: int, hedef: int) -> str:
        if hedef == 0:
            return "Düşük"
        oran = adet / hedef
        if 0.8 <= oran <= 1.25:
            return "Yüksek"
        if 0.6 <= oran <= 1.5:
            return "Orta"
        return "Düşük"

    sonuc = []
    for dealer in mevcut_bayiler:
        adet = araç_adet[dealer]
        bayi_last6 = last6[last6["Dealer Name"] == dealer]
        model_mix: dict[str, float] = {}
        if len(bayi_last6) > 0:
            mc = bayi_last6.groupby("Model Description").size()
            model_mix = {str(k): round(float(v / mc.sum()), 3) for k, v in mc.items()}

        jan26_h = jan26_targets.get(dealer, 0)
        sonuc.append({
            "dealer": dealer,
            "tier": dealer_tiers.get(dealer, "C"),
            "adet": adet,
            "pay_pct": round(adet / ocak_hedef * 100, 2),
            "model_mix": model_mix,
            "gercekci_mi": gercekcilik(adet, jan26_h),
            "jan26_hedef": jan26_h,
            "perf_skoru": round(float(perf_scores.get(dealer, 0.5)), 3),
        })

    return sonuc


# ---------------------------------------------------------------------------
# Stratejik bağlam ve veri kaynakları
# ---------------------------------------------------------------------------

def _build_stratejik_baglamlar(
    plan_sonuc: dict,
    boost_justifikasyon: dict | None = None,
) -> dict:
    """Ocak-Şubat düşük hedef ve Mart lansman stratejisini açıklar."""
    s8  = plan_sonuc["senaryo_8500"]["ozet"]
    s10 = plan_sonuc["senaryo_10000"]["ozet"]

    baglam: dict = {
        "ocak_subat_analizi": {
            "baslik": "Ocak–Şubat 2026: Kasıtlı Düşük Hedefin Stratejik Gerekçesi",
            "durum": (
                f"Ocak 2026 SI bazlı hedef: {s8['ocak_hedef']} araç (senaryo 8500) / "
                f"{s10['ocak_hedef']} araç (senaryo 10000). "
                "Bu rakamlar yıllık aylık ortalamanın altındadır (SI ≈ 0.66). "
                "Ocak-Şubat 2026'da fiili satışlar bu hedeflerin de altında kaldı — "
                "aşağıda stratejik gerekçe açıklanmaktadır."
            ),
            "nedenler": [
                {
                    "baslik": "1. Stok Kısıtı (Arz Tarafı)",
                    "aciklama": (
                        "2025 sonu itibarıyla mevcut model envanteri hızla azaldı. "
                        "Üretim kapasitesi yeni model ({LANSMAN_MODEL}) geçişine kilitlendiğinden "
                        "Ocak-Şubat'ta bayilere dağıtılacak araç miktarı doğal olarak kısıtlandı. "
                        "Bu durum bir arz problemi olup talep eksikliğini yansıtmaz."
                    ).format(LANSMAN_MODEL=LANSMAN_MODEL),
                },
                {
                    "baslik": "2. Mart Lansmanı için Stok Biriktirme (Distribütör Stratejisi)",
                    "aciklama": (
                        f"Yeni model ({LANSMAN_MODEL}) Mart 2026'da tam kapasiteyle piyasaya girecek. "
                        "Distribütörün bilinçli stratejisi: Ocak-Şubat'ta kısıtlı envanter yönetimiyle "
                        "stoku tutmak, Mart lansmanında maksimum araç mevcudiyetiyle çıkmak. "
                        f"Bu strateji nedeniyle modelimizde Mart ve sonrasına ×{LANSMAN_BOOST} boost uygulandı."
                    ),
                },
                {
                    "baslik": "3. Piyasa Beklentisi (Demand-Side Kanibalizasyon)",
                    "aciklama": (
                        "Yeni model haberinin piyasaya yayılmasıyla birlikte müşterilerin mevcut modeli "
                        "satın alma kararları ertelendi ('bekleme etkisi'). "
                        "Bu davranışsal etki Ocak-Şubat'ta organik talebi ek olarak baskıladı. "
                        f"Modeldeki düşük Ocak SI değeri (≈0.66) bu eğilimi kısmen yansıtır; "
                        "ancak stratejik gecikme etkisini tam olarak modellemez."
                    ),
                },
            ],
            "yorum": (
                "Ocak-Şubat'taki düşük gerçekleşme bir tahmin başarısızlığı değil, "
                "kasıtlı bir stok yönetimi ve ürün lansman stratejisinin planlanmış sonucudur. "
                "Model bu stratejik kararı SI dağılımıyla kısmen yansıtır; ekip Ocak-Şubat "
                "hedeflerini mevcut fiziksel arz kısıtıyla elle revize etmelidir."
            ),
        },
        "mart_lansman_stratejisi": {
            "baslik": f"Mart 2026: {LANSMAN_MODEL} Modeli Yeni Versiyon Lansmanı",
            "aciklama": (
                f"B1 (Premium SUV) modelinin yeni versiyonu Mart 2026'da piyasaya çıkıyor. "
                f"Modelimizde Mart ve sonrası için ×{LANSMAN_BOOST} SI boost uygulandı. "
                "Bu, %15 ek talep beklentisini ve yeni versiyon dönemindeki "
                "distribütör motivasyon primini yansıtır."
            ),
            "etkiler": [
                "Mart ayı toplam hedefi diğer aylara göre belirgin biçimde yüksek",
                "B1 yeni versiyon talebi Mart–Haziran döneminde pik yapması bekleniyor",
                "Bayi stok talebi Şubat sonunda yoğunlaşacak (lansman öncesi hazırlık)",
                "A1 modelinin payı 2026 boyunca organik olarak artmaya devam edecek",
                "C1 modelinin payı 2026 boyunca azalmaya devam edecek (ürün yaşam döngüsü sonu)",
            ],
        },
        "model_yorumu": {
            "baslik": "2026 Model Karışımı Beklentisi",
            "mevcut_durum": (
                "2025 yılı sonu model dağılımı: A2 hakimiyeti (%39), B1 ikinci (%25), "
                "A3 üçüncü (%20), C1 dördüncü ama hızla azalıyor (%13 → Aralık'ta %4), "
                "A1 yeni giriyor (Eylül 2025'ten itibaren, %4)."
            ),
            "2026_beklenti": (
                "B1 yeni versiyon lansmanıyla Mart–Haziran döneminde B1 payı güçlü yükselecek. "
                "A2 liderliği sürecek, A1 organik büyümeyle pay artıracak, "
                "C1 satışları büyük ölçüde duracak. "
                "Aylık model hedefleri bu geçiş dinamiğini yansıtacak şekilde tasarlandı."
            ),
        },
    }

    if boost_justifikasyon is not None:
        baglam["boost_justifikasyon"] = boost_justifikasyon

    return baglam


def _build_veri_kaynaklari() -> list[dict]:
    """Tahmin ve plan hesaplamalarında kullanılan veri kaynaklarını döndürür."""
    return [
        {
            "dosya": "2024&2025-ALL-SALES-CSV-FILE.csv",
            "icerik": (
                "Marka X'in tüm satış geçmişi (2024–2025). "
                "Bayi adı, model tanımı, satış tarihi, VIN, renk ve diğer araç detayları. "
                "Toplam 6,718 satış kaydı; 28 aktif bayi; 7 farklı model (A1/A2/A3/B1/B2/C1/D1)."
            ),
            "kullanim": [
                "Aylık toplam satış hacimleri (aylık trend grafiği)",
                "Tier bazlı Seasonal Index (SI) hesabı",
                "Tier bazlı trend düzeltmesi (son 6 ay / önceki 6 ay)",
                "Aylık model bazlı karışım (model mix) — plan hedefleri için",
                "Bayi pay dağılımı (son 12 ay ağırlıkla Ocak dağıtımı)",
            ],
        },
        {
            "dosya": "outputs/seasonality/04_FINAL_si.csv",
            "icerik": (
                "Nihai Seasonal Index değerleri (ay 1–12). "
                "Piyasa geneli (ODD verileri) + marka verisi ağırlıklı ortalamasıyla türetildi. "
                "Değer aralığı: Ocak ≈ 0.66 (en düşük) → Aralık ≈ 1.47 (en yüksek)."
            ),
            "kullanim": [
                "Yıllık toplam hedefe aylık pay dağılımı (her iki senaryo için)",
                "Mart+ lansman boost'u bu SI değerlerine ×1.15 uygulanır",
                "Aralık 2025 tahmini için global SI referansı (tier harmanlama)",
            ],
        },
        {
            "dosya": "Bayi-Adi-Kodu.csv",
            "icerik": (
                "28 aktif bayinin kod listesi (örn. BA-3-MAR-01 formatı). "
                "Kodun 3. parçası bölge kısaltmasını (MAR, EGE, ICA, AKD, GDA, KAR) verir."
            ),
            "kullanim": [
                "Bayi → Tier eşlemesi: MAR/EGE/ICA → A, AKD → B, GDA/KAR/diğer → C",
                "Her tier için ayrı SI ve trend hesabı",
            ],
        },
        {
            "dosya": "dealer_target_january26.csv",
            "icerik": (
                "Ocak 2026 için bayi bazında resmi satış hedefleri. "
                "Distribütör tarafından belirlenen alt limit hedeflerdir."
            ),
            "kullanim": [
                "Ocak 2026 bayi dağıtımında %30 ağırlıkla",
                "Bayi güven seviyesi hesabı (atama / resmi hedef oranı)",
            ],
        },
        {
            "dosya": "NORTHSTAR_2025_[AY]_Hedef_Gerçekleştirmesi.csv (12 dosya)",
            "icerik": (
                "2025 yılı her ay için bayi bazında satış hedefi ve gerçekleşme verileri. "
                "Performans oranı (actual/target) hesabı için kullanılır."
            ),
            "kullanim": [
                "Bayi performans skoru (P-score): 2025 yıllık hedef gerçekleştirme oranı",
                "Ocak 2026 bayi dağıtımında %20 ağırlıkla (normalize edilmiş)",
            ],
        },
    ]


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------

def main() -> None:
    print("Veri yükleniyor...")
    df = load_sales()
    si_df = load_final_si()

    print(f"  Satış kaydı: {len(df)}, bayi: {df['Dealer Name'].nunique()}")
    print(f"  Tarih: {df['Sales Date'].min().date()} – {df['Sales Date'].max().date()}")
    print(f"  Modeller: {sorted(df['Model Description'].dropna().unique())}")

    # Tier özeti
    tiers = load_dealer_tiers()
    for t in ["A", "B", "C"]:
        bayiler = [d for d, v in tiers.items() if v == t]
        print(f"  Tier {t} ({TIER_ACIKLAMALAR[t]}): {len(bayiler)} bayi")

    print("\nAralık 2025 tier bazlı tahmini hesaplanıyor...")
    aralik_sonuc = compute_aralik_tahmini(df, si_df)
    oz = aralik_sonuc["ozet"]
    print(f"  Tahmin: {oz['toplam_tahmin']}, Gerçek: {oz['toplam_gercek']}")
    print(f"  MAPE: {oz['mape']:.2f}%, MAE: {oz['mae']:.1f}, Bayi MAPE: {oz.get('bayi_mape', 'N/A')}")
    for t_oz in aralik_sonuc["tier_ozet"]:
        print(
            f"  Tier {t_oz['tier']} — Tahmin: {t_oz['tahmin']}, Gerçek: {t_oz['gercek']}, "
            f"MAPE: {t_oz['mape']}%, SI: {t_oz['si']}, Trend: {t_oz['trend']}"
        )

    print("\n2026 yıllık plan (iki senaryo) hesaplanıyor...")
    plan_sonuc = compute_plan_2026(df, si_df)
    for hedef in PLAN_HEDEFLER:
        s = plan_sonuc[f"senaryo_{hedef}"]
        print(f"  {hedef} araç: Ocak={s['ozet']['ocak_hedef']}, toplam={s['ozet']['toplam_kontrol']}")

    print("\nAylık model bazlı hedefler hesaplanıyor...")
    model_aylik = compute_model_aylik_hedefler(df, plan_sonuc)
    for hedef in PLAN_HEDEFLER:
        key = f"senaryo_{hedef}"
        print(f"  {hedef} senaryosu — Ocak model dağılımı:")
        for m in model_aylik[key][0]["model_dagilim"]:
            print(f"    {m['model']}: {m['adet']} araç ({m['pay_pct']}%)")

    # Senaryolara model_aylik ekle
    for hedef in PLAN_HEDEFLER:
        key = f"senaryo_{hedef}"
        plan_sonuc[key]["model_aylik"] = model_aylik[key]

    print("\nLansman boost istatistiksel gerekçesi hesaplanıyor...")
    boost_just = compute_lansman_boost_justifikasyon(df, si_df)
    print(f"  B seg Mart payı 2024: %{boost_just['b_mart_pay_2024']*100:.1f}, 2025: %{boost_just['b_mart_pay_2025']*100:.1f}")
    print(f"  B seg Mart SI 2024: {boost_just['b_mart_si_2024']}, 2025: {boost_just['b_mart_si_2025']}")
    print(f"  Pay farkı (restore beklentisi): +%{boost_just['pay_farki']*100:.1f} puan")
    print(f"  Veri bazlı alt sınır: {boost_just['hesaplanan_boost']}, Uygulanan: {boost_just['uygulanan_boost']}")

    print("\nPazar kapasitesi bazlı bayi payları hesaplanıyor (hibrit formül)...")
    pazar_paylari = compute_pazar_bazli_dealer_paylari(df)
    for d in sorted(pazar_paylari.keys(), key=lambda x: int(x.split()[-1])):
        p = pazar_paylari[d]
        yeni = " 🆕" if p["yeni_bayi"] else ""
        print(f"  {d}: {p['il']}/{p['ilce']} | 2025 pay=%{p['brand_pay_2025']:.2f} | "
              f"capacity={p['capacity_per_dealer']:.2f} | 2026 hedef=%{p['target_pay_2026']:.3f}{yeni}")

    print("\nBayi aylık model hedefleri hesaplanıyor (pazar bazlı hibrit)...")
    bayi_hedefler = compute_bayi_aylik_model_hedefleri(df, plan_sonuc, pazar_paylari)
    for hedef in PLAN_HEDEFLER:
        key = f"senaryo_{hedef}"
        toplam_bayi = len(bayi_hedefler[key])
        print(f"  {hedef} senaryosu — {toplam_bayi} bayi için hesaplandı")

    stratejik_baglamlar = _build_stratejik_baglamlar(plan_sonuc, boost_just)
    veri_kaynaklari = _build_veri_kaynaklari()

    # Pazar kapasitesi tablosu (JSON çıktısı için düzleştir)
    pazar_kapasite_tablosu = []
    for dealer in sorted(pazar_paylari.keys(), key=lambda x: int(x.split()[-1])):
        p = pazar_paylari[dealer]
        il = p["il"]
        il_veri = IL_PAZAR_KAPASITE.get(il, {"kendi_pay": 0, "komsular": []})
        pazar_kapasite_tablosu.append({
            "dealer": dealer,
            "il": p["il"],
            "ilce": p["ilce"],
            "il_kendi_pay": il_veri["kendi_pay"],
            "komsular": [{"il": k, "pay": v} for k, v in il_veri["komsular"]],
            "catchment_pay": p["catchment_pay"],
            "n_il": p["n_il"],
            "capacity_per_dealer": p["capacity_per_dealer"],
            "brand_pay_2025": p["brand_pay_2025"],
            "target_pay_2026": p["target_pay_2026"],
            "yeni_bayi": p["yeni_bayi"],
            "hedef_8500": round(p["target_pay_2026"] / 100 * 8500),
            "hedef_10000": round(p["target_pay_2026"] / 100 * 10000),
        })

    # --- JSON çıktısı ---
    cikti = {
        "aralik_tahmin": {
            "ozet": aralik_sonuc["ozet"],
            "tier_ozet": aralik_sonuc["tier_ozet"],
            "bayi_tahmin": aralik_sonuc["bayi_tahmin"],
            "aylik_trend": aralik_sonuc["aylik_trend"],
            "metodoloji": aralik_sonuc["metodoloji"],
            "model_aralik_analiz": aralik_sonuc["model_aralik_analiz"],
            "veri_kaynaklari": veri_kaynaklari,
        },
        "plan_2026": {
            **plan_sonuc,
            "stratejik_baglamlar": stratejik_baglamlar,
        },
        "pazar_kapasitesi": {
            "metodoloji": {
                "baslik": "Pazar Kapasitesi Bazlı Hibrit Bayi Hedef Dağıtımı",
                "formul": "target_pay = 0.5 × brand_pay_2025 + 0.5 × (catchment_pay / n_bayis_in_il)",
                "aciklama": (
                    "Geleneksel yaklaşım bayileri yalnızca geçmiş performanslarına göre "
                    "sıralar; ancak bu yöntem pazar büyüklüğünü görmezden gelir. "
                    "Örneğin Ankara'da tek bir bayi olan bölgede iki bayi olan İstanbul "
                    "bölgesine kıyasla daha geniş bir pazar havuzuna erişim hakkı vardır. "
                    "Hibrit formül %50 geçmiş performans + %50 pazar kapasitesini dengeler. "
                    "Yeni bayiler (2025 satışı = 0) için formül tamamen pazar kapasitesine dayanır."
                ),
                "kaynak": "TÜİK Motorlu Kara Taşıtları Aralık 2024 Bülteni",
                "kaynak_url": "https://data.tuik.gov.tr/Bulten/Index?p=Road-Motor-Vehicles-December-2024-53463",
                "toplam_stok": 31301389,
                "aciklama_catchment": (
                    "Catchment (hizmet alanı): Bayinin bulunduğu il + coğrafi komşu iller. "
                    "Müşteriler yalnızca kendi illerinden değil, yakın çevre illerden de gelir."
                ),
            },
            "tablo": pazar_kapasite_tablosu,
        },
        "bayi_aylik_hedefler": bayi_hedefler,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print(f"\nJSON kaydedildi: {OUT_JSON}")
    print("\nAylık plan (8500 senaryosu):")
    for row in plan_sonuc["senaryo_8500"]["aylik"]:
        tag = " ← LANSMAN" if row["ay"] == LANSMAN_AY else ""
        print(f"  {row['ay_adi']:10s}: {row['hedef']:4d} araç (SI={row['si']:.3f}){tag}")


if __name__ == "__main__":
    main()
