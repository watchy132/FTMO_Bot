#!/usr/bin/env python3
"""Run walk-forward evaluation from a CSV of prices.

Usage examples:
  ./scripts/walkforward_cli.py --csv data/prices.csv --close-col Close --shorts 3,5,7 --longs 20,30,40
  /path/to/.venv/bin/python scripts/walkforward_cli.py --csv data/prices.csv

Outputs (in current directory by default):
  - wf_results.json
  - wf_topN.csv

The script uses src.bot.optimizer.walk_forward_evaluate and saves results using provided helpers.
"""

import argparse
import csv
from pathlib import Path
from typing import List

import pandas as pd

from src.bot.optimizer import (
    walk_forward_evaluate,
    save_walkforward_json,
    save_top_from_walkforward,
)


def parse_int_list(s: str) -> List[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main():
    p = argparse.ArgumentParser(description="Run walk-forward evaluation on price CSV")
    p.add_argument(
        "--csv",
        required=True,
        help="Path to CSV file containing price series (close prices or OHLC)",
    )
    p.add_argument(
        "--close-col",
        default=None,
        help="Name of close column in CSV (default: try Close/close/last column)",
    )
    p.add_argument(
        "--shorts",
        default="3,5,7",
        help='Comma-separated shortlist windows (e.g. "3,5,7")',
    )
    p.add_argument(
        "--longs",
        default="20,30,40",
        help='Comma-separated long windows (e.g. "20,30,40")',
    )
    p.add_argument(
        "--train-size", type=int, default=150, help="Initial training window length"
    )
    p.add_argument("--test-size", type=int, default=50, help="Test window length")
    p.add_argument(
        "--step",
        type=int,
        default=None,
        help="Step size between windows (default = test-size)",
    )
    p.add_argument(
        "--position-sizing",
        choices=["fixed", "atr"],
        default="fixed",
        help="Position sizing method: fixed or atr",
    )
    p.add_argument(
        "--atr-method",
        choices=["sma", "wilder"],
        default="sma",
        help="ATR calculation method when using --position-sizing atr",
    )
    p.add_argument(
        "--atr-period",
        type=int,
        default=14,
        help="ATR period when using --position-sizing atr",
    )
    p.add_argument("--top-n", type=int, default=5, help="Number of top combos to save")
    p.add_argument(
        "--out-dir",
        default=".",
        help="Directory to save outputs (wf_results.json, wf_topN.csv)",
    )

    args = p.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Determine close series
    if args.close_col and args.close_col in df.columns:
        close = df[args.close_col].astype(float).tolist()
    else:
        for col in ("Close", "close", "close_price"):
            if col in df.columns:
                close = df[col].astype(float).tolist()
                break
        else:
            # fallback to last numeric column
            numeric_cols = [
                c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
            ]
            if not numeric_cols:
                raise SystemExit(
                    "No numeric columns found in CSV to interpret as price/close"
                )
            close = df[numeric_cols[-1]].astype(float).tolist()

    short_windows = parse_int_list(args.shorts)
    long_windows = parse_int_list(args.longs)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Running walk-forward: shorts={short_windows}, longs={long_windows}, train={args.train_size}, test={args.test_size}, step={args.step or args.test_size}"
    )

    # detect highs/lows if present to support ATR-based sizing
    highs = None
    lows = None
    if "High" in df.columns and "Low" in df.columns:
        highs = df["High"].astype(float).tolist()
        lows = df["Low"].astype(float).tolist()
    elif "high" in df.columns and "low" in df.columns:
        highs = df["high"].astype(float).tolist()
        lows = df["low"].astype(float).tolist()

    aggregated = walk_forward_evaluate(
        close,
        short_windows=short_windows,
        long_windows=long_windows,
        train_size=args.train_size,
        test_size=args.test_size,
        step=args.step,
        position_sizing=args.position_sizing,
        highs=highs,
        lows=lows,
        period=args.atr_period,
        atr_method=args.atr_method,
    )

    results_json = out_dir / "wf_results.json"
    save_walkforward_json(aggregated, filename=str(results_json))

    top_csv = out_dir / f"wf_top{args.top_n}.csv"
    save_top_from_walkforward(
        aggregated, top_n=args.top_n, sort_key="avg_sharpe", filename=str(top_csv)
    )

    print(f"Saved {results_json} and {top_csv}")


if __name__ == "__main__":
    main()
