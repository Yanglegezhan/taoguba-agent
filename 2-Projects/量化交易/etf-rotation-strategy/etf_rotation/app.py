from __future__ import annotations

from pathlib import Path

from etf_rotation.config import AppConfig, load_config
from etf_rotation.engine.batch import BatchRunner


def run_all() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg: AppConfig = load_config(root / "config.yaml")

    runner = BatchRunner(cfg=cfg, project_root=root)
    runner.run_all()


def run_s1_optimize() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg: AppConfig = load_config(root / "config.yaml")

    runner = BatchRunner(cfg=cfg, project_root=root)
    runner.run_s1_optimize_only()
