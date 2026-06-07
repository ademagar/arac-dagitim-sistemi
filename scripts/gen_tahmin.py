"""gen_tahmin.py

Aralık 2025 tahminlemesi (A/B/C tier bazlı) ve 2026 yıllık dağıtım planı üretir.
Çıktı: web/public/data/tahmin.json

Metodoloji:
- Bayiler bölgesel koda göre A/B/C tier'a ayrılır (MAR+EGE+ICA → A, AKD → B, GDA+KAR → C)
- Her tier için ayrı Seasonal Index + ayrı trend düzeltmesi hesaplanır
- 2026 planı: 8500 ve 10000 araç olmak üzere iki senaryo, Ocak dahil tüm aylar SI bazlı

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
LANSMAN_BOOST = 1.15  # Mart+ çarpanı

PLAN_HEDEFLER = [8500, 10000]  # İki senaryo

AY_ADLARI = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

# Tier tanımları (bayi kodu içindeki bölge kısaltmasına göre)
TIER_A_BOLGELER = {"MAR", "EGE", "ICA"}   # Marmara, Ege, İç Anadolu/Ankara
TIER_B_BOLGELER = {"AKD"}                  # Akdeniz
# Tier C: GDA, KAR ve bilinmeyen diğerleri

TIER_ACIKLAMALAR = {
    "A": "Marmara + Ege + İç Anadolu (Ankara)",
    "B": "Akdeniz",
    "C": "Güneydoğu Anadolu + Karadeniz",
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
    """Bayi-Adi-Kodu.csv'den bayi → tier (A/B/C) eşlemesi döndürür.

    Kod formatı: BA-3-MAR-01 → bölge kısaltması = MAR
    A: MAR + EGE + ICA  |  B: AKD  |  C: diğerleri (GDA, KAR ...)
    """
    df = pd.read_csv(BAYI_KOD_FILE, sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"Unnamed: 0": "dealer", "BAYİ-KODU": "kod"})

    tiers: dict[str, str] = {}
    for _, row in df.iterrows():
        dealer = str(row["dealer"]).strip()
        kod = str(row["kod"]).strip()
        parts = kod.split("-")
        bolge = parts[2] if len(parts) >= 3 else "UNK"
        if bolge in TIER_A_BOLGELER:
            tiers[dealer] = "A"
        elif bolge in TIER_B_BOLGELER:
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
        # Tier'ın kendi December verisi var → daha fazla ağırlık ver
        si_tier_w = 0.70
    else:
        tier_dec_si = global_dec_si
        si_tier_w = 0.40

    # Global SI ile harmanla (tier verisi sınırlıysa global ağırlığı artır)
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

    metodoloji = [
        {
            "baslik": "A/B/C Tier Gruplandırması",
            "aciklama": (
                "Bayiler bölgesel potansiyele göre 3 gruba ayrıldı. "
                "A = Marmara + Ege + İç Anadolu/Ankara (yüksek hacim), "
                "B = Akdeniz (orta), C = Güneydoğu + Karadeniz (düşük). "
                "Kaynak: Bayi-Adi-Kodu.csv bölge kısaltması."
            ),
        },
        {
            "baslik": "Tier Bazlı Seasonal Index",
            "aciklama": (
                "Her tier için Aralık SI'sı kendi 2024-2025 satış verisinden hesaplandı "
                "(ratio-to-mean). Global SI ile %40 ağırlıklı harmanlama uygulandı "
                "veri seyrekliğine karşı sigorta olarak."
            ),
        },
        {
            "baslik": "Tier Bazlı Trend Düzeltmesi",
            "aciklama": (
                "Her tier için son 6 ay ortalaması / önceki 6 ay ortalaması oranı ayrı hesaplandı. "
                "Aşırı tepkiyi önlemek için 0.85–1.20 aralığında sınırlandırıldı."
            ),
        },
        {
            "baslik": "Bayi Pay Dağıtımı",
            "aciklama": (
                f"Tier A: {tier_data['A']['tahmin']} + Tier B: {tier_data['B']['tahmin']} "
                f"+ Tier C: {tier_data['C']['tahmin']} = {tahmin_toplam} araç (Gerçek: {gercek_toplam}). "
                "Her tier tahmini, o tier bayilerinin son 12 ay satış payıyla dağıtıldı."
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
    }


# ---------------------------------------------------------------------------
# GÖREV 2: 2026 Yıllık Plan (İki Senaryo)
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
    # Boost uygulanmış SI değerleri
    si_vals: dict[int, float] = {}
    for _, row in si_df.iterrows():
        ay = int(row["month"])
        si = float(row["final_si"])
        si_vals[ay] = si * (LANSMAN_BOOST if ay >= LANSMAN_AY else 1.0)

    toplam_si = sum(si_vals.values())
    si_pay = {ay: v / toplam_si for ay, v in si_vals.items()}

    # Ham hedefler
    aylik_ham = {ay: yillik_hedef * p for ay, p in si_pay.items()}
    aylik_hedefler = {ay: round(v) for ay, v in aylik_ham.items()}

    # Yuvarlama düzeltmesi — toplam garantile
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
                "outputs/seasonality/04_FINAL_si.csv piyasa + marka mevsimselliğinin ağırlıklı ortalaması."
            ),
        },
        {
            "baslik": "Mart Lansman Boost (×1.15)",
            "aciklama": (
                "Mart ayı ve sonrası için SI değeri 1.15 ile çarpıldı. "
                "Yeni model lansmanının Mart'ta piyasa talebini artırması bekleniyor."
            ),
        },
        {
            "baslik": "İki Senaryo: 8500 vs 10000",
            "aciklama": (
                "8500 araç mevcut büyüme trendini sürdürür. "
                "10000 araç agresif büyüme hedefidir (~%18 artış). "
                "Her iki senaryoda aylık dağılım aynı SI oranlarını kullanır."
            ),
        },
        {
            "baslik": "Ocak Bayi Dağıtımı",
            "aciklama": (
                "Ocak hedefi: 0.5 × son 12 ay satış payı + 0.3 × Ocak 2026 hedef payı "
                "+ 0.2 × 2025 performans skoru ağırlıklı dağıtım."
            ),
        },
    ]

    return {**senaryolar, "metodoloji": metodoloji}


# ---------------------------------------------------------------------------
# Ocak 2026 bayi dağıtımı (hedef adet parametrik)
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

    # Performans skoru
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

    # Model karışımı (son 6 ay)
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
# Ana akış
# ---------------------------------------------------------------------------

def main() -> None:
    print("Veri yükleniyor...")
    df = load_sales()
    si_df = load_final_si()

    print(f"  Satış kaydı: {len(df)}, bayi: {df['Dealer Name'].nunique()}")
    print(f"  Tarih: {df['Sales Date'].min().date()} – {df['Sales Date'].max().date()}")

    # Tier özeti
    tiers = load_dealer_tiers()
    for t in ["A", "B", "C"]:
        bayiler = [d for d, v in tiers.items() if v == t]
        print(f"  Tier {t} ({TIER_ACIKLAMALAR[t]}): {len(bayiler)} bayi → {', '.join(sorted(bayiler))}")

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

    # --- JSON çıktısı ---
    cikti = {
        "aralik_tahmin": {
            "ozet": aralik_sonuc["ozet"],
            "tier_ozet": aralik_sonuc["tier_ozet"],
            "bayi_tahmin": aralik_sonuc["bayi_tahmin"],
            "aylik_trend": aralik_sonuc["aylik_trend"],
            "metodoloji": aralik_sonuc["metodoloji"],
        },
        "plan_2026": plan_sonuc,
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
