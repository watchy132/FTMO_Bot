import json
import time
from datetime import datetime
import pandas as pd
import MetaTrader5 as MT5
from typing import Dict, Optional

# ===================== CONFIG =====================
MAX_RISK_PCT = 1.5  # exposition max par trade (equity %)
MAX_OPEN_TRADES = 2  # nombre max de trades simultanés
CSV_JOURNAL = "journal_trades.csv"
# ==================================================


def init_mt5():
    if not MT5.initialize():
        raise RuntimeError(f"MT5 init failed: {MT5.last_error()}")
    account_info = MT5.account_info()
    if account_info is None:
        raise RuntimeError("MT5 account not logged in (ouvrir la session dans le terminal).")
    return account_info


def ensure_symbol(symbol: str):
    if not MT5.symbol_select(symbol, True):
        raise RuntimeError(f"Symbol select failed: {symbol}")


def equity_usd() -> float:
    info = MT5.account_info()
    return float(info.equity) if info else 0.0


def open_positions_count() -> int:
    poss = MT5.positions_get()
    return len(poss) if poss else 0


def price_snapshot(symbol: str) -> Dict[str, float]:
    tick = MT5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No tick for {symbol}")
    return {"bid": tick.bid, "ask": tick.ask}


def symbol_risk_metrics(symbol: str) -> Dict[str, float]:
    si = MT5.symbol_info(symbol)
    if si is None:
        raise RuntimeError(f"No symbol_info for {symbol}")
    # Per "point" cash value per 1.0 lot:
    # trade_tick_value = cash value of one tick movement
    # trade_tick_size  = price size of that tick
    # So value per 1.0 price unit = trade_tick_value / trade_tick_size
    if si.trade_tick_size == 0:
        raise RuntimeError(f"{symbol} trade_tick_size is 0")
    value_per_price_unit_per_lot = si.trade_tick_value / si.trade_tick_size
    return {
        "point": si.point,
        "value_per_price_unit_per_lot": value_per_price_unit_per_lot,
        "min_lot": si.volume_min,
        "lot_step": si.volume_step,
        "max_lot": si.volume_max,
    }


def round_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    return round(round(value / step) * step, 8)


def loss_per_lot(symbol: str, entry: float, sl: float) -> float:
    m = symbol_risk_metrics(symbol)
    stop_distance = abs(entry - sl)  # price distance
    return stop_distance * m["value_per_price_unit_per_lot"]  # $ per 1.0 lot


def compute_lot_for_risk(symbol: str, entry: float, sl: float, max_risk_pct: float) -> float:
    eq = equity_usd()
    max_loss = eq * (max_risk_pct / 100.0)
    per_lot = loss_per_lot(symbol, entry, sl)
    if per_lot <= 0:
        return 0.0
    raw_lot = max_loss / per_lot
    m = symbol_risk_metrics(symbol)
    lot = min(m["max_lot"], max(m["min_lot"], round_step(raw_lot, m["lot_step"])))
    return lot


def current_trade_risk_pct(symbol: str, entry: float, sl: float, lots: float) -> float:
    eq = equity_usd()
    if eq <= 0:
        return 999.0
    per_lot = loss_per_lot(symbol, entry, sl)
    return (per_lot * lots) / eq * 100.0


def order_type_from_setup(side: str, entry_type: str, entry: float, snapshot: Dict[str, float]):
    side = side.lower()
    entry_type = entry_type.lower()
    if entry_type == "market":
        return MT5.ORDER_TYPE_BUY if side == "buy" else MT5.ORDER_TYPE_SELL, None
    if entry_type == "limit":
        if side == "buy":
            return MT5.ORDER_TYPE_BUY_LIMIT, entry
        else:
            return MT5.ORDER_TYPE_SELL_LIMIT, entry
    if entry_type == "stop":
        if side == "buy":
            return MT5.ORDER_TYPE_BUY_STOP, entry
        else:
            return MT5.ORDER_TYPE_SELL_STOP, entry
    # fallback market
    return (MT5.ORDER_TYPE_BUY if side == "buy" else MT5.ORDER_TYPE_SELL), None


def send_order(setup: Dict) -> Dict:
    """
    setup expected keys: symbol, side ('buy'/'sell'), entry_type ('market'/'limit'/'stop'),
    entry (float), sl (float), tp (float)
    """
    symbol = setup["symbol"]
    side = setup["side"]
    entry_type = setup.get("entry_type", "market")
    entry = float(setup["entry"])
    sl = float(setup["sl"])
    tp = float(setup["tp"])

    ensure_symbol(symbol)
    snap = price_snapshot(symbol)
    otype, price = order_type_from_setup(side, entry_type, entry, snap)

    # Compute lot size under MAX_RISK_PCT
    lots = compute_lot_for_risk(symbol, entry, sl, MAX_RISK_PCT)
    if lots <= 0:
        return {"status": "blocked", "reason": "lot=0 (distance SL trop faible ou equity nulle)"}

    # Check per-trade risk actually <= MAX_RISK_PCT
    trade_risk_pct = current_trade_risk_pct(symbol, entry, sl, lots)
    if trade_risk_pct > MAX_RISK_PCT + 1e-6:
        return {"status": "blocked", "reason": f"expo dépasserait {MAX_RISK_PCT}% (calc={trade_risk_pct:.2f}%)"}

    # Cap number of open trades
    if open_positions_count() >= MAX_OPEN_TRADES:
        return {"status": "blocked", "reason": f"max {MAX_OPEN_TRADES} trades déjà ouverts"}

    # Build request
    request = {
        "action": MT5.TRADE_ACTION_DEAL if price is None else MT5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lots,
        "type": otype,
        "price": price if price is not None else (snap["ask"] if side.lower() == "buy" else snap["bid"]),
        "sl": sl,
        "tp": tp,
        "deviation": 50,
        "type_time": MT5.ORDER_TIME_GTC,
        "type_filling": MT5.ORDER_FILLING_FOK,
    }

    # Send
    result = MT5.order_send(request)
    ok = result is not None and result.retcode in (MT5.TRADE_RETCODE_DONE, MT5.TRADE_RETCODE_PLACED)
    status = "placed" if ok else "error"

    # Journal
    row = {
        "ts": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "side": side,
        "entry_type": entry_type,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "lots": lots,
        "risk_pct": round(trade_risk_pct, 4),
        "retcode": getattr(result, "retcode", None),
        "order": getattr(result, "order", None),
        "deal": getattr(result, "deal", None),
        "status": status,
        "reason": "" if ok else str(getattr(result, "comment", "")),
    }
    try:
        df = pd.DataFrame([row])
        try:
            pd.read_csv(CSV_JOURNAL)  # check exists
            df.to_csv(CSV_JOURNAL, mode="a", header=False, index=False)
        except Exception:
            df.to_csv(CSV_JOURNAL, index=False)
    except Exception as e:
        # journaling failure shouldn't block
        pass

    return {
        "status": status,
        "risk_pct": trade_risk_pct,
        "lots": lots,
        "mt5": {
            "retcode": getattr(result, "retcode", None),
            "comment": getattr(result, "comment", None),
            "order": getattr(result, "order", None),
            "deal": getattr(result, "deal", None),
        },
    }


def place_mt5_order(setup: Dict) -> Dict:
    """
    Public function: appelle ça depuis ton pipeline GPT quand un setup est validé par le Risk Engine.
    """
    return send_order(setup)


# ===================== DEMO RAPIDE =====================
if __name__ == "__main__":
    init_mt5()

    # Exemples de test (désactive si tu appelles depuis ton pipeline)
    demo_setups = [
        {"symbol": "XAUUSD", "side": "buy", "entry_type": "limit", "entry": 3675.50, "sl": 3665.50, "tp": 3695.50},
        {
            "symbol": "US30.cash",
            "side": "buy",
            "entry_type": "limit",
            "entry": 45850.00,
            "sl": 45700.00,
            "tp": 46100.00,
        },
    ]

    for s in demo_setups:
        try:
            res = place_mt5_order(s)
            print(s["symbol"], res)
            time.sleep(0.5)
        except Exception as e:
            print(s["symbol"], "ERROR:", e)
