#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, MetaTrader5 as mt5
from datetime import datetime, timezone

TIERS = [10_000, 25_000, 50_000, 100_000, 200_000, 500_000]
PROFILES = {
    t: {"risk_per_trade_pct": 0.25, "max_daily_loss_pct": 5, "max_total_loss_pct": 10}
    for t in TIERS
}


def pick_tier(bal):
    for t in TIERS:
        if bal <= t:
            return t
    return TIERS[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="logs/ftmo_profile.json")
    args = ap.parse_args()

    if not mt5.initialize():
        raise SystemExit("mt5.init_failed")
    ai = mt5.account_info()
    if ai is None:
        raise SystemExit("account_info_none")

    bal = float(ai.balance)
    tier = pick_tier(bal)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "account": {
            "login": ai.login,
            "name": ai.name,
            "server": ai.server,
            "currency": ai.currency,
            "leverage": ai.leverage,
            "balance": bal,
            "equity": float(ai.equity),
        },
        "bot_profile": {"account_tier": tier, **PROFILES[tier]},
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"wrote {args.out}")
    mt5.shutdown()


if __name__ == "__main__":
    main()
