from src.bot.optimizer import (
    walk_forward_evaluate,
    save_walkforward_csv,
    save_walkforward_json,
    save_top_from_walkforward,
)
import os


def make_prices(n=300):
    return [100 + i * 0.2 for i in range(n)]


def test_walkforward_saves(tmp_path):
    prices = make_prices(250)
    aggregated = walk_forward_evaluate(
        prices,
        short_windows=[3, 5],
        long_windows=[20, 30],
        train_size=100,
        test_size=30,
    )
    csv_file = tmp_path / "wf.csv"
    json_file = tmp_path / "wf.json"
    top_file = tmp_path / "wf_top.csv"

    save_walkforward_csv(aggregated, filename=str(csv_file))
    save_walkforward_json(aggregated, filename=str(json_file))
    save_top_from_walkforward(aggregated, top_n=2, filename=str(top_file))

    assert os.path.exists(str(csv_file))
    assert os.path.exists(str(json_file))
    assert os.path.exists(str(top_file))


if __name__ == "__main__":
    test_walkforward_saves("/tmp")
