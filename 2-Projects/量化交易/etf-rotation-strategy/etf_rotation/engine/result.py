from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    nav: pd.Series
    returns: pd.Series
    benchmark_nav: pd.Series
    benchmark_returns: pd.Series
    rebalance_dates: pd.DatetimeIndex
    positions: pd.DataFrame
