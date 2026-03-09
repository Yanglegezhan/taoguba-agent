from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from etf_rotation.config import AppConfig
from etf_rotation.engine.result import BacktestResult
from etf_rotation.reporting.stats import compute_metrics


@dataclass
class Reporter:
    cfg: AppConfig

    METRIC_NAME_MAP: ClassVar[Dict[str, str]] = {
        "cum_return": "累计收益率",
        "ann_return": "年化收益率",
        "ann_vol": "年化波动率",
        "return_over_vol": "年化收益/年化波动",
        "sharpe": "夏普比率",
        "sortino": "索提诺比率",
        "downside_vol": "年化下行波动率",
        "max_drawdown": "最大回撤",
        "max_drawdown_start": "最大回撤开始日期",
        "max_drawdown_end": "最大回撤结束日期",
        "calmar": "卡尔玛比率",
        "alpha": "阿尔法",
        "beta": "贝塔",
        "win_rate": "胜率(按调仓周期)",
        "profit_loss_ratio": "盈亏比(按调仓周期)",
        "pos_periods": "盈利周期数",
        "neg_periods": "亏损周期数",

        "bench_cum_return": "基准累计收益率",
        "bench_ann_return": "基准年化收益率",
        "bench_ann_vol": "基准年化波动率",
        "bench_sharpe": "基准夏普比率",
        "bench_sortino": "基准索提诺比率",
        "bench_max_drawdown": "基准最大回撤",
        "bench_return_over_vol": "基准年化收益/年化波动",

        "excess_ann_return": "超额年化收益率",
        "excess_ann_vol": "超额年化波动率",
        "excess_return_over_vol": "超额年化收益/年化波动",
        "excess_sharpe": "超额夏普比率",
        "excess_sortino": "超额索提诺比率",
        "excess_max_drawdown": "超额最大回撤",
        "information_ratio": "信息比率",
        "period_excess_win_rate": "超额胜率(按调仓周期)",
        "avg_excess_return": "平均超额收益(每周期)",
        "excess_pos_periods": "超额盈利周期数",
        "excess_neg_periods": "超额亏损周期数",
    }

    def write_all(self, out_dir: Path, result: BacktestResult) -> Dict[str, float]:
        metrics = compute_metrics(result)

        if isinstance(result.positions, pd.DataFrame) and not result.positions.empty:
            code_to_name = {u.code: u.name for u in self.cfg.universe}
            pos = result.positions.copy()
            pos["name"] = pos["code"].map(code_to_name).fillna("")
            cols = [c for c in ["date", "code", "name", "weight", "value", "qty", "price"] if c in pos.columns]
            pos = pos[cols]
            pos.to_csv(out_dir / "positions.csv", index=False, encoding="utf-8-sig")

        nav_df = pd.DataFrame({"nav": result.nav, "benchmark_nav": result.benchmark_nav}).dropna()
        nav_df.to_csv(out_dir / "nav.csv", encoding="utf-8-sig")

        ret_df = pd.DataFrame({"ret": result.returns, "benchmark_ret": result.benchmark_returns}).dropna()
        ret_df.to_csv(out_dir / "returns.csv", encoding="utf-8-sig")

        self._plot_nav(out_dir / "equity_curve.png", nav_df)
        self._write_md(out_dir / "report.md", metrics)
        return metrics

    def _plot_nav(self, path: Path, nav_df: pd.DataFrame) -> None:
        df = nav_df.copy().dropna()
        if df.empty:
            return

        s0 = float(df["nav"].iloc[0])
        b0 = float(df["benchmark_nav"].iloc[0])
        if s0 <= 0 or b0 <= 0:
            return

        df["nav_norm"] = df["nav"] / s0
        df["bench_norm"] = df["benchmark_nav"] / b0

        roll_max = df["nav_norm"].cummax()
        df["drawdown"] = df["nav_norm"] / roll_max - 1.0

        df["nav_norm"] = df["nav_norm"].round(5)
        df["bench_norm"] = df["bench_norm"].round(5)
        df["drawdown"] = df["drawdown"].round(5)

        plt.rcParams.update({
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
            "axes.unicode_minus": False,
        })

        fig, (ax1, ax2) = plt.subplots(
            2,
            1,
            figsize=(13, 7.5),
            sharex=True,
            gridspec_kw={"height_ratios": [3, 1]},
        )

        ax1.plot(df.index, df["nav_norm"], label="策略", linewidth=2.0)
        ax1.plot(df.index, df["bench_norm"], label="基准", linewidth=1.6, alpha=0.9)
        ax1.set_title("净值曲线（归一化）")
        ax1.legend(loc="upper left", frameon=False)
        ax1.set_ylabel("净值")

        underwater = (df["drawdown"] * 100.0).astype(float)
        ax2.axhline(0.0, color="#666666", linewidth=0.8, alpha=0.6)
        ax2.plot(df.index, underwater, color="#1f77b4", linewidth=1.2)
        ax2.fill_between(df.index, underwater.to_numpy(), np.zeros(len(df)), color="#1f77b4", alpha=0.18)
        ax2.set_ylabel("水下（%）")
        ax2.set_xlabel("日期")
        ymin = float(underwater.min()) * 1.05 if np.isfinite(float(underwater.min())) else -10.0
        ax2.set_ylim(min(-100.0, ymin), 2.0)

        plt.tight_layout()
        plt.savefig(path, dpi=220)
        plt.close(fig)

    def _format_value(self, v) -> str:
        if isinstance(v, (float, int, np.floating, np.integer)):
            if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                return ""
            if isinstance(v, (int, np.integer)):
                return str(int(v))
            return f"{float(v):.5f}"
        if v is None:
            return ""
        return str(v)

    def _cn_metric_name(self, k: str) -> str:
        return self.METRIC_NAME_MAP.get(k, k)

    def _write_md(self, path: Path, metrics: Dict[str, float]) -> None:
        lines = ["# 回测报告", "", "## 指标", "", "| 指标 | 数值 |", "|---|---:|"]
        for k, v in metrics.items():
            lines.append(f"| {self._cn_metric_name(k)} | {self._format_value(v)} |")
        path.write_text("\n".join(lines), encoding="utf-8")
