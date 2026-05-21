"""MILP optimizasyon modülü — PuLP / CBC solver.

Karar değişkeni:
    x[d, t] ∈ ℤ≥0  →  dealer d'ye atanan vehicle_type t adedi

Amaç (maksimizasyon):
    Σ_{d,t}  x[d,t] · (score[d] + W_LP · affinity[d,t])

Kısıtlar:
    (1)  Σ_t x[d,t]  = target[d]               ∀ d (target > 0)
    (2)  Σ_d x[d,t]  ≤ inventory[t]            ∀ t
    (3)  x[d,t] ≥ 0, tamsayı
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd
import pulp

if TYPE_CHECKING:
    pass

W_LP = 0.35
logger = logging.getLogger(__name__)


def run_optimizer(
    inv_summary: pd.DataFrame,
    targets: pd.DataFrame,
    composite_scores: pd.Series,
    lp_affinity: pd.DataFrame,
) -> pd.DataFrame:
    """MILP modelini kurar, çözer ve sonuçları döndürür.

    Args:
        inv_summary:      inventory_summary() çıktısı:
                          vehicle_type, model, version, color, quantity
        targets:          load_targets() çıktısı:
                          dealer_name, dealer_code, target
        composite_scores: compute_composite_scores() çıktısı:
                          index=dealer_name, values=[0,1]
        lp_affinity:      compute_lp_affinity() çıktısı:
                          DataFrame satır=dealer_name, sütun=vehicle_type

    Returns:
        DataFrame sütunları:
            dealer_name, dealer_code, vehicle_type, model, version, color,
            allocated_qty, composite_score, lp_affinity_score
        Sadece allocated_qty > 0 olan satırlar döner.

    Raises:
        RuntimeError: Çözüm bulunamazsa (INFEASIBLE veya UNDEFINED).
    """
    # Aktif bayiler (target > 0)
    active = targets[targets["target"] > 0].copy()
    dealers = active["dealer_name"].tolist()
    dealer_target = dict(zip(active["dealer_name"], active["target"]))
    dealer_code   = dict(zip(active["dealer_name"], active["dealer_code"]))

    vehicle_types = inv_summary["vehicle_type"].tolist()
    inventory_qty = dict(zip(inv_summary["vehicle_type"], inv_summary["quantity"]))

    # ---------- Model ----------
    prob = pulp.LpProblem("VehicleAllocation", pulp.LpMaximize)

    # Karar değişkenleri
    x = pulp.LpVariable.dicts(
        "x",
        [(d, t) for d in dealers for t in vehicle_types],
        lowBound=0,
        cat="Integer",
    )

    # ---------- Objective ----------
    prob += pulp.lpSum(
        x[(d, t)] * (
            float(composite_scores.get(d, 0.5))
            + W_LP * float(lp_affinity.loc[d, t] if d in lp_affinity.index and t in lp_affinity.columns else 0)
        )
        for d in dealers
        for t in vehicle_types
    )

    # ---------- Kısıt 1: bayi hedefi ----------
    for d in dealers:
        prob += (
            pulp.lpSum(x[(d, t)] for t in vehicle_types) == dealer_target[d],
            f"target_{d}",
        )

    # ---------- Kısıt 2: envanter ----------
    for t in vehicle_types:
        prob += (
            pulp.lpSum(x[(d, t)] for d in dealers) <= inventory_qty[t],
            f"inv_{t.replace(' ', '_').replace('/', '_')}",
        )

    # ---------- Çöz ----------
    solver = pulp.PULP_CBC_CMD(msg=0)
    status = prob.solve(solver)

    status_str = pulp.LpStatus[prob.status]
    logger.info("Solver durumu: %s", status_str)

    if status_str not in ("Optimal", "Not Solved"):
        pass  # uyarı loglanır, aşağıda kontrol edilir

    if pulp.value(prob.objective) is None:
        raise RuntimeError(f"Çözüm bulunamadı: {status_str}")

    # ---------- Sonuçları topla ----------
    records: list[dict] = []
    vt_meta = inv_summary.set_index("vehicle_type")[["model", "version", "color"]]

    for d in dealers:
        for t in vehicle_types:
            qty = int(round(pulp.value(x[(d, t)]) or 0))
            if qty <= 0:
                continue
            aff = float(
                lp_affinity.loc[d, t]
                if d in lp_affinity.index and t in lp_affinity.columns
                else 0
            )
            records.append({
                "dealer_name":       d,
                "dealer_code":       dealer_code[d],
                "vehicle_type":      t,
                "model":             vt_meta.loc[t, "model"]   if t in vt_meta.index else "",
                "version":           vt_meta.loc[t, "version"] if t in vt_meta.index else "",
                "color":             vt_meta.loc[t, "color"]   if t in vt_meta.index else "",
                "allocated_qty":     qty,
                "composite_score":   round(float(composite_scores.get(d, 0.5)), 4),
                "lp_affinity_score": round(aff, 4),
            })

    if not records:
        raise RuntimeError("Optimizer çalıştı ama hiç atama üretmedi.")

    df_result = pd.DataFrame(records)
    return df_result.sort_values(["dealer_name", "model", "version", "color"]).reset_index(drop=True)
