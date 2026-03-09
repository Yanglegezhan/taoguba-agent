from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.engine.result import BacktestResult
from etf_rotation.strategies.base import RotationStrategy


def _week_ends(index: pd.DatetimeIndex, rebalance_weekday: int) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(index).sort_values().unique()
    wk = idx[idx.weekday == rebalance_weekday]
    return wk


def _liquidity_filter(
    prices: pd.DataFrame,
    candidates: List[str],
    asof: pd.Timestamp,
    window_days: int,
    min_avg_amount: float,
) -> List[str]:
    amt = prices.attrs.get("amount")
    if not isinstance(amt, pd.DataFrame) or amt.empty:
        return candidates
    amt = amt.reindex(prices.index)
    amt = amt.loc[amt.index <= asof]
    if amt.empty:
        return candidates
    avg_amt = amt[candidates].rolling(window_days).mean().iloc[-1]
    liquid = avg_amt[avg_amt >= float(min_avg_amount)].index.tolist()
    liquid_set = set(liquid)
    return [c for c in candidates if c in liquid_set]


def _correlation_diversify(
    prices: pd.DataFrame,
    ranked: List[str],
    asof: pd.Timestamp,
    lookback_days: int,
    threshold: float,
    top_n: int,
) -> List[str]:
    if not ranked:
        return []
    if len(ranked) <= 1:
        return ranked[:top_n]

    px = prices[ranked].loc[prices.index <= asof]
    if px.empty:
        return ranked[:top_n]

    rets = px.pct_change().dropna()
    rets = rets.iloc[-lookback_days:] if len(rets) > lookback_days else rets
    if rets.empty:
        return ranked[:top_n]

    corr = rets.corr()

    chosen: List[str] = []
    for code in ranked:
        if code not in corr.columns:
            continue
        ok = True
        for c in chosen:
            if c not in corr.columns:
                continue
            v = float(corr.loc[code, c])
            if np.isfinite(v) and abs(v) >= float(threshold):
                ok = False
                break
        if ok:
            chosen.append(code)
        if len(chosen) >= int(top_n):
            break

    if len(chosen) < int(top_n):
        chosen_set = set(chosen)
        for code in ranked:
            if code in chosen_set:
                continue
            chosen.append(code)
            if len(chosen) >= int(top_n):
                break

    return chosen


@dataclass
class Backtester:
    cfg: AppConfig
    strategy: RotationStrategy

    def run(self, prices: pd.DataFrame, benchmark: pd.Series) -> BacktestResult:
        prices = prices.sort_index()
        benchmark = benchmark.sort_index().reindex(prices.index).ffill()

        rebal_dates = _week_ends(prices.index, self.cfg.backtest.rebalance_weekday)
        rebal_dates = rebal_dates[(rebal_dates >= prices.index.min()) & (rebal_dates <= prices.index.max())]

        initial_cash = float(self.cfg.backtest.initial_cash)
        nav = pd.Series(index=prices.index, dtype=float)
        holdings: Dict[str, float] = {}
        last_rebalance_date: Optional[pd.Timestamp] = None
        entry_week_by_code: Dict[str, pd.Timestamp] = {}
        pos_records: List[Dict[str, float | str]] = []

        peak_nav = float(self.cfg.backtest.initial_cash)
        cooldown_until: Optional[pd.Timestamp] = None

        cash = initial_cash

        for dt in prices.index:
            px = prices.loc[dt]
            port_value = cash + sum(qty * float(px.get(code, np.nan)) for code, qty in holdings.items())
            nav.loc[dt] = port_value

            if np.isfinite(float(port_value)) and float(port_value) > peak_nav:
                peak_nav = float(port_value)

            stop_dd = float(getattr(self.cfg.backtest, "stoploss_drawdown", 0.0) or 0.0)
            if stop_dd > 0 and peak_nav > 0 and holdings:
                dd = float(port_value / peak_nav - 1.0)
                if dd <= -abs(stop_dd):
                    commission_rate = float(self.cfg.backtest.commission_rate)
                    min_commission = float(self.cfg.backtest.min_commission)
                    slippage_rate = float(self.cfg.backtest.slippage_rate)
                    for code, qty in list(holdings.items()):
                        price = float(px.get(code, np.nan))
                        if not np.isfinite(price) or price <= 0:
                            continue
                        trade_value = abs(float(qty)) * price
                        commission = max(trade_value * commission_rate, min_commission) if trade_value > 0 else 0.0
                        slippage = trade_value * slippage_rate
                        cost = commission + slippage
                        cash += (trade_value - cost)
                    holdings.clear()
                    entry_week_by_code.clear()

                    cd_weeks = int(getattr(self.cfg.backtest, "stoploss_cooldown_weeks", 0) or 0)
                    cooldown_until = (dt + pd.Timedelta(days=cd_weeks * 7)) if cd_weeks > 0 else None
                    peak_nav = float(cash)

                    # realize liquidation on the trigger day
                    nav.loc[dt] = float(cash)
                    port_value = float(cash)

                    pos_records.append({
                        "date": str(dt.date()),
                        "code": "CASH",
                        "qty": float("nan"),
                        "price": float("nan"),
                        "value": float(cash),
                        "weight": 1.0,
                    })

            if dt not in rebal_dates:
                continue

            if cooldown_until is not None and dt <= cooldown_until:
                continue

            if last_rebalance_date is None:
                last_rebalance_date = dt

            selected = self.strategy.select(date=dt, prices=prices)
            selected = [c for c in selected if c in prices.columns]

            selected = _liquidity_filter(
                prices=prices,
                candidates=selected,
                asof=dt,
                window_days=int(self.cfg.filters.liquidity_window_days),
                min_avg_amount=float(self.cfg.filters.min_avg_daily_amount),
            )

            if getattr(self.cfg.correlation, "enabled", True):
                selected = _correlation_diversify(
                    prices=prices,
                    ranked=selected,
                    asof=dt,
                    lookback_days=int(self.cfg.correlation.lookback_days),
                    threshold=float(self.cfg.correlation.threshold),
                    top_n=int(self.cfg.backtest.top_n),
                )

            target_weights = self.strategy.weights(date=dt, selected=selected, prices=prices)

            min_hold_weeks = int(self.cfg.backtest.min_hold_weeks)
            if min_hold_weeks > 0 and holdings:
                allowed_to_sell = set()
                for code in list(holdings.keys()):
                    entry_dt = entry_week_by_code.get(code)
                    if entry_dt is None:
                        allowed_to_sell.add(code)
                        continue
                    weeks_held = int(((dt - entry_dt).days) // 7)
                    if weeks_held >= min_hold_weeks:
                        allowed_to_sell.add(code)
                forced_hold = set(holdings.keys()) - allowed_to_sell
                for code in forced_hold:
                    if code not in target_weights:
                        target_weights[code] = 0.0

            target_weights = {k: float(v) for k, v in target_weights.items() if float(v) >= 0}
            s = sum(target_weights.values())
            if s > 0:
                target_weights = {k: v / s for k, v in target_weights.items()}

            port_value = float(nav.loc[dt])

            target_qty: Dict[str, float] = {}
            for code, w in target_weights.items():
                price = float(px[code])
                if not np.isfinite(price) or price <= 0:
                    continue
                target_qty[code] = (port_value * w) / price

            all_codes = set(holdings.keys()) | set(target_qty.keys())

            commission_rate = float(self.cfg.backtest.commission_rate)
            min_commission = float(self.cfg.backtest.min_commission)
            slippage_rate = float(self.cfg.backtest.slippage_rate)

            for code in all_codes:
                cur = float(holdings.get(code, 0.0))
                tgt = float(target_qty.get(code, 0.0))
                delta = tgt - cur
                if abs(delta) < 1e-12:
                    continue

                price = float(px.get(code, np.nan))
                if not np.isfinite(price) or price <= 0:
                    continue

                trade_value = abs(delta) * price
                commission = max(trade_value * commission_rate, min_commission) if trade_value > 0 else 0.0
                slippage = trade_value * slippage_rate
                cost = commission + slippage

                if delta > 0:
                    cash_change = -(trade_value + cost)
                else:
                    cash_change = +(trade_value - cost)

                cash += cash_change
                new_qty = cur + delta
                if abs(new_qty) < 1e-10:
                    holdings.pop(code, None)
                    entry_week_by_code.pop(code, None)
                else:
                    holdings[code] = new_qty
                    if code not in entry_week_by_code and delta > 0:
                        entry_week_by_code[code] = dt

            # snapshot positions after rebalance
            px_now = prices.loc[dt]
            pos_value = 0.0
            for code, qty in holdings.items():
                p = float(px_now.get(code, np.nan))
                if not np.isfinite(p) or p <= 0:
                    continue
                pos_value += float(qty) * p
            total_value = float(cash + pos_value)
            if total_value > 0:
                for code, qty in holdings.items():
                    p = float(px_now.get(code, np.nan))
                    if not np.isfinite(p) or p <= 0:
                        continue
                    v = float(qty) * p
                    w = v / total_value
                    pos_records.append({
                        "date": str(dt.date()),
                        "code": str(code),
                        "qty": float(qty),
                        "price": float(p),
                        "value": float(v),
                        "weight": float(w),
                    })
                pos_records.append({
                    "date": str(dt.date()),
                    "code": "CASH",
                    "qty": float("nan"),
                    "price": float("nan"),
                    "value": float(cash),
                    "weight": float(cash / total_value),
                })

            last_rebalance_date = dt

        daily_ret = nav.pct_change().fillna(0.0)
        bench_nav = benchmark / float(benchmark.iloc[0]) * initial_cash
        bench_ret = bench_nav.pct_change().fillna(0.0)

        positions = pd.DataFrame(pos_records)

        return BacktestResult(
            nav=nav,
            returns=daily_ret,
            benchmark_nav=bench_nav,
            benchmark_returns=bench_ret,
            rebalance_dates=rebal_dates,
            positions=positions,
        )
