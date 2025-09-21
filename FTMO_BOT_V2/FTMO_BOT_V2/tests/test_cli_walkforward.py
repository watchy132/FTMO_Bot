import subprocess
import sys
from pathlib import Path
import csv

import json

def test_walkforward_cli_creates_outputs(tmp_path):
    # create synthetic OHLC CSV
    csv_path = tmp_path / 'prices.csv'
    headers = ['Date', 'Open', 'High', 'Low', 'Close']
    rows = []
    price = 100.0
    for i in range(300):
        o = price
        h = price + 0.5
        l = price - 0.5
        c = price + 0.1
        rows.append([f'2025-01-{(i%30)+1:02d}', f'{o:.2f}', f'{h:.2f}', f'{l:.2f}', f'{c:.2f}'])
        price += 0.2

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    # run CLI script using workspace venv python
    python_bin = Path(sys.executable).parent.parent / 'bin' / 'python'
    # Fallback to current interpreter if that path doesn't exist
    if not python_bin.exists():
        python_bin = Path(sys.executable)

    out_dir = tmp_path / 'out'
    out_dir.mkdir()

    cmd = [str(python_bin), 'scripts/walkforward_cli.py', '--csv', str(csv_path), '--position-sizing', 'atr', '--atr-method', 'sma', '--atr-period', '14', '--out-dir', str(out_dir), '--shorts', '3,5', '--longs', '20,30', '--train-size', '100', '--test-size', '50', '--top-n', '2']

    # ensure subprocess runs from repository root so package imports like 'src' resolve
    repo_root = Path(__file__).resolve().parent.parent
    # ensure the subprocess can import the local 'src' package
    env = dict(**{k: v for k, v in dict(**__import__('os').environ).items()})
    env['PYTHONPATH'] = str(repo_root)
    completed = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, env=env)
    assert completed.returncode == 0, f'CLI failed: {completed.stdout}\n{completed.stderr}'

    # check outputs
    results_json = out_dir / 'wf_results.json'
    top_csv = out_dir / 'wf_top2.csv'
    assert results_json.exists(), 'wf_results.json not created'
    assert top_csv.exists(), 'wf_top2.csv not created'

    # basic sanity on json
    with open(results_json) as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) > 0

    # check top file has header and rows
    with open(top_csv) as f:
        lines = f.read().strip().splitlines()
    assert len(lines) >= 2
