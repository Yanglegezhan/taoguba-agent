from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import enforce_one_per_theme, momentum_score, weekly_prices, zscore


@dataclass
class MultiFactorRotation(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="multi_factor")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        mom12 = momentum_score(prices, date=date, lookback_weeks=12, weekday=self.cfg.backtest.rebalance_weekday)
        if mom12.empty:
            return []

        wk = weekly_prices(prices, weekday=self.cfg.backtest.rebalance_weekday)
        wk = wk[wk.index <= date]
        latest = wk.iloc[-1]
        rolling_min = wk.rolling(52).min().iloc[-1]
        rolling_max = wk.rolling(52).max().iloc[-1]
        price_pct = ((latest - rolling_min) / (rolling_max - rolling_min)).replace([np.inf, -np.inf], np.nan)
        value = (1.0 - price_pct).fillna(0.0)

        amt = prices.attrs.get("amount")
        if isinstance(amt, pd.DataFrame) and not amt.empty:
            wk_amt = weekly_prices(amt, weekday=self.cfg.backtest.rebalance_weekday)
            wk_amt = wk_amt[wk_amt.index <= date]
            flow = (wk_amt.pct_change(4).iloc[-1]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        else:
            flow = pd.Series(index=mom12.index, data=0.0)

        trend = wk.pct_change().rolling(12).mean().iloc[-1].replace([np.inf, -np.inf], np.nan).fillna(0.0)

        score = zscore(mom12) * 0.3 + zscore(value.reindex(mom12.index).fillna(0.0)) * 0.2 + zscore(flow.reindex(mom12.index).fillna(0.0)) * 0.2 + zscore(trend.reindex(mom12.index).fillna(0.0)) * 0.3
        ranked = score.sort_values(ascending=False).index.tolist()

        code_to_theme = {u.code: u.theme for u in self.cfg.universe}
        ranked = enforce_one_per_theme(ranked, code_to_theme=code_to_theme)
        return ranked[: self.cfg.backtest.top_n]
