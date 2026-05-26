"""Yeni Dağıtım — dosya yükle ve optimize et."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Yeni Dağıtım", page_icon="⚡", layout="wide")

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.title("⚡ Yeni Dağıtım")
st.caption("Envanter ve bayi hedef dosyalarını yükleyin; sistem optimal dağıtımı hesaplayıp sunacak.")

# ---------------------------------------------------------------------------
# Adım göstergesi
# ---------------------------------------------------------------------------
steps = ["1️⃣ Envanter", "2️⃣ Hedefler", "3️⃣ Optimize Et", "4️⃣ Sonuçlar"]
step_cols = st.columns(4)
for i, (col, label) in enumerate(zip(step_cols, steps)):
    col.markdown(
        f"<div style='text-align:center; padding:8px; border-radius:8px; "
        f"background:{'#1565C0' if i == 0 else '#E2E8F0'}; "
        f"color:{'white' if i == 0 else '#64748B'}; font-weight:600'>{label}</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Adım 1: Envanter
# ---------------------------------------------------------------------------
with st.expander("**Adım 1 — Envanter Dosyası**", expanded=True):
    st.markdown("""
    Dağıtılacak araç havuzu CSV dosyasını yükleyin.

    Beklenen sütunlar: `Dealer Code Processing`, `Dispatchable`, `Month Number`,
    `Model Description`, `Vehicle Version`, `Exterior Color`

    *Aynı formatta:* `NORTHSTAR-BULUNURLUK-JANUARY-2TH-csv.csv`
    """)

    use_existing_inv = st.checkbox("Mevcut Ocak 2026 envanterini kullan", value=True)

    inv_file = None
    if not use_existing_inv:
        inv_file = st.file_uploader(
            "Envanter CSV yükle",
            type=["csv"],
            key="inv_upload",
            help="UTF-8 veya UTF-8-BOM, noktalı virgül (;) delimiter",
        )
        if inv_file:
            df_preview = pd.read_csv(inv_file, sep=";", encoding="utf-8-sig", nrows=5)
            st.dataframe(df_preview, use_container_width=True)
            inv_file.seek(0)

    month_options = {
        "Ocak": (["January", "Current Month"], 1),
        "Şubat": (["February", "Current Month"], 2),
        "Mart": (["March", "Current Month"], 3),
        "Nisan": (["April", "Current Month"], 4),
        "Mayıs": (["May", "Current Month"], 5),
        "Haziran": (["June", "Current Month"], 6),
    }
    month_label = st.selectbox("Dağıtım ayı", list(month_options.keys()))
    month_labels, month_num = month_options[month_label]

# ---------------------------------------------------------------------------
# Adım 2: Hedefler
# ---------------------------------------------------------------------------
with st.expander("**Adım 2 — Bayi Hedefleri**", expanded=True):
    st.markdown("""
    Bayi aylık hedeflerini içeren CSV dosyasını yükleyin.

    Beklenen sütunlar: `Dealer Name`, `Dealer Code`, `Target`
    """)

    use_existing_tgt = st.checkbox("Mevcut Ocak 2026 hedeflerini kullan", value=True)

    tgt_file = None
    if not use_existing_tgt:
        tgt_file = st.file_uploader(
            "Hedef CSV yükle",
            type=["csv"],
            key="tgt_upload",
            help="UTF-8 veya UTF-8-BOM, noktalı virgül (;) delimiter",
        )
        if tgt_file:
            df_preview_t = pd.read_csv(tgt_file, sep=";", encoding="utf-8-sig", nrows=10)
            st.dataframe(df_preview_t, use_container_width=True)
            tgt_file.seek(0)

# ---------------------------------------------------------------------------
# Adım 3: Optimize Et
# ---------------------------------------------------------------------------
st.markdown("### Adım 3 — Optimize Et")

ready = True
if not use_existing_inv and inv_file is None:
    st.warning("Envanter dosyası yükleyin veya mevcut envanteri seçin.")
    ready = False
if not use_existing_tgt and tgt_file is None:
    st.warning("Hedef dosyası yükleyin veya mevcut hedefleri seçin.")
    ready = False

if ready and st.button("🚀  Dağıtımı Hesapla", type="primary", use_container_width=True):
    with st.spinner("Veriler hazırlanıyor..."):
        try:
            from src.allocation.data_prep import inventory_summary, load_inventory, load_targets
            from src.allocation.optimizer import run_optimizer
            from src.allocation.scorer import (
                compute_composite_scores,
                compute_h_scores,
                compute_lp_affinity,
                compute_p_scores,
                compute_s_scores,
            )
            from src.analysis.data_loader import load_monthly_performance, load_sales

            # Envanter
            if use_existing_inv:
                pool = load_inventory(month_labels=month_labels)
            else:
                import tempfile, os
                suffix = Path(inv_file.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(inv_file.read())
                    tmp_path = Path(tmp.name)
                pool = load_inventory(path=tmp_path, month_labels=month_labels)
                os.unlink(tmp_path)

            inv_sum = inventory_summary(pool)

            # Hedefler
            if use_existing_tgt:
                targets = load_targets()
            else:
                import tempfile, os
                suffix = Path(tgt_file.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(tgt_file.read())
                    tmp_path = Path(tmp.name)
                targets = load_targets(path=tmp_path)
                os.unlink(tmp_path)

        except Exception as exc:
            st.error(f"Veri yükleme hatası: {exc}")
            st.stop()

    with st.spinner("Skorlar hesaplanıyor..."):
        try:
            dealer_names  = targets[targets["target"] > 0]["dealer_name"].tolist()
            vehicle_types = inv_sum["vehicle_type"].tolist()

            df_perf = load_monthly_performance()
            df_sales = load_sales()

            p_scores  = compute_p_scores(df_perf, dealer_names)
            lp_aff    = compute_lp_affinity(df_sales, dealer_names, vehicle_types)
            s_scores  = compute_s_scores(dealer_names, month=month_num)
            h_scores  = compute_h_scores(targets[targets["target"] > 0])
            composite = compute_composite_scores(p_scores, s_scores, h_scores, dealer_names)
        except Exception as exc:
            st.error(f"Skorlama hatası: {exc}")
            st.stop()

    with st.spinner("MILP optimizasyonu çalıştırılıyor..."):
        try:
            allocation = run_optimizer(inv_sum, targets, composite, lp_aff)
        except Exception as exc:
            st.error(f"Optimizasyon hatası: {exc}")
            st.stop()

    score_df = pd.DataFrame({
        "dealer_name":     dealer_names,
        "p_score":         p_scores.reindex(dealer_names).values,
        "s_score":         s_scores.reindex(dealer_names).values,
        "h_score":         h_scores.reindex(dealer_names).values,
        "composite_score": composite.reindex(dealer_names).values,
    })

    st.session_state["allocation_result"]  = allocation
    st.session_state["score_result"]       = score_df
    st.session_state["inv_summary_result"] = inv_sum
    st.session_state["targets_result"]     = targets
    st.session_state["run_month"]          = month_label
    st.success("Dağıtım tamamlandı! Sonuçlar aşağıda.")
    st.rerun()

# ---------------------------------------------------------------------------
# Adım 4: Sonuçlar
# ---------------------------------------------------------------------------
if "allocation_result" in st.session_state:
    allocation = st.session_state["allocation_result"]
    score_df   = st.session_state["score_result"]
    inv_sum    = st.session_state["inv_summary_result"]
    targets    = st.session_state["targets_result"]
    run_month  = st.session_state.get("run_month", "")

    st.divider()
    st.markdown(f"### Adım 4 — Sonuçlar · {run_month}")

    summary = allocation.groupby("dealer_name")["allocated_qty"].sum().reset_index()
    summary.columns = ["dealer_name", "allocated"]
    summary = summary.merge(
        targets[["dealer_name", "dealer_code", "target"]], on="dealer_name", how="left"
    )
    summary["gap"]       = summary["allocated"] - summary["target"]
    summary["fill_rate"] = (summary["allocated"] / summary["target"] * 100).round(1)

    total_alloc  = int(summary["allocated"].sum())
    total_target = int(summary["target"].sum())

    km1, km2, km3, km4 = st.columns(4)
    km1.metric("Toplam Atanan", f"{total_alloc:,}", f"/{total_target:,} hedef")
    km2.metric("Doluluk", f"{total_alloc/total_target*100:.0f}%")
    km3.metric("Aktif Bayi", len(summary))
    km4.metric("Araç Tipi", allocation["vehicle_type"].nunique())

    res_tab1, res_tab2, res_tab3 = st.tabs(["Dağıtım Tablosu", "Bayi Özeti", "Skor Analizi"])

    with res_tab1:
        dealer_f = st.multiselect(
            "Bayi filtrele", sorted(allocation["dealer_name"].unique()), key="res_dealer"
        )
        df_view = allocation[allocation["dealer_name"].isin(dealer_f)] if dealer_f else allocation
        st.dataframe(
            df_view.rename(columns={
                "dealer_name": "Bayi", "dealer_code": "Kod",
                "model": "Model", "version": "Versiyon", "color": "Renk",
                "allocated_qty": "Atanan", "composite_score": "Skor",
                "lp_affinity_score": "LP",
            }),
            use_container_width=True, hide_index=True,
        )

        csv_bytes = allocation.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            "⬇️  Dağıtım CSV İndir",
            data=csv_bytes,
            file_name=f"allocation_{run_month.lower()}.csv",
            mime="text/csv",
        )

    with res_tab2:
        st.dataframe(
            summary.rename(columns={
                "dealer_name": "Bayi", "dealer_code": "Kod",
                "target": "Hedef", "allocated": "Atanan",
                "gap": "Fark", "fill_rate": "Doluluk %",
            }).sort_values("Atanan", ascending=False),
            use_container_width=True, hide_index=True,
        )

    with res_tab3:
        df_sc = score_df.copy()
        for col in ["p_score", "s_score", "h_score", "composite_score"]:
            df_sc[col] = df_sc[col].map("{:.3f}".format)
        st.dataframe(
            df_sc.rename(columns={
                "dealer_name": "Bayi",
                "p_score": "P (Perf)",
                "s_score": "S (Mevsim)",
                "h_score": "H (Hedef)",
                "composite_score": "Bileşik",
            }).sort_values("Bileşik", ascending=False),
            use_container_width=True, hide_index=True,
        )
