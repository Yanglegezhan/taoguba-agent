from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import enforce_one_per_theme, momentum_score


@dataclass
class SeasonalityRotation(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="seasonality")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        month = str(int(date.month))
        preferred = set(self.cfg.seasonality.get(month, []))

        code_to_theme = {u.code: u.theme for u in self.cfg.universe}
        candidates = [u.code for u in self.cfg.universe if (not preferred) or (u.theme in preferred)]
        candidates = [c for c in candidates if c in prices.columns]
        if not candidates:
            return []

        px = prices[candidates]
        score = momentum_score(px, date=date, lookback_weeks=6, weekday=self.cfg.backtest.rebalance_weekday)
        ranked = score.sort_values(ascending=False).index.tolist()
        ranked = enforce_one_per_theme(ranked, code_to_theme=code_to_theme)
        return ranked[: self.cfg.backtest.top_n]
