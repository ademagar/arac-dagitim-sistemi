"""gen_tahmin.py

Aralık 2025 tahminlemesi ve 2026 yıllık dağıtım planı üretir.
Çıktı: web/public/data/tahmin.json

Metodoloji:
- Seasonal Index (ratio-to-mean) ile marka toplam tahmini
- Bayi payı ile bayi bazlı dağıtım
- Model karışımı ile ürün bazlı dağıtım

Kullanım:
    python scripts/gen_tahmin.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Yol tanımlamaları (repo-relative, cloud uyumlu)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
SEASONALITY_DIR = REPO_ROOT / "outputs" / "seasonality"
OUT_JSON = REPO_ROOT / "web" / "public" / "data" / "tahmin.json"

SALES_FILE = DATA_RAW / "2024&2025-ALL-SALES-CSV-FILE.csv"
SI_FILE = SEASONALITY_DIR / "04_FINAL_si.csv"
DEALER_TARGETS_FILE = DATA_RAW / "dealer_target_january26.csv"
BAYI_HEDEF_FILE = DATA_RAW / "Bayi-Hedefleri.csv"

# ---------------------------------------------------------------------------
# Yardımcı sabitler
# ---------------------------------------------------------------------------
YILLIK_HEDEF_2026 = 8500
OCAK_2026_HEDEF = 250
LANSMAN_AY = 3          # Mart'ta lansman
LANSMAN_BOOST = 1.15    # Lansman çarpanı (Mart ve sonrası)

# Türkçe ay isimleri
AY_ADLARI = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
]

PERFORMANS_DOSYALAR = {
    m: DATA_RAW / f"NORTHSTAR_2025_{m}_Bayinin_Aylık_Model_Bazlı_Araç_Satışı_Hedef_Gerçekleştirmesi.csv"
    for m in [
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
    ]
}
PERFORMANS_AY_NO = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12
}


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

def load_sales() -> pd.DataFrame:
    """Satış verisini yükler, zaman sütunlarını hazırlar."""
    df = pd.read_csv(SALES_FILE, sep=";", encoding="utf-8-sig", low_memory=False)
    df["Sales Date"] = pd.to_datetime(df["Sales Date"])
    df["year"] = df["Sales Date"].dt.year
    df["month"] = df["Sales Date"].dt.month
    df["ym"] = df["Sales Date"].dt.to_period("M").astype(str)
    # Model boş olanları çıkar
    df = df.dropna(subset=["Model Description"])
    return df


def load_final_si() -> pd.DataFrame:
    """04_FINAL_si.csv'yi yükler."""
    df = pd.read_csv(SI_FILE, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return df


def load_dealer_jan26_targets() -> dict[str, int]:
    """Ocak 2026 bayi hedeflerini yükler (dealer_target_january26.csv)."""
    df = pd.read_csv(DEALER_TARGETS_FILE, sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return dict(zip(df["Dealer Name"].str.strip(), df["Target"].fillna(0).astype(int)))


def load_bayi_hedef() -> pd.DataFrame:
    """Bayi-Hedefleri.csv'den toplam yıllık hedef paylarını yükler."""
    df = pd.read_csv(BAYI_HEDEF_FILE, sep=";", encoding="utf-8-sig")
    # İlk sütun bayi adı
    df = df.rename(columns={"Unnamed: 0": "dealer"})
    df = df[df["dealer"].notna() & df["dealer"].str.startswith("DEALER")]
    # Ocak hedefini al (gerçek bayi hedefleri zaten dealer_target_january26.csv'de)
    ocak_col = "OCAK"
    df = df[["dealer", ocak_col]].copy()
    df[ocak_col] = pd.to_numeric(df[ocak_col], errors="coerce").fillna(0)
    return df


def load_2025_perf_targets() -> pd.DataFrame:
    """2025 aylık hedef verilerini performans dosyalarından çeker."""
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
        # Satır 2-24 arasında bayi hedefleri
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
# GÖREV 1a: Aralık 2025 Tahmini
# ---------------------------------------------------------------------------

def compute_aralik_tahmini(df: pd.DataFrame, si_df: pd.DataFrame) -> dict:
    """Aralık 2025 tahminini hesaplar ve metrikleri döndürür."""

    # Eğitim verisi: Ay 1-23 (Ocak 2024 - Kasım 2025)
    train_df = df[~((df["year"] == 2025) & (df["month"] == 12))].copy()
    test_df = df[(df["year"] == 2025) & (df["month"] == 12)].copy()

    # Gerçek Aralık toplamı
    gercek_toplam = len(test_df)

    # --- Marka Toplam Tahmini ---
    # Aylık toplamlar (eğitim seti)
    monthly_total = train_df.groupby(["year", "month"]).size().reset_index(name="satis")
    monthly_total = monthly_total.sort_values(["year", "month"]).reset_index(drop=True)
    # Seasonal Index: Aralık (ay=12) için ratio-to-mean yöntemi
    # SI = Aralık ayları ortalaması / tüm ayların ortalaması
    genel_ortalama = monthly_total["satis"].mean()

    # Sadece Aralık aylarını al (eğitim setinde var mı kontrol et)
    dec_rows = monthly_total[monthly_total["month"] == 12]
    if len(dec_rows) > 0:
        aralik_si_calculated = dec_rows["satis"].mean() / genel_ortalama
    else:
        # final_si'den al
        aralik_si_calculated = float(si_df[si_df["month"] == 12]["final_si"].values[0])

    # Final SI dosyasındaki Aralık SI'sı
    aralik_final_si = float(si_df[si_df["month"] == 12]["final_si"].values[0])

    # Ağırlıklı SI: kendi veri + final_si
    aralik_si = 0.6 * aralik_si_calculated + 0.4 * aralik_final_si

    # Son 12 ay ortalaması (eğitim setinin son 12 ayı)
    son12 = monthly_total.tail(12)
    son12_ortalama = son12["satis"].mean()

    # Küçük trend düzeltmesi: son 6 ay vs önceki 6 ay
    son6 = monthly_total.tail(6)["satis"].mean()
    onceki6 = monthly_total.iloc[-12:-6]["satis"].mean() if len(monthly_total) >= 12 else son12_ortalama
    trend_carpani = son6 / onceki6 if onceki6 > 0 else 1.0
    # Trend çarpanını sınırla (aşırı tepki vermemek için)
    trend_carpani = max(0.85, min(1.20, trend_carpani))

    tahmin_toplam = round(aralik_si * son12_ortalama * trend_carpani)

    # --- Validasyon metrikleri ---
    hata_abs = abs(gercek_toplam - tahmin_toplam)
    mape_overall = (hata_abs / gercek_toplam) * 100
    mae_overall = float(hata_abs)
    rmse_overall = float(hata_abs)  # Tek nokta tahmini için MAE=RMSE=AE

    # --- Bayi Bazında Tahmin ---
    # Son 12 ay bayi satış payları (eğitim setinin son 12 ayı)
    last12_start_period = pd.Period("2024-12", freq="M")
    last12_end_period = pd.Period("2025-11", freq="M")
    train_df["period"] = train_df["ym"].apply(lambda x: pd.Period(x, freq="M"))
    last12_df = train_df[
        (train_df["period"] >= last12_start_period) &
        (train_df["period"] <= last12_end_period)
    ].copy()

    dealer_son12 = last12_df.groupby("Dealer Name").size()
    dealer_pay = dealer_son12 / dealer_son12.sum()

    # Aralık 2025 gerçek bayi bazında
    gercek_bayi = test_df.groupby("Dealer Name").size()

    # Bayi tahminleri
    tum_bayiler = sorted(
        set(list(dealer_pay.index) + list(gercek_bayi.index)),
        key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 99
    )

    bayi_tahmin_listesi = []
    tahmin_bayiler = {}
    for dealer in tum_bayiler:
        pay = float(dealer_pay.get(dealer, 0.0))
        tahmin_adet = round(tahmin_toplam * pay)
        gercek_adet = int(gercek_bayi.get(dealer, 0))
        tahmin_bayiler[dealer] = tahmin_adet

        if gercek_adet > 0:
            hata_pct = round(((tahmin_adet - gercek_adet) / gercek_adet) * 100, 1)
        else:
            hata_pct = None

        # Bayi × model karışımı (son 12 ay)
        bayi_last12 = last12_df[last12_df["Dealer Name"] == dealer]
        model_mix = {}
        if len(bayi_last12) > 0:
            mc = bayi_last12.groupby("Model Description").size()
            mc_pct = (mc / mc.sum()).round(3)
            model_mix = {str(k): float(v) for k, v in mc_pct.items()}

        bayi_tahmin_listesi.append({
            "dealer": dealer,
            "tahmin": tahmin_adet,
            "gercek": gercek_adet,
            "hata_pct": hata_pct,
            "model_mix": model_mix,
        })

    # Bayi bazında MAPE (gerçek > 0 olanlar için)
    hata_listesi = [
        abs(r["gercek"] - r["tahmin"]) / r["gercek"] * 100
        for r in bayi_tahmin_listesi
        if r["gercek"] and r["gercek"] > 0
    ]
    bayi_mape = round(float(np.mean(hata_listesi)), 2) if hata_listesi else None

    # --- Aylık trend verisi ---
    aylik_gercek = (
        df.groupby("ym").size()
        .reset_index(name="gercek")
        .sort_values("ym")
    )
    aylik_trend = []
    for _, row in aylik_gercek.iterrows():
        ym_str = str(row["ym"])
        tahmin_val = tahmin_toplam if ym_str == "2025-12" else None
        aylik_trend.append({
            "ym": ym_str,
            "gercek": int(row["gercek"]) if ym_str != "2025-12" else int(row["gercek"]),
            "tahmin": tahmin_val,
        })

    # Son satırı ayır - Dec 2025'te hem gercek hem tahmin var
    # Trend grafiği için Nov öncesi hepsi gerçek, Dec'te gerçek + tahmin noktası

    metodoloji = [
        {
            "baslik": "Seasonal Index (Ratio-to-Mean)",
            "aciklama": (
                "Eğitim verisinden (Ocak 2024 – Kasım 2025) hesaplanan aylık mevsimsellik indeksi. "
                "Aralık ayının kendi ortalama satışı, genel aylık ortalamaya bölünerek SI elde edilir."
            ),
        },
        {
            "baslik": "Son 12 Ay Ortalaması",
            "aciklama": (
                "Tahmin = SI × son 12 aylık ortalama × trend düzeltmesi. "
                "Trend: son 6 ay / önceki 6 ay oranı (0.85–1.20 arasında sınırlandırıldı)."
            ),
        },
        {
            "baslik": "Bayi Pay Dağıtımı",
            "aciklama": (
                "Her bayinin son 12 aydaki toplam satış payı kullanılarak marka tahmini bayilere dağıtıldı. "
                f"Toplam tahmin = {tahmin_toplam}, gerçek = {gercek_toplam}."
            ),
        },
        {
            "baslik": "Model Karışımı",
            "aciklama": (
                "Her bayi için son 12 aydaki model (A1, A2, A3, B1...) dağılım oranları, "
                "bayi bazındaki tahmini model bazında böldü."
            ),
        },
    ]

    return {
        "aralik_si_hesaplanan": round(aralik_si_calculated, 4),
        "aralik_si_final": round(aralik_final_si, 4),
        "aralik_si_kullanilan": round(aralik_si, 4),
        "trend_carpani": round(trend_carpani, 4),
        "son12_ortalama": round(float(son12_ortalama), 1),
        "ozet": {
            "toplam_tahmin": tahmin_toplam,
            "toplam_gercek": gercek_toplam,
            "mape": round(mape_overall, 2),
            "mae": round(mae_overall, 1),
            "rmse": round(rmse_overall, 1),
            "bayi_mape": bayi_mape,
            "yontem": (
                f"Seasonal Index ({aralik_si:.3f}) × son 12 ay ort. ({son12_ortalama:.0f}) "
                f"× trend ({trend_carpani:.3f}) = {tahmin_toplam}"
            ),
        },
        "bayi_tahmin": bayi_tahmin_listesi,
        "aylik_trend": aylik_trend,
        "metodoloji": metodoloji,
    }


# ---------------------------------------------------------------------------
# GÖREV 1b: 2026 Yıllık Dağıtım Planı
# ---------------------------------------------------------------------------

def compute_plan_2026(df: pd.DataFrame, si_df: pd.DataFrame) -> dict:
    """2026 yıllık aylık dağıtım planını hesaplar."""

    # --- Aylık dağılım: SI bazlı, Mart+ lansman boost ---
    # Lansman öncesi (Ocak-Şubat) ve sonrası (Mart-Aralık) için ayrı SI ölçekleme
    si_vals = {}
    for _, row in si_df.iterrows():
        ay = int(row["month"])
        si = float(row["final_si"])
        boost = LANSMAN_BOOST if ay >= LANSMAN_AY else 1.0
        si_vals[ay] = si * boost

    # SI'ları normalize et (toplam = 12 olacak şekilde değil, pay olarak)
    toplam_si = sum(si_vals.values())
    si_pay = {ay: v / toplam_si for ay, v in si_vals.items()}

    # Her ay hedef = 8500 × pay
    aylik_ham = {ay: YILLIK_HEDEF_2026 * p for ay, p in si_pay.items()}

    # Ocak sabit = 250; Şubat = SI oranıyla; geri kalan aylara 8250 dağıt
    ocak_hedef = OCAK_2026_HEDEF
    subat_hedef = round(ocak_hedef * si_vals[2] / si_vals[1])

    # Mart-Aralık için kalan = 8500 - Ocak - Şubat
    kalan_hedef = YILLIK_HEDEF_2026 - ocak_hedef - subat_hedef
    mart_aralik_si_toplam = sum(si_vals[ay] for ay in range(3, 13))
    aylik_hedefler: dict[int, int] = {1: ocak_hedef, 2: subat_hedef}
    for ay in range(3, 13):
        pay = si_vals[ay] / mart_aralik_si_toplam
        aylik_hedefler[ay] = round(kalan_hedef * pay)

    # Yuvarlama düzeltmesi (toplam = 8500 garantile)
    toplam_simdi = sum(aylik_hedefler.values())
    fark = YILLIK_HEDEF_2026 - toplam_simdi
    # Farkı en büyük aya ekle
    if fark != 0:
        max_ay = max(aylik_hedefler, key=aylik_hedefler.get)
        aylik_hedefler[max_ay] += fark

    # Son kontrol
    assert sum(aylik_hedefler.values()) == YILLIK_HEDEF_2026, \
        f"Toplam hata: {sum(aylik_hedefler.values())} != {YILLIK_HEDEF_2026}"

    # --- Aylık plan listesi ---
    aylik_liste = []
    for ay in range(1, 13):
        hedef = aylik_hedefler[ay]
        si = float(si_df[si_df["month"] == ay]["final_si"].values[0])
        boost = LANSMAN_BOOST if ay >= LANSMAN_AY else 1.0
        pay_pct = round(hedef / YILLIK_HEDEF_2026 * 100, 2)
        aylik_liste.append({
            "ay": ay,
            "ay_adi": AY_ADLARI[ay - 1],
            "hedef": hedef,
            "si": round(si, 4),
            "lansman_boost": boost,
            "pay_pct": pay_pct,
        })

    # --- Ocak 2026 Bayi Dağılımı ---
    # Ağırlık = 0.5 × son 12 ay satış payı + 0.3 × Ocak 2026 hedef payı + 0.2 × performans skoru
    ocak_26_dagitim = compute_ocak_2026_dagitim(df)

    metodoloji = [
        {
            "baslik": "Final SI Tabanlı Aylık Dağılım",
            "aciklama": (
                "outputs/seasonality/04_FINAL_si.csv'deki final_si indeksleri aylık satış paylarını belirler. "
                "Piyasa (ODD) ve marka kendi mevsimselliğinin ağırlıklı ortalamasıdır."
            ),
        },
        {
            "baslik": "Mart Lansman Boost (×1.15)",
            "aciklama": (
                "Mart ayı ve sonrası için SI değeri 1.15 ile çarpılır. "
                "Yeni model lansmanının piyasa talebini artırması beklenmektedir."
            ),
        },
        {
            "baslik": "Sabit Ocak Hedefi",
            "aciklama": (
                f"Ocak 2026 = {OCAK_2026_HEDEF} araç (verildi). Şubat SI oranıyla ölçeklendi. "
                f"Mart–Aralık = kalan {YILLIK_HEDEF_2026 - ocak_hedef - subat_hedef} araç SI ile dağıtıldı."
            ),
        },
        {
            "baslik": "Yuvarlama Garantisi",
            "aciklama": (
                f"12 ay toplamı = {YILLIK_HEDEF_2026} araç. "
                "Yuvarlama hataları en büyük aya eklenerek giderildi."
            ),
        },
    ]

    return {
        "ozet": {
            "yillik_hedef": YILLIK_HEDEF_2026,
            "ocak_hedef": OCAK_2026_HEDEF,
            "lansman_ay": LANSMAN_AY,
            "lansman_boost": LANSMAN_BOOST,
            "toplam_kontrol": sum(aylik_hedefler.values()),
        },
        "aylik": aylik_liste,
        "ocak_bayi_dagilim": ocak_26_dagitim,
        "metodoloji": metodoloji,
    }


def compute_ocak_2026_dagitim(df: pd.DataFrame) -> list[dict]:
    """Ocak 2026 bayi bazında dağıtım hesaplar."""

    # --- Son 12 ay satış payı (Aralık 2024 – Kasım 2025) ---
    last12_start = pd.Period("2024-12", freq="M")
    last12_end = pd.Period("2025-11", freq="M")
    df["period"] = df["ym"].apply(lambda x: pd.Period(x, freq="M"))
    last12 = df[
        (df["period"] >= last12_start) & (df["period"] <= last12_end)
    ]
    dealer_son12 = last12.groupby("Dealer Name").size()
    dealer_son12_pay = dealer_son12 / dealer_son12.sum()

    # --- Ocak 2026 hedef payı (dealer_target_january26.csv) ---
    jan26_targets = load_dealer_jan26_targets()
    # Sadece 22 bayi (mevcut veri olan)
    mevcut_bayiler = sorted(
        list(dealer_son12.index),
        key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 99
    )
    jan26_toplam = sum(jan26_targets.get(d, 0) for d in mevcut_bayiler)
    jan26_pay = {
        d: jan26_targets.get(d, 0) / jan26_toplam if jan26_toplam > 0 else 0
        for d in mevcut_bayiler
    }

    # --- Performans skoru ---
    # 2025 yılı boyunca hedef gerçekleştirme oranı (ortalama)
    perf_targets = load_2025_perf_targets()
    actuals_2025 = (
        df[(df["year"] == 2025)]
        .groupby(["month", "Dealer Name"])
        .size()
        .reset_index(name="actual")
    )

    perf_scores: dict[str, float] = {}
    if not perf_targets.empty:
        merged = perf_targets.merge(
            actuals_2025, left_on=["month", "dealer"], right_on=["month", "Dealer Name"], how="left"
        )
        merged["actual"] = merged["actual"].fillna(0)
        merged["achievement"] = merged.apply(
            lambda r: min(r["actual"] / r["target"], 1.5) if r["target"] > 0 else 0.5,
            axis=1,
        )
        perf_avg = merged.groupby("dealer")["achievement"].mean()
        # Min-max normalize
        if perf_avg.max() > perf_avg.min():
            perf_norm = (perf_avg - perf_avg.min()) / (perf_avg.max() - perf_avg.min())
        else:
            perf_norm = perf_avg * 0 + 0.5
        perf_scores = perf_norm.to_dict()
    else:
        perf_scores = {d: 0.5 for d in mevcut_bayiler}

    # --- Ağırlıklı birleşik pay ---
    W_SATIS = 0.5
    W_HEDEF = 0.3
    W_PERF = 0.2

    agirlikli_pay: dict[str, float] = {}
    for dealer in mevcut_bayiler:
        w = (
            W_SATIS * float(dealer_son12_pay.get(dealer, 0))
            + W_HEDEF * float(jan26_pay.get(dealer, 0))
            + W_PERF * float(perf_scores.get(dealer, 0.5) / len(mevcut_bayiler))
        )
        agirlikli_pay[dealer] = w

    # Normalize
    toplam_pay = sum(agirlikli_pay.values())
    if toplam_pay > 0:
        agirlikli_pay = {d: v / toplam_pay for d, v in agirlikli_pay.items()}

    # Araç sayısı
    araç_adet_raw: dict[str, float] = {
        d: OCAK_2026_HEDEF * p for d, p in agirlikli_pay.items()
    }
    # Integer yuvarlama (toplam = 250)
    araç_adet = {d: int(v) for d, v in araç_adet_raw.items()}
    kalan = OCAK_2026_HEDEF - sum(araç_adet.values())
    # Kalan birimi ondalık kısmı en büyük olanlara ver
    kesirler = sorted(mevcut_bayiler, key=lambda d: araç_adet_raw[d] - araç_adet[d], reverse=True)
    for i in range(kalan):
        araç_adet[kesirler[i % len(kesirler)]] += 1

    assert sum(araç_adet.values()) == OCAK_2026_HEDEF, \
        f"Ocak dağıtım toplam hatası: {sum(araç_adet.values())}"

    # --- Model karışımı (son 6 ay) ---
    last6_start = pd.Period("2025-06", freq="M")
    last6_end = pd.Period("2025-11", freq="M")
    if "period" not in df.columns:
        df["period"] = df["ym"].apply(lambda x: pd.Period(x, freq="M"))
    last6 = df[(df["period"] >= last6_start) & (df["period"] <= last6_end)]

    # Güven seviyesi
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
        pay_pct = round(adet / OCAK_2026_HEDEF * 100, 2)

        # Model karışımı (son 6 ay)
        bayi_last6 = last6[last6["Dealer Name"] == dealer]
        model_mix: dict[str, float] = {}
        if len(bayi_last6) > 0:
            mc = bayi_last6.groupby("Model Description").size()
            mc_pct = (mc / mc.sum()).round(3)
            model_mix = {str(k): float(v) for k, v in mc_pct.items()}

        # Güven seviyesi: Ocak hedefiyle karşılaştır
        jan26_h = jan26_targets.get(dealer, 0)
        gercekci = gercekcilik(adet, jan26_h)

        sonuc.append({
            "dealer": dealer,
            "adet": adet,
            "pay_pct": pay_pct,
            "model_mix": model_mix,
            "gercekci_mi": gercekci,
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

    print(f"  Toplam satış kaydı: {len(df)}")
    print(f"  Tarih aralığı: {df['Sales Date'].min().date()} – {df['Sales Date'].max().date()}")
    print(f"  Bayi sayısı: {df['Dealer Name'].nunique()}")

    print("\nAralık 2025 tahmini hesaplanıyor...")
    aralik_sonuc = compute_aralik_tahmini(df, si_df)
    oz = aralik_sonuc["ozet"]
    print(f"  Tahmin: {oz['toplam_tahmin']}, Gerçek: {oz['toplam_gercek']}")
    print(f"  MAPE: {oz['mape']:.2f}%, MAE: {oz['mae']:.1f}")
    print(f"  Bayi MAPE: {oz.get('bayi_mape', 'N/A')}")

    print("\n2026 yıllık plan hesaplanıyor...")
    plan_sonuc = compute_plan_2026(df, si_df)
    print(f"  Yıllık toplam: {plan_sonuc['ozet']['toplam_kontrol']}")
    print(f"  Ocak bayi dağılımı toplam: {sum(r['adet'] for r in plan_sonuc['ocak_bayi_dagilim'])}")

    # --- JSON oluştur ---
    cikti = {
        "aralik_tahmin": {
            "ozet": aralik_sonuc["ozet"],
            "bayi_tahmin": aralik_sonuc["bayi_tahmin"],
            "aylik_trend": aralik_sonuc["aylik_trend"],
            "metodoloji": aralik_sonuc["metodoloji"],
            "_debug": {
                "aralik_si_hesaplanan": aralik_sonuc["aralik_si_hesaplanan"],
                "aralik_si_final": aralik_sonuc["aralik_si_final"],
                "aralik_si_kullanilan": aralik_sonuc["aralik_si_kullanilan"],
                "trend_carpani": aralik_sonuc["trend_carpani"],
                "son12_ortalama": aralik_sonuc["son12_ortalama"],
            },
        },
        "plan_2026": {
            "ozet": plan_sonuc["ozet"],
            "aylik": plan_sonuc["aylik"],
            "ocak_bayi_dagilim": plan_sonuc["ocak_bayi_dagilim"],
            "metodoloji": plan_sonuc["metodoloji"],
        },
    }

    # Çıktı dizinini oluştur
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print(f"\nJSON kaydedildi: {OUT_JSON}")
    print("\n--- ÖZET ---")
    print(f"Aralik 2025 Tahmini: {oz['toplam_tahmin']} (Gerçek: {oz['toplam_gercek']}, MAPE: {oz['mape']:.2f}%)")
    print(f"2026 Yıllık Plan: {plan_sonuc['ozet']['toplam_kontrol']} araç")
    print("Aylık dağılım:")
    for row in plan_sonuc["aylik"]:
        boost_str = " [LANSMAN]" if row["ay"] == LANSMAN_AY else ""
        print(f"  {row['ay_adi']:10s}: {row['hedef']:4d} araç (SI={row['si']:.3f}{boost_str})")


if __name__ == "__main__":
    main()
