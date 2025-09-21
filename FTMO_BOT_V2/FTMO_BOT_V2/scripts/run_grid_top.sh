#!/bin/bash

# Run a larger grid search and save top-10 results
python - <<'PY'
from src.bot.optimizer import grid_search_ma, get_top_results, save_top_csv

prices = [100 + i*0.25 for i in range(800)]
shorts = [3,5,7,9]
longs = [20,30,40,60]
results = grid_search_ma(prices, shorts, longs, initial_capital=10000, commission=0.0005, slippage=0.0002)
top10 = get_top_results(results, top_n=10, sort_key='sharpe')
save_top_csv(top10, filename='top10_grid.csv')
print('Top 10 saved to top10_grid.csv')
PY
