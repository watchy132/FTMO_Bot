#!/bin/bash

# Example grid search run using synthetic data
python - <<'PY'
from src.bot.optimizer import grid_search_ma, save_results_csv, plot_heatmap

prices = [100 + i*0.3 for i in range(400)]
shorts = [3,5,7]
longs = [15,20,30]
results = grid_search_ma(prices, shorts, longs, initial_capital=10000, commission=0.0005, slippage=0.0002)
save_results_csv(results, filename='grid_results.csv')
try:
    plot_heatmap(results, filename='grid_heatmap.png')
    print('Saved grid_heatmap.png')
except Exception as e:
    print('Plot skipped:', e)

print('Grid search complete. Results saved to grid_results.csv')
PY
