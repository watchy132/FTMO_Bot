from src.bot.optimizer import grid_search_ma


def make_prices(n=100):
    return [100 + i*0.2 for i in range(n)]


def test_grid_search_runs():
    prices = make_prices(120)
    results = grid_search_ma(prices, short_windows=[3,5], long_windows=[15,20], initial_capital=10000)
    assert len(results) > 0
    # ensure each result has structure (short,long,dict)
    for short, long, res in results:
        assert isinstance(short, int)
        assert isinstance(long, int)
        assert isinstance(res, dict)


if __name__ == '__main__':
    test_grid_search_runs()
