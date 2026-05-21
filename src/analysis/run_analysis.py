"""Satış analizi çalıştırma scripti.

Kullanım:
    python -m src.analysis.run_analysis

Çıktılar:
    outputs/2024/      — CSV analizleri (2024)
    outputs/2025/      — CSV analizleri (2025)
    outputs/all/       — CSV analizleri (tüm dönem)
    outputs/images/2024/  — Görseller (2024)
    outputs/images/2025/  — Görseller (2025)
    outputs/images/all/   — Görseller (tüm dönem)
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
from src.analysis.visualizations import (
    plot_channel_breakdown,
    plot_color_distribution,
    plot_competitor_comparison,
    plot_dealer_model_heatmap,
    plot_dealer_sales,
    plot_model_month_heatmap,
    plot_model_monthly_trend,
    plot_model_sales,
    plot_monthly_trend,
    plot_target_achievement,
    plot_version_sales,
    plot_yoy_monthly,
)

OUTPUT_DIR = Path(__file__).parents[2] / "outputs"


def save_csv(df: pd.DataFrame, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"
    df.to_csv(path, index=True, encoding="utf-8-sig")
    print(f"  Kaydedildi: {path.relative_to(Path.cwd())}")


def run_core_analyses(df: pd.DataFrame, folder: Path) -> None:
    """Verilen DataFrame için tüm temel CSV analizleri."""
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


def run_core_visuals(df: pd.DataFrame, folder: Path, label: str) -> None:
    """Verilen DataFrame için tüm temel görseller."""
    plot_model_sales(df, folder, label)
    plot_version_sales(df, folder, label)
    plot_color_distribution(df, folder, label)
    plot_dealer_sales(df, folder, label)
    plot_monthly_trend(df, folder, label)
    plot_dealer_model_heatmap(df, folder, label)
    plot_channel_breakdown(df, folder, label)


def main() -> None:
    print("\n[1/6] Veriler yükleniyor...")
    df_all = load_sales()
    perf   = load_monthly_performance()
    comp   = load_competitors()
    ta_24  = load_target_achievement(2024)
    ta_25  = load_target_achievement(2025)
    print(f"  Ana satış (tümü): {len(df_all):,} kayıt")

    df_2024 = df_all[df_all["year"] == 2024].copy()
    df_2025 = df_all[df_all["year"] == 2025].copy()
    print(f"  2024: {len(df_2024):,} | 2025: {len(df_2025):,}")

    img_2024 = OUTPUT_DIR / "images" / "2024"
    img_2025 = OUTPUT_DIR / "images" / "2025"
    img_all  = OUTPUT_DIR / "images" / "all"

    # ------------------------------------------------------------------ 2024
    print("\n[2/6] 2024 CSV analizleri...")
    run_core_analyses(df_2024, OUTPUT_DIR / "2024")
    save_csv(ta_24["wide"], OUTPUT_DIR / "2024", "11_hedef_gerceklestirme_wide")
    save_csv(ta_24["long"], OUTPUT_DIR / "2024", "12_hedef_gerceklestirme_long")

    print("\n[3/6] 2024 görselleri...")
    run_core_visuals(df_2024, img_2024, "2024")
    plot_target_achievement(ta_24["wide"], img_2024, "2024")

    # ------------------------------------------------------------------ 2025
    print("\n[4/6] 2025 CSV analizleri...")
    run_core_analyses(df_2025, OUTPUT_DIR / "2025")
    save_csv(ta_25["wide"], OUTPUT_DIR / "2025", "11_hedef_gerceklestirme_wide")
    save_csv(ta_25["long"], OUTPUT_DIR / "2025", "12_hedef_gerceklestirme_long")

    print("\n[5/6] 2025 görselleri...")
    run_core_visuals(df_2025, img_2025, "2025")
    plot_target_achievement(ta_25["wide"], img_2025, "2025")
    if not perf.empty:
        plot_model_month_heatmap(perf, img_2025, "2025")

    # ------------------------------------------------------------------ ALL
    print("\n[6/6] Tüm dönem CSV + görseller...")
    folder_all = OUTPUT_DIR / "all"
    run_core_analyses(df_all, folder_all)
    save_csv(yoy_comparison(df_all), folder_all, "11_yillik_karsilastirma")
    if not perf.empty:
        save_csv(monthly_performance_summary(perf),  folder_all, "12_aylik_hedef_performansi")
        save_csv(dealer_annual_performance(perf),    folder_all, "13_bayi_2025_performansi")
        save_csv(model_monthly_heatmap_data(perf),   folder_all, "14_model_ay_heatmap")
    if not comp.empty:
        save_csv(comp, folder_all, "15_rakip_satislar")

    report = generate_text_report(df_all, perf, comp if not comp.empty else None)
    (folder_all / "satis_analizi_raporu.txt").write_text(report, encoding="utf-8")

    run_core_visuals(df_all, img_all, "2024-2025")
    plot_model_monthly_trend(df_all, img_all, "2024-2025")
    plot_yoy_monthly(df_all, img_all)
    if not comp.empty:
        plot_competitor_comparison(comp, len(df_all), img_all)
    if not perf.empty:
        plot_model_month_heatmap(perf, img_all, "2025 Performans")

    print("\n✓ Tamamlandı.")
    print(f"   outputs/2024/        — {len(list((OUTPUT_DIR/'2024').glob('*.csv')))} CSV")
    print(f"   outputs/2025/        — {len(list((OUTPUT_DIR/'2025').glob('*.csv')))} CSV")
    print(f"   outputs/all/         — {len(list(folder_all.glob('*.csv')))} CSV + rapor")
    print(f"   outputs/images/2024/ — {len(list(img_2024.glob('*.png')))} görsel")
    print(f"   outputs/images/2025/ — {len(list(img_2025.glob('*.png')))} görsel")
    print(f"   outputs/images/all/  — {len(list(img_all.glob('*.png')))} görsel")


if __name__ == "__main__":
    main()
