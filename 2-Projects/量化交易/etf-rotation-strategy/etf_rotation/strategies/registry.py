from __future__ import annotations

from typing import Dict

from etf_rotation.config import AppConfig
from etf_rotation.strategies.s1_momentum import MomentumRotation
from etf_rotation.strategies.s2_mean_reversion import MeanReversionRSI
from etf_rotation.strategies.s4_vol_target import VolTargetRotation
from etf_rotation.strategies.s6_cross_market import CrossMarketRelativeStrength
from etf_rotation.strategies.s10_multi_factor import MultiFactorRotationV2
from etf_rotation.strategies.s8_seasonality import SeasonalityRotation
from etf_rotation.strategies.s9_risk_parity import RiskParityRotation


def build_all_strategies(cfg: AppConfig) -> Dict[str, object]:
    return {
        "s1_momentum": MomentumRotation(cfg),
        "s2_mean_reversion_rsi": MeanReversionRSI(cfg),
        "s4_vol_target": VolTargetRotation(cfg),
        "s6_cross_market": CrossMarketRelativeStrength(cfg),
        "s10_multi_factor_v2": MultiFactorRotationV2(cfg),
        "s8_seasonality": SeasonalityRotation(cfg),
        "s9_risk_parity": RiskParityRotation(cfg),
    }
