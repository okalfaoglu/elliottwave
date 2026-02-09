import pandas as pd

from ew6.swing.zigzag import ZigZagConfig, zigzag_from_close


def test_zigzag_basic():
    idx = pd.date_range("2025-01-01", periods=6, freq="D")
    close = pd.Series([100, 102, 105, 100, 98, 103], index=idx)
    pts = zigzag_from_close(close, ZigZagConfig(pct=3.0))
    assert len(pts) >= 1
