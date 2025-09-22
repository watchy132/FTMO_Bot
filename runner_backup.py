from __future__ import annotations
import os, time, json, argparse
from datetime import datetime, timezone
from typing import List

from schemas import parse_decision, Action
from risk_engine import DEFAULT_SPECS, sl_distance_pips, lot_for_risk, enforce_rrr
import mt5_io

SYMBOLS = ["EURUSD", "XAUUSD", "US30.cash"]
TIMEFRAME = "M5"
CAPITAL = 200000.0
RISK_PCT = 0.005
DEVIATION = 10
LOG = "journal_trades.csv"


def call_gpt(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "Réponds strictement en JSON Decision{action,expires_at,setup?,risk?}. Aucune prose.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return r.choices[0].message.content


def is_session_open_utc() -> bool:
    now = datetime.utcnow()
    t = now.hour + now.minute / 60
    return (7.0 <= t <= 16.5) or (13.5 <= t <= 20.0)


def write_log(row: List):
    import csv, os

    header = [
        "ts",
        "symbol",
        "direction",
        "entry",
        "sl",
        "tp",
        "risk_pct",
        "lot",
        "rrr_planned",
        "action",
        "reason",
        "pnl",
        "equity",
    ]
    exists = os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(header)
        w.writerow(row)


def prompt_from_market(symbol: str, last_close: float) -> str:
    return json.dumps(
        {
            "symbol": symbol,
            "price": last_close,
            "ask_for": "Decision",
            "rules": {"rrr_min": 2.0, "risk_pct": RISK_PCT},
        }
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--symbol", type=str, default=None)
    ap.add_argument("--minutes", type=int, default=10)
    args = ap.parse_args()
    live = bool(args.live) and not bool(args.dry)

    mt5_io.ensure_mt5()
    symbols = [args.symbol] if args.symbol else SYMBOLS
    t_end = time.time() + args.minutes * 60

    while time.time() < t_end:
        if not is_session_open_utc():
            print("Hors session. Pause 30s.")
            time.sleep(30)
            continue

        for sym in symbols:
            try:
                mt5_io.symbol_select(sym)
                rates = mt5_io.market_data(sym, TIMEFRAME, n=200)
                last = float(rates[-1]["close"])
                raw = call_gpt(prompt_from_market(sym, last))

                try:
                    decision = parse_decision(raw)
                except Exception as e:
                    write_log(
                        [
                            datetime.now(timezone.utc).isoformat(),
                            sym,
                            "-",
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            "SKIP",
                            f"JSON_INVALID:{e}",
                            0,
                            CAPITAL,
                        ]
                    )
                    print(f"{sym}: JSON invalide")
                    continue

                if decision.action != Action.PLACE or decision.setup is None:
                    write_log(
                        [
                            datetime.now(timezone.utc).isoformat(),
                            sym,
                            "-",
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            decision.action,
                            "not_place",
                            0,
                            CAPITAL,
                        ]
                    )
                    print(f"{sym}: action={decision.action}")
                    continue

                st = decision.setup
                if not enforce_rrr(st.rrr, 2.0):
                    write_log(
                        [
                            datetime.now(timezone.utc).isoformat(),
                            sym,
                            st.direction,
                            st.entry,
                            st.sl,
                            st.tp,
                            RISK_PCT,
                            0,
                            st.rrr,
                            "SKIP",
                            "RRR<2",
                            0,
                            CAPITAL,
                        ]
                    )
                    print(f"{sym}: RRR<2 → skip")
                    continue

                spec = DEFAULT_SPECS.get(sym, DEFAULT_SPECS["EURUSD"])
                sl_pips = sl_distance_pips(st.entry, st.sl, spec.tick_size)
                lot = lot_for_risk(
                    CAPITAL,
                    RISK_PCT,
                    sl_pips,
                    tick_value=spec.tick_value,
                    tick_size=spec.tick_size,
                    lot_step=spec.lot_step,
                    min_lot=spec.min_lot,
                    max_lot=spec.max_lot,
                    spread_pips=1.0,
                    commission_per_lot=6.0,
                    slippage_pips=0.5,
                )
                if lot <= 0:
                    write_log(
                        [
                            datetime.now(timezone.utc).isoformat(),
                            sym,
                            st.direction,
                            st.entry,
                            st.sl,
                            st.tp,
                            RISK_PCT,
                            0,
                            st.rrr,
                            "SKIP",
                            "lot<=0",
                            0,
                            CAPITAL,
                        ]
                    )
                    print(f"{sym}: lot<=0 → skip")
                    continue

                req = mt5_io.make_order_request(
                    sym, lot, st.direction, st.entry, st.sl, st.tp, deviation=DEVIATION
                )
                res = mt5_io.place_order(req, live=live)
                status = "DRY-RUN" if res.get("dry_run") else "SENT"
                write_log(
                    [
                        datetime.now(timezone.utc).isoformat(),
                        sym,
                        st.direction,
                        st.entry,
                        st.sl,
                        st.tp,
                        RISK_PCT,
                        lot,
                        st.rrr,
                        status,
                        "ok",
                        0,
                        CAPITAL,
                    ]
                )
                print(f"{sym}: {status} lot={lot:.2f}")

            except Exception as e:
                write_log(
                    [
                        datetime.now(timezone.utc).isoformat(),
                        sym,
                        "-",
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        "ERROR",
                        str(e),
                        0,
                        CAPITAL,
                    ]
                )
                print(f"{sym}: ERROR {e}")

        time.sleep(10)


if __name__ == "__main__":
    main()
