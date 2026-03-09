from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import momentum_score


@dataclass
class CrossMarketRelativeStrength(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="cross_market")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        candidates = ["510300", "159920", "513100"]
        candidates = [c for c in candidates if c in prices.columns]
        if not candidates:
            return []

        px = prices[candidates]
        score = momentum_score(px, date=date, lookback_weeks=12, weekday=self.cfg.backtest.rebalance_weekday)
        ranked = score.sort_values(ascending=False).index.tolist()
        return ranked[: min(3, self.cfg.backtest.top_n)]
