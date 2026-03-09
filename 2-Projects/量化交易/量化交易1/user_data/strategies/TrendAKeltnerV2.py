from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from freqtrade.strategy import IStrategy
from freqtrade.strategy import merge_informative_pair


@dataclass
class Regime:
    long_only: bool
    short_only: bool


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _chop(df: pd.DataFrame, length: int) -> pd.Series:
    tr = _true_range(df)
    tr_sum = tr.rolling(length).sum()
    rng = (df["high"].rolling(length).max() - df["low"].rolling(length).min())
    chop = 100.0 * np.log10(tr_sum / rng.replace(0, np.nan)) / np.log10(float(length))
    return chop


class TrendAKeltnerV2(IStrategy):
    timeframe = "15m"
    can_short = True

    startup_candle_count = 400

    # Freqtrade uses these for standard exits; we'll primarily use custom_exit.
    minimal_roi = {"0": 10}
    stoploss = -0.99

    process_only_new_candles = True
    use_exit_signal = True
    ignore_roi_if_entry_signal = True

    # --- Strategy parameters (match Pine logic) ---
    tf_regime = "1h"

    len_di = 14
    adx_smooth = 14
    adx_th = 25.0
    di_spread_th = 6.0
    len_roc = 20

    use_chop = True
    len_chop = 14
    chop_th = 61.8

    len_kc = 20
    m_kc = 2.0
    confirm2 = True
    entry_buf = 0.15

    len_atr_stop = 14
    k_sl = 2.4
    k_tr = 3.8

    use_be = True
    be_at_atr = 1.0
    be_buf_atr = 0.05

    use_fail_exit = True
    fail_bars = 8
    fail_move_atr = 0.8

    use_premium_filter = True
    prem_th_long = 0.0035
    prem_th_short = -0.0035

    # More aggressive sizing - implement as % of available stake.
    stake_pct = 0.35

    # Leverage for futures.
    leverage_value = 3.0

    @property
    def protections(self) -> List[Dict[str, Any]]:
        # Cooldown after a stop/exit loss is best handled by protections.
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 6,
            }
        ]

    def leverage(self, pair: str, current_time: datetime, current_rate: float, proposed_leverage: float, max_leverage: float, side: str, **kwargs: Any) -> float:
        return float(min(self.leverage_value, max_leverage))

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs: Any,
    ) -> float:
        stake = max_stake * float(self.stake_pct)
        if min_stake is not None:
            stake = max(stake, min_stake)
        return float(min(stake, max_stake))

    def informative_pairs(self) -> List[Tuple[str, str]]:
        pairs = [(pair, self.tf_regime) for pair in self.dp.current_whitelist()]

        # Funding proxy via premium: need spot pair as informative.
        # On Binance futures, pairs look like "BTC/USDT:USDT". Spot is "BTC/USDT".
        if self.use_premium_filter:
            for pair in self.dp.current_whitelist():
                if ":" in pair:
                    spot_pair = pair.split(":")[0]
                    pairs.append((spot_pair, self.timeframe))

        return pairs

    def _get_spot_pair(self, pair: str) -> Optional[str]:
        if ":" not in pair:
            return None
        return pair.split(":")[0]

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        pair = metadata["pair"]

        # --- 15m indicators ---
        try:
            import talib.abstract as ta
        except Exception as exc:
            raise ImportError("Freqtrade strategy requires TA-Lib (talib).") from exc

        dataframe["ema_kc"] = ta.EMA(dataframe, timeperiod=self.len_kc)
        dataframe["atr_kc"] = ta.ATR(dataframe, timeperiod=self.len_kc)
        dataframe["upper"] = dataframe["ema_kc"] + self.m_kc * dataframe["atr_kc"]
        dataframe["lower"] = dataframe["ema_kc"] - self.m_kc * dataframe["atr_kc"]
        dataframe["entry_buffer"] = self.entry_buf * dataframe["atr_kc"]

        dataframe["atr_stop"] = ta.ATR(dataframe, timeperiod=self.len_atr_stop)

        # --- 1h regime (informative) ---
        informative = self.dp.get_pair_dataframe(pair=pair, timeframe=self.tf_regime)
        informative["roc"] = ta.ROC(informative, timeperiod=self.len_roc)
        informative["pdi"] = ta.PLUS_DI(informative, timeperiod=self.len_di)
        informative["mdi"] = ta.MINUS_DI(informative, timeperiod=self.len_di)
        informative["adx"] = ta.ADX(informative, timeperiod=self.adx_smooth)
        informative["spread"] = (informative["pdi"] - informative["mdi"]).abs()

        if self.use_chop:
            informative["chop"] = _chop(informative, self.len_chop)
        else:
            informative["chop"] = 0.0

        informative["trend_ok"] = (
            (informative["adx"] > self.adx_th)
            & (informative["spread"] > self.di_spread_th)
            & ((not self.use_chop) | (informative["chop"] < self.chop_th))
        )

        informative["long_only"] = informative["trend_ok"] & (informative["roc"] > 0) & (informative["pdi"] > informative["mdi"])
        informative["short_only"] = informative["trend_ok"] & (informative["roc"] < 0) & (informative["mdi"] > informative["pdi"])

        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, self.tf_regime, ffill=True)

        dataframe["regime"] = 0
        dataframe.loc[dataframe[f"long_only_{self.tf_regime}"] == True, "regime"] = 1
        dataframe.loc[dataframe[f"short_only_{self.tf_regime}"] == True, "regime"] = -1

        # --- Premium (funding proxy) ---
        dataframe["premium_ok_long"] = True
        dataframe["premium_ok_short"] = True

        if self.use_premium_filter:
            spot_pair = self._get_spot_pair(pair)
            if spot_pair:
                spot_df = self.dp.get_pair_dataframe(pair=spot_pair, timeframe=self.timeframe)
                spot_df = spot_df.rename(columns={"close": "spot_close"})
                dataframe = dataframe.join(spot_df[["spot_close"]], how="left")
                dataframe["spot_close"] = dataframe["spot_close"].ffill()
                dataframe["premium"] = dataframe["close"] / dataframe["spot_close"] - 1.0
                dataframe["premium_ok_long"] = dataframe["premium"] <= self.prem_th_long
                dataframe["premium_ok_short"] = dataframe["premium"] >= self.prem_th_short

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df = dataframe

        upper_hit = df["close"] > (df["upper"] + df["entry_buffer"])
        lower_hit = df["close"] < (df["lower"] - df["entry_buffer"])

        if self.confirm2:
            upper_hit = upper_hit & (df["close"].shift(1) > (df["upper"].shift(1) + df["entry_buffer"].shift(1)))
            lower_hit = lower_hit & (df["close"].shift(1) < (df["lower"].shift(1) - df["entry_buffer"].shift(1)))

        df.loc[
            (df["regime"] == 1) & upper_hit & df["premium_ok_long"],
            ["enter_long", "enter_tag"],
        ] = (1, "kc_break")

        df.loc[
            (df["regime"] == -1) & lower_hit & df["premium_ok_short"],
            ["enter_short", "enter_tag"],
        ] = (1, "kc_break")

        return df

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Exits are handled by custom_exit (dynamic), so keep this empty.
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe

    def custom_exit(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> Optional[str]:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return None

        if current_time not in df.index:
            # Use last available candle.
            row = df.iloc[-1]
            idx = df.index[-1]
        else:
            row = df.loc[current_time]
            idx = current_time

        atr = float(row.get("atr_stop", np.nan))
        if not np.isfinite(atr) or atr <= 0:
            return None

        # Regime flip exit
        regime = int(row.get("regime", 0))
        is_long = trade.is_long
        if is_long and regime != 1:
            return "regime_flip"
        if (not is_long) and regime != -1:
            return "regime_flip"

        # Bars since entry
        try:
            entry_idx = int(df.index.get_indexer([trade.open_date_utc], method="nearest")[0])
            now_idx = int(df.index.get_indexer([idx], method="nearest")[0])
            bars_in_trade = int(max(0, now_idx - entry_idx))
        except Exception:
            bars_in_trade = 0

        # Compute HH/LL since entry using dataframe (close-based logic)
        try:
            start_i = max(0, now_idx - bars_in_trade)
            window = df.iloc[start_i : now_idx + 1]
        except Exception:
            window = df

        hh = float(window["high"].max())
        ll = float(window["low"].min())

        entry_price = float(trade.open_rate)

        if is_long:
            sl = entry_price - self.k_sl * atr
            trail = hh - self.k_tr * atr
            exit_stop = max(sl, trail)

            if self.use_be and (current_rate - entry_price) >= self.be_at_atr * atr:
                exit_stop = max(exit_stop, entry_price + self.be_buf_atr * atr)

            if self.use_fail_exit and bars_in_trade >= self.fail_bars:
                max_move = (hh - entry_price) / atr
                if max_move < self.fail_move_atr:
                    return "fail_exit"

            if current_rate <= exit_stop:
                return "stop_trail"

        else:
            sl = entry_price + self.k_sl * atr
            trail = ll + self.k_tr * atr
            exit_stop = min(sl, trail)

            if self.use_be and (entry_price - current_rate) >= self.be_at_atr * atr:
                exit_stop = min(exit_stop, entry_price - self.be_buf_atr * atr)

            if self.use_fail_exit and bars_in_trade >= self.fail_bars:
                max_move = (entry_price - ll) / atr
                if max_move < self.fail_move_atr:
                    return "fail_exit"

            if current_rate >= exit_stop:
                return "stop_trail"

        return None
