# risk_engine.py — FTMO Risk Engine avec journalisation des rejets/validations
# Python 3.10+

from __future__ import annotations
import csv, os, math, time
from dataclasses import dataclass
from typing import Optional, Dict, Any

# =========================
# Config
# =========================
ACCOUNT_EQUITY_USD      = float(os.getenv("FTMO_EQUITY", "200000"))
RISK_PER_TRADE_PCT      = float(os.getenv("RISK_PCT", "0.015"))      # 1.5% par défaut
MAX_DAILY_LOSS_PCT      = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.05"))  # 5% FTMO
MAX_TOTAL_LOSS_PCT      = float(os.getenv("MAX_TOTAL_LOSS_PCT", "0.10"))  # 10% FTMO
EXPOSURE_CAP_PCT        = float(os.getenv("EXPOSURE_CAP_PCT", "0.015"))   # plafond d’exposition par trade
MAX_CONCURRENT_TRADES   = int(os.getenv("MAX_CONCURRENT_TRADES", "3"))
REQUIRE_TP_FOR_ENTRY    = bool(int(os.getenv("REQUIRE_TP_FOR_ENTRY", "0")))
MIN_RRR_TRADE           = float(os.getenv("MIN_RRR_TRADE", "1.6"))        # filtre final
JOURNAL_PATH            = os.getenv("JOURNAL_PATH", "journal_trades.csv")

# Paramètres instrument (ex: depuis MT5 symbols_info)
@dataclass
class Instrument:
    symbol: str
    tick_size: float
    tick_value: float         # valeur d’un tick pour 1 lot
    lot_step: float
    min_lot: float
    max_lot: float
    contract_size: float      # si utile, sinon laisser 1

@dataclass
class Setup:
    symbol: str
    direction: str            # "buy" / "sell"
    entry: float
    sl: float
    tp: Optional[float] = None
    rrr: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

# =========================
# Utilitaires
# =========================
def round_lot(lot: float, step: float, min_lot: float, max_lot: float) -> float:
    if step <= 0:
        step = 0.01
    k = round(lot / step)
    lot_r = max(min_lot, min(max_lot, k * step))
    return float(f"{lot_r:.4f}")

def price_to_ticks(p1: float, p2: float, tick_size: float) -> int:
    return int(round(abs(p1 - p2) / tick_size)) if tick_size > 0 else 0

def pnl_per_tick_for_lots(lots: float, tick_value: float) -> float:
    return lots * tick_value

def ensure_journal_header(path: str = JOURNAL_PATH):
    new = not os.path.exists(path)
    if new:
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "ts","status","reason","symbol","direction","entry","sl","tp","rrr",
                "lots","risk_usd","reward_usd_est","exposure_cap_pct","risk_pct","extra"
            ])

def journal(status: str, reason: str, setup: Optional[Setup], lots: float = 0.0,
            risk_usd: float = 0.0, reward_usd: float = 0.0, extra: Optional[Dict[str,Any]] = None):
    ensure_journal_header(JOURNAL_PATH)
    s = setup or Setup(symbol="", direction="", entry=0.0, sl=0.0)
    row = [
        int(time.time()),
        status,
        reason,
        s.symbol,
        s.direction,
        s.entry,
        s.sl,
        (s.tp if s.tp is not None else ""),
        (f"{s.rrr:.3f}" if s.rrr is not None else ""),
        f"{lots:.2f}",
        f"{risk_usd:.2f}",
        f"{reward_usd:.2f}",
        f"{EXPOSURE_CAP_PCT:.4f}",
        f"{RISK_PER_TRADE_PCT:.4f}",
        (extra if extra is not None else {}),
    ]
    with open(JOURNAL_PATH, "a", newline="") as f:
        csv.writer(f).writerow(row)

# =========================
# Contrôles d’exposition
# =========================
def exposure_check(risk_usd: float) -> tuple[bool, str]:
    cap_usd = ACCOUNT_EQUITY_USD * EXPOSURE_CAP_PCT
    if risk_usd > cap_usd + 1e-9:
        return False, f"exposure_exceeds_cap risk_usd={risk_usd:.2f} cap_usd={cap_usd:.2f}"
    return True, "ok"

# Placeholder. À connecter à votre journal PnL intraday.
def daily_loss_guard() -> tuple[bool, str]:
    # Ici on suppose 0 perte courante pour la démo.
    # Brancher votre calcul (journal du jour) pour refuser si perte >= MAX_DAILY_LOSS_PCT * equity.
    return True, "ok"

# =========================
# Calcul de lot
# =========================
def compute_lot_from_risk(setup: Setup, instr: Instrument,
                          equity_usd: float = ACCOUNT_EQUITY_USD,
                          risk_pct: float = RISK_PER_TRADE_PCT) -> tuple[float, float, float]:
    """Retourne (lots_arrondi, risk_usd, reward_usd_est)"""
    ticks_sl = price_to_ticks(setup.entry, setup.sl, instr.tick_size)
    if ticks_sl <= 0:
        return 0.0, 0.0, 0.0

    risk_usd_target = equity_usd * risk_pct
    # $ par tick pour 1 lot = tick_value
    # Donc lots = risk_usd_target / (ticks_sl * tick_value)
    denom = ticks_sl * instr.tick_value
    lots_raw = 0.0 if denom <= 0 else (risk_usd_target / denom)
    lots = round_lot(lots_raw, instr.lot_step, instr.min_lot, instr.max_lot)

    # Risk USD réel avec ce lot arrondi
    risk_usd = ticks_sl * pnl_per_tick_for_lots(lots, instr.tick_value)

    reward_usd = 0.0
    if setup.tp is not None:
        ticks_tp = price_to_ticks(setup.tp, setup.entry, instr.tick_size)
        reward_usd = ticks_tp * pnl_per_tick_for_lots(lots, instr.tick_value)

    return lots, risk_usd, reward_usd

# =========================
# Évaluation complète
# =========================
def evaluate(setup_dict: Dict[str, Any], instr_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Entrées simples dict → sortie normalisée + journaux.
       Retour: {'decision': 'TRADE'|'SKIP', 'why': str, 'lots': float, ...}
    """
    # Map entrées
    setup = Setup(
        symbol = setup_dict.get("symbol"),
        direction = str(setup_dict.get("direction","")).lower(),
        entry = float(setup_dict.get("entry")),
        sl = float(setup_dict.get("sl")),
        tp = (float(setup_dict["tp"]) if setup_dict.get("tp") is not None else None),
        rrr = (float(setup_dict["rrr"]) if setup_dict.get("rrr") is not None else None),
        meta = setup_dict.get("meta") or {}
    )
    instr = Instrument(
        symbol=instr_dict["symbol"],
        tick_size=float(instr_dict["tick_size"]),
        tick_value=float(instr_dict["tick_value"]),
        lot_step=float(instr_dict["lot_step"]),
        min_lot=float(instr_dict["min_lot"]),
        max_lot=float(instr_dict["max_lot"]),
        contract_size=float(instr_dict.get("contract_size", 1.0)),
    )

    # Checks de base
    if REQUIRE_TP_FOR_ENTRY and setup.tp is None:
        journal("REJECT", "missing_tp_required", setup, 0.0, 0.0, 0.0, {})
        return {"decision":"SKIP","why":"missing_tp_required"}

    if setup.rrr is not None and setup.rrr < MIN_RRR_TRADE:
        journal("REJECT", f"rrr_below_min:{setup.rrr:.2f}<{MIN_RRR_TRADE}", setup, 0.0, 0.0, 0.0, {})
        return {"decision":"SKIP","why":"rrr_below_min"}

    lots, risk_usd, reward_usd = compute_lot_from_risk(setup, instr, ACCOUNT_EQUITY_USD, RISK_PER_TRADE_PCT)

    if lots <= 0.0 or risk_usd <= 0.0:
        journal("REJECT", "non_positive_lot_or_risk", setup, lots, risk_usd, reward_usd, {})
        return {"decision":"SKIP","why":"non_positive_lot_or_risk"}

    ok, msg = exposure_check(risk_usd)
    if not ok:
        journal("REJECT", msg, setup, lots, risk_usd, reward_usd, {"cap_pct":EXPOSURE_CAP_PCT})
        return {"decision":"SKIP","why":msg}

    ok, msg = daily_loss_guard()
    if not ok:
        journal("REJECT", msg, setup, lots, risk_usd, reward_usd, {})
        return {"decision":"SKIP","why":msg}

    # OK → TRADE
    journal("ACCEPT", "risk_ok", setup, lots, risk_usd, reward_usd,
            {"min_rrr":MIN_RRR_TRADE,"risk_pct":RISK_PER_TRADE_PCT})
    return {
        "decision":"TRADE",
        "why":"risk_ok",
        "symbol": setup.symbol,
        "direction": setup.direction,
        "entry": setup.entry,
        "sl": setup.sl,
        "tp": setup.tp,
        "lots": lots,
        "risk_usd": round(risk_usd,2),
        "reward_usd_est": round(reward_usd,2)
    }

# =========================
# Test local
# =========================
if __name__ == "__main__":
    s = {"symbol":"XAUUSD","direction":"sell","entry":2400.0,"sl":2412.0,"tp":2360.0,"rrr":3.33}
    i = {"symbol":"XAUUSD","tick_size":0.1,"tick_value":1.0,"lot_step":0.01,"min_lot":0.01,"max_lot":100.0,"contract_size":1.0}
    out = evaluate(s, i)
    print(out)
    print("Journal →", JOURNAL_PATH)
