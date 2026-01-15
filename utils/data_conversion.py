"""Data conversion utilities for NautilusTrader formats"""

from typing import List
import pandas as pd
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos


def dataframe_to_bars(df: pd.DataFrame, bar_type: BarType) -> List[Bar]:
    """
    Convert DataFrame with OHLCV data to list of NautilusTrader Bar objects

    Args:
        df: DataFrame with columns [open, high, low, close, volume]
        bar_type: BarType specification for the bars

    Returns:
        List[Bar]: List of Bar objects for NautilusTrader
    """
    bars = []
    for timestamp, row in df.iterrows():
        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(str(row['open'])),
            high=Price.from_str(str(row['high'])),
            low=Price.from_str(str(row['low'])),
            close=Price.from_str(str(row['close'])),
            volume=Quantity.from_str(str(row['volume'])),
            ts_event=dt_to_unix_nanos(timestamp),
            ts_init=dt_to_unix_nanos(timestamp),
        )
        bars.append(bar)
    return bars
