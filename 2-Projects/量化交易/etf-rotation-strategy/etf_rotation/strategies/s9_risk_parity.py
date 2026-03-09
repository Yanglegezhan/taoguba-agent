from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import enforce_one_per_theme, momentum_score, weekly_prices


def _risk_parity_weights(cov: np.ndarray, max_iter: int = 500, tol: float = 1e-8) -> np.ndarray:
    n = cov.shape[0]
    w = np.ones(n) / n
    target = np.ones(n) / n

    for _ in range(max_iter):
        port_var = float(w.T @ cov @ w)
        if port_var <= 0:
            break
        mrc = cov @ w
        rc = w * mrc / port_var
        diff = rc - target
        if np.max(np.abs(diff)) < tol:
            break
        w = w * (target / (rc + 1e-12))
        w = np.clip(w, 1e-6, None)
        w = w / w.sum()
    return w


@dataclass
class RiskParityRotation(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="risk_parity")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        score = momentum_score(prices, date=date, lookback_weeks=12, weekday=self.cfg.backtest.rebalance_weekday)
        ranked = score.sort_values(ascending=False).index.tolist()
        code_to_theme = {u.code: u.theme for u in self.cfg.universe}
        ranked = enforce_one_per_theme(ranked, code_to_theme=code_to_theme)
        return ranked[: self.cfg.backtest.top_n]

    def weights(self, date: pd.Timestamp, selected: List[str], prices: pd.DataFrame) -> Dict[str, float]:
        if len(selected) <= 1:
            return super().weights(date, selected, prices)

        wk = weekly_prices(prices[selected], weekday=self.cfg.backtest.rebalance_weekday)
        wk = wk[wk.index <= date]
        rets = wk.pct_change().dropna()
        if len(rets) < 20:
            return super().weights(date, selected, prices)

        cov = rets.cov().to_numpy()
        w = _risk_parity_weights(cov)
        return {c: float(w[i]) for i, c in enumerate(selected)}
