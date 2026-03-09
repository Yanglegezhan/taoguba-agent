from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import shutil

import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.data.market_data import MarketData
from etf_rotation.engine.backtester import Backtester
from etf_rotation.reporting.reporter import Reporter
from etf_rotation.reporting.stats import compute_metrics
from etf_rotation.strategies.registry import build_all_strategies
from etf_rotation.strategies.s1_momentum import build_s1_momentum_variants
from etf_rotation.strategies.s1_momentum import MomentumRotationVariant
from etf_rotation.strategies.helpers import momentum_score


@dataclass
class BatchRunner:
    cfg: AppConfig
    project_root: Path

    def run_all(self) -> None:
        output_root = self.project_root / self.cfg.project.output_dir
        output_root.mkdir(parents=True, exist_ok=True)

        mkt = MarketData(cfg=self.cfg, project_root=self.project_root)
        prices = mkt.load_universe_prices()
        benchmark = mkt.load_benchmark_prices()

        strategies = build_all_strategies(cfg=self.cfg)

        for legacy in ["s3_flow_proxy", "s5_value_earnings_proxy", "s7_multi_factor"]:
            p = output_root / legacy
            if p.exists() and legacy not in strategies:
                shutil.rmtree(p, ignore_errors=True)

        summary_rows = []
        for name, strat in strategies.items():
            bt = Backtester(cfg=self.cfg, strategy=strat)
            result = bt.run(prices=prices, benchmark=benchmark)

            rep = Reporter(cfg=self.cfg)
            out_dir = output_root / name
            out_dir.mkdir(parents=True, exist_ok=True)
            metrics = rep.write_all(out_dir=out_dir, result=result)
            metrics["strategy"] = name
            summary_rows.append(metrics)

        self._run_s1_momentum_compare(output_root=output_root, prices=prices, benchmark=benchmark)
        self._run_s1_momentum_optimize(output_root=output_root, prices=prices, benchmark=benchmark)

        if summary_rows:
            summary = pd.DataFrame(summary_rows).set_index("strategy").sort_index()
            summary.to_csv(output_root / "summary.csv", encoding="utf-8-sig")

    def run_s1_optimize_only(self) -> None:
        output_root = self.project_root / self.cfg.project.output_dir
        output_root.mkdir(parents=True, exist_ok=True)

        mkt = MarketData(cfg=self.cfg, project_root=self.project_root)
        prices = mkt.load_universe_prices()
        benchmark = mkt.load_benchmark_prices()

        self._run_s1_momentum_optimize(output_root=output_root, prices=prices, benchmark=benchmark)

    def _run_s1_momentum_compare(self, output_root: Path, prices: pd.DataFrame, benchmark: pd.Series) -> None:
        compare_root = output_root / "s1_momentum_compare"
        compare_root.mkdir(parents=True, exist_ok=True)

        variants = build_s1_momentum_variants(cfg=self.cfg)

        in_start = pd.Timestamp("2020-01-01")
        in_end = pd.Timestamp("2024-01-01")
        out_start = pd.Timestamp("2024-01-01")
        out_end = pd.Timestamp("2026-01-01")
        warmup_days = 260

        rep = Reporter(cfg=self.cfg)
        in_rows = []
        out_rows = []

        for strat in variants:
            bt = Backtester(cfg=self.cfg, strategy=strat)

            in_dir = compare_root / strat.name / "in_sample"
            in_dir.mkdir(parents=True, exist_ok=True)
            in_res = bt.run(prices=_slice_with_warmup(prices, in_start, in_end, warmup_days), benchmark=_slice_with_warmup(benchmark, in_start, in_end, warmup_days))
            in_res = _trim_result(in_res, start=in_start, end=in_end)
            in_metrics = rep.write_all(out_dir=in_dir, result=in_res)
            in_metrics["version"] = strat.name
            in_rows.append(in_metrics)

            out_dir = compare_root / strat.name / "out_sample"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_res = bt.run(prices=_slice_with_warmup(prices, out_start, out_end, warmup_days), benchmark=_slice_with_warmup(benchmark, out_start, out_end, warmup_days))
            out_res = _trim_result(out_res, start=out_start, end=out_end)
            out_metrics = rep.write_all(out_dir=out_dir, result=out_res)
            out_metrics["version"] = strat.name
            out_rows.append(out_metrics)

        _write_compare_report(compare_root / "report.md", in_rows=in_rows, out_rows=out_rows, reporter=rep)

    def _run_s1_momentum_optimize(self, output_root: Path, prices: pd.DataFrame, benchmark: pd.Series) -> None:
        opt_root = output_root / "s1_momentum_optimize"
        opt_root.mkdir(parents=True, exist_ok=True)

        in_start = pd.Timestamp("2020-01-01")
        in_end = pd.Timestamp("2024-01-01")
        out_start = pd.Timestamp("2024-01-01")
        out_end = pd.Timestamp("2026-01-01")
        warmup_days = 520

        rep = Reporter(cfg=self.cfg)

        stop_dd = float(getattr(self.cfg.backtest, "stoploss_drawdown", 0.10) or 0.10)
        cd_weeks = int(getattr(self.cfg.backtest, "stoploss_cooldown_weeks", 4) or 4)

        lookbacks = [2, 3, 4, 6, 8, 12, 16, 24, 36, 52]
        top_ns = [1, 2, 3, 4, 5, 7, 10]
        trend_weeks = [None, 10, 20, 30]
        abs_cash = [False, True]
        corr_enabled = [True, False]
        theme_enforced = [True, False]
        risk_off = [False, True]
        breadth_th = [0.0, 0.3, 0.5, 0.7]

        best = None
        best_metrics = None

        for lb in lookbacks:
            for n in top_ns:
                for tw in trend_weeks:
                    for ac in abs_cash:
                        for corr_on in corr_enabled:
                            for theme_on in theme_enforced:
                                for ro in risk_off:
                                    for br in breadth_th:
                                        if (not ro) and float(br) > 0:
                                            continue
                                        cfg_n = self.cfg.model_copy(update={
                                            "backtest": self.cfg.backtest.model_copy(update={
                                                "top_n": int(n),
                                                "stoploss_drawdown": float(stop_dd),
                                                "stoploss_cooldown_weeks": int(cd_weeks),
                                            }),
                                            "correlation": self.cfg.correlation.model_copy(update={
                                                "enabled": bool(corr_on),
                                            }),
                                        })
                                        strat = MomentumRotationVariant(
                                            cfg=cfg_n,
                                            name=f"opt_lb{lb}_n{n}_trend{tw if tw is not None else 0}_abs{1 if ac else 0}_corr{1 if corr_on else 0}_theme{1 if theme_on else 0}_ro{1 if ro else 0}_br{int(round(float(br)*10))}",
                                            score_fn=(lambda prices_, date_, weekday_, _lb=int(lb): momentum_score(prices_, date=date_, lookback_weeks=_lb, weekday=weekday_)),
                                            fallback_score_fn=None,
                                            liquidity_window=20,
                                            trend_filter_weeks=tw,
                                            abs_momentum_cash=ac,
                                            enforce_theme=bool(theme_on),
                                            risk_off_to_commodities=bool(ro),
                                            breadth_positive_ratio_threshold=float(br),
                                        )
                                        bt = Backtester(cfg=cfg_n, strategy=strat)
                                        in_res = bt.run(
                                            prices=_slice_with_warmup(prices, in_start, in_end, warmup_days),
                                            benchmark=_slice_with_warmup(benchmark, in_start, in_end, warmup_days),
                                        )
                                        in_res = _trim_result(in_res, start=in_start, end=in_end)
                                        m = compute_metrics(in_res)
                                        ann = float(m.get("ann_return", float("nan")))
                                        if not np.isfinite(ann):
                                            continue
                                        if best_metrics is None or ann > float(best_metrics.get("ann_return", float("-inf"))):
                                            best = (cfg_n, strat)
                                            best_metrics = m

        lines = [
            "# 策略1（动量）自动优化报告",
            "",
            f"止损阈值: {-abs(stop_dd):.2%}",
            f"冷静期(周): {cd_weeks}",
            "说明：止损为触发式风控（触发后清仓+冷静期），最大回撤可能仍会略超阈值（跳空/周度交易/手续费等原因）。",
            "",
        ]

        if best is None or best_metrics is None:
            (opt_root / "report.md").write_text("\n".join(lines + ["未找到可用参数组合。"]), encoding="utf-8")
            return

        cfg_best, strat_best = best
        target = 0.50
        ann_best = float(best_metrics.get("ann_return", float("nan")))
        reached = bool(np.isfinite(ann_best) and ann_best >= target)

        lines += [
            "## 样本内最优参数（2020-01-01 ~ 2024-01-01）",
            "",
            f"最优版本: `{strat_best.name}`",
            f"样本内年化收益率: {ann_best:.5f}",
            f"是否达到50%: {'是' if reached else '否'}",
            "",
        ]

        best_in_dir = opt_root / "best" / "in_sample"
        best_in_dir.mkdir(parents=True, exist_ok=True)
        bt_best = Backtester(cfg=cfg_best, strategy=strat_best)
        in_res = bt_best.run(
            prices=_slice_with_warmup(prices, in_start, in_end, warmup_days),
            benchmark=_slice_with_warmup(benchmark, in_start, in_end, warmup_days),
        )
        in_res = _trim_result(in_res, start=in_start, end=in_end)
        in_m = rep.write_all(out_dir=best_in_dir, result=in_res)

        best_out_dir = opt_root / "best" / "out_sample"
        best_out_dir.mkdir(parents=True, exist_ok=True)
        out_res = bt_best.run(
            prices=_slice_with_warmup(prices, out_start, out_end, warmup_days),
            benchmark=_slice_with_warmup(benchmark, out_start, out_end, warmup_days),
        )
        out_res = _trim_result(out_res, start=out_start, end=out_end)
        out_m = rep.write_all(out_dir=best_out_dir, result=out_res)

        lines += [
            "## 样本外验证（2024-01-01 ~ 2026-01-01）",
            "",
            "| 指标 | 样本内 | 样本外 |",
            "|---|---:|---:|",
            f"| 年化收益率 | {rep._format_value(in_m.get('ann_return'))} | {rep._format_value(out_m.get('ann_return'))} |",
            f"| 最大回撤 | {rep._format_value(in_m.get('max_drawdown'))} | {rep._format_value(out_m.get('max_drawdown'))} |",
            f"| 夏普比率 | {rep._format_value(in_m.get('sharpe'))} | {rep._format_value(out_m.get('sharpe'))} |",
            f"| 累计收益率 | {rep._format_value(in_m.get('cum_return'))} | {rep._format_value(out_m.get('cum_return'))} |",
            "",
        ]

        (opt_root / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _slice_with_warmup(obj, start: pd.Timestamp, end: pd.Timestamp, warmup_days: int):
    s = pd.Timestamp(start) - pd.Timedelta(days=int(warmup_days))
    e = pd.Timestamp(end)
    if isinstance(obj, pd.DataFrame):
        return obj.loc[(obj.index >= s) & (obj.index <= e)].copy()
    return obj.loc[(obj.index >= s) & (obj.index <= e)].copy()


def _trim_result(result, start: pd.Timestamp, end: pd.Timestamp):
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    nav = result.nav.loc[(result.nav.index >= start) & (result.nav.index <= end)].copy()
    bnav = result.benchmark_nav.reindex(nav.index).copy()
    ret = nav.pct_change().fillna(0.0)
    bret = bnav.pct_change().fillna(0.0)
    reb = pd.DatetimeIndex(result.rebalance_dates)
    reb = reb[(reb >= start) & (reb <= end)]
    pos = result.positions
    if isinstance(pos, pd.DataFrame) and not pos.empty and "date" in pos.columns:
        d = pd.to_datetime(pos["date"], errors="coerce")
        m = (d >= start) & (d <= end)
        pos = pos.loc[m].copy()
    return type(result)(
        nav=nav,
        returns=ret,
        benchmark_nav=bnav,
        benchmark_returns=bret,
        rebalance_dates=reb,
        positions=pos,
    )


def _write_compare_report(path: Path, in_rows: list[dict], out_rows: list[dict], reporter: Reporter) -> None:
    def _table(rows: list[dict]) -> list[str]:
        if not rows:
            return ["(无数据)"]
        cols = [
            ("version", "版本"),
            ("cum_return", "累计收益率"),
            ("ann_return", "年化收益率"),
            ("ann_vol", "年化波动率"),
            ("sharpe", "夏普比率"),
            ("max_drawdown", "最大回撤"),
        ]
        header = "| " + " | ".join([c[1] for c in cols]) + " |"
        sep = "|" + "|".join(["---" for _ in cols]) + "|"
        lines = [header, sep]
        for r in rows:
            vals = []
            for k, _cn in cols:
                if k == "version":
                    vals.append(str(r.get(k, "")))
                else:
                    vals.append(reporter._format_value(r.get(k)))
            lines.append("| " + " | ".join(vals) + " |")
        return lines

    in_rows = sorted(in_rows, key=lambda x: float(x.get("ann_return", float("-inf"))), reverse=True)
    out_rows = sorted(out_rows, key=lambda x: float(x.get("ann_return", float("-inf"))), reverse=True)

    lines = [
        "# 策略1（动量）改进对比报告",
        "",
        "## 样本内（2020-01-01 ~ 2024-01-01）",
        "",
        *_table(in_rows),
        "",
        "## 样本外（2024-01-01 ~ 2026-01-01）",
        "",
        *_table(out_rows),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
