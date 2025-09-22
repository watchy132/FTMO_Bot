#!/usr/bin/env python3
"""Run a larger MA grid search on synthetic prices and save CSV, heatmap and top-N.

Outputs saved to outputs/:
 - grid_results.csv
 - heatmap.png
 - top10.csv
"""
from pathlib import Path
from src.bot.optimizer import grid_search_ma, save_results_csv, plot_heatmap, get_top_results, save_top_csv

# parameters
shorts = list(range(3, 11, 2))  # 3,5,7,9
longs = [20, 30, 40, 60, 80]

# synthetic prices: upward trend + noise
prices = [100 + i * 0.15 + ((i % 10) - 5) * 0.2 for i in range(1000)]

out = Path("outputs")
out.mkdir(exist_ok=True)

print("Running grid search...")
results = grid_search_ma(prices, short_windows=shorts, long_windows=longs, position_sizing="fixed")

csv_path = out / "grid_results.csv"
save_results_csv(results, filename=str(csv_path))
print(f"Saved grid CSV to {csv_path}")

try:
    heatmap_path = out / "heatmap.png"
    plot_heatmap(results, filename=str(heatmap_path))
    print(f"Saved heatmap to {heatmap_path}")
except Exception as e:
    print("Could not generate heatmap:", e)

# save top-10
top10 = get_top_results(results, top_n=10, sort_key="sharpe")
top_csv = out / "top10.csv"
save_top_csv(top10, filename=str(top_csv))
print(f"Saved top-10 to {top_csv}")

# print best combo
if top10:
    best = top10[0]
    print("Best combo:", best[0], best[1], "metrics:", best[2])
else:
    print("No results found")
