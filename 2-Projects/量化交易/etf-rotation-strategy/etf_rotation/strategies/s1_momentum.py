from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.data.market_data import avg_daily_amount
from etf_rotation.strategies.base import RotationStrategy
from etf_rotation.strategies.helpers import enforce_one_per_theme, momentum_score, weekly_prices


@dataclass
class MomentumRotation(RotationStrategy):
    cfg: AppConfig

    def __init__(self, cfg: AppConfig):
        super().__init__(name="momentum")
        self.cfg = cfg

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        variant = MomentumRotationVariant(
            cfg=self.cfg,
            name="s1_momentum_base",
            score_fn=_score_simple_momentum(lookback_weeks=6),
            liquidity_window=20,
            trend_filter_weeks=None,
            abs_momentum_cash=False,
        )
        return variant.select(date=date, prices=prices)


@dataclass
class MomentumRotationVariant(RotationStrategy):
    cfg: AppConfig
    variant_name: str
    score_fn: Callable[[pd.DataFrame, pd.Timestamp, int], pd.Series]
    fallback_score_fn: Optional[Callable[[pd.DataFrame, pd.Timestamp, int], pd.Series]] = None
    liquidity_window: int = 20
    trend_filter_weeks: Optional[int] = None
    abs_momentum_cash: bool = False
    enforce_theme: bool = True
    risk_off_to_commodities: bool = False
    breadth_positive_ratio_threshold: float = 0.0

    def __init__(
        self,
        cfg: AppConfig,
        name: str,
        score_fn: Callable[[pd.DataFrame, pd.Timestamp, int], pd.Series],
        fallback_score_fn: Optional[Callable[[pd.DataFrame, pd.Timestamp, int], pd.Series]] = None,
        liquidity_window: int = 20,
        trend_filter_weeks: Optional[int] = None,
        abs_momentum_cash: bool = False,
        enforce_theme: bool = True,
        risk_off_to_commodities: bool = False,
        breadth_positive_ratio_threshold: float = 0.0,
    ):
        super().__init__(name=name)
        self.cfg = cfg
        self.variant_name = name
        self.score_fn = score_fn
        self.fallback_score_fn = fallback_score_fn
        self.liquidity_window = int(liquidity_window)
        self.trend_filter_weeks = int(trend_filter_weeks) if trend_filter_weeks is not None else None
        self.abs_momentum_cash = bool(abs_momentum_cash)
        self.enforce_theme = bool(enforce_theme)
        self.risk_off_to_commodities = bool(risk_off_to_commodities)
        self.breadth_positive_ratio_threshold = float(breadth_positive_ratio_threshold)

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        wkday = int(self.cfg.backtest.rebalance_weekday)
        score = self.score_fn(prices, date, wkday)
        if score.empty:
            if self.fallback_score_fn is None:
                return []
            score = self.fallback_score_fn(prices, date, wkday)
            if score.empty:
                return []

        if self.risk_off_to_commodities:
            positive_ratio = float((score > 0).mean()) if len(score) > 0 else 0.0
            if positive_ratio < float(self.breadth_positive_ratio_threshold):
                comm = _commodity_codes(self.cfg)
                score = score[score.index.isin(comm)]

        if self.abs_momentum_cash:
            if float(score.max()) <= 0:
                return []

        amt = avg_daily_amount(prices, window=self.liquidity_window)
        liquid = amt[amt >= self.cfg.filters.min_avg_daily_amount].index
        score = score[score.index.isin(liquid)]

        if score.empty and self.fallback_score_fn is not None:
            fb = self.fallback_score_fn(prices, date, wkday)
            if not fb.empty:
                fb = fb[fb.index.isin(liquid)]
                score = fb

        if self.trend_filter_weeks is not None and self.trend_filter_weeks > 0:
            allowed = _trend_filter(prices=prices, date=date, weeks=self.trend_filter_weeks, weekday=wkday)
            score = score[score.index.isin(allowed)]

        if score.empty and self.fallback_score_fn is not None:
            fb = self.fallback_score_fn(prices, date, wkday)
            if not fb.empty:
                fb = fb[fb.index.isin(liquid)]
                if self.trend_filter_weeks is not None and self.trend_filter_weeks > 0:
                    allowed = _trend_filter(prices=prices, date=date, weeks=self.trend_filter_weeks, weekday=wkday)
                    fb = fb[fb.index.isin(allowed)]
                score = fb

        ranked = score.sort_values(ascending=False).index.tolist()
        if self.enforce_theme:
            code_to_theme = {u.code: u.theme for u in self.cfg.universe}
            ranked = enforce_one_per_theme(ranked, code_to_theme=code_to_theme)
        return ranked[: self.cfg.backtest.top_n]


def _commodity_codes(cfg: AppConfig) -> List[str]:
    out = []
    for u in cfg.universe:
        theme = str(getattr(u, "theme", ""))
        name = str(getattr(u, "name", ""))
        if ("商品" in theme) or ("商品" in name) or ("黄金" in theme) or ("黄金" in name) or ("原油" in theme) or ("原油" in name):
            out.append(str(u.code))
    for code in ["518880", "159937", "159746", "159981", "159970", "512400", "159735", "159839"]:
        if code not in out:
            out.append(code)
    return out


def _score_simple_momentum(lookback_weeks: int) -> Callable[[pd.DataFrame, pd.Timestamp, int], pd.Series]:
    def _fn(prices: pd.DataFrame, date: pd.Timestamp, weekday: int) -> pd.Series:
        return momentum_score(prices, date=date, lookback_weeks=int(lookback_weeks), weekday=weekday)

    return _fn


def _score_composite_momentum(lookbacks: List[int]) -> Callable[[pd.DataFrame, pd.Timestamp, int], pd.Series]:
    lookbacks = [int(x) for x in lookbacks if int(x) > 0]

    def _fn(prices: pd.DataFrame, date: pd.Timestamp, weekday: int) -> pd.Series:
        parts = []
        for lb in lookbacks:
            s = momentum_score(prices, date=date, lookback_weeks=lb, weekday=weekday)
            if not s.empty:
                parts.append(s)
        if not parts:
            return pd.Series(dtype=float)
        idx = parts[0].index
        for s in parts[1:]:
            idx = idx.union(s.index)
        mat = np.vstack([s.reindex(idx).to_numpy(dtype=float) for s in parts])
        out = np.nanmean(mat, axis=0)
        return pd.Series(out, index=idx).dropna()

    return _fn


def _score_vol_adj_momentum(lookback_weeks: int, vol_weeks: int) -> Callable[[pd.DataFrame, pd.Timestamp, int], pd.Series]:
    def _fn(prices: pd.DataFrame, date: pd.Timestamp, weekday: int) -> pd.Series:
        mom = momentum_score(prices, date=date, lookback_weeks=int(lookback_weeks), weekday=weekday)
        if mom.empty:
            return mom
        wk = weekly_prices(prices, weekday=weekday)
        wk = wk[wk.index <= date]
        if wk.empty:
            return pd.Series(dtype=float)
        rets = wk.pct_change().dropna()
        if rets.empty:
            return pd.Series(dtype=float)
        rets = rets.iloc[-int(vol_weeks) :] if len(rets) > int(vol_weeks) else rets
        vol = rets.std(ddof=0).replace(0.0, float("nan"))
        out = (mom / vol).replace([float("inf"), float("-inf")], float("nan"))
        out = out.dropna()
        return out if not out.empty else mom.dropna()

    return _fn


def _trend_filter(prices: pd.DataFrame, date: pd.Timestamp, weeks: int, weekday: int) -> List[str]:
    wk = weekly_prices(prices, weekday=weekday)
    wk = wk[wk.index <= date]
    if wk.empty:
        return []
    end = wk.iloc[-1]
    n = int(weeks)
    ma = wk.rolling(window=n, min_periods=n).mean().iloc[-1]
    ok = (end > ma).replace([True, False], [True, False])
    return ok[ok].index.tolist()


def build_s1_momentum_variants(cfg: AppConfig) -> List[RotationStrategy]:
    return [
        MomentumRotationVariant(
            cfg=cfg,
            name="s1_momentum_base",
            score_fn=_score_simple_momentum(lookback_weeks=6),
            liquidity_window=20,
            trend_filter_weeks=None,
            abs_momentum_cash=False,
        ),
        MomentumRotationVariant(
            cfg=cfg,
            name="s1_momentum_imp1_long_lookback",
            score_fn=_score_simple_momentum(lookback_weeks=12),
            liquidity_window=20,
            trend_filter_weeks=None,
            abs_momentum_cash=False,
        ),
        MomentumRotationVariant(
            cfg=cfg,
            name="s1_momentum_imp2_vol_adj",
            score_fn=_score_vol_adj_momentum(lookback_weeks=12, vol_weeks=12),
            fallback_score_fn=_score_simple_momentum(lookback_weeks=12),
            liquidity_window=20,
            trend_filter_weeks=None,
            abs_momentum_cash=False,
        ),
        MomentumRotationVariant(
            cfg=cfg,
            name="s1_momentum_imp3_trend_filter",
            score_fn=_score_simple_momentum(lookback_weeks=12),
            liquidity_window=20,
            trend_filter_weeks=20,
            abs_momentum_cash=False,
        ),
        MomentumRotationVariant(
            cfg=cfg,
            name="s1_momentum_imp4_abs_mom_cash",
            score_fn=_score_simple_momentum(lookback_weeks=12),
            liquidity_window=20,
            trend_filter_weeks=None,
            abs_momentum_cash=True,
        ),
        MomentumRotationVariant(
            cfg=cfg,
            name="s1_momentum_imp5_composite",
            score_fn=_score_composite_momentum([4, 12, 24]),
            liquidity_window=20,
            trend_filter_weeks=None,
            abs_momentum_cash=False,
        ),
    ]
