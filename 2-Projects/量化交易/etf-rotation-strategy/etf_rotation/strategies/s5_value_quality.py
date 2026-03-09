from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import enforce_one_per_theme, momentum_score, weekly_prices, zscore


@dataclass
class ValueEarningsRotation(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="value_earnings_proxy")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        wk = weekly_prices(prices, weekday=self.cfg.backtest.rebalance_weekday)
        wk = wk[wk.index <= date]
        if len(wk) < 60:
            return []

        latest = wk.iloc[-1]
        rolling_min = wk.rolling(52).min().iloc[-1]
        rolling_max = wk.rolling(52).max().iloc[-1]
        price_pct = ((latest - rolling_min) / (rolling_max - rolling_min)).replace([np.inf, -np.inf], np.nan).dropna()

        value_factor = (1.0 - price_pct).clip(lower=0.0, upper=1.0)
        earnings_proxy = momentum_score(prices, date=date, lookback_weeks=4, weekday=self.cfg.backtest.rebalance_weekday)

        score = zscore(value_factor).reindex(value_factor.index).fillna(0.0) * 0.6 + zscore(earnings_proxy).reindex(value_factor.index).fillna(0.0) * 0.4
        ranked = score.sort_values(ascending=False).index.tolist()

        code_to_theme = {u.code: u.theme for u in self.cfg.universe}
        ranked = enforce_one_per_theme(ranked, code_to_theme=code_to_theme)
        return ranked[: self.cfg.backtest.top_n]
