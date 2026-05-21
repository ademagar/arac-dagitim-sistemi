"""Ocak 2026 araç dağıtım orchestrator.

Kullanım:
    python -m src.allocation.run_allocation
    python src/allocation/run_allocation.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

# Proje kökü sys.path'e ekle (script doğrudan çalıştırıldığında)
_ROOT = Path(__file__).parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.allocation.data_prep import inventory_summary, load_inventory, load_targets
from src.allocation.optimizer import run_optimizer
from src.allocation.scorer import (
    compute_composite_scores,
    compute_h_scores,
    compute_lp_affinity,
    compute_p_scores,
    compute_s_scores,
)
from src.allocation.visualizations import (
    plot_allocation_heatmap,
    plot_dealer_summary,
    plot_inventory_usage,
    plot_model_distribution,
    plot_score_breakdown,
)
from src.analysis.data_loader import load_monthly_performance, load_sales

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = _ROOT / "outputs" / "allocation" / "2026_01"
MONTH = 1  # Ocak


def _print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run() -> pd.DataFrame:
    """Tam dağıtım pipeline'ını çalıştırır ve sonuç DataFrame döndürür."""

    # ------------------------------------------------------------------
    # 1. Veri yükleme
    # ------------------------------------------------------------------
    _print_section("1 / 6  Veri Yükleniyor")

    logger.info("Envanter yükleniyor...")
    pool = load_inventory()
    inv_summary = inventory_summary(pool)
    logger.info("  Havuz: %d araç, %d farklı tip", len(pool), len(inv_summary))

    logger.info("Bayi hedefleri yükleniyor...")
    targets = load_targets()
    total_demand = targets["target"].sum()
    total_supply = inv_summary["quantity"].sum()
    logger.info(
        "  Toplam talep: %d araç | Toplam arz: %d araç", total_demand, total_supply
    )

    logger.info("Satış geçmişi yükleniyor...")
    try:
        df_sales = load_sales()
        logger.info("  Satış kaydı: %d satır", len(df_sales))
    except Exception as exc:
        logger.warning("Satış verisi yüklenemedi (%s) — LP affinity sıfırlanacak.", exc)
        df_sales = pd.DataFrame()

    logger.info("Aylık performans yükleniyor...")
    try:
        df_perf = load_monthly_performance()
        logger.info("  Performans kaydı: %d satır", len(df_perf))
    except Exception as exc:
        logger.warning("Performans verisi yüklenemedi (%s) — P skoru varsayılan.", exc)
        df_perf = pd.DataFrame()

    # ------------------------------------------------------------------
    # 2. Skorlama
    # ------------------------------------------------------------------
    _print_section("2 / 6  Bayi Skorları Hesaplanıyor")

    dealer_names = targets[targets["target"] > 0]["dealer_name"].tolist()
    vehicle_types = inv_summary["vehicle_type"].tolist()

    logger.info("P skoru (performans)...")
    p_scores = compute_p_scores(df_perf, dealer_names)

    logger.info("LP affinitesi (lokasyon-ürün uyum)...")
    lp_affinity = compute_lp_affinity(df_sales, dealer_names, vehicle_types)

    logger.info("S skoru (mevsimsellik, ay=%d)...", MONTH)
    s_scores = compute_s_scores(dealer_names, month=MONTH)

    logger.info("H skoru (hedef yakınlık)...")
    h_scores = compute_h_scores(targets[targets["target"] > 0])

    logger.info("Bileşik skor...")
    composite = compute_composite_scores(p_scores, s_scores, h_scores, dealer_names)

    score_df = pd.DataFrame({
        "dealer_name":      dealer_names,
        "p_score":          p_scores.reindex(dealer_names).values,
        "s_score":          s_scores.reindex(dealer_names).values,
        "h_score":          h_scores.reindex(dealer_names).values,
        "composite_score":  composite.reindex(dealer_names).values,
    })

    print("\nBayi Skoru Özeti (ilk 10):")
    print(score_df.sort_values("composite_score", ascending=False).head(10).to_string(index=False))

    # ------------------------------------------------------------------
    # 3. Optimizasyon
    # ------------------------------------------------------------------
    _print_section("3 / 6  MILP Optimizasyonu Çalıştırılıyor")

    logger.info("PuLP/CBC solver başlatılıyor...")
    allocation = run_optimizer(inv_summary, targets, composite, lp_affinity)
    logger.info("  Atama tamamlandı: %d satır (pozitif atama)", len(allocation))

    total_allocated = allocation["allocated_qty"].sum()
    logger.info("  Toplam atanan araç: %d / %d", total_allocated, total_demand)

    # ------------------------------------------------------------------
    # 4. Sonuçları kaydet
    # ------------------------------------------------------------------
    _print_section("4 / 6  Sonuçlar Kaydediliyor")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Ana atama tablosu
    alloc_path = OUTPUT_DIR / "allocation_january2026.csv"
    allocation.to_csv(alloc_path, index=False, sep=";", encoding="utf-8-sig")
    logger.info("  Atama tablosu: %s", alloc_path.name)

    # Skor tablosu
    score_path = OUTPUT_DIR / "dealer_scores.csv"
    score_df.to_csv(score_path, index=False, sep=";", encoding="utf-8-sig")
    logger.info("  Skor tablosu: %s", score_path.name)

    # Bayi özeti (toplam atanan vs hedef)
    summary = allocation.groupby("dealer_name")["allocated_qty"].sum().reset_index()
    summary.columns = ["dealer_name", "allocated"]
    summary = summary.merge(
        targets[["dealer_name", "dealer_code", "target"]], on="dealer_name", how="left"
    )
    summary["gap"] = summary["allocated"] - summary["target"]
    summary["fill_rate"] = (summary["allocated"] / summary["target"] * 100).round(1)
    summary_path = OUTPUT_DIR / "dealer_summary.csv"
    summary.to_csv(summary_path, index=False, sep=";", encoding="utf-8-sig")
    logger.info("  Bayi özeti: %s", summary_path.name)

    # Envanter kullanım özeti
    inv_used = allocation.groupby("vehicle_type")["allocated_qty"].sum().reset_index()
    inv_used.columns = ["vehicle_type", "used"]
    inv_report = inv_summary.merge(inv_used, on="vehicle_type", how="left").fillna({"used": 0})
    inv_report["used"] = inv_report["used"].astype(int)
    inv_report["remaining"] = inv_report["quantity"] - inv_report["used"]
    inv_report["usage_rate"] = (inv_report["used"] / inv_report["quantity"] * 100).round(1)
    inv_path = OUTPUT_DIR / "inventory_usage.csv"
    inv_report.to_csv(inv_path, index=False, sep=";", encoding="utf-8-sig")
    logger.info("  Envanter raporu: %s", inv_path.name)

    # ------------------------------------------------------------------
    # 5. Görselleştirme
    # ------------------------------------------------------------------
    _print_section("5 / 6  Grafikler Üretiliyor")

    plot_allocation_heatmap(allocation, OUTPUT_DIR)
    plot_dealer_summary(allocation, targets, OUTPUT_DIR)
    plot_model_distribution(allocation, OUTPUT_DIR)
    plot_score_breakdown(score_df, OUTPUT_DIR)
    plot_inventory_usage(inv_summary, allocation, OUTPUT_DIR)

    # ------------------------------------------------------------------
    # 6. Sonuç özeti
    # ------------------------------------------------------------------
    _print_section("6 / 6  Sonuç")

    print("\n📋 OCAK 2026 — BAYİ DAĞITIM TABLOSU")
    print("─" * 65)
    print(f"{'Bayi':<30} {'Hedef':>7} {'Atanan':>7} {'Fark':>6} {'Doluluk':>8}")
    print("─" * 65)
    for _, row in summary.sort_values("dealer_name").iterrows():
        gap_str = f"+{int(row['gap'])}" if row["gap"] >= 0 else str(int(row["gap"]))
        print(
            f"{row['dealer_name']:<30} {int(row['target']):>7} "
            f"{int(row['allocated']):>7} {gap_str:>6} {row['fill_rate']:>7}%"
        )
    print("─" * 65)
    total_fill = round(total_allocated / total_demand * 100, 1)
    print(f"{'TOPLAM':<30} {total_demand:>7} {total_allocated:>7} {'':>6} {total_fill:>7}%")

    print(f"\nÇıktı dizini: {OUTPUT_DIR}")
    print(f"  • allocation_january2026.csv")
    print(f"  • dealer_summary.csv")
    print(f"  • dealer_scores.csv")
    print(f"  • inventory_usage.csv")
    print(f"  • 01_allocation_heatmap.png")
    print(f"  • 02_dealer_summary.png")
    print(f"  • 03_model_distribution.png")
    print(f"  • 04_score_breakdown.png")
    print(f"  • 05_inventory_usage.png")

    return allocation


if __name__ == "__main__":
    run()
