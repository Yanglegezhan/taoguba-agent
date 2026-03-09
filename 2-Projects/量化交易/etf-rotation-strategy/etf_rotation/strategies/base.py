from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class RotationStrategy:
    name: str

    def select(self, date: pd.Timestamp, prices: pd.DataFrame) -> List[str]:
        raise NotImplementedError

    def weights(self, date: pd.Timestamp, selected: List[str], prices: pd.DataFrame) -> Dict[str, float]:
        if not selected:
            return {}
        w = 1.0 / len(selected)
        return {c: w for c in selected}
