"""data_loader.py için temel testler."""

from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).parents[1] / "data" / "raw"
HAVE_DATA = (DATA_DIR / "2024&2025-ALL-SALES-CSV-FILE.csv").exists()


@pytest.mark.skipif(not HAVE_DATA, reason="data/raw/ erişimi yok")
def test_load_sales_returns_dataframe():
    from src.analysis.data_loader import load_sales
    df = load_sales(DATA_DIR)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


@pytest.mark.skipif(not HAVE_DATA, reason="data/raw/ erişimi yok")
def test_load_sales_has_required_columns():
    from src.analysis.data_loader import load_sales
    df = load_sales(DATA_DIR)
    required = {"year", "month", "year_month", "model_version", "Dealer Name"}
    assert required.issubset(df.columns)


@pytest.mark.skipif(not HAVE_DATA, reason="data/raw/ erişimi yok")
def test_load_sales_years():
    from src.analysis.data_loader import load_sales
    df = load_sales(DATA_DIR)
    years = set(df["year"].dropna().astype(int))
    assert years.issubset({2024, 2025})


@pytest.mark.skipif(not HAVE_DATA, reason="data/raw/ erişimi yok")
def test_load_competitors_anonymized():
    from src.analysis.data_loader import load_competitors, COMPETITOR_ALIAS_MAP
    df = load_competitors(DATA_DIR)
    assert isinstance(df, pd.DataFrame)
    # Gerçek marka adları OLMAMALI
    real_brands = set(COMPETITOR_ALIAS_MAP.keys())
    brands_in_df = set(df["brand"].unique())
    assert len(real_brands & brands_in_df) == 0, "Gerçek marka adı sızdı"


@pytest.mark.skipif(not HAVE_DATA, reason="data/raw/ erişimi yok")
def test_load_competitors_columns():
    from src.analysis.data_loader import load_competitors
    df = load_competitors(DATA_DIR)
    assert {"brand", "year_month", "sales_qty"}.issubset(df.columns)
