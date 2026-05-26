"""Yeni Dağıtım — Excel yükle + hedefleri gir + optimize et."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Yeni Dağıtım", page_icon="⚡", layout="wide")

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _to_excel(df: pd.DataFrame) -> bytes:
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dağıtım")
    return buf.getvalue()

# ---------------------------------------------------------------------------
# Stil
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.step-box {
    background: #F0F4F8; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 16px;
    border-left: 4px solid #1565C0;
}
.step-title { font-size: 16px; font-weight: 700; color: #1565C0; margin-bottom: 8px; }
.step-desc  { font-size: 13px; color: #475569; }
.total-chip {
    display:inline-block; background:#1565C0; color:white;
    border-radius:20px; padding:4px 14px; font-weight:700; font-size:14px;
}
</style>
""", unsafe_allow_html=True)

st.title("⚡ Yeni Dağıtım")
st.caption("Envanter dosyasını yükleyin, bayi hedeflerini girin ve optimal dağıtımı hesaplayın.")

# ---------------------------------------------------------------------------
# İlerleme çubuğu
# ---------------------------------------------------------------------------
def progress_bar(active: int) -> None:
    steps = ["1 Envanter", "2 Hedefler", "3 Optimize", "4 Sonuçlar"]
    cols = st.columns(4)
    for i, (col, label) in enumerate(zip(cols, steps)):
        done = i < active
        current = i == active
        bg = "#1565C0" if current else ("#4CAF50" if done else "#E2E8F0")
        fg = "white" if (current or done) else "#94A3B8"
        col.markdown(
            f"<div style='text-align:center;padding:8px;border-radius:8px;"
            f"background:{bg};color:{fg};font-weight:600;font-size:13px'>"
            f"{'✓ ' if done else ''}{label}</div>",
            unsafe_allow_html=True,
        )


# Hangi adımda olduğumuzu belirle
has_inventory = "inv_pool" in st.session_state
has_targets   = "target_df" in st.session_state
has_result    = "alloc_result" in st.session_state

active_step = 0
if has_inventory:
    active_step = 1
if has_targets:
    active_step = 2
if has_result:
    active_step = 3

progress_bar(active_step)
st.divider()

# ===========================================================================
# ADIM 1 — ENVANTER
# ===========================================================================
with st.expander("**Adım 1 — Envanter Dosyası Yükle**", expanded=not has_inventory):
    st.markdown("""
    **Desteklenen formatlar:** Excel (.xlsx) veya CSV (.csv ; delimiter)

    **Gerekli sütunlar:**
    `Dealer Code Processing` · `Dispatchable` · `Month Number` ·
    `Model Description` · `Vehicle Version` · `Exterior Color`
    """)

    month_tr = st.selectbox(
        "Dağıtım ayı",
        ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
        key="month_select",
    )
    month_map = {
        "Ocak": ("January", 1), "Şubat": ("February", 2), "Mart": ("March", 3),
        "Nisan": ("April", 4), "Mayıs": ("May", 5), "Haziran": ("June", 6),
        "Temmuz": ("July", 7), "Ağustos": ("August", 8), "Eylül": ("September", 9),
        "Ekim": ("October", 10), "Kasım": ("November", 11), "Aralık": ("December", 12),
    }
    month_en, month_num = month_map[month_tr]

    uploaded = st.file_uploader(
        "Envanter dosyasını sürükleyin veya seçin",
        type=["xlsx", "xls", "csv"],
        key="inv_uploader",
    )

    if uploaded:
        with st.spinner("Dosya okunuyor..."):
            try:
                from src.allocation.data_prep import (
                    MONTH_LABEL_VARIANTS,
                    _read_file,
                    inventory_summary,
                )

                suffix = Path(uploaded.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = Path(tmp.name)

                raw_df = _read_file(tmp_path)

                # Month Number sütunundaki değerler ne olursa olsun eşleştir
                labels = MONTH_LABEL_VARIANTS.get(month_en, [month_en, "Current Month"])
                mask = (
                    (raw_df["Dealer Code Processing"] == "CENT-STOCK")
                    & (raw_df["Dispatchable"] == "Y")
                    & (raw_df["Month Number"].isin(labels))
                )
                pool = raw_df[mask].copy()
                pool["vehicle_type"] = (
                    pool["Model Description"].str.strip()
                    + " / "
                    + pool["Vehicle Version"].str.strip()
                    + " / "
                    + pool["Exterior Color"].str.strip()
                )
                pool = pool.reset_index(drop=True)
                tmp_path.unlink()

                if pool.empty:
                    st.error(
                        f"Filtre sonucu boş geldi. Dosyada 'CENT-STOCK' + 'Dispatchable=Y' + "
                        f"ay='{month_en}' olan satır bulunamadı. "
                        f"Dosyadaki 'Month Number' değerlerini kontrol edin."
                    )
                    with st.expander("Month Number sütunundaki değerler"):
                        st.write(raw_df["Month Number"].value_counts().to_dict())
                else:
                    inv_sum = inventory_summary(pool)
                    st.session_state["inv_pool"]    = pool
                    st.session_state["inv_summary"] = inv_sum
                    st.session_state["month_tr"]    = month_tr
                    st.session_state["month_num"]   = month_num

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Toplam Araç", len(pool))
                    c2.metric("Farklı Tip", len(inv_sum))
                    c3.metric("Model", inv_sum["model"].nunique())

                    with st.expander("Envanter Özeti (ilk 10 tip)"):
                        st.dataframe(inv_sum.head(10), use_container_width=True, hide_index=True)

                    st.success(f"✓ {len(pool)} araç yüklendi.")
                    if st.button("Adım 2'ye Geç →", type="primary", key="go_step2"):
                        st.rerun()

            except Exception as exc:
                st.error(f"Hata: {exc}")

    elif has_inventory:
        pool    = st.session_state["inv_pool"]
        inv_sum = st.session_state["inv_summary"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Araç", len(pool))
        c2.metric("Farklı Tip", len(inv_sum))
        c3.metric("Model", inv_sum["model"].nunique())
        st.success(f"✓ Envanter yüklendi ({st.session_state.get('month_tr', '')}). Değiştirmek için yeni dosya yükleyin.")

# ===========================================================================
# ADIM 2 — BAYİ HEDEFLERİ
# ===========================================================================
if has_inventory:
    with st.expander("**Adım 2 — Aylık Bayi Hedeflerini Girin**", expanded=not has_targets):

        st.markdown("Her bayi için **Hedef** sütununa o ay dağıtılacak araç adedini girin.")

        # Şablon: mevcut bayi listesi, hedefler sıfır
        template_path = ROOT / "data" / "raw" / "dealer_target_january26.csv"
        if "editor_df" not in st.session_state:
            if template_path.exists():
                tmpl = pd.read_csv(template_path, sep=";", encoding="utf-8-sig")
                tmpl.columns = tmpl.columns.str.strip()
                tmpl = tmpl.rename(columns={
                    "Dealer Name": "Bayi Adı",
                    "Dealer Code": "Bayi Kodu",
                    "Target": "Hedef",
                })
                tmpl["Hedef"] = 0
            else:
                tmpl = pd.DataFrame({
                    "Bayi Adı":  [f"DEALER {i}" for i in range(1, 6)],
                    "Bayi Kodu": [f"BA-0-XXX-{i:02d}" for i in range(1, 6)],
                    "Hedef":     [0] * 5,
                })
            st.session_state["editor_df"] = tmpl

        edited = st.data_editor(
            st.session_state["editor_df"],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Bayi Adı":  st.column_config.TextColumn("Bayi Adı", disabled=True),
                "Bayi Kodu": st.column_config.TextColumn("Bayi Kodu", disabled=True),
                "Hedef":     st.column_config.NumberColumn(
                    "Hedef (araç)",
                    min_value=0,
                    max_value=500,
                    step=1,
                    help="Bu bayi için dağıtılacak araç adedi",
                ),
            },
            key="target_editor",
        )

        total_demand = int(edited["Hedef"].sum())
        total_supply = len(st.session_state["inv_pool"])
        supply_ok    = total_demand <= total_supply

        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.markdown(
                f"Toplam talep: **{total_demand} araç** &nbsp;|&nbsp; "
                f"Mevcut arz: **{total_supply} araç** &nbsp;|&nbsp; "
                + (f"✅ Arz yeterli" if supply_ok else f"⚠️ Talep arzi aşıyor!"),
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Hedefleri Kaydet →", type="primary", use_container_width=True):
                if total_demand == 0:
                    st.warning("En az bir bayi için hedef girin.")
                elif not supply_ok:
                    st.error(f"Toplam hedef ({total_demand}) envanterdeki araç sayısını ({total_supply}) aşıyor.")
                else:
                    targets_df = edited.rename(columns={
                        "Bayi Adı": "dealer_name",
                        "Bayi Kodu": "dealer_code",
                        "Hedef": "target",
                    })
                    targets_df["target"] = targets_df["target"].astype(int)
                    st.session_state["target_df"]      = targets_df
                    st.session_state["editor_df"]      = edited
                    st.session_state["total_demand"]   = total_demand
                    st.rerun()

    if has_targets:
        demand = st.session_state["total_demand"]
        supply = len(st.session_state["inv_pool"])
        st.info(
            f"✓ Hedefler kaydedildi — Toplam talep: **{demand}** araç / "
            f"Arz: **{supply}** araç. Değiştirmek için yukarıyı açın.",
            icon="✅",
        )

# ===========================================================================
# ADIM 3 — OPTİMİZE ET
# ===========================================================================
if has_inventory and has_targets:
    st.markdown("### Adım 3 — Dağıtımı Hesapla")

    if st.button(
        "🚀  Optimal Dağıtımı Hesapla",
        type="primary",
        use_container_width=True,
        disabled=has_result,
    ):
        pool    = st.session_state["inv_pool"]
        inv_sum = st.session_state["inv_summary"]
        targets = st.session_state["target_df"]
        m_num   = st.session_state.get("month_num", 1)

        prog = st.progress(0, text="Başlatılıyor...")

        try:
            from src.allocation.data_prep import inventory_summary
            from src.allocation.optimizer import run_optimizer
            from src.allocation.scorer import (
                compute_composite_scores,
                compute_h_scores,
                compute_lp_affinity,
                compute_p_scores,
                compute_s_scores,
            )
            from src.analysis.data_loader import load_monthly_performance, load_sales

            dealer_names  = targets[targets["target"] > 0]["dealer_name"].tolist()
            vehicle_types = inv_sum["vehicle_type"].tolist()

            prog.progress(15, "Satış geçmişi yükleniyor...")
            try:
                df_sales = load_sales()
            except Exception:
                df_sales = pd.DataFrame()

            prog.progress(30, "Performans verisi yükleniyor...")
            try:
                df_perf = load_monthly_performance()
            except Exception:
                df_perf = pd.DataFrame()

            prog.progress(45, "Bayi skorları hesaplanıyor...")
            p_scores  = compute_p_scores(df_perf, dealer_names)
            lp_aff    = compute_lp_affinity(df_sales, dealer_names, vehicle_types)
            s_scores  = compute_s_scores(dealer_names, month=m_num)
            h_scores  = compute_h_scores(targets[targets["target"] > 0])
            composite = compute_composite_scores(p_scores, s_scores, h_scores, dealer_names)

            prog.progress(70, "MILP optimizasyonu çalışıyor...")
            allocation = run_optimizer(inv_sum, targets, composite, lp_aff)

            score_df = pd.DataFrame({
                "dealer_name":     dealer_names,
                "p_score":         p_scores.reindex(dealer_names).values,
                "s_score":         s_scores.reindex(dealer_names).values,
                "h_score":         h_scores.reindex(dealer_names).values,
                "composite_score": composite.reindex(dealer_names).values,
            })

            prog.progress(100, "Tamamlandı!")
            st.session_state["alloc_result"] = allocation
            st.session_state["score_result"] = score_df
            st.success("✓ Dağıtım tamamlandı!")
            st.rerun()

        except Exception as exc:
            prog.empty()
            st.error(f"Hata: {exc}")

    if has_result:
        st.success("✓ Dağıtım hesaplandı. Yeniden hesaplamak için sayfayı yenileyin.")

# ===========================================================================
# ADIM 4 — SONUÇLAR
# ===========================================================================
if has_result:
    allocation = st.session_state["alloc_result"]
    score_df   = st.session_state["score_result"]
    targets    = st.session_state["target_df"]
    month_label = st.session_state.get("month_tr", "")

    st.divider()
    st.markdown(f"### Adım 4 — Sonuçlar · {month_label}")

    # Özet tablo
    summary = allocation.groupby("dealer_name")["allocated_qty"].sum().reset_index()
    summary.columns = ["dealer_name", "allocated"]
    summary = summary.merge(
        targets[["dealer_name", "dealer_code", "target"]], on="dealer_name", how="left"
    )
    summary["gap"]       = summary["allocated"] - summary["target"]
    summary["fill_rate"] = (summary["allocated"] / summary["target"].replace(0, 1) * 100).round(1)

    total_alloc  = int(allocation["allocated_qty"].sum())
    total_target = int(targets["target"].sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Atanan", f"{total_alloc:,}", f"/{total_target:,} hedef")
    k2.metric("Doluluk Oranı", f"{total_alloc/total_target*100:.0f}%" if total_target else "—")
    k3.metric("Aktif Bayi", len(summary))
    k4.metric("Araç Tipi Çeşidi", allocation["vehicle_type"].nunique())

    tab1, tab2, tab3, tab4 = st.tabs(["Dağıtım Tablosu", "Bayi Özeti", "Model Dağılımı", "Skor Analizi"])

    # --- Tab 1: Dağıtım Tablosu ---
    with tab1:
        dealer_f = st.multiselect(
            "Bayi filtrele", sorted(allocation["dealer_name"].unique()), key="r_dealer"
        )
        model_f = st.multiselect(
            "Model filtrele", sorted(allocation["model"].unique()), key="r_model"
        )
        view = allocation.copy()
        if dealer_f:
            view = view[view["dealer_name"].isin(dealer_f)]
        if model_f:
            view = view[view["model"].isin(model_f)]

        st.dataframe(
            view.rename(columns={
                "dealer_name": "Bayi", "dealer_code": "Kod",
                "model": "Model", "version": "Versiyon", "color": "Renk",
                "allocated_qty": "Atanan", "composite_score": "Skor",
                "lp_affinity_score": "LP",
            }),
            use_container_width=True, hide_index=True,
        )

        excel_bytes = _to_excel(allocation)
        st.download_button(
            "⬇️  Tam Dağıtımı Excel Olarak İndir",
            data=excel_bytes,
            file_name=f"dagitim_{month_label.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # --- Tab 2: Bayi Özeti + Grafik ---
    with tab2:
        fig = px.bar(
            summary.sort_values("allocated"),
            x=["target", "allocated"],
            y="dealer_name",
            orientation="h",
            barmode="group",
            labels={"value": "Araç Adedi", "dealer_name": "Bayi", "variable": ""},
            color_discrete_map={"target": "#90CAF9", "allocated": "#1565C0"},
            title=f"{month_label} — Bayi Hedef vs Atanan",
        )
        fig.update_layout(height=max(400, len(summary) * 28), legend_title_text="")
        fig.for_each_trace(lambda t: t.update(name={"target": "Hedef", "allocated": "Atanan"}[t.name]))
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            summary.rename(columns={
                "dealer_name": "Bayi", "dealer_code": "Kod",
                "target": "Hedef", "allocated": "Atanan",
                "gap": "Fark", "fill_rate": "Doluluk %",
            }).sort_values("Atanan", ascending=False),
            use_container_width=True, hide_index=True,
        )

    # --- Tab 3: Model Dağılımı ---
    with tab3:
        pivot = (
            allocation.groupby(["dealer_name", "model"])["allocated_qty"]
            .sum()
            .reset_index()
        )
        fig2 = px.bar(
            pivot,
            x="allocated_qty",
            y="dealer_name",
            color="model",
            orientation="h",
            barmode="stack",
            labels={"allocated_qty": "Araç", "dealer_name": "Bayi", "model": "Model"},
            title=f"{month_label} — Bayi × Model Dağılımı",
        )
        fig2.update_layout(height=max(400, len(summary) * 28))
        st.plotly_chart(fig2, use_container_width=True)

    # --- Tab 4: Skor Analizi ---
    with tab4:
        fig3 = px.bar(
            score_df.sort_values("composite_score"),
            x=["p_score", "s_score", "h_score"],
            y="dealer_name",
            orientation="h",
            barmode="group",
            labels={"value": "Skor [0-1]", "dealer_name": "Bayi", "variable": ""},
            color_discrete_map={
                "p_score": "#42A5F5",
                "s_score": "#66BB6A",
                "h_score": "#FFA726",
            },
            title="Bayi Skor Bileşenleri",
        )
        fig3.update_layout(height=max(400, len(score_df) * 28))
        fig3.for_each_trace(lambda t: t.update(
            name={"p_score": "P (Performans)", "s_score": "S (Mevsim)", "h_score": "H (Hedef)"}[t.name]
        ))
        st.plotly_chart(fig3, use_container_width=True)
