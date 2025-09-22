# -*- coding: utf-8 -*-
import argparse, sys, math, json
from datetime import datetime, timezone
from pathlib import Path
import MetaTrader5 as mt5

from pathlib import Path as _Path

# log absolu basé sur l’emplacement du fichier
_LOGP = _Path(__file__).resolve().parent.parent / "logs" / "guardrails.log"


def log(msg):
    from datetime import datetime as _dt

    ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        _LOGP.parent.mkdir(parents=True, exist_ok=True)
        with _LOGP.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass
    print(msg)


log("guardrails logger ready")  # dès l’import


LOGP = Path("logs/guardrails.log")


def log(msg):
    from datetime import datetime

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        LOGP.parent.mkdir(parents=True, exist_ok=True)
        with LOGP.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass
    print(msg)


DEF_PROFILE = {"risk_per_trade_pct": 0.25, "max_daily_loss_pct": 5, "max_total_loss_pct": 10}


def load_profile():
    p = Path("logs/ftmo_profile.json")
    prof = {}
    if p.exists():
        try:
            prof = json.loads(p.read_text()).get("bot_profile", {}) or {}
        except Exception:
            prof = {}
    out = DEF_PROFILE | prof
    out["initial_balance"] = float(prof.get("account_tier") or 0) or None
    return out


def lots_from_risk(symbol, entry, sl, risk_amount):
    si = mt5.symbol_info(symbol)
    if si is None:
        raise RuntimeError(f"Symbol {symbol} not found")
    if not si.visible:
        mt5.symbol_select(symbol, True)
    tick_val = float(si.trade_tick_value)
    tick_sz = float(si.trade_tick_size)
    if tick_sz <= 0 or tick_val <= 0:
        raise RuntimeError("Invalid tick_size/tick_value")
    sl_dist = abs(entry - sl)
    if sl_dist <= 0:
        raise RuntimeError("SL distance must be > 0")
    risk_per_lot = (sl_dist / tick_sz) * tick_val
    lots = risk_amount / risk_per_lot
    step = float(si.volume_step or 0.01)
    vmin = float(si.volume_min or 0.01)
    vmax = float(si.volume_max or 100.0)
    lots = math.floor(max(vmin, min(lots, vmax)) / step) * step
    return round(max(vmin, min(lots, vmax)), 2 if step < 0.1 else 1)


def potential_loss_currency(symbol, entry, sl, lots):
    si = mt5.symbol_info(symbol)
    tick_val = float(si.trade_tick_value)
    tick_sz = float(si.trade_tick_size)
    sl_dist = abs(entry - sl)
    loss_per_lot = (sl_dist / tick_sz) * tick_val
    return float(lots) * loss_per_lot


def today_closed_pnl(login):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(start, now) or []
    pnl = 0.0
    for d in deals:
        if getattr(d, "login", login) != login:
            continue
        pnl += float(d.profit) + float(getattr(d, "swap", 0.0)) + float(getattr(d, "commission", 0.0))
    return pnl


def open_positions_pnl(login):
    pos = mt5.positions_get() or []
    pnl = 0.0
    for p in pos:
        if getattr(p, "login", login) != login:
            continue
        pnl += float(p.profit)
    return pnl


def guardrails_allow(a, ai, prof, entry, lots):
    ref_balance = float(prof.get("initial_balance") or ai.balance)
    max_daily_loss_amt = ref_balance * (float(prof["max_daily_loss_pct"]) / 100.0)
    max_total_loss_amt = ref_balance * (float(prof["max_total_loss_pct"]) / 100.0)
    closed = today_closed_pnl(ai.login)
    floating = open_positions_pnl(ai.login)
    used_today_loss = max(0.0, -(closed + min(floating, 0.0)))
    pot_loss = potential_loss_currency(a.symbol, entry, a.sl, lots)
    if used_today_loss + pot_loss >= max_daily_loss_amt:
        log(f"BLOCKED: daily loss {used_today_loss:.2f} + potential {pot_loss:.2f} > limit {max_daily_loss_amt:.2f}")
        return False
    min_equity = ref_balance - max_total_loss_amt
    if (ai.equity - pot_loss) < min_equity:
        log(f"BLOCKED: equity after potential loss {ai.equity - pot_loss:.2f} < min equity {min_equity:.2f}")
        return False
    return True


def send_order(a):
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
    ai = mt5.account_info()
    if ai is None:
        raise RuntimeError(f"account_info() failed: {mt5.last_error()}")
    prof = load_profile()
    si = mt5.symbol_info(a.symbol)
    if si is None:
        raise RuntimeError(f"Symbol {a.symbol} not found")
    if not si.visible:
        mt5.symbol_select(a.symbol, True)
    tick = mt5.symbol_info_tick(a.symbol)
    mkt_price = float(tick.ask if a.side == "buy" else tick.bid)
    entry = float(a.entry) if a.entry is not None else mkt_price
    risk_pct = float(a.risk_pct) if a.risk_pct is not None else float(prof["risk_per_trade_pct"])
    risk_amount = float(ai.balance) * (risk_pct / 100.0)
    lots = float(a.lots) if a.lots else lots_from_risk(a.symbol, entry, float(a.sl), risk_amount)
    if not guardrails_allow(a, ai, prof, entry, lots):
        mt5.shutdown()
        sys.exit(2)
    if a.pending:
        typ = mt5.ORDER_TYPE_BUY_LIMIT if a.side == "buy" else mt5.ORDER_TYPE_SELL_LIMIT
        price = float(entry)
        action = mt5.TRADE_ACTION_PENDING
    else:
        typ = mt5.ORDER_TYPE_BUY if a.side == "buy" else mt5.ORDER_TYPE_SELL
        price = mkt_price
        action = mt5.TRADE_ACTION_DEAL
    req = {
        "action": action,
        "symbol": a.symbol,
        "volume": float(lots),
        "type": typ,
        "price": price,
        "sl": float(a.sl),
        "tp": float(a.tp),
        "deviation": 10,
        "type_filling": mt5.ORDER_FILLING_FOK,
        "type_time": mt5.ORDER_TIME_GTC,
        "comment": f"AUTO_FTMO r{risk_pct:.2f}%",
    }
    res = mt5.order_send(req)
    if res is None:
        raise RuntimeError(f"order_send() failed: {mt5.last_error()}")
    log(f"OK lots={lots} retcode={res.retcode} comment={res.comment}")
    mt5.shutdown()


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", choices=["buy", "sell"], required=True)
    p.add_argument("--sl", type=float, required=True)
    p.add_argument("--tp", type=float, required=True)
    p.add_argument("--pending", action="store_true")
    p.add_argument("--entry", type=float)
    p.add_argument("--risk-pct", dest="risk_pct", type=float)
    p.add_argument("--lots", type=float)
    return p.parse_args()


if __name__ == "__main__":
    try:
        send_order(parse())
    except Exception as e:
        log(f"ERR {e}")
        sys.exit(1)
