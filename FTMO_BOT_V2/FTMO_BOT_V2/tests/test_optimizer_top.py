from src.bot.optimizer import grid_search_ma, get_top_results


def make_prices(n=200):
    return [100 + i * 0.2 for i in range(n)]


def test_get_top_results():
    prices = make_prices(200)
    results = grid_search_ma(
        prices, short_windows=[3, 5, 7], long_windows=[20, 30], initial_capital=10000
    )
    top = get_top_results(results, top_n=3, sort_key="sharpe")
    assert len(top) == 3
    # check ordering descending by the chosen metric
    metrics = [
        res.get("sharpe") if res.get("sharpe") is not None else res.get("total_return")
        for _, _, res in top
    ]
    # metrics should be non-increasing
    for i in range(1, len(metrics)):
        assert metrics[i] <= metrics[i - 1]


if __name__ == "__main__":
    test_get_top_results()
