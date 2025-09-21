PY := /Users/ayoubzahour/FTMO_Bot/FTMO_BOT_V2/.venv/bin/python

.PHONY: grid-report walkforward zip-report test

grid-report:
	@echo "Running grid report..."
	PYTHONPATH=. $(PY) scripts/run_grid_report.py

walkforward:
	@echo "Run walk-forward CLI (edit args as needed)"
	PYTHONPATH=. $(PY) scripts/walkforward_cli.py --csv data/prices.csv --position-sizing atr --atr-method sma --atr-period 14 --out-dir outputs

zip-report:
	@echo "Archiving outputs to outputs/grid_report.zip"
	zip -r outputs/grid_report.zip outputs

test:
	$(PY) -m pytest -q
