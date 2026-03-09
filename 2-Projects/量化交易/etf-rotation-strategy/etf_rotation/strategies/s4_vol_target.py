from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import momentum_score


def _hist_vol(returns: pd.Series, window: int = 20) -> float:
    x = returns.dropna().iloc[-window:]
    if len(x) < window:
        return float("nan")
    return float(x.std(ddof=0) * np.sqrt(252))


@dataclass
class VolTargetRotation(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="vol_target")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        risk_pool = list(self.cfg.pools.risk_assets)
        def_pool = list(self.cfg.pools.defensive_assets)
        universe = list(dict.fromkeys(risk_pool + def_pool))

        px = prices.reindex(columns=[c for c in universe if c in prices.columns])
        score = momentum_score(px, date=date, lookback_weeks=6, weekday=self.cfg.backtest.rebalance_weekday)
        ranked = score.sort_values(ascending=False).index.tolist()
        return ranked[: self.cfg.backtest.top_n]

    def weights(self, date: pd.Timestamp, selected: List[str], prices: pd.DataFrame) -> Dict[str, float]:
        bench = prices.mean(axis=1).pct_change()
        vol = _hist_vol(bench, window=20)

        if not np.isfinite(vol):
            return super().weights(date, selected, prices)

        if vol < 0.20:
            risk_w, def_w = 1.0, 0.0
        elif vol < 0.30:
            risk_w, def_w = 0.7, 0.3
        else:
            risk_w, def_w = 0.3, 0.7

        risk = [c for c in selected if c in set(self.cfg.pools.risk_assets)]
        defensive = [c for c in selected if c in set(self.cfg.pools.defensive_assets)]
        other = [c for c in selected if c not in set(self.cfg.pools.risk_assets) and c not in set(self.cfg.pools.defensive_assets)]

        w: Dict[str, float] = {}
        if risk:
            ew = risk_w / len(risk)
            w.update({c: ew for c in risk})
        if defensive:
            ew = def_w / len(defensive)
            w.update({c: ew for c in defensive})
        if other:
            rem = max(0.0, 1.0 - sum(w.values()))
            ew = rem / len(other)
            w.update({c: ew for c in other})
        return w
