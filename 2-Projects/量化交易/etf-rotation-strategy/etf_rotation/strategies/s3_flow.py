from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import enforce_one_per_theme, momentum_score, weekly_prices, zscore


@dataclass
class FlowRotation(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="flow_proxy")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        amt = prices.attrs.get("amount")
        if not isinstance(amt, pd.DataFrame) or amt.empty:
            amt = None

        mom = momentum_score(prices, date=date, lookback_weeks=4, weekday=self.cfg.backtest.rebalance_weekday)
        if mom.empty:
            return []

        if amt is not None:
            wk_amt = weekly_prices(amt, weekday=self.cfg.backtest.rebalance_weekday)
            wk_amt = wk_amt[wk_amt.index <= date]
            if len(wk_amt) >= 6:
                amt_chg = (wk_amt.iloc[-1] / wk_amt.iloc[-6] - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
            else:
                amt_chg = pd.Series(index=mom.index, data=0.0)
        else:
            amt_chg = pd.Series(index=mom.index, data=0.0)

        score = zscore(mom).reindex(mom.index).fillna(0.0) * 0.5 + zscore(amt_chg).reindex(mom.index).fillna(0.0) * 0.5
        ranked = score.sort_values(ascending=False).index.tolist()

        code_to_theme = {u.code: u.theme for u in self.cfg.universe}
        ranked = enforce_one_per_theme(ranked, code_to_theme=code_to_theme)
        return ranked[: self.cfg.backtest.top_n]
