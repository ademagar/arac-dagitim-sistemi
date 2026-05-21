"""Satış analizi çalıştırma scripti.

Kullanım:
    python -m src.analysis.run_analysis

Çıktılar outputs/ klasörüne kaydedilir.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis.data_loader import load_competitors, load_monthly_performance, load_sales
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
OUTPUT_DIR.mkdir(exist_ok=True)


def save_csv(df: pd.DataFrame, name: str) -> None:
    path = OUTPUT_DIR / f"{name}.csv"
    df.to_csv(path, index=True, encoding="utf-8-sig")
    print(f"  Kaydedildi: {path.relative_to(Path.cwd())}")


def main() -> None:
    print("\n[1/4] Veriler yükleniyor...")
    df = load_sales()
    perf = load_monthly_performance()
    comp = load_competitors()
    print(f"  Ana satış: {len(df):,} kayıt")
    print(f"  Aylık performans: {len(perf):,} kayıt ({perf['month'].nunique()} ay)" if not perf.empty else "  Aylık performans: yüklenemedi")
    print(f"  Rakip verisi: {comp['brand'].nunique()} marka" if not comp.empty else "  Rakip verisi: yüklenemedi")

    print("\n[2/4] Analizler hesaplanıyor...")

    model_rank = model_only_ranking(df)
    ver_rank = model_version_ranking(df)
    col_rank = color_ranking(df)
    d_total = dealer_total_sales(df)
    d_model = dealer_model_matrix(df)
    d_ver = dealer_version_matrix(df)
    d_top = dealer_top_model(df)
    monthly = monthly_sales_trend(df)
    model_monthly = monthly_model_trend(df)
    ch = channel_breakdown(df)
    yoy = yoy_comparison(df)

    print("\n[3/4] CSV çıktıları kaydediliyor...")
    save_csv(model_rank, "01_model_satislari")
    save_csv(ver_rank, "02_versiyon_satislari")
    save_csv(col_rank, "03_renk_satislari")
    save_csv(d_total, "04_bayi_toplam_satis")
    save_csv(d_model, "05_bayi_model_matrix")
    save_csv(d_ver, "06_bayi_versiyon_matrix")
    save_csv(d_top, "07_bayi_top_model")
    save_csv(monthly, "08_aylik_trend")
    save_csv(model_monthly, "09_model_aylik_trend")
    save_csv(ch, "10_kanal_dagilimi")
    save_csv(yoy, "11_yillik_karsilastirma")

    if not perf.empty:
        perf_sum = monthly_performance_summary(perf)
        d_ann = dealer_annual_performance(perf)
        heatmap = model_monthly_heatmap_data(perf)
        save_csv(perf_sum, "12_aylik_hedef_performansi")
        save_csv(d_ann, "13_bayi_2025_performansi")
        save_csv(heatmap, "14_model_ay_heatmap")

    if not comp.empty:
        save_csv(comp, "15_rakip_satislar")

    print("\n[4/4] Metin raporu oluşturuluyor...")
    report = generate_text_report(df, perf, comp if not comp.empty else None)
    report_path = OUTPUT_DIR / "satis_analizi_raporu.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Kaydedildi: {report_path.relative_to(Path.cwd())}")

    # Konsola da bas
    print("\n" + report)


if __name__ == "__main__":
    main()
