"""Dağıtım sonuçları görselleştirme modülü."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"figure.dpi": 150, "font.family": "DejaVu Sans",
                     "axes.titlesize": 12, "axes.titleweight": "bold"})


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Kaydedildi: {path.name}")


def plot_allocation_heatmap(allocation: pd.DataFrame, output_dir: Path) -> None:
    """Bayi × model bazında atama ısı haritası."""
    pivot = allocation.pivot_table(
        index="dealer_name", columns="model",
        values="allocated_qty", aggfunc="sum", fill_value=0,
    )
    fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.5), max(8, len(pivot) * 0.5)))
    sns.heatmap(pivot, annot=True, fmt="d", cmap="YlOrRd",
                linewidths=0.4, linecolor="white", ax=ax,
                cbar_kws={"label": "Atanan Araç"})
    ax.set_title("Bayi × Model Atama Dağılımı", fontsize=13, fontweight="bold")
    ax.set_xlabel("Model")
    ax.set_ylabel("Bayi")
    fig.tight_layout()
    _save(fig, output_dir / "01_allocation_heatmap.png")


def plot_dealer_summary(
    allocation: pd.DataFrame,
    targets: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Bayi başına atanan araç adedi vs hedef bar grafiği."""
    summary = allocation.groupby("dealer_name")["allocated_qty"].sum().reset_index()
    summary.columns = ["dealer_name", "allocated"]
    summary = summary.merge(
        targets[["dealer_name", "target"]], on="dealer_name", how="left"
    )
    summary = summary.sort_values("allocated", ascending=True)

    x = np.arange(len(summary))
    fig, ax = plt.subplots(figsize=(12, max(6, len(summary) * 0.4)))
    ax.barh(x - 0.2, summary["target"], 0.38,
            color="#90CAF9", label="Hedef", alpha=0.9)
    ax.barh(x + 0.2, summary["allocated"], 0.38,
            color="#1565C0", label="Atanan", alpha=0.9)

    for i, (_, row) in enumerate(summary.iterrows()):
        ax.text(row["allocated"] + 0.1, i + 0.2, f"{int(row['allocated'])}",
                va="center", fontsize=8, color="#1565C0", fontweight="bold")

    ax.set_yticks(x)
    ax.set_yticklabels(summary["dealer_name"], fontsize=8)
    ax.set_xlabel("Araç Adedi")
    ax.set_title("Ocak 2026 — Bayi Hedef vs Atanan", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v)}"))
    fig.tight_layout()
    _save(fig, output_dir / "02_dealer_summary.png")


def plot_model_distribution(allocation: pd.DataFrame, output_dir: Path) -> None:
    """Model bazında toplam atama dağılımı (stacked bar)."""
    pivot = allocation.pivot_table(
        index="dealer_name", columns="model",
        values="allocated_qty", aggfunc="sum", fill_value=0,
    )
    pivot = pivot.sort_values(pivot.columns[0], ascending=True)

    colors = sns.color_palette("Set2", n_colors=len(pivot.columns))
    fig, ax = plt.subplots(figsize=(12, max(6, len(pivot) * 0.45)))

    left = np.zeros(len(pivot))
    for col, color in zip(pivot.columns, colors):
        vals = pivot[col].values
        ax.barh(range(len(pivot)), vals, left=left,
                color=color, label=col, alpha=0.88, edgecolor="white")
        for i, (v, l) in enumerate(zip(vals, left)):
            if v > 0:
                ax.text(l + v / 2, i, str(int(v)),
                        ha="center", va="center", fontsize=7.5, color="white", fontweight="bold")
        left += vals

    ax.set_yticks(range(len(pivot)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_xlabel("Araç Adedi")
    ax.set_title("Ocak 2026 — Bayi × Model Dağılımı (Stacked)", fontsize=13, fontweight="bold")
    ax.legend(title="Model", fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    _save(fig, output_dir / "03_model_distribution.png")


def plot_score_breakdown(score_df: pd.DataFrame, output_dir: Path) -> None:
    """Bayi skor bileşenleri (grouped bar)."""
    df = score_df.sort_values("composite_score", ascending=True)
    x = np.arange(len(df))
    width = 0.22

    fig, ax = plt.subplots(figsize=(12, max(6, len(df) * 0.4)))
    ax.barh(x - width, df["p_score"],  width, label="P (Perf)",   color="#42A5F5", alpha=0.85)
    ax.barh(x,         df["s_score"],  width, label="S (Sezon)",  color="#66BB6A", alpha=0.85)
    ax.barh(x + width, df["h_score"],  width, label="H (Hedef)",  color="#FFA726", alpha=0.85)

    ax.set_yticks(x)
    ax.set_yticklabels(df["dealer_name"], fontsize=8)
    ax.set_xlabel("Skor [0-1]")
    ax.set_title("Bayi Skor Bileşenleri (P · S · H)", fontsize=13, fontweight="bold")
    ax.axvline(0.5, color="gray", linestyle="--", lw=1.0, alpha=0.6)
    ax.legend(fontsize=9)
    fig.tight_layout()
    _save(fig, output_dir / "04_score_breakdown.png")


def plot_inventory_usage(inv_summary: pd.DataFrame, allocation: pd.DataFrame,
                         output_dir: Path) -> None:
    """Envanter kullanım oranı (kullanılan vs kalan)."""
    used = (
        allocation.groupby("vehicle_type")["allocated_qty"]
        .sum()
        .reindex(inv_summary["vehicle_type"], fill_value=0)
    )
    total = inv_summary.set_index("vehicle_type")["quantity"]
    remaining = (total - used).clip(lower=0)

    df_plot = pd.DataFrame({
        "type": inv_summary["vehicle_type"],
        "used": used.values,
        "remaining": remaining.values,
    }).sort_values("used", ascending=True)

    # Sadece herhangi bir kullanım olanları göster
    df_plot = df_plot[df_plot["used"] + df_plot["remaining"] > 0]

    fig, ax = plt.subplots(figsize=(10, max(6, len(df_plot) * 0.35)))
    ax.barh(range(len(df_plot)), df_plot["used"], color="#1565C0",
            label="Atanan", alpha=0.85, edgecolor="white")
    ax.barh(range(len(df_plot)), df_plot["remaining"],
            left=df_plot["used"], color="#CFD8DC",
            label="Kalan", alpha=0.85, edgecolor="white")

    ax.set_yticks(range(len(df_plot)))
    ax.set_yticklabels(df_plot["type"], fontsize=7)
    ax.set_xlabel("Araç Adedi")
    ax.set_title("Ocak 2026 — Envanter Kullanımı (Atanan vs Kalan)", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    fig.tight_layout()
    _save(fig, output_dir / "05_inventory_usage.png")
