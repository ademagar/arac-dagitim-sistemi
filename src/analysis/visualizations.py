"""Satış verisi görselleştirme modülü.

Her fonksiyon bir grafik üretir ve belirtilen klasöre PNG olarak kaydeder.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # GUI olmayan ortamlar için

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

# Ortak stil
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({
    "figure.dpi": 150,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
})

COLORS_MODEL = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4", "#FF5722"]
COLORS_CHANNEL = {"B2C": "#2196F3", "B2B": "#FF9800", "B2B+B2C": "#4CAF50"}


def _save(fig: plt.Figure, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Kaydedildi: {path.relative_to(Path.cwd())}")


# ---------------------------------------------------------------------------
# 1. Model satışları yatay bar
# ---------------------------------------------------------------------------
def plot_model_sales(df: pd.DataFrame, folder: Path, label: str) -> None:
    from src.analysis.sales_analysis import model_only_ranking
    data = model_only_ranking(df)

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(data["model"][::-1], data["total_sales"][::-1],
                   color=COLORS_MODEL[:len(data)], edgecolor="white", height=0.6)
    for bar, pct in zip(bars, data["share_pct"][::-1]):
        ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height() / 2,
                f"{int(bar.get_width()):,}  (%{pct:.1f})",
                va="center", fontsize=10)
    ax.set_xlabel("Satış Adedi")
    ax.set_title(f"Model Bazında Satışlar — {label}")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_xlim(0, data["total_sales"].max() * 1.22)
    fig.tight_layout()
    _save(fig, folder, "01_model_satislari")


# ---------------------------------------------------------------------------
# 2. Versiyon satışları (top 10) yatay bar
# ---------------------------------------------------------------------------
def plot_version_sales(df: pd.DataFrame, folder: Path, label: str) -> None:
    from src.analysis.sales_analysis import model_version_ranking
    data = model_version_ranking(df).head(10)
    data["label"] = data["model"] + " / " + data["version"]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(data["label"][::-1], data["total_sales"][::-1],
                   color="#2196F3", edgecolor="white", height=0.6)
    for bar, pct in zip(bars, data["share_pct"][::-1]):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2,
                f"{int(bar.get_width()):,}  (%{pct:.1f})",
                va="center", fontsize=9)
    ax.set_xlabel("Satış Adedi")
    ax.set_title(f"Versiyon Bazında Satışlar (Top 10) — {label}")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_xlim(0, data["total_sales"].max() * 1.25)
    fig.tight_layout()
    _save(fig, folder, "02_versiyon_satislari")


# ---------------------------------------------------------------------------
# 3. Renk dağılımı (pasta + yatay bar yan yana)
# ---------------------------------------------------------------------------
def plot_color_distribution(df: pd.DataFrame, folder: Path, label: str) -> None:
    from src.analysis.sales_analysis import color_ranking
    data = color_ranking(df).head(8)
    others = df["Exterior Color"].notna().sum() - data["total_sales"].sum()
    if others > 0:
        data = pd.concat([
            data,
            pd.DataFrame([{"Exterior Color": "Diğer", "total_sales": others,
                           "share_pct": others / df["Exterior Color"].notna().sum() * 100}])
        ], ignore_index=True)

    palette = sns.color_palette("Set2", len(data))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pasta
    wedges, texts, autotexts = ax1.pie(
        data["total_sales"], labels=data["Exterior Color"],
        autopct="%1.1f%%", colors=palette, startangle=140,
        pctdistance=0.8, wedgeprops={"edgecolor": "white", "linewidth": 1.2}
    )
    for t in autotexts:
        t.set_fontsize(8)
    ax1.set_title(f"Renk Dağılımı — {label}")

    # Yatay bar
    bars = ax2.barh(data["Exterior Color"][::-1], data["total_sales"][::-1],
                    color=palette[::-1], edgecolor="white", height=0.65)
    for bar in bars:
        ax2.text(bar.get_width() + 3, bar.get_y() + bar.get_height() / 2,
                 f"{int(bar.get_width()):,}", va="center", fontsize=9)
    ax2.set_xlabel("Satış Adedi")
    ax2.set_title(f"Renk Bazında Satışlar — {label}")
    ax2.set_xlim(0, data["total_sales"].max() * 1.18)
    fig.tight_layout()
    _save(fig, folder, "03_renk_dagilimi")


# ---------------------------------------------------------------------------
# 4. Bayi toplam satışlar
# ---------------------------------------------------------------------------
def plot_dealer_sales(df: pd.DataFrame, folder: Path, label: str) -> None:
    from src.analysis.sales_analysis import dealer_total_sales
    data = dealer_total_sales(df)
    avg = data["total_sales"].mean()

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ["#E53935" if v < avg else "#43A047" for v in data["total_sales"]]
    bars = ax.barh(data["Dealer Name"][::-1], data["total_sales"][::-1],
                   color=colors[::-1], edgecolor="white", height=0.7)
    ax.axvline(avg, color="#FB8C00", linestyle="--", linewidth=1.5,
               label=f"Ortalama: {avg:.0f}")
    for bar in bars:
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height() / 2,
                f"{int(bar.get_width()):,}", va="center", fontsize=8.5)
    ax.set_xlabel("Satış Adedi")
    ax.set_title(f"Bayi Bazında Toplam Satışlar — {label}")
    ax.legend(fontsize=10)
    ax.set_xlim(0, data["total_sales"].max() * 1.18)
    fig.tight_layout()
    _save(fig, folder, "04_bayi_toplam_satis")


# ---------------------------------------------------------------------------
# 5. Aylık satış trendi (çizgi)
# ---------------------------------------------------------------------------
def plot_monthly_trend(df: pd.DataFrame, folder: Path, label: str) -> None:
    from src.analysis.sales_analysis import monthly_sales_trend
    data = monthly_sales_trend(df)
    x_labels = data["year_month"].astype(str)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(range(len(x_labels)), data["sales_qty"], marker="o", linewidth=2.2,
            color="#1565C0", markersize=6, markerfacecolor="white", markeredgewidth=2)
    for i, (qty, lbl) in enumerate(zip(data["sales_qty"], x_labels)):
        ax.annotate(f"{qty:,}", (i, qty), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=8, color="#1565C0")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Satış Adedi")
    ax.set_title(f"Aylık Satış Trendi — {label}")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.fill_between(range(len(x_labels)), data["sales_qty"], alpha=0.08, color="#1565C0")
    fig.tight_layout()
    _save(fig, folder, "05_aylik_trend")


# ---------------------------------------------------------------------------
# 6. Bayi × Model ısı haritası
# ---------------------------------------------------------------------------
def plot_dealer_model_heatmap(df: pd.DataFrame, folder: Path, label: str) -> None:
    pivot = (
        df.groupby(["Dealer Name", "Model Description"], dropna=True)
        .size()
        .unstack(fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(pivot, annot=True, fmt="d", cmap="YlOrRd", linewidths=0.5,
                linecolor="white", ax=ax, cbar_kws={"label": "Satış Adedi"})
    ax.set_title(f"Bayi × Model Satış Isı Haritası — {label}")
    ax.set_xlabel("Model")
    ax.set_ylabel("Bayi")
    fig.tight_layout()
    _save(fig, folder, "06_bayi_model_heatmap")


# ---------------------------------------------------------------------------
# 7. Kanal dağılımı (B2C vs B2B) — yıl gruplu bar
# ---------------------------------------------------------------------------
def plot_channel_breakdown(df: pd.DataFrame, folder: Path, label: str) -> None:
    from src.analysis.sales_analysis import channel_breakdown
    data = channel_breakdown(df)

    years = sorted(data["year"].unique())
    channels = data["Channel Group"].unique()
    x = np.arange(len(years))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Adet
    for i, ch in enumerate(channels):
        sub = data[data["Channel Group"] == ch]
        ax1.bar(x + i * width - width / 2, sub["sales_qty"],
                width, label=ch,
                color=COLORS_CHANNEL.get(ch, "#78909C"), edgecolor="white")
    ax1.set_xticks(x)
    ax1.set_xticklabels(years)
    ax1.set_ylabel("Satış Adedi")
    ax1.set_title(f"Kanal Bazında Satış Adedi — {label}")
    ax1.legend()
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Yüzde
    for i, ch in enumerate(channels):
        sub = data[data["Channel Group"] == ch]
        ax2.bar(x + i * width - width / 2, sub["share_pct"],
                width, label=ch,
                color=COLORS_CHANNEL.get(ch, "#78909C"), edgecolor="white")
    ax2.set_xticks(x)
    ax2.set_xticklabels(years)
    ax2.set_ylabel("Oran (%)")
    ax2.set_title(f"Kanal Bazında Satış Oranı — {label}")
    ax2.legend()
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"%{x:.0f}"))
    fig.tight_layout()
    _save(fig, folder, "07_kanal_dagilimi")


# ---------------------------------------------------------------------------
# 8. Hedef vs Gerçekleşme (B2C + B2B aylık)
# ---------------------------------------------------------------------------
def plot_target_achievement(ta_wide: pd.DataFrame, folder: Path, label: str) -> None:
    months = [c for c in ta_wide.columns if c != "TOTAL"]

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f"Hedef vs Gerçekleşme — {label}", fontsize=15, fontweight="bold", y=1.01)

    for ax, (tgt_row, ach_row, ch_label, color) in zip(axes, [
        ("TARGET B2C", "ACHIEVEMENT B2C", "B2C", "#1565C0"),
        ("TARGET B2B", "ACHIEVEMENT B2B", "B2B", "#E65100"),
    ]):
        if tgt_row not in ta_wide.index or ach_row not in ta_wide.index:
            ax.set_visible(False)
            continue
        target = [ta_wide.loc[tgt_row, m] for m in months]
        achiev = [ta_wide.loc[ach_row, m] for m in months]
        x = np.arange(len(months))
        w = 0.38

        ax.bar(x - w / 2, target, w, label="Hedef", color="#B0BEC5", edgecolor="white")
        ax.bar(x + w / 2, achiev, w, label="Gerçekleşen", color=color, alpha=0.85, edgecolor="white")

        # Achievement % çizgisi
        if "Target Achievement %" in ta_wide.index:
            pcts = [ta_wide.loc["Target Achievement %", m] for m in months]
            ax2 = ax.twinx()
            ax2.plot(x, pcts, "o--", color="#FDD835", linewidth=1.8,
                     markersize=5, label="Gerç. %")
            ax2.axhline(100, color="#FDD835", linestyle=":", linewidth=1, alpha=0.6)
            ax2.set_ylabel("Gerçekleşme %", color="#F9A825")
            ax2.tick_params(axis="y", labelcolor="#F9A825")
            ax2.set_ylim(0, max(pcts) * 1.3 if pcts else 150)
            ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"%{v:.0f}"))
            ax2.legend(loc="upper right", fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("Satış Adedi")
        ax.set_title(f"{ch_label} Kanal")
        ax.legend(loc="upper left", fontsize=9)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))

    fig.tight_layout()
    _save(fig, folder, "08_hedef_gerceklestirme")


# ---------------------------------------------------------------------------
# 9. Model aylık trend (çoklu çizgi) — all için
# ---------------------------------------------------------------------------
def plot_model_monthly_trend(df: pd.DataFrame, folder: Path, label: str) -> None:
    from src.analysis.sales_analysis import monthly_model_trend
    data = monthly_model_trend(df)
    models = data["Model Description"].unique()
    periods = sorted(data["year_month"].unique(), key=str)

    fig, ax = plt.subplots(figsize=(14, 6))
    for i, model in enumerate(models):
        sub = data[data["Model Description"] == model]
        sub_indexed = sub.set_index("year_month")["sales_qty"].reindex(
            [str(p) for p in periods], fill_value=0
        )
        ax.plot(range(len(periods)), sub_indexed.values, marker="o",
                label=model, color=COLORS_MODEL[i % len(COLORS_MODEL)],
                linewidth=2, markersize=5)

    ax.set_xticks(range(len(periods)))
    ax.set_xticklabels([str(p) for p in periods], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Satış Adedi")
    ax.set_title(f"Model Bazında Aylık Satış Trendi — {label}")
    ax.legend(title="Model", bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    fig.tight_layout()
    _save(fig, folder, "09_model_aylik_trend")


# ---------------------------------------------------------------------------
# 10. YoY Karşılaştırma — all için
# ---------------------------------------------------------------------------
def plot_yoy_monthly(df: pd.DataFrame, folder: Path) -> None:
    from src.analysis.sales_analysis import monthly_sales_trend
    data = monthly_sales_trend(df)

    d2024 = data[data["year"] == 2024].set_index("month")["sales_qty"]
    d2025 = data[data["year"] == 2025].set_index("month")["sales_qty"]
    months = sorted(set(d2024.index) | set(d2025.index))
    x = np.arange(len(months))
    w = 0.38

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.bar(x - w / 2, [d2024.get(m, 0) for m in months], w,
           label="2024", color="#1565C0", alpha=0.85, edgecolor="white")
    ax.bar(x + w / 2, [d2025.get(m, 0) for m in months], w,
           label="2025", color="#43A047", alpha=0.85, edgecolor="white")

    for xi, m in enumerate(months):
        v24, v25 = d2024.get(m, 0), d2025.get(m, 0)
        if v24 > 0:
            chg = (v25 - v24) / v24 * 100
            color = "#43A047" if chg >= 0 else "#E53935"
            ax.annotate(f"{chg:+.0f}%", (xi + w / 2, v25),
                        xytext=(0, 6), textcoords="offset points",
                        ha="center", fontsize=7.5, color=color)

    import calendar
    ax.set_xticks(x)
    ax.set_xticklabels([calendar.month_abbr[m] for m in months], fontsize=10)
    ax.set_ylabel("Satış Adedi")
    ax.set_title("2024 vs 2025 Aylık Satış Karşılaştırması")
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    _save(fig, folder, "10_yoy_karsilastirma")


# ---------------------------------------------------------------------------
# 11. Rakip marka karşılaştırması — all için
# ---------------------------------------------------------------------------
def plot_competitor_comparison(comp: pd.DataFrame, northstar_total: int,
                                folder: Path) -> None:
    brand_totals = (
        comp.groupby("brand")["sales_qty"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    brand_totals.loc[-1] = ["NORTHSTAR", northstar_total]
    brand_totals = brand_totals.sort_values("sales_qty", ascending=False).reset_index(drop=True)

    colors = ["#E53935" if b == "NORTHSTAR" else "#90A4AE" for b in brand_totals["brand"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(brand_totals["brand"][::-1], brand_totals["sales_qty"][::-1],
                   color=colors[::-1], edgecolor="white", height=0.65)
    for bar in bars:
        ax.text(bar.get_width() + 200, bar.get_y() + bar.get_height() / 2,
                f"{int(bar.get_width()):,}", va="center", fontsize=9)
    ax.set_xlabel("Toplam Satış (2024-2025)")
    ax.set_title("Rakip Marka Karşılaştırması (2024-2025 Toplam)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_xlim(0, brand_totals["sales_qty"].max() * 1.18)
    fig.tight_layout()
    _save(fig, folder, "11_rakip_karsilastirma")


# ---------------------------------------------------------------------------
# 12. Model × Ay ısı haritası — 2025 performans (all/2025)
# ---------------------------------------------------------------------------
def plot_model_month_heatmap(perf: pd.DataFrame, folder: Path, label: str) -> None:
    from src.analysis.sales_analysis import model_monthly_heatmap_data
    heatmap = model_monthly_heatmap_data(perf)
    if heatmap.empty:
        return

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(heatmap, annot=True, fmt="d", cmap="Blues", linewidths=0.5,
                linecolor="white", ax=ax, cbar_kws={"label": "Satış Adedi"})
    short_cols = {c: c[:3] for c in heatmap.columns}
    ax.set_xticklabels([short_cols.get(c, c) for c in heatmap.columns],
                       rotation=45, ha="right")
    ax.set_title(f"Model Grubu × Ay Satış Isı Haritası — {label}")
    ax.set_xlabel("Ay")
    ax.set_ylabel("Model Grubu")
    fig.tight_layout()
    _save(fig, folder, "12_model_ay_heatmap")
