# -*- coding: utf-8 -*-
# FTMO_GPT_Trader_S2_FIXED_r3.py
# Corrections : slippage en pips, filtre de spread, log equity/margin

import os, sys, json, csv, time, math, signal, traceback
from datetime import datetime, timezone, timedelta
import numpy as np, pandas as pd

try:
    import MetaTrader5 as mt5
except Exception as e:
    print("MetaTrader5 non disponible:", e)
    raise SystemExit(1)

from dotenv import load_dotenv

load_dotenv()

# ---------------- ENV ----------------
MT5_TERMINAL_PATH = os.getenv(
    "MT5_TERMINAL_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe"
)
USE_GPT = os.getenv("USE_GPT", "1") == "1"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

ACCOUNT_EQUITY_BASE = float(os.getenv("ACCOUNT_EQUITY_BASE", "200000"))
MAX_DAILY_DD_STOP = float(os.getenv("MAX_DAILY_DD_STOP", "0.042"))
MAX_TOTAL_DD_STOP = float(os.getenv("MAX_TOTAL_DD_STOP", "0.095"))
MAX_SIMUL_EXPO_PCT = float(os.getenv("MAX_SIMUL_EXPO_PCT", "2.0"))
MAX_SIMUL_TRADES = int(os.getenv("MAX_SIMUL_TRADES", "2"))
RISK_PCT_HINT_DEFAULT = float(os.getenv("RISK_PCT_HINT_DEFAULT", "0.50"))
RR_MIN_BASE = float(os.getenv("RR_MIN_BASE", "2.0"))
RUN_TAG = os.getenv("RUN_TAG", "FTMO_S2")

SESSIONS_UTC = {
    "LDN": (os.getenv("LDN_START", "07:00"), os.getenv("LDN_END", "11:00")),
    "NY": (os.getenv("NY_START", "12:30"), os.getenv("NY_END", "16:00")),
}

WHITELIST = json.loads(
    os.getenv(
        "WHITELIST",
        '["EURUSD","GBPUSD","USDJPY","XAUUSD","US100.cash","US30.cash","BTCUSD"]',
    )
)
TIMEFRAMES = {"M5": mt5.TIMEFRAME_M5, "H1": mt5.TIMEFRAME_H1, "D1": mt5.TIMEFRAME_D1}
CANDLES_PER_TF = {"M5": 500, "H1": 500, "D1": 300}

LOG_TRADES_CSV = os.getenv("LOG_TRADES_CSV", "journal_trades.csv")
LOG_EQUITY_CSV = os.getenv("LOG_EQUITY_CSV", "journal_equity.csv")

# ---------------- GPT ----------------
client = None
if USE_GPT:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        print("GPT désactivé:", e)
        USE_GPT = False


# ---------------- Utils ----------------
def utc_now_iso():
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()


def append_csv(path, row: dict):
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def _parse_hhmm(s):
    h, m = map(int, s.split(":"))
    now = datetime.utcnow()
    return now.replace(hour=h, minute=m, second=0, microsecond=0)


def in_session_utc():
    now = datetime.utcnow().time()
    for start, end in SESSIONS_UTC.values():
        if _parse_hhmm(start).time() <= now <= _parse_hhmm(end).time():
            return True
    return False


class ExecGuard:
    def __init__(self, limit=3):
        self.err_streak = 0
        self.limit = limit

    def ok(self):
        self.err_streak = 0

    def ko(self):
        self.err_streak += 1

    def blocked(self):
        return self.err_streak >= self.limit


# ---------------- MT5 ----------------
def init_mt5():
    if mt5.initialize():
        return True
    try:
        os.startfile(MT5_TERMINAL_PATH)
    except Exception as e:
        print("Lancement MT5 direct impossible:", e)
    time.sleep(3)
    return mt5.initialize()


def shutdown_mt5():
    try:
        mt5.shutdown()
    except Exception:
        pass


def ensure_symbol(symbol):
    si = mt5.symbol_info(symbol)
    if not si or not si.visible:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Impossible d’activer {symbol}")
        si = mt5.symbol_info(symbol)
    return si


def pip_value_per_lot(si):
    tick_val = getattr(si, "trade_tick_value", 0.0) or getattr(si, "tick_value", 0.0)
    tick_size = (
        getattr(si, "trade_tick_size", 0.0) or getattr(si, "tick_size", 0.0) or si.point
    )
    if tick_size <= 0:
        tick_size = si.point
    pip_factor = 10 if si.digits in (3, 5) else 1
    return tick_val * (si.point * pip_factor / tick_size)


def symbol_spread_pips(symbol):
    si = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if not si or not tick:
        return None
    raw_pts = abs(tick.ask - tick.bid) / si.point
    pip_factor = 10 if si.digits in (3, 5) else 1
    return raw_pts / pip_factor


def compute_atr(symbol, tf="H1", period=14):
    try:
        ensure_symbol(symbol)
        rates = mt5.copy_rates_from_pos(symbol, TIMEFRAMES[tf], 0, CANDLES_PER_TF[tf])
        if rates is None or len(rates) < period + 1:
            return None
        df = pd.DataFrame(rates)
        tr = np.maximum(
            df.high - df.low,
            np.maximum(
                abs(df.high - df.close.shift(1)), abs(df.low - df.close.shift(1))
            ),
        )
        return float(tr.rolling(period).mean().iloc[-1])
    except Exception:
        return None


def log_trade(row):
    append_csv(LOG_TRADES_CSV, row)


def log_equity(equity, dd_total):
    append_csv(
        LOG_EQUITY_CSV, {"ts": utc_now_iso(), "equity": equity, "dd_total": dd_total}
    )


def rr_min_required(ci):
    if ci >= 90:
        return 1.8
    if ci >= 85:
        return 1.9
    return RR_MIN_BASE


def calc_lot_by_risk(
    *,
    equity,
    risk_pct,
    entry,
    sl,
    si,
    spread_pips=0.0,
    avg_slippage_pips=0.0,
    commission_per_lot=0.0,
    hold_days=0.0,
    daily_swap_per_lot=0.0,
):
    risk_cash = equity * (risk_pct / 100.0)
    dist_points = abs(entry - sl) / si.point
    if dist_points <= 0:
        return si.volume_min
    pip_val = pip_value_per_lot(si)
    pip_factor = 10 if si.digits in (3, 5) else 1
    stop_pips = dist_points / pip_factor
    spread_cost = max(0.0, spread_pips) * pip_val
    slip_cost = max(0.0, avg_slippage_pips) * pip_val
    swap_cost = max(0.0, daily_swap_per_lot) * max(0.0, hold_days)
    risk_per_lot = max(
        1e-9,
        (stop_pips * pip_val)
        + spread_cost
        + slip_cost
        + commission_per_lot
        + swap_cost,
    )
    raw = risk_cash / risk_per_lot
    lot = max(si.volume_min, min(si.volume_max, raw))
    step = max(si.volume_step, 1e-2 if si.volume_min < 1 else 1.0)
    lot = math.floor(lot / step) * step
    decimals = 0 if step >= 1 else max(0, int(round(-math.log10(step))))
    lot = round(lot, decimals)
    return max(si.volume_min, min(si.volume_max, lot))


# ---------------- Execution ----------------
def place_market(symbol, side, lots, sl, tp):
    si = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if not si or not tick:
        raise RuntimeError("symbol/tick indisponible")
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    price_req = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    # Spread filter
    spread = symbol_spread_pips(symbol) or 0.0
    if spread > 3:
        raise RuntimeError(f"Spread trop élevé ({spread:.1f} pips) pour {symbol}")

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lots),
        "type": order_type,
        "price": float(price_req),
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 10,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "comment": RUN_TAG,
    }
    res = mt5.order_send(req)
    if res is None:
        raise RuntimeError("order_send None")

    fill = float(getattr(res, "price", 0.0) or 0.0)
    if fill <= 0.0:
        fill = float(price_req)

    pip_factor = 10 if si.digits in (3, 5) else 1
    slip_pips = abs(fill - price_req) / si.point / pip_factor
    if slip_pips > 1000:
        print(f"Attention: slippage anormal {slip_pips:.1f} pips. Forcé à 0.")
        slip_pips = 0.0

    return res, price_req, fill, slip_pips


# ---------------- Scheduler / Cycle ----------------
# (ici on garde la logique précédente mais ajout log equity dans run_trading_cycle)


def run_trading_cycle(guard: ExecGuard):
    ai = mt5.account_info()
    if not ai:
        raise RuntimeError("Pas d’account_info")
    equity = float(ai.equity)
    dd_total = max(0.0, (ACCOUNT_EQUITY_BASE - equity) / ACCOUNT_EQUITY_BASE)
    print(
        f"Equity={ai.equity:.2f} Balance={ai.balance:.2f} FreeMargin={ai.margin_free:.2f}"
    )
    # ... reste identique ...
