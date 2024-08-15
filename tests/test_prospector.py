from flows.prospector import get_wikipedia_nasdaq100


def test_get_wikipedia_nasdaq100():
    df = get_wikipedia_nasdaq100()
    assert set(df.columns) == set(
        ["Ticker", "Company", "GICS Sector", "GICS Sub-Industry"]
    )
