from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.data.market_data import avg_daily_amount
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import enforce_one_per_theme, momentum_score, weekly_prices, zscore


@dataclass
class MultiFactorRotationV2(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="multi_factor_v2")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        wk = weekly_prices(prices, weekday=self.cfg.backtest.rebalance_weekday)
        wk = wk[wk.index <= date]
        if len(wk) < 60:
            return []

        mom12 = momentum_score(prices, date=date, lookback_weeks=12, weekday=self.cfg.backtest.rebalance_weekday)
        if mom12.empty:
            return []

        value = pd.Series(index=mom12.index, data=0.0)
        rolling_min = wk.rolling(52).min().iloc[-1]
        rolling_max = wk.rolling(52).max().iloc[-1]
        latest = wk.iloc[-1]
        price_pct = ((latest - rolling_min) / (rolling_max - rolling_min)).replace([np.inf, -np.inf], np.nan)
        value = (1.0 - price_pct).reindex(mom12.index).fillna(0.0)

        daily_ret = prices.pct_change()
        vol20 = daily_ret.rolling(20).std(ddof=0).iloc[-1].replace([np.inf, -np.inf], np.nan)
        low_vol = (-vol20).reindex(mom12.index).fillna(0.0)

        amt = avg_daily_amount(prices, window=20)
        liq = np.log(amt.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)

        score = zscore(mom12) * 0.35 + zscore(value) * 0.15 + zscore(low_vol) * 0.35 + zscore(liq) * 0.15

        liquid = amt[amt >= self.cfg.filters.min_avg_daily_amount].index
        score = score[score.index.isin(liquid)]

        ranked = score.sort_values(ascending=False).index.tolist()
        code_to_theme = {u.code: u.theme for u in self.cfg.universe}
        ranked = enforce_one_per_theme(ranked, code_to_theme=code_to_theme)
        return ranked[: self.cfg.backtest.top_n]
