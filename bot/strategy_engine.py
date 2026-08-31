import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from bot.config import config
from bot.utils import logger

@dataclass
class SignalResult:
    action: str  # "BUY", "SELL", "EXIT_LONG", "EXIT_SHORT", "NONE"
    reason: str
    price: float
    position_state: int  # 0: Flat, 1: Long, -1: Short
    entry_price: Optional[float]
    highest_price: Optional[float]
    lowest_price: Optional[float]
    metrics: Dict[str, Any]

class StrategyEngine:
    """
    21 EMA Body-Cut Breakout Strategy with 9 EMA Regular Analysis & 1:3 Trailing Take Profit.
    
    Core Rules:
    1. 21 EMA acts as the primary trigger: Identifies candles where the body is cut/intersected by the 21 EMA.
    2. 9 EMA is calculated for regular trend/momentum analysis and visual HUD display.
    3. Next candle [0] breakout:
       - High break (high > high[1]) -> Immediate BUY (Long).
       - Low break (low < low[1]) -> Immediate SELL (Short).
    4. Stop Loss: Set at the Low[1] (for BUY) or High[1] (for SELL) of the 21 EMA cutting candle.
    5. 1:3 Trailing Profit: For every 3.0 points the market moves in profit, the stop-loss trails forward by 1.0 point (0.333 ratio).
    6. Opposite Signal: If an opposite cut breakout occurs while in a position, close to Flat.
    """
    def __init__(
        self,
        entry_ema_length: int = 21,
        fast_ema_length: int = 9,
        trail_move_unit: float = 3.0,
        trail_step_unit: float = 1.0,
        trail_profit_ratio: Optional[float] = None,
        exit_on_opposite: bool = True,
        fee_buffer: float = 0.50,
    ):
        self.entry_ema_length = entry_ema_length
        self.fast_ema_length = fast_ema_length
        self.trail_move_unit = trail_move_unit
        self.trail_step_unit = trail_step_unit
        self.trail_profit_ratio = trail_profit_ratio if (trail_profit_ratio is not None and trail_profit_ratio > 0) else (trail_step_unit / trail_move_unit)
        self.exit_on_opposite = exit_on_opposite
        self.fee_buffer = fee_buffer

        # State tracking
        self.position_state: int = 0  # 0 = Flat, 1 = Long, -1 = Short
        self.entry_price: Optional[float] = None
        self.highest_price: Optional[float] = None
        self.lowest_price: Optional[float] = None
        self.initial_stop_loss: Optional[float] = None
        self.active_trailing_stop: Optional[float] = None

    def reset_state(self):
        """Resets the internal position state to Flat."""
        self.position_state = 0
        self.entry_price = None
        self.highest_price = None
        self.lowest_price = None
        self.initial_stop_loss = None
        self.active_trailing_stop = None

    def sync_position(self, current_size: float, entry_price: Optional[float] = None, stop_loss: Optional[float] = None):
        """Syncs internal state with actual exchange position."""
        if current_size > 0:
            if self.position_state != 1:
                self.position_state = 1
                self.entry_price = entry_price or self.entry_price
                self.highest_price = self.entry_price
                self.lowest_price = None
                self.initial_stop_loss = stop_loss or (self.entry_price - 10.0 if self.entry_price else None)
                self.active_trailing_stop = self.initial_stop_loss
        elif current_size < 0:
            if self.position_state != -1:
                self.position_state = -1
                self.entry_price = entry_price or self.entry_price
                self.lowest_price = self.entry_price
                self.highest_price = None
                self.initial_stop_loss = stop_loss or (self.entry_price + 10.0 if self.entry_price else None)
                self.active_trailing_stop = self.initial_stop_loss
        else:
            if self.position_state != 0:
                self.reset_state()

    def update_1to3_trailing_stop(self, current_price: float, high: Optional[float] = None, low: Optional[float] = None) -> Optional[float]:
        """
        Calculates and ratchets the 1:3 trailing stop:
        For every 3 points of favorable price movement, the stop trails forward by 1 point.
        """
        if self.position_state == 0 or self.entry_price is None or self.initial_stop_loss is None:
            return None

        if self.position_state == 1:  # LONG
            peak = high if high is not None else current_price
            self.highest_price = peak if self.highest_price is None else max(self.highest_price, peak)
            
            max_profit = self.highest_price - self.entry_price
            if max_profit > 0:
                trail_step = max_profit * self.trail_profit_ratio
                candidate_stop = self.initial_stop_loss + trail_step
                self.active_trailing_stop = max(self.active_trailing_stop or self.initial_stop_loss, candidate_stop)
            else:
                if self.active_trailing_stop is None:
                    self.active_trailing_stop = self.initial_stop_loss
            return self.active_trailing_stop

        elif self.position_state == -1:  # SHORT
            trough = low if low is not None else current_price
            self.lowest_price = trough if self.lowest_price is None else min(self.lowest_price, trough)
            
            max_profit = self.entry_price - self.lowest_price
            if max_profit > 0:
                trail_step = max_profit * self.trail_profit_ratio
                candidate_stop = self.initial_stop_loss - trail_step
                self.active_trailing_stop = min(self.active_trailing_stop or self.initial_stop_loss, candidate_stop)
            else:
                if self.active_trailing_stop is None:
                    self.active_trailing_stop = self.initial_stop_loss
            return self.active_trailing_stop

        return None

    def update_1to4_trailing_stop(self, current_price: float, high: Optional[float] = None, low: Optional[float] = None) -> Optional[float]:
        """Alias for backwards compatibility."""
        return self.update_1to3_trailing_stop(current_price, high=high, low=low)

    def check_realtime_exit(self, current_price: float) -> Optional[SignalResult]:
        """
        Checks real-time live price tick against the 1:3 Trailing Stop Loss
        intra-candle (without waiting for the candle to close).
        """
        if self.position_state == 0 or self.entry_price is None:
            return None

        # Update 1:3 trailing stop with live price
        trail_stop = self.update_1to3_trailing_stop(current_price)

        if self.position_state == 1:  # LONG
            if trail_stop is not None and current_price <= trail_stop:
                profit_pts = current_price - self.entry_price
                reason = f"TrailingStop1:3(stop={trail_stop:.2f}|pnl={profit_pts:+.2f}pts)"
                self.reset_state()
                return SignalResult(
                    action="EXIT_LONG",
                    reason=reason,
                    price=current_price,
                    position_state=0,
                    entry_price=None,
                    highest_price=None,
                    lowest_price=None,
                    metrics={"current_price": current_price, "exit_stop": trail_stop, "profit_pts": profit_pts}
                )

        elif self.position_state == -1:  # SHORT
            if trail_stop is not None and current_price >= trail_stop:
                profit_pts = self.entry_price - current_price
                reason = f"TrailingStop1:3(stop={trail_stop:.2f}|pnl={profit_pts:+.2f}pts)"
                self.reset_state()
                return SignalResult(
                    action="EXIT_SHORT",
                    reason=reason,
                    price=current_price,
                    position_state=0,
                    entry_price=None,
                    highest_price=None,
                    lowest_price=None,
                    metrics={"current_price": current_price, "exit_stop": trail_stop, "profit_pts": profit_pts}
                )

        return None

    def get_live_signal(self, df: pd.DataFrame) -> SignalResult:
        """
        Evaluates real-time live price against 21 EMA Cut Breakouts and 1:4 Trailing Exits.
        """
        if len(df) < max(self.entry_ema_length, self.fast_ema_length) + 2:
            return SignalResult("NONE", "Insufficient Data", float(df['close'].iloc[-1]), self.position_state, self.entry_price, self.highest_price, self.lowest_price, {})

        ema21_series = self.calculate_ema(df['close'], self.entry_ema_length)
        ema9_series = self.calculate_ema(df['close'], self.fast_ema_length)

        live_close = float(df['close'].iloc[-1])
        live_high = float(df['high'].iloc[-1])
        live_low = float(df['low'].iloc[-1])
        live_ema21 = float(ema21_series.iloc[-1])
        live_ema9 = float(ema9_series.iloc[-1])

        prev_open = float(df['open'].iloc[-2])
        prev_high = float(df['high'].iloc[-2])
        prev_low = float(df['low'].iloc[-2])
        prev_close = float(df['close'].iloc[-2])
        prev_ema21 = float(ema21_series.iloc[-2])
        prev_ema9 = float(ema9_series.iloc[-2])

        # 1. Detect 21 EMA Body-Cut on Previous Candle [1]
        prev_body_top = max(prev_open, prev_close)
        prev_body_bottom = min(prev_open, prev_close)
        ema21_cut_prev = (prev_body_bottom <= prev_ema21) and (prev_body_top >= prev_ema21)

        # 2. Check Breakout on Current Immediate Candle [0]
        breakout_high = ema21_cut_prev and (live_high > prev_high)
        breakout_low = ema21_cut_prev and (live_low < prev_low)

        action = "NONE"
        reason = ""
        stop_loss = None

        # If currently in position, check trailing exit first, then check opposite signal close
        if self.position_state != 0:
            realtime_exit = self.check_realtime_exit(live_close)
            if realtime_exit is not None:
                return realtime_exit

            # Opposite signal -> Close to Flat
            if self.position_state == 1 and breakout_low and self.exit_on_opposite:
                action = "EXIT_LONG"
                reason = f"OppositeSignal(21_EMA_Cut_Low_Break={prev_low:.2f})"
                self.reset_state()
            elif self.position_state == -1 and breakout_high and self.exit_on_opposite:
                action = "EXIT_SHORT"
                reason = f"OppositeSignal(21_EMA_Cut_High_Break={prev_high:.2f})"
                self.reset_state()

        # If Flat, evaluate New Entries
        elif self.position_state == 0:
            if breakout_high:
                action = "BUY"
                reason = f"21_EMA_Cut_High_Break(prev_high={prev_high:.2f}|cut_ema={prev_ema21:.2f})"
                stop_loss = prev_low
                self.position_state = 1
                self.entry_price = live_close
                self.highest_price = live_high
                self.lowest_price = None
                self.initial_stop_loss = prev_low
                self.active_trailing_stop = prev_low

            elif breakout_low:
                action = "SELL"
                reason = f"21_EMA_Cut_Low_Break(prev_low={prev_low:.2f}|cut_ema={prev_ema21:.2f})"
                stop_loss = prev_high
                self.position_state = -1
                self.entry_price = live_close
                self.lowest_price = live_low
                self.highest_price = None
                self.initial_stop_loss = prev_high
                self.active_trailing_stop = prev_high

        # 9 EMA analysis trend
        ema9_trend = "BULLISH" if live_close > live_ema9 else "BEARISH"
        dynamic_lots = self.calculate_dynamic_lots(df, action) if action in ("BUY", "SELL") else 1

        return SignalResult(
            action=action,
            reason=reason,
            price=live_close,
            position_state=self.position_state,
            entry_price=self.entry_price,
            highest_price=self.highest_price,
            lowest_price=self.lowest_price,
            metrics={
                "ema21": live_ema21,
                "ema9": live_ema9,
                "ema9_trend": ema9_trend,
                "ema21_cut_prev": ema21_cut_prev,
                "prev_high": prev_high,
                "prev_low": prev_low,
                "initial_stop": self.initial_stop_loss,
                "trailing_stop": self.active_trailing_stop,
                "stop_loss": stop_loss or self.active_trailing_stop,
                "dynamic_lots": dynamic_lots,
            }
        )

    def calculate_dynamic_lots(self, df: pd.DataFrame, action: str, min_lots: int = 1, max_lots: int = 3) -> int:
        """
        Calculates dynamic lot size (1 to 3 lots) for high-potential setups:
        - 3 Lots: 9 EMA & 21 EMA trend alignment + strong cut candle direction + momentum expansion
        - 2 Lots: Trend aligned or strong breakout momentum
        - 1 Lot: Baseline entry
        """
        if len(df) < max(self.entry_ema_length, self.fast_ema_length) + 2 or action not in ("BUY", "SELL"):
            return min_lots

        ema21 = float(self.calculate_ema(df['close'], self.entry_ema_length).iloc[-1])
        ema9 = float(self.calculate_ema(df['close'], self.fast_ema_length).iloc[-1])
        
        prev_open = float(df['open'].iloc[-2])
        prev_close = float(df['close'].iloc[-2])
        live_close = float(df['close'].iloc[-1])
        
        score = 1  # Base 1 lot
        
        # Factor 1: Trend Alignment (EMA 9 vs EMA 21)
        trend_aligned = (action == "BUY" and ema9 > ema21) or (action == "SELL" and ema9 < ema21)
        if trend_aligned:
            score += 1
            
        # Factor 2: Candle Momentum (Cut candle body matches breakout direction)
        candle_momentum = (action == "BUY" and prev_close >= prev_open) or (action == "SELL" and prev_close <= prev_open)
        # Factor 3: Live price momentum (Live close strongly advancing beyond EMA 9)
        price_momentum = (action == "BUY" and live_close > ema9) or (action == "SELL" and live_close < ema9)
        
        if candle_momentum and price_momentum:
            score += 1

        return max(min_lots, min(max_lots, score))

    # =========================================================================
    # INDICATOR CALCULATIONS
    # =========================================================================

    @staticmethod
    def calculate_ema(series: pd.Series, length: int) -> pd.Series:
        """Calculates Exponential Moving Average (ta.ema)."""
        return series.ewm(span=length, adjust=False).mean()

    def compute_indicator_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Appends 21 EMA and 9 EMA indicators to a copy of the OHLCV DataFrame."""
        data = df.copy()
        for col in ['open', 'high', 'low', 'close']:
            data[col] = data[col].astype(float)
            
        data['ema21'] = self.calculate_ema(data['close'], self.entry_ema_length)
        data['ema9'] = self.calculate_ema(data['close'], self.fast_ema_length)
        return data

    # =========================================================================
    # HISTORICAL BAR PROCESSOR (Matches Pine Script Confirmed Bars)
    # =========================================================================

    def process_candles(self, df: pd.DataFrame) -> List[SignalResult]:
        """
        Runs the full 21 EMA Cut Breakout strategy over historical candles bar-by-bar
        and tracks state changes with 1:4 trailing take-profit.
        """
        data = self.compute_indicator_dataframe(df)
        results: List[SignalResult] = []
        
        self.reset_state()
        n = len(data)
        
        for i in range(1, n):
            # Previous bar [1]
            prev_open = data['open'].iloc[i - 1]
            prev_high = data['high'].iloc[i - 1]
            prev_low = data['low'].iloc[i - 1]
            prev_close = data['close'].iloc[i - 1]
            prev_ema21 = data['ema21'].iloc[i - 1]
            prev_ema9 = data['ema9'].iloc[i - 1]

            # Current bar [0]
            curr_open = data['open'].iloc[i]
            curr_high = data['high'].iloc[i]
            curr_low = data['low'].iloc[i]
            curr_close = data['close'].iloc[i]
            curr_ema21 = data['ema21'].iloc[i]
            curr_ema9 = data['ema9'].iloc[i]

            # 1. 21 EMA Body-Cut on Previous Bar [1]
            prev_body_top = max(prev_open, prev_close)
            prev_body_bottom = min(prev_open, prev_close)
            ema21_cut_prev = (prev_body_bottom <= prev_ema21) and (prev_body_top >= prev_ema21)

            # 2. Breakouts on Current Bar [0]
            raw_buy = ema21_cut_prev and (curr_high > prev_high)
            raw_sell = ema21_cut_prev and (curr_low < prev_low)

            action = "NONE"
            reason = ""
            exited_this_bar = False

            # 3. Position Management & 1:3 Trailing Take Profit
            if self.position_state == 1:  # LONG
                trail_stop = self.update_1to3_trailing_stop(curr_close, high=curr_high, low=curr_low)
                
                # Check trailing exit
                if trail_stop is not None and curr_low <= trail_stop:
                    action = "EXIT_LONG"
                    reason = f"TrailingStop1:3(stop={trail_stop:.2f})"
                    self.reset_state()
                    exited_this_bar = True
                
                # Check opposite signal exit
                elif raw_sell and self.exit_on_opposite:
                    action = "EXIT_LONG"
                    reason = f"OppositeSignal(21_EMA_Cut_Low_Break={prev_low:.2f})"
                    self.reset_state()
                    exited_this_bar = True

            elif self.position_state == -1:  # SHORT
                trail_stop = self.update_1to3_trailing_stop(curr_close, high=curr_high, low=curr_low)
                
                # Check trailing exit
                if trail_stop is not None and curr_high >= trail_stop:
                    action = "EXIT_SHORT"
                    reason = f"TrailingStop1:3(stop={trail_stop:.2f})"
                    self.reset_state()
                    exited_this_bar = True
                
                # Check opposite signal exit
                elif raw_buy and self.exit_on_opposite:
                    action = "EXIT_SHORT"
                    reason = f"OppositeSignal(21_EMA_Cut_High_Break={prev_high:.2f})"
                    self.reset_state()
                    exited_this_bar = True

            # 4. Handle New Entries (Only if Flat and not exited on the same bar)
            if self.position_state == 0 and not exited_this_bar:
                if raw_buy:
                    action = "BUY"
                    reason = f"21_EMA_Cut_High_Break(prev_high={prev_high:.2f})"
                    self.position_state = 1
                    self.entry_price = curr_close
                    self.highest_price = curr_high
                    self.lowest_price = None
                    self.initial_stop_loss = prev_low
                    self.active_trailing_stop = prev_low

                elif raw_sell:
                    action = "SELL"
                    reason = f"21_EMA_Cut_Low_Break(prev_low={prev_low:.2f})"
                    self.position_state = -1
                    self.entry_price = curr_close
                    self.lowest_price = curr_low
                    self.highest_price = None
                    self.initial_stop_loss = prev_high
                    self.active_trailing_stop = prev_high

            metrics = {
                "ema21": curr_ema21,
                "ema9": curr_ema9,
                "ema21_cut_prev": ema21_cut_prev,
                "raw_buy": raw_buy,
                "raw_sell": raw_sell,
                "initial_stop": self.initial_stop_loss,
                "trailing_stop": self.active_trailing_stop,
            }

            results.append(SignalResult(
                action=action,
                reason=reason,
                price=curr_close,
                position_state=self.position_state,
                entry_price=self.entry_price,
                highest_price=self.highest_price,
                lowest_price=self.lowest_price,
                metrics=metrics
            ))
            
        return results

    def get_latest_signal(self, df: pd.DataFrame) -> SignalResult:
        """Processes candle DataFrame for the current live state without wiping state."""
        data = self.compute_indicator_dataframe(df)
        if len(data) < 2:
            return SignalResult("NONE", "Insufficient data", 0.0, self.position_state, self.entry_price, self.highest_price, self.lowest_price, {})

        i = len(data) - 1
        prev_open = float(data['open'].iloc[i - 1])
        prev_high = float(data['high'].iloc[i - 1])
        prev_low = float(data['low'].iloc[i - 1])
        prev_close = float(data['close'].iloc[i - 1])
        prev_ema21 = float(data['ema21'].iloc[i - 1])
        prev_ema9 = float(data['ema9'].iloc[i - 1])

        curr_open = float(data['open'].iloc[i])
        curr_high = float(data['high'].iloc[i])
        curr_low = float(data['low'].iloc[i])
        curr_close = float(data['close'].iloc[i])
        curr_ema21 = float(data['ema21'].iloc[i])
        curr_ema9 = float(data['ema9'].iloc[i])

        # 1. 21 EMA Body Cut on Previous Candle [1]
        prev_body_top = max(prev_open, prev_close)
        prev_body_bottom = min(prev_open, prev_close)
        ema21_cut_prev = (prev_body_bottom <= prev_ema21) and (prev_body_top >= prev_ema21)

        # 2. Breakouts on Current Candle [0]
        raw_buy = ema21_cut_prev and (curr_high > prev_high)
        raw_sell = ema21_cut_prev and (curr_low < prev_low)

        action = "NONE"
        reason = ""
        stop_loss = None

        if self.position_state == 1:  # LONG
            trail_stop = self.update_1to4_trailing_stop(curr_close, high=curr_high, low=curr_low)
            if trail_stop is not None and curr_close <= trail_stop:
                action = "EXIT_LONG"
                reason = f"TrailingStop1:4(stop={trail_stop:.2f})"
            elif raw_sell and self.exit_on_opposite:
                action = "EXIT_LONG"
                reason = f"OppositeSignal(21_EMA_Cut_Low_Break={prev_low:.2f})"

        elif self.position_state == -1:  # SHORT
            trail_stop = self.update_1to4_trailing_stop(curr_close, high=curr_high, low=curr_low)
            if trail_stop is not None and curr_close >= trail_stop:
                action = "EXIT_SHORT"
                reason = f"TrailingStop1:4(stop={trail_stop:.2f})"
            elif raw_buy and self.exit_on_opposite:
                action = "EXIT_SHORT"
                reason = f"OppositeSignal(21_EMA_Cut_High_Break={prev_high:.2f})"

        elif self.position_state == 0:
            if raw_buy:
                action = "BUY"
                reason = f"21_EMA_Cut_High_Break(prev_high={prev_high:.2f})"
                stop_loss = prev_low
            elif raw_sell:
                action = "SELL"
                reason = f"21_EMA_Cut_Low_Break(prev_low={prev_low:.2f})"
                stop_loss = prev_high

        return SignalResult(
            action=action,
            reason=reason,
            price=curr_close,
            position_state=self.position_state,
            entry_price=self.entry_price,
            highest_price=self.highest_price,
            lowest_price=self.lowest_price,
            metrics={
                "ema21": curr_ema21,
                "ema9": curr_ema9,
                "ema21_cut_prev": ema21_cut_prev,
                "raw_buy": raw_buy,
                "raw_sell": raw_sell,
                "stop_loss": stop_loss or self.active_trailing_stop,
                "initial_stop": self.initial_stop_loss,
                "trailing_stop": self.active_trailing_stop,
                "prev_high": prev_high,
                "prev_low": prev_low,
            }
        )
