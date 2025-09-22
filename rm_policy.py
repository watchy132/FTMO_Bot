import math


def lot_size(
    equity, risk_pct, sl_pips, pip_value, lot_step=0.01, min_lot=0.01, max_lot=100.0
):
    risk_usd = equity * risk_pct
    raw = risk_usd / max(sl_pips * pip_value, 1e-9)
    stepped = math.floor(raw / lot_step) * lot_step
    return max(min(stepped, max_lot), min_lot)


def rr_effectif(
    sl_pips, tp_rr, spread_pips, commission_per_lot, slippage_pips, pip_value, lot
):
    comm_pips = commission_per_lot / (pip_value * max(lot, 1e-9))
    sl_eff = sl_pips + slippage_pips
    tp_pips = tp_rr * sl_pips
    tp_eff = max(tp_pips - spread_pips - slippage_pips - comm_pips, 0.0)
    return (tp_eff / sl_eff) if sl_eff > 0 else 0.0


def validate_setup(
    equity,
    risk_pct,
    sl_pips,
    tp_rr,
    spread_pips,
    commission_per_lot,
    slippage_pips,
    pip_value,
    lot_step=0.01,
    min_lot=0.01,
    max_lot=100.0,
    rr_min=2.0,
    rr_buffer=0.05,
):
    lot = lot_size(equity, risk_pct, sl_pips, pip_value, lot_step, min_lot, max_lot)
    rr_eff = rr_effectif(
        sl_pips, tp_rr, spread_pips, commission_per_lot, slippage_pips, pip_value, lot
    )
    ok = rr_eff >= (rr_min + rr_buffer)
    return ok, lot, rr_eff
