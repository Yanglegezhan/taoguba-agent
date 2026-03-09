from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    timezone: str = "Asia/Shanghai"
    output_dir: str = "outputs"
    universe_source: str = "config"
    plan_md_path: str = "etf-rotation-strategy-plan.md"


class DataConfig(BaseModel):
    provider: str = "akshare"
    cache_dir: str = "data_cache"
    start_date: str = "2018-01-01"
    end_date: Optional[str] = None
    benchmark_code: str = "sh000001"
    disable_proxy: bool = True
    max_retries: int = 5
    retry_backoff_seconds: float = 1.5


class BacktestConfig(BaseModel):
    initial_cash: float = 1_000_000
    rebalance_weekday: int = 4
    top_n: int = 5
    min_hold_weeks: int = 1
    commission_rate: float = 0.0005
    min_commission: float = 5
    slippage_rate: float = 0.001
    stoploss_drawdown: float = 0.10
    stoploss_cooldown_weeks: int = 4


class FilterConfig(BaseModel):
    min_avg_daily_amount: float = 50_000_000
    liquidity_window_days: int = 20


class CorrelationConfig(BaseModel):
    enabled: bool = True
    lookback_days: int = 60
    threshold: float = 0.9


class UniverseItem(BaseModel):
    code: str
    name: str
    theme: str


class PoolsConfig(BaseModel):
    risk_assets: List[str] = Field(default_factory=list)
    defensive_assets: List[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    filters: FilterConfig = Field(default_factory=FilterConfig)
    correlation: CorrelationConfig = Field(default_factory=CorrelationConfig)
    universe: List[UniverseItem] = Field(default_factory=list)
    pools: PoolsConfig = Field(default_factory=PoolsConfig)
    seasonality: Dict[str, List[str]] = Field(default_factory=dict)


def load_config(path: Path) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = AppConfig.model_validate(raw)
    if getattr(cfg.project, "universe_source", "config") == "plan_md":
        from etf_rotation.universe import load_universe_from_plan

        md_path = (path.parent / cfg.project.plan_md_path).resolve()
        universe = load_universe_from_plan(md_path)
        cfg = cfg.model_copy(update={"universe": universe})
    return cfg
