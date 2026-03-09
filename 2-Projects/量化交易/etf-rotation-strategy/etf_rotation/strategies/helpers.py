from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


def weekly_prices(prices: pd.DataFrame, weekday: int = 4) -> pd.DataFrame:
    prices = prices.sort_index().ffill()
    wk = prices[prices.index.weekday == weekday]
    return wk


def momentum_score(prices: pd.DataFrame, date: pd.Timestamp, lookback_weeks: int, weekday: int = 4) -> pd.Series:
    wk = weekly_prices(prices, weekday=weekday)
    if date not in wk.index:
        wk = wk[wk.index <= date]
        if wk.empty:
            return pd.Series(dtype=float)
        date = wk.index[-1]

    end_loc = wk.index.get_loc(date)
    start_loc = end_loc - lookback_weeks
    if start_loc < 0:
        return pd.Series(dtype=float)

    start = wk.iloc[start_loc]
    end = wk.iloc[end_loc]
    return (end / start - 1.0).replace([np.inf, -np.inf], np.nan).dropna()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = ma_up / ma_down.replace(0.0, np.nan)
    return 100 - (100 / (1 + rs))


def enforce_one_per_theme(selected: List[str], code_to_theme: Dict[str, str]) -> List[str]:
    out: List[str] = []
    used = set()
    for code in selected:
        theme = code_to_theme.get(code, code)
        if theme in used:
            continue
        used.add(theme)
        out.append(code)
    return out


def zscore(x: pd.Series) -> pd.Series:
    x = x.astype(float)
    std = x.std(ddof=0)
    if std == 0 or not np.isfinite(std):
        return x * 0.0
    return (x - x.mean()) / std
