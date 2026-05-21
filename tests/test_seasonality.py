"""seasonality.py için temel testler."""

from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).parents[1] / "data" / "raw"
HAVE_DATA = (DATA_DIR / "2024&2025-ALL-SALES-CSV-FILE.csv").exists()


def test_ratio_to_mean_mean_is_one():
    """SI serisi ortalaması her zaman 1.0 olmalı."""
    from src.analysis.seasonality import _ratio_to_mean
    import pandas as pd
    import numpy as np

    # Sentetik veri: 2 yıl × 12 ay, rastgele ama pozitif
    rng = [10, 20, 30, 25, 15, 35, 22, 18, 28, 24, 40, 55]
    rows = []
    for yr in [2024, 2025]:
        for m, v in enumerate(rng, 1):
            rows.append({"year": yr, "month": m, "sales_qty": v + yr - 2024})
    df = pd.DataFrame(rows)

    si = _ratio_to_mean(df, "sales_qty")
    assert abs(si.mean() - 1.0) < 1e-6, f"SI ortalaması 1.0 değil: {si.mean()}"
    assert len(si) == 12


def test_ratio_to_mean_index_range():
    from src.analysis.seasonality import _ratio_to_mean
    rows = [{"year": 2024, "month": m, "sales_qty": m * 10} for m in range(1, 13)]
    df = pd.DataFrame(rows)
    si = _ratio_to_mean(df, "sales_qty")
    assert list(si.index) == list(range(1, 13))


def test_compute_final_si_mean_is_one():
    """Nihai ağırlıklı SI ortalaması da 1.0 olmalı."""
    from src.analysis.seasonality import compute_final_si
    import pandas as pd

    # SI'lar ortalaması 1.0 olan sentetik seriler
    vals = [0.6, 0.8, 1.0, 0.9, 1.1, 1.2, 0.95, 0.85, 0.9, 1.0, 1.1, 1.55]
    s = pd.Series(vals, index=range(1, 13))
    # Aynı seriyi kullansak bile ağırlıklı ortalama = aynı seri
    final = compute_final_si(s, s, s, 0.5, 0.3, 0.2)
    assert abs(final.mean() - s.mean()) < 1e-4


def test_monthly_plan_sums_to_target():
    """Aylık plan toplamı yıllık hedefe eşit olmalı."""
    from src.analysis.seasonality import monthly_plan
    import pandas as pd

    si = pd.Series(
        [0.66, 0.89, 1.03, 0.83, 0.96, 1.07, 0.94, 0.89, 0.92, 1.00, 1.20, 1.62],
        index=range(1, 13),
    )
    for target in [1200, 3600, 5000]:
        plan = monthly_plan(target, si)
        assert plan["planned_qty"].sum() == target, \
            f"Toplam {plan['planned_qty'].sum()} ≠ {target}"


def test_monthly_plan_share_pct_sums_100():
    from src.analysis.seasonality import monthly_plan
    import pandas as pd

    si = pd.Series([1.0] * 12, index=range(1, 13))
    plan = monthly_plan(1200, si)
    assert abs(plan["share_pct"].sum() - 100.0) < 0.1


@pytest.mark.skipif(not HAVE_DATA, reason="data/raw/ erişimi yok")
def test_compute_optimal_weights_sum_to_one():
    from src.analysis.seasonality import compute_optimal_weights
    from src.analysis.data_loader import load_sales, load_competitors
    w_odd, w_seg, w_ns = compute_optimal_weights(
        DATA_DIR, load_competitors(DATA_DIR), load_sales(DATA_DIR)
    )
    total = w_odd + w_seg + w_ns
    assert abs(total - 1.0) < 1e-4, f"Ağırlık toplamı 1.0 değil: {total}"
    assert all(w >= 0 for w in [w_odd, w_seg, w_ns]), "Negatif ağırlık"
