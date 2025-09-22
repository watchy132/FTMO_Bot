from __future__ import annotations
from typing import Any, Dict, Optional
import MetaTrader5 as mt5


def ensure_mt5() -> None:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")


def timeframe_map(tf: str) -> int:
    tf = tf.upper()
    return {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }.get(tf, mt5.TIMEFRAME_M5)


def symbol_select(symbol: str) -> None:
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"symbol_select({symbol}) failed")


def get_symbol_spec(symbol: str) -> Dict[str, Any]:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"symbol_info({symbol}) is None")
    return dict(
        digits=info.digits,
        point=info.point,
        trade_contract_size=info.trade_contract_size,
        trade_tick_size=info.trade_tick_size,
        trade_tick_value=info.trade_tick_value,
        volume_min=info.volume_min,
        volume_max=info.volume_max,
        volume_step=info.volume_step,
    )


def market_data(symbol: str, tf: str, n: int = 200):
    rates = mt5.copy_rates_from_pos(symbol, timeframe_map(tf), 0, n)
    if rates is None:
        raise RuntimeError(f"copy_rates_from_pos failed for {symbol}")
    return rates  # numpy structured array


def make_order_request(
    symbol: str,
    volume: float,
    side: str,
    price: float,
    sl: Optional[float],
    tp: Optional[float],
    deviation: int = 10,
) -> Dict[str, Any]:
    ord_type = mt5.ORDER_TYPE_BUY if side.upper() == "BUY" else mt5.ORDER_TYPE_SELL
    return {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": ord_type,
        "price": float(price),
        "sl": float(sl or 0.0),
        "tp": float(tp or 0.0),
        "deviation": deviation,
        "type_filling": mt5.ORDER_FILLING_FOK,
        "type_time": mt5.ORDER_TIME_GTC,
        "comment": "FTMO_GPT_Trader",
    }


def place_order(request: Dict[str, Any], live: bool = False) -> Dict[str, Any]:
    if not live:
        return {"dry_run": True, "request": request}
    res = mt5.order_send(request)
    if res is None:
        raise RuntimeError("order_send returned None")
    if res.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"order_send retcode={res.retcode} ({res._asdict()})")
    return {"dry_run": False, "result": res._asdict()}
