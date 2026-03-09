from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import enforce_one_per_theme, rsi, weekly_prices


@dataclass
class MeanReversionRSI(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="mean_reversion_rsi")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        wk = weekly_prices(prices, weekday=self.cfg.backtest.rebalance_weekday)
        wk = wk[wk.index <= date]
        if len(wk) < 20:
            return []

        rsi_map = {}
        for code in wk.columns:
            rs = rsi(wk[code], period=14)
            if rs.empty:
                continue
            rsi_map[code] = float(rs.iloc[-1])

        s = pd.Series(rsi_map).dropna()
        if s.empty:
            return []

        oversold = s[s < 30].sort_values(ascending=True)
        ranked = oversold.index.tolist()
        if len(ranked) < self.cfg.backtest.top_n:
            ranked = s.sort_values(ascending=True).index.tolist()

        code_to_theme = {u.code: u.theme for u in self.cfg.universe}
        ranked = enforce_one_per_theme(ranked, code_to_theme=code_to_theme)
        return ranked[: self.cfg.backtest.top_n]
