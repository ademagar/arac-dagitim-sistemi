"""Satış analizi çalıştırma scripti.

Kullanım:
    python -m src.analysis.run_analysis

Çıktılar outputs/2024/, outputs/2025/, outputs/all/ klasörlerine kaydedilir.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis.data_loader import (
    load_competitors,
    load_monthly_performance,
    load_sales,
    load_target_achievement,
)
from src.analysis.sales_analysis import (
    channel_breakdown,
    color_ranking,
    dealer_annual_performance,
    dealer_model_matrix,
    dealer_top_model,
    dealer_total_sales,
    dealer_version_matrix,
    generate_text_report,
    model_monthly_heatmap_data,
    model_only_ranking,
    model_version_ranking,
    monthly_model_trend,
    monthly_performance_summary,
    monthly_sales_trend,
    yoy_comparison,
)

OUTPUT_DIR = Path(__file__).parents[2] / "outputs"


def save_csv(df: pd.DataFrame, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"
    df.to_csv(path, index=True, encoding="utf-8-sig")
    print(f"  Kaydedildi: {path.relative_to(Path.cwd())}")


def run_core_analyses(df: pd.DataFrame, folder: Path) -> None:
    """Verilen DataFrame için tüm temel analizleri çalıştırır ve kaydeder."""
    save_csv(model_only_ranking(df),    folder, "01_model_satislari")
    save_csv(model_version_ranking(df), folder, "02_versiyon_satislari")
    save_csv(color_ranking(df),         folder, "03_renk_satislari")
    save_csv(dealer_total_sales(df),    folder, "04_bayi_toplam_satis")
    save_csv(dealer_model_matrix(df),   folder, "05_bayi_model_matrix")
    save_csv(dealer_version_matrix(df), folder, "06_bayi_versiyon_matrix")
    save_csv(dealer_top_model(df),      folder, "07_bayi_top_model")
    save_csv(monthly_sales_trend(df),   folder, "08_aylik_trend")
    save_csv(monthly_model_trend(df),   folder, "09_model_aylik_trend")
    save_csv(channel_breakdown(df),     folder, "10_kanal_dagilimi")


def main() -> None:
    print("\n[1/5] Veriler yükleniyor...")
    df_all = load_sales()
    perf = load_monthly_performance()
    comp = load_competitors()
    print(f"  Ana satış (tümü): {len(df_all):,} kayıt")

    df_2024 = df_all[df_all["year"] == 2024].copy()
    df_2025 = df_all[df_all["year"] == 2025].copy()
    print(f"  2024: {len(df_2024):,} kayıt | 2025: {len(df_2025):,} kayıt")
    print(f"  Aylık performans: {len(perf):,} kayıt" if not perf.empty else "  Aylık performans: yüklenemedi")
    print(f"  Rakip verisi: {comp['brand'].nunique()} marka" if not comp.empty else "  Rakip verisi: yüklenemedi")

    # ------------------------------------------------------------------ 2024
    print("\n[2/5] 2024 analizleri...")
    run_core_analyses(df_2024, OUTPUT_DIR / "2024")
    ta_2024 = load_target_achievement(2024)
    save_csv(ta_2024["wide"], OUTPUT_DIR / "2024", "11_hedef_gerceklestirme_wide")
    save_csv(ta_2024["long"], OUTPUT_DIR / "2024", "12_hedef_gerceklestirme_long")

    # ------------------------------------------------------------------ 2025
    print("\n[3/5] 2025 analizleri...")
    run_core_analyses(df_2025, OUTPUT_DIR / "2025")
    ta_2025 = load_target_achievement(2025)
    save_csv(ta_2025["wide"], OUTPUT_DIR / "2025", "11_hedef_gerceklestirme_wide")
    save_csv(ta_2025["long"], OUTPUT_DIR / "2025", "12_hedef_gerceklestirme_long")

    # ------------------------------------------------------------------ ALL
    print("\n[4/5] Tüm dönem (all) analizleri...")
    folder_all = OUTPUT_DIR / "all"
    run_core_analyses(df_all, folder_all)
    save_csv(yoy_comparison(df_all), folder_all, "11_yillik_karsilastirma")

    if not perf.empty:
        save_csv(monthly_performance_summary(perf),  folder_all, "12_aylik_hedef_performansi")
        save_csv(dealer_annual_performance(perf),    folder_all, "13_bayi_2025_performansi")
        save_csv(model_monthly_heatmap_data(perf),   folder_all, "14_model_ay_heatmap")

    if not comp.empty:
        save_csv(comp, folder_all, "15_rakip_satislar")

    # ------------------------------------------------------------------ Rapor
    print("\n[5/5] Metin raporu oluşturuluyor...")
    report = generate_text_report(df_all, perf, comp if not comp.empty else None)
    report_path = folder_all / "satis_analizi_raporu.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Kaydedildi: {report_path.relative_to(Path.cwd())}")

    print("\n✓ Tamamlandı. Çıktı klasörleri:")
    print(f"   outputs/2024/  ({len(df_2024):,} satış kaydı)")
    print(f"   outputs/2025/  ({len(df_2025):,} satış kaydı)")
    print(f"   outputs/all/   ({len(df_all):,} satış kaydı)")


if __name__ == "__main__":
    main()
