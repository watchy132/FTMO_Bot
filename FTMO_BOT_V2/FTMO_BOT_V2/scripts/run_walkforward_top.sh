#!/bin/bash

python - <<'PY'
from src.bot.optimizer import walk_forward_evaluate, save_walkforward_json, save_top_from_walkforward

prices = [100 + i*0.3 for i in range(500)]
shorts = [3,5,7]
longs = [20,30,40]
aggregated = walk_forward_evaluate(prices, short_windows=shorts, long_windows=longs, train_size=150, test_size=50, step=50)
save_walkforward_json(aggregated, filename='wf_results.json')
save_top_from_walkforward(aggregated, top_n=5, sort_key='avg_sharpe', filename='wf_top5.csv')
print('Saved wf_results.json and wf_top5.csv')
PY
