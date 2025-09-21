from src.bot.optimizer import walk_forward_evaluate


def make_prices(n=300):
    return [100 + i*0.2 for i in range(n)]


def test_walk_forward_evaluate():
    prices = make_prices(250)
    res = walk_forward_evaluate(prices, short_windows=[3,5], long_windows=[20,30], train_size=100, test_size=30)
    assert isinstance(res, list)
    assert len(res) > 0
    # each item should be (short, long, dict)
    for s, l, metrics in res:
        assert isinstance(s, int)
        assert isinstance(l, int)
        assert isinstance(metrics, dict)


if __name__ == '__main__':
    test_walk_forward_evaluate()
