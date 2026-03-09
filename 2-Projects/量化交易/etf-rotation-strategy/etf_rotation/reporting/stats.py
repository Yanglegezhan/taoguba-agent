from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from etf_rotation.engine.result import BacktestResult


def _max_drawdown(nav: pd.Series) -> float:
    cum_max = nav.cummax()
    dd = nav / cum_max - 1.0
    return float(dd.min())


def _max_drawdown_interval(nav: pd.Series) -> tuple[pd.Timestamp | None, pd.Timestamp | None, float]:
    nav = nav.dropna()
    if nav.empty:
        return None, None, float("nan")

    cum_max = nav.cummax()
    dd = nav / cum_max - 1.0
    end = dd.idxmin()
    start = nav.loc[:end].idxmax() if pd.notna(end) else None
    return start, end, float(dd.min())


def _annualized_return(nav: pd.Series) -> float:
    nav = nav.dropna()
    if len(nav) < 2:
        return float("nan")
    days = (nav.index[-1] - nav.index[0]).days
    if days <= 0:
        return float("nan")
    total = float(nav.iloc[-1] / nav.iloc[0])
    return total ** (365.0 / days) - 1.0


def _annualized_return_by_periods(nav: pd.Series, periods_per_year: int) -> float:
    nav = nav.dropna()
    if len(nav) < 2:
        return float("nan")
    total = float(nav.iloc[-1] / nav.iloc[0])
    n = len(nav) - 1
    if n <= 0:
        return float("nan")
    return total ** (float(periods_per_year) / float(n)) - 1.0


def _annualized_vol(returns: pd.Series) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    return float(r.std(ddof=0) * np.sqrt(252))


def _annualized_vol_by_periods(returns: pd.Series, periods_per_year: int) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    return float(r.std(ddof=0) * np.sqrt(periods_per_year))


def _downside_vol(returns: pd.Series, rf_per_period: float = 0.0, periods_per_year: int = 252) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    ex = r - rf_per_period
    downside = ex[ex < 0]
    if downside.empty:
        return 0.0
    return float(downside.std(ddof=0) * np.sqrt(periods_per_year))


def _sharpe(returns: pd.Series, rf_per_period: float = 0.0, periods_per_year: int = 252) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    ex = r - rf_per_period
    vol = ex.std(ddof=0)
    if vol == 0:
        return float("nan")
    return float(ex.mean() / vol * np.sqrt(periods_per_year))


def _sortino(returns: pd.Series, rf_per_period: float = 0.0, periods_per_year: int = 252) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    ex = r - rf_per_period
    downside = ex[ex < 0]
    dd = downside.std(ddof=0)
    if dd == 0 or not np.isfinite(dd):
        return float("nan")
    return float(ex.mean() / dd * np.sqrt(periods_per_year))


def _calmar(ann_return: float, max_drawdown: float) -> float:
    if not np.isfinite(ann_return) or not np.isfinite(max_drawdown) or max_drawdown == 0:
        return float("nan")
    return float(ann_return / abs(max_drawdown))


def _alpha_beta(
    strategy_ret: pd.Series,
    benchmark_ret: pd.Series,
    rf_per_period: float = 0.0,
    periods_per_year: int = 252,
) -> tuple[float, float]:
    s = strategy_ret.dropna()
    b = benchmark_ret.dropna()
    idx = s.index.intersection(b.index)
    if len(idx) < 30:
        return float("nan"), float("nan")

    s = s.loc[idx].astype(float)
    b = b.loc[idx].astype(float)
    s_ex = s - rf_per_period
    b_ex = b - rf_per_period

    var_b = float(b_ex.var(ddof=0))
    if var_b == 0 or not np.isfinite(var_b):
        return float("nan"), float("nan")

    beta = float(np.cov(s_ex, b_ex, ddof=0)[0, 1] / var_b)
    alpha_daily = float(s_ex.mean() - beta * b_ex.mean())
    alpha_ann = float(alpha_daily * periods_per_year)
    return alpha_ann, beta


def _information_ratio(excess_returns: pd.Series) -> float:
    x = excess_returns.dropna().astype(float)
    if x.empty:
        return float("nan")
    te = float(x.std(ddof=0))
    if te == 0 or not np.isfinite(te):
        return float("nan")
    return float(x.mean() / te * np.sqrt(252))


def _information_ratio_by_periods(excess_returns: pd.Series, periods_per_year: int) -> float:
    x = excess_returns.dropna().astype(float)
    if x.empty:
        return float("nan")
    te = float(x.std(ddof=0))
    if te == 0 or not np.isfinite(te):
        return float("nan")
    return float(x.mean() / te * np.sqrt(periods_per_year))


def _win_rate(returns: pd.Series) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    return float((r > 0).mean())


def _profit_loss_ratio(returns: pd.Series) -> float:
    r = returns.dropna().astype(float)
    if r.empty:
        return float("nan")
    pos = r[r > 0]
    neg = r[r < 0]
    if pos.empty or neg.empty:
        return float("nan")
    return float(pos.mean() / abs(neg.mean()))


def _count_pos_neg(returns: pd.Series) -> tuple[int, int]:
    r = returns.dropna().astype(float)
    if r.empty:
        return 0, 0
    return int((r > 0).sum()), int((r < 0).sum())


def compute_metrics(result: BacktestResult) -> Dict[str, float]:
    nav = result.nav.dropna()
    bnav = result.benchmark_nav.reindex(nav.index).dropna()

    cum_return = float(nav.iloc[-1] / nav.iloc[0] - 1.0) if len(nav) >= 2 else float("nan")
    bench_cum_return = float(bnav.iloc[-1] / bnav.iloc[0] - 1.0) if len(bnav) >= 2 else float("nan")

    periods_per_year = 52
    rf_annual = 0.0
    rf_per_period = rf_annual / periods_per_year

    reb = pd.DatetimeIndex(result.rebalance_dates)
    nav_p = nav.reindex(reb).dropna()
    bnav_p = bnav.reindex(reb).dropna()
    idx = nav_p.index.intersection(bnav_p.index)
    nav_p = nav_p.loc[idx]
    bnav_p = bnav_p.loc[idx]

    if len(nav_p) < 2:
        nav_p = nav
        bnav_p = bnav

    ret_p = nav_p.pct_change().dropna()
    bret_p = bnav_p.pct_change().dropna()

    ann_ret = _annualized_return_by_periods(nav_p, periods_per_year=periods_per_year)
    ann_vol = _annualized_vol_by_periods(ret_p, periods_per_year=periods_per_year)
    sharpe = _sharpe(ret_p, rf_per_period=rf_per_period, periods_per_year=periods_per_year)
    dd_start, dd_end, mdd = _max_drawdown_interval(nav_p)

    sortino = _sortino(ret_p, rf_per_period=rf_per_period, periods_per_year=periods_per_year)
    calmar = _calmar(ann_ret, mdd)
    downside_vol = _downside_vol(ret_p, rf_per_period=rf_per_period, periods_per_year=periods_per_year)

    excess_ret = (ret_p - bret_p).dropna()
    excess_sharpe = _sharpe(excess_ret, rf_per_period=0.0, periods_per_year=periods_per_year)
    info_ratio = _information_ratio_by_periods(excess_ret, periods_per_year=periods_per_year)

    excess_ann_vol = _annualized_vol_by_periods(excess_ret, periods_per_year=periods_per_year)
    excess_sortino = _sortino(excess_ret, rf_per_period=0.0, periods_per_year=periods_per_year)

    alpha, beta = _alpha_beta(ret_p, bret_p, rf_per_period=rf_per_period, periods_per_year=periods_per_year)

    rel_nav = (nav_p / nav_p.iloc[0]) / (bnav_p / bnav_p.iloc[0])
    excess_mdd = _max_drawdown(rel_nav)

    bench_ann_ret = _annualized_return_by_periods(bnav_p, periods_per_year=periods_per_year)
    bench_ann_vol = _annualized_vol_by_periods(bret_p, periods_per_year=periods_per_year)
    bench_sharpe = _sharpe(bret_p, rf_per_period=rf_per_period, periods_per_year=periods_per_year)
    bench_sortino = _sortino(bret_p, rf_per_period=rf_per_period, periods_per_year=periods_per_year)
    bench_mdd = _max_drawdown(bnav_p)

    win_rate = _win_rate(ret_p)
    profit_loss = _profit_loss_ratio(ret_p)
    win_rate_excess = _win_rate(excess_ret)

    pos_cnt, neg_cnt = _count_pos_neg(ret_p)
    pos_cnt_ex, neg_cnt_ex = _count_pos_neg(excess_ret)

    avg_excess = float(excess_ret.mean()) if not excess_ret.empty else float("nan")

    return {
        "cum_return": float(cum_return),
        "ann_return": float(ann_ret),
        "ann_vol": float(ann_vol),
        "return_over_vol": float(ann_ret / ann_vol) if np.isfinite(ann_ret) and np.isfinite(ann_vol) and ann_vol != 0 else float("nan"),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "downside_vol": float(downside_vol),
        "max_drawdown": float(mdd),
        "max_drawdown_start": dd_start.date().isoformat() if dd_start is not None else "",
        "max_drawdown_end": dd_end.date().isoformat() if dd_end is not None else "",
        "calmar": float(calmar),
        "alpha": float(alpha),
        "beta": float(beta),
        "win_rate": float(win_rate),
        "profit_loss_ratio": float(profit_loss),
        "pos_periods": int(pos_cnt),
        "neg_periods": int(neg_cnt),

        "bench_cum_return": float(bench_cum_return),
        "bench_ann_return": float(bench_ann_ret),
        "bench_ann_vol": float(bench_ann_vol),
        "bench_sharpe": float(bench_sharpe),
        "bench_sortino": float(bench_sortino),
        "bench_max_drawdown": float(bench_mdd),
        "bench_return_over_vol": float(bench_ann_ret / bench_ann_vol) if np.isfinite(bench_ann_ret) and np.isfinite(bench_ann_vol) and bench_ann_vol != 0 else float("nan"),

        "excess_ann_return": float(_annualized_return_by_periods(rel_nav, periods_per_year=periods_per_year)),
        "excess_ann_vol": float(excess_ann_vol),
        "excess_return_over_vol": float(_annualized_return_by_periods(rel_nav, periods_per_year=periods_per_year) / excess_ann_vol) if np.isfinite(_annualized_return_by_periods(rel_nav, periods_per_year=periods_per_year)) and np.isfinite(excess_ann_vol) and excess_ann_vol != 0 else float("nan"),
        "excess_sharpe": float(excess_sharpe),
        "excess_sortino": float(excess_sortino),
        "excess_max_drawdown": float(excess_mdd),
        "information_ratio": float(info_ratio),
        "period_excess_win_rate": float(win_rate_excess),
        "avg_excess_return": float(avg_excess),
        "excess_pos_periods": int(pos_cnt_ex),
        "excess_neg_periods": int(neg_cnt_ex),
    }
