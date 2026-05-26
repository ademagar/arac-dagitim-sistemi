"""Envanter ve bayi hedefi yükleme modülü."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parents[2] / "data" / "raw"

# Excel'deki Türkçe ay adları → filtre etiketleri
MONTH_LABEL_VARIANTS: dict[str, list[str]] = {
    "January":   ["January",   "Ocak",    "Current Month"],
    "February":  ["February",  "Şubat",   "Current Month"],
    "March":     ["March",     "Mart",    "Current Month"],
    "April":     ["April",     "Nisan",   "Current Month"],
    "May":       ["May",       "Mayıs",   "Current Month"],
    "June":      ["June",      "Haziran", "Current Month"],
    "July":      ["July",      "Temmuz",  "Current Month"],
    "August":    ["August",    "Ağustos", "Current Month"],
    "September": ["September", "Eylül",   "Current Month"],
    "October":   ["October",   "Ekim",    "Current Month"],
    "November":  ["November",  "Kasım",   "Current Month"],
    "December":  ["December",  "Aralık",  "Current Month"],
}


def _read_file(path: Path) -> pd.DataFrame:
    """CSV veya Excel dosyasını okur."""
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    # Noktalı virgül önce dene, virgüle fallback
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    if len(df.columns) == 1:
        df = pd.read_csv(path, sep=",", encoding="utf-8-sig")
    return df


def load_inventory(
    path: Path | None = None,
    month_labels: list[str] | None = None,
) -> pd.DataFrame:
    """Envanter CSV/Excel'ini okur ve dağıtılabilir araç havuzunu döndürür.

    Filtre kriteri (VE koşulu):
        • Dealer Code Processing == 'CENT-STOCK'
        • Dispatchable == 'Y'
        • Month Number ∈ month_labels

    Args:
        path:         Dosya yolu (CSV veya Excel). None ise varsayılan kullanılır.
        month_labels: Hangi Month Number etiketlerinin dahil edileceği.
                      Varsayılan: ['January', 'Current Month']

    Returns:
        Her satır bir araç olan DataFrame.
        Eklenen sütun: vehicle_type = "Model / Version / Color"
    """
    if path is None:
        path = DATA_DIR / "NORTHSTAR-BULUNURLUK-JANUARY-2TH-csv.csv"
    if month_labels is None:
        month_labels = ["January", "Current Month"]

    df = _read_file(path)

    mask = (
        (df["Dealer Code Processing"] == "CENT-STOCK")
        & (df["Dispatchable"] == "Y")
        & (df["Month Number"].isin(month_labels))
    )
    pool = df[mask].copy()

    pool["vehicle_type"] = (
        pool["Model Description"].str.strip()
        + " / "
        + pool["Vehicle Version"].str.strip()
        + " / "
        + pool["Exterior Color"].str.strip()
    )
    return pool.reset_index(drop=True)


def inventory_summary(pool: pd.DataFrame) -> pd.DataFrame:
    """Envanter havuzunu model/versiyon/renk bazında özetler.

    Returns:
        DataFrame: vehicle_type, model, version, color, quantity sütunları.
    """
    grp = (
        pool.groupby(["vehicle_type", "Model Description", "Vehicle Version", "Exterior Color"])
        .size()
        .reset_index(name="quantity")
        .rename(columns={
            "Model Description": "model",
            "Vehicle Version":   "version",
            "Exterior Color":    "color",
        })
    )
    return grp.sort_values(["model", "version", "color"]).reset_index(drop=True)


def load_targets(path: Path | None = None) -> pd.DataFrame:
    """Bayi hedefleri CSV'sini okur.

    Args:
        path: CSV dosyası yolu. None ise varsayılan DATA_DIR kullanılır.

    Returns:
        DataFrame sütunları: dealer_name, dealer_code, target (int).
        target == 0 olan satırlar dahil edilir ancak optimizasyonda atlanır.
    """
    if path is None:
        path = DATA_DIR / "dealer_target_january26.csv"

    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()

    # Sütun adı normalleştirme
    col_map = {
        "Dealer Name":  "dealer_name",
        "Dealer Code":  "dealer_code",
        "Target":       "target",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    df["target"] = pd.to_numeric(df["target"], errors="coerce").fillna(0).astype(int)
    return df[["dealer_name", "dealer_code", "target"]].copy()
