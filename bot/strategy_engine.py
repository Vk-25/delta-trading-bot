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
    Algorithmic replication of EMA_Cut_Breakout_Universal_Smart_Exit_FIXED.pine
    """
    def __init__(
        self,
        entry_ema_length: int = 21,
        exit_ema_length: int = 21,
        rsi_length: int = 14,
        atr_length: int = 14,
        enable_smart_exit: bool = True,
        exit_on_opposite: bool = True,
        exit_confirmations: int = 2,
        enable_breakeven: bool = True,
        breakeven_atr: float = 0.24,
        fee_buffer: float = 0.5,
        enable_protection: bool = True,
        activation_atr: float = 0.50,
        trail_atr: float = 0.35,
        take_profit_atr: float = 0.0,
        enable_emergency: bool = True,
        emergency_atr: float = 0.45,
        enable_live_entries: bool = True,
        enable_trend_continuation: bool = True,
        # ── High-Frequency Scalper Parameters (60+ Entries/Day) ──
        strategy_mode: str = "scalper",
        fast_ema_length: int = 9,
        enable_range_breakout: bool = True,
        enable_rsi_reversal: bool = True,
        range_lookback: int = 5,
        # ── Smart Filters ──
        enable_volume_filter: bool = True,
        volume_multiplier: float = 1.1,
        volume_lookback: int = 20,
        enable_adx_filter: bool = False,
        adx_length: int = 14,
        min_adx: float = 15.0,
        enable_regime_filter: bool = False,
        enable_mtf_alignment: bool = False,
    ):
        self.strategy_mode = strategy_mode.lower().strip()
        self.fast_ema_length = fast_ema_length
        self.entry_ema_length = entry_ema_length
        self.exit_ema_length = exit_ema_length
        self.rsi_length = rsi_length
        self.atr_length = atr_length
        self.enable_smart_exit = enable_smart_exit
        self.exit_on_opposite = exit_on_opposite
        self.exit_confirmations = exit_confirmations
        self.enable_breakeven = enable_breakeven
        self.breakeven_atr = breakeven_atr
        self.fee_buffer = fee_buffer
        self.enable_protection = enable_protection
        self.activation_atr = activation_atr
        self.trail_atr = trail_atr
        self.take_profit_atr = take_profit_atr
        self.enable_emergency = enable_emergency
        self.emergency_atr = emergency_atr
        self.enable_live_entries = enable_live_entries
        self.enable_trend_continuation = enable_trend_continuation
        self.enable_range_breakout = enable_range_breakout
        self.enable_rsi_reversal = enable_rsi_reversal
        self.range_lookback = range_lookback

        # ── Smart Filters ──
        self.enable_volume_filter = enable_volume_filter
        self.volume_multiplier = volume_multiplier
        self.volume_lookback = volume_lookback
        self.enable_adx_filter = enable_adx_filter
        self.adx_length = adx_length
        self.min_adx = min_adx
        self.enable_regime_filter = enable_regime_filter
        self.enable_mtf_alignment = enable_mtf_alignment
        
        # State variables
        self.position_state: int = 0  # 0 = Flat, 1 = Long, -1 = Short
        self.entry_price: Optional[float] = None
        self.highest_price: Optional[float] = None
        self.lowest_price: Optional[float] = None
        self.long_trail_stop: Optional[float] = None
        self.short_trail_stop: Optional[float] = None
        self.breakeven_locked: bool = False

    def reset_state(self):
        """Resets the internal position state."""
        self.position_state = 0
        self.entry_price = None
        self.highest_price = None
        self.lowest_price = None
        self.long_trail_stop = None
        self.short_trail_stop = None
        self.breakeven_locked = False

    def sync_position(self, current_size: float, entry_price: Optional[float] = None):
        """Syncs internal state with actual exchange position."""
        if current_size > 0:
            if self.position_state != 1:
                self.position_state = 1
                self.entry_price = entry_price or self.entry_price
                self.highest_price = self.entry_price
                self.long_trail_stop = None
                self.breakeven_locked = False
        elif current_size < 0:
            if self.position_state != -1:
                self.position_state = -1
                self.entry_price = entry_price or self.entry_price
                self.lowest_price = self.entry_price
                self.short_trail_stop = None
                self.breakeven_locked = False
        else:
            if self.position_state != 0:
                self.reset_state()

    def check_realtime_exit(self, current_price: float, current_atr: float) -> Optional[SignalResult]:
        """
        Checks real-time live price against Auto-Breakeven, Trailing Stop, Take Profit, and Emergency Stop
        intra-candle (without waiting for the candle to close) to lock in profit and guarantee zero loss.
        """
        if self.position_state == 0 or self.entry_price is None or current_atr <= 0:
            return None

        exit_reasons = []
        action = "NONE"

        if self.position_state == 1:  # LONG
            if self.highest_price is None:
                self.highest_price = current_price
            else:
                self.highest_price = max(self.highest_price, current_price)

            profit_atr = (current_price - self.entry_price) / current_atr

            # 1. Take Profit
            if self.take_profit_atr > 0 and profit_atr >= self.take_profit_atr:
                exit_reasons.append(f"RealtimeTakeProfit(+{profit_atr:.2f} ATR)")

            # 2. Zero-Loss Auto-Breakeven Lock (+Fees)
            if self.enable_breakeven and profit_atr >= self.breakeven_atr:
                be_level = self.entry_price + self.fee_buffer
                if self.long_trail_stop is None or self.long_trail_stop < be_level:
                    self.long_trail_stop = be_level
                    self.breakeven_locked = True

            # 3. Ratcheting Trailing Stop (Profit Protection)
            protection_active = self.enable_protection and (profit_atr >= self.activation_atr)
            long_candidate_stop = max(self.entry_price + (self.fee_buffer if self.breakeven_locked else 0),
                                      self.highest_price - (current_atr * self.trail_atr))
            if protection_active:
                if self.long_trail_stop is None:
                    self.long_trail_stop = long_candidate_stop
                else:
                    self.long_trail_stop = max(self.long_trail_stop, long_candidate_stop)

            if (self.long_trail_stop is not None) and (current_price <= self.long_trail_stop):
                exit_label = "AutoBreakeven" if self.breakeven_locked and not protection_active else "RealtimeTrailingStop"
                exit_reasons.append(f"{exit_label}(stop={self.long_trail_stop:.2f})")

            # 4. Emergency Stop
            if self.enable_emergency and (profit_atr <= -self.emergency_atr):
                exit_reasons.append(f"RealtimeEmergencyStop({profit_atr:.2f} ATR)")

            if exit_reasons:
                action = "EXIT_LONG"

        elif self.position_state == -1:  # SHORT
            if self.lowest_price is None:
                self.lowest_price = current_price
            else:
                self.lowest_price = min(self.lowest_price, current_price)

            profit_atr = (self.entry_price - current_price) / current_atr

            # 1. Take Profit
            if self.take_profit_atr > 0 and profit_atr >= self.take_profit_atr:
                exit_reasons.append(f"RealtimeTakeProfit(+{profit_atr:.2f} ATR)")

            # 2. Zero-Loss Auto-Breakeven Lock (+Fees)
            if self.enable_breakeven and profit_atr >= self.breakeven_atr:
                be_level = self.entry_price - self.fee_buffer
                if self.short_trail_stop is None or self.short_trail_stop > be_level:
                    self.short_trail_stop = be_level
                    self.breakeven_locked = True

            # 3. Ratcheting Trailing Stop (Profit Protection)
            protection_active = self.enable_protection and (profit_atr >= self.activation_atr)
            short_candidate_stop = min(self.entry_price - (self.fee_buffer if self.breakeven_locked else 0),
                                       self.lowest_price + (current_atr * self.trail_atr))
            if protection_active:
                if self.short_trail_stop is None:
                    self.short_trail_stop = short_candidate_stop
                else:
                    self.short_trail_stop = min(self.short_trail_stop, short_candidate_stop)

            if (self.short_trail_stop is not None) and (current_price >= self.short_trail_stop):
                exit_label = "AutoBreakeven" if self.breakeven_locked and not protection_active else "RealtimeTrailingStop"
                exit_reasons.append(f"{exit_label}(stop={self.short_trail_stop:.2f})")

            # 4. Emergency Stop
            if self.enable_emergency and (profit_atr <= -self.emergency_atr):
                exit_reasons.append(f"RealtimeEmergencyStop({profit_atr:.2f} ATR)")

            if exit_reasons:
                action = "EXIT_SHORT"

        if action != "NONE":
            reason = " | ".join(exit_reasons)
            self.reset_state()
            return SignalResult(
                action=action,
                reason=reason,
                price=current_price,
                position_state=0,
                entry_price=None,
                highest_price=None,
                lowest_price=None,
                metrics={"current_price": current_price, "profit_atr": profit_atr, "breakeven": self.breakeven_locked}
            )

        return None

    def get_live_signal(self, df: pd.DataFrame) -> SignalResult:
        """
        Evaluates real-time live price against EMA Cut Breakouts and Trend Continuation
        without waiting for the candle to close.
        """
        if len(df) < 30:
            return SignalResult("NONE", "Insufficient Data", float(df['close'].iloc[-1]), self.position_state, self.entry_price, self.highest_price, self.lowest_price, {})

        fast_ema_series = self.calculate_ema(df['close'], self.fast_ema_length)
        ema_series = self.calculate_ema(df['close'], self.entry_ema_length)
        rsi_series = self.calculate_rsi(df['close'], self.rsi_length)
        atr_series = self.calculate_atr(df, self.atr_length)
        macd_line, macd_sig, _ = self.calculate_macd(df['close'])

        live_close = float(df['close'].iloc[-1])
        live_high = float(df['high'].iloc[-1])
        live_low = float(df['low'].iloc[-1])
        live_fema = float(fast_ema_series.iloc[-1])
        live_ema = float(ema_series.iloc[-1])
        live_rsi = float(rsi_series.iloc[-1])
        live_atr = float(atr_series.iloc[-1])
        live_macd = float(macd_line.iloc[-1])
        live_signal_line = float(macd_sig.iloc[-1])

        prev_open = float(df['open'].iloc[-2])
        prev_high = float(df['high'].iloc[-2])
        prev_low = float(df['low'].iloc[-2])
        prev_close = float(df['close'].iloc[-2])
        prev_fema = float(fast_ema_series.iloc[-2])
        prev_ema = float(ema_series.iloc[-2])

        action = "NONE"
        reason = ""
        stop_loss = None

        # Only evaluate entries if currently flat (or looking to reverse)
        if self.position_state == 0:
            # 1. EMA Cut / Cross Entry (Fast 9 EMA cross or 21 EMA body cut)
            prev_body_top = max(prev_open, prev_close)
            prev_body_bottom = min(prev_open, prev_close)
            ema_cut_prev = (prev_body_top >= prev_ema) and (prev_body_bottom <= prev_ema)
            ema_cross_up = (prev_fema <= prev_ema) and (live_fema > live_ema)
            ema_cross_down = (prev_fema >= prev_ema) and (live_fema < live_ema)
            
            # Clean Bullish Breakout: Breaks High, closes above EMA
            live_bullish_cut_breakout = (ema_cut_prev or ema_cross_up) and (live_high > prev_high) and (live_close > live_ema) and (live_low >= prev_low)
            
            # Clean Bearish Breakdown: Breaks Low, closes below EMA
            live_bearish_cut_breakout = (ema_cut_prev or ema_cross_down) and (live_low < prev_low) and (live_close < live_ema) and (live_high <= prev_high)

            if live_bullish_cut_breakout:
                action = "BUY"
                reason = "LiveEMABreakout(High)"
                stop_loss = prev_low
            elif live_bearish_cut_breakout:
                action = "SELL"
                reason = "LiveEMABreakout(Low)"
                stop_loss = prev_high

            # 2. Trend Continuation / Momentum Re-entry (EMA Pullback & Bounce)
            elif self.enable_trend_continuation:
                uptrend = (live_close > live_ema) and (live_rsi >= 50)
                downtrend = (live_close < live_ema) and (live_rsi <= 50)

                # Bullish continuation: Pullback to 9/21 EMA and bounce upward
                if uptrend and (prev_low <= live_fema or prev_low <= live_ema) and (live_close > live_fema) and (live_high > prev_high):
                    action = "BUY"
                    reason = "LiveTrendContinuation(Bounce)"
                    stop_loss = min(prev_low, live_low)
                elif uptrend and (live_high > prev_high and live_close > live_fema):
                    action = "BUY"
                    reason = "LiveTrendContinuation(Breakout)"
                    stop_loss = prev_low

                # Bearish continuation: Pullback to 9/21 EMA and reject downward
                elif downtrend and (prev_high >= live_fema or prev_high >= live_ema) and (live_close < live_fema) and (live_low < prev_low):
                    action = "SELL"
                    reason = "LiveTrendContinuation(Rejection)"
                    stop_loss = max(prev_high, live_high)
                elif downtrend and (live_low < prev_low and live_close < live_fema):
                    action = "SELL"
                    reason = "LiveTrendContinuation(Breakdown)"
                    stop_loss = prev_high

            # 3. Micro Range Breakout (5-Bar High/Low Impulse)
            if action == "NONE" and self.enable_range_breakout and len(df) >= 7:
                recent_high = float(df['high'].iloc[-6:-1].max())
                recent_low = float(df['low'].iloc[-6:-1].min())

                if live_close > recent_high and live_rsi >= 52 and live_close > live_ema:
                    action = "BUY"
                    reason = "LiveRangeBreakout(5BarHigh)"
                    stop_loss = min(prev_low, live_low)
                elif live_close < recent_low and live_rsi <= 48 and live_close < live_ema:
                    action = "SELL"
                    reason = "LiveRangeBreakdown(5BarLow)"
                    stop_loss = max(prev_high, live_high)

            # 4. RSI Extreme Mean-Reversion Snap
            if action == "NONE" and self.enable_rsi_reversal:
                if live_rsi < 32 and live_close > float(df['open'].iloc[-1]) and live_high > prev_high:
                    action = "BUY"
                    reason = "LiveRSIReversal(OversoldSnap)"
                    stop_loss = live_low
                elif live_rsi > 68 and live_close < float(df['open'].iloc[-1]) and live_low < prev_low:
                    action = "SELL"
                    reason = "LiveRSIReversal(OverboughtSnap)"
                    stop_loss = live_high

            target_state = 1 if action == "BUY" else (-1 if action == "SELL" else self.position_state)

            # ── NEW: Smart Filters for live entries ──
            if action in ("BUY", "SELL"):
                # Volume Filter
                if self.enable_volume_filter:
                    if not self.has_volume_confirmation(df, self.volume_multiplier, self.volume_lookback):
                        logger.info(f"[LIVE FILTER] Volume too low → SKIPPING {action}")
                        action = "NONE"
                        reason = ""
                        stop_loss = None

                # ADX Filter
                if action in ("BUY", "SELL") and self.enable_adx_filter:
                    adx_series = self.calculate_adx(df, self.adx_length)
                    curr_adx = float(adx_series.iloc[-1])
                    if curr_adx < self.min_adx:
                        logger.info(f"[LIVE FILTER] ADX {curr_adx:.1f} < {self.min_adx} → SKIPPING {action}")
                        action = "NONE"
                        reason = ""
                        stop_loss = None

                # Regime Filter
                if action in ("BUY", "SELL") and self.enable_regime_filter and len(df) >= 55:
                    regime = self.detect_regime(df, self.adx_length)
                    if regime in ('volatile', 'ranging'):
                        logger.info(f"[LIVE FILTER] Regime: {regime.upper()} → SKIPPING {action}")
                        action = "NONE"
                        reason = ""
                        stop_loss = None

        return SignalResult(
            action=action,
            reason=reason,
            price=live_close,
            position_state=self.position_state,
            entry_price=self.entry_price,
            highest_price=self.highest_price,
            lowest_price=self.lowest_price,
            metrics={
                "rsi": live_rsi,
                "atr": live_atr,
                "ema": live_ema,
                "live_price": live_close,
                "stop_loss": stop_loss,
                "prev_high": prev_high,
                "prev_low": prev_low
            }
        )

    # =========================================================================
    # INDICATOR CALCULATIONS (Matching Pine Script exactly)
    # =========================================================================

    @staticmethod
    def calculate_ema(series: pd.Series, length: int) -> pd.Series:
        """Calculates Exponential Moving Average (ta.ema)."""
        return series.ewm(span=length, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, length: int = 14) -> pd.Series:
        """Calculates Relative Strength Index using Wilder's RMA (ta.rsi)."""
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        # Wilder RMA (alpha = 1 / length)
        alpha = 1.0 / length
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    @staticmethod
    def calculate_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
        """Calculates Average True Range using Wilder's RMA (ta.atr)."""
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        alpha = 1.0 / length
        atr = tr.ewm(alpha=alpha, adjust=False).mean()
        return atr

    @staticmethod
    def calculate_macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculates MACD line, signal line, and histogram (ta.macd)."""
        fast_ema = series.ewm(span=fast, adjust=False).mean()
        slow_ema = series.ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        macd_hist = macd_line - macd_signal
        return macd_line, macd_signal, macd_hist

    # =========================================================================
    # NEW: ADX, Volume, Regime Detection, Multi-Timeframe Alignment
    # =========================================================================

    @staticmethod
    def calculate_adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
        """
        Average Directional Index — measures trend STRENGTH (not direction).
        ADX > 25 = strong trend, ADX < 20 = choppy/ranging market.
        """
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        close = df['close'].astype(float)

        plus_dm = high.diff()
        minus_dm = -low.diff()

        # Only keep the larger directional movement
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        atr = StrategyEngine.calculate_atr(df, length)
        alpha = 1.0 / length

        plus_di = 100 * (plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr)

        di_sum = plus_di + minus_di
        di_sum = di_sum.replace(0, np.nan)
        dx = 100 * (plus_di - minus_di).abs() / di_sum
        adx = dx.ewm(alpha=alpha, adjust=False).mean()
        return adx.fillna(0)

    @staticmethod
    def has_volume_confirmation(df: pd.DataFrame, multiplier: float = 1.5, lookback: int = 20) -> bool:
        """
        Checks if the current candle's volume exceeds multiplier × average volume.
        Breakouts on high volume are real; breakouts on low volume are fakeouts.
        """
        if 'volume' not in df.columns or len(df) < lookback + 1:
            return True  # Default to True if volume data unavailable
        vol = df['volume'].astype(float)
        avg_vol = vol.iloc[-(lookback + 1):-1].mean()
        current_vol = float(vol.iloc[-1])
        if avg_vol <= 0:
            return True
        return bool(current_vol > (float(avg_vol) * multiplier))

    @staticmethod
    def detect_regime(df: pd.DataFrame, adx_length: int = 14, atr_short: int = 14, atr_long: int = 50) -> str:
        """
        Detects the current market regime:
          - 'trending':  ADX > 25 and volatility is normal → use breakout strategy
          - 'ranging':   ADX < 20 and volatility is low → use mean-reversion or SKIP
          - 'volatile':  ATR is spiking (> 1.8× long-term) → reduce size or SKIP
        """
        if len(df) < max(atr_long + 5, 30):
            return 'trending'  # Default to trending with insufficient data

        adx_series = StrategyEngine.calculate_adx(df, adx_length)
        atr_s = StrategyEngine.calculate_atr(df, atr_short)
        atr_l = StrategyEngine.calculate_atr(df, atr_long)

        adx_val = float(adx_series.iloc[-1])
        atr_ratio = float(atr_s.iloc[-1]) / float(atr_l.iloc[-1]) if float(atr_l.iloc[-1]) > 0 else 1.0

        if atr_ratio > 1.8:
            return 'volatile'
        elif adx_val >= 25:
            return 'trending'
        elif adx_val < 20:
            return 'ranging'
        else:
            return 'trending'  # ADX 20-25: borderline, lean toward trend

    @staticmethod
    def is_higher_tf_aligned(df_higher: pd.DataFrame, direction: str, ema_length: int = 21) -> bool:
        """
        Checks if the higher timeframe (e.g. 1H) EMA slope agrees with trade direction.
        Only take BUY when 1H trend is UP; only take SELL when 1H trend is DOWN.
        """
        if df_higher is None or len(df_higher) < ema_length + 5:
            return True  # Default to True if higher TF data is unavailable

        ema_ht = StrategyEngine.calculate_ema(df_higher['close'].astype(float), ema_length)
        # Use 3-bar slope for smooth direction detection
        slope = float(ema_ht.iloc[-1]) - float(ema_ht.iloc[-3])

        if direction == "BUY" and slope > 0:
            return True
        elif direction == "SELL" and slope < 0:
            return True
        return False

    def compute_indicator_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Appends all strategy indicators to a copy of the OHLCV DataFrame.
        DataFrame must contain columns: 'open', 'high', 'low', 'close', 'volume'
        """
        data = df.copy()
        for col in ['open', 'high', 'low', 'close']:
            data[col] = data[col].astype(float)
            
        data['fast_ema'] = self.calculate_ema(data['close'], self.fast_ema_length)
        data['entry_ema'] = self.calculate_ema(data['close'], self.entry_ema_length)
        data['exit_ema'] = self.calculate_ema(data['close'], self.exit_ema_length)
        data['rsi'] = self.calculate_rsi(data['close'], self.rsi_length)
        data['atr'] = self.calculate_atr(data, self.atr_length)
        
        macd_line, macd_signal, macd_hist = self.calculate_macd(data['close'], 12, 26, 9)
        data['macd_line'] = macd_line
        data['macd_signal'] = macd_signal
        data['macd_hist'] = macd_hist

        # ── Micro Range high/low for breakout scalps ──
        data['range_high'] = data['high'].shift(1).rolling(self.range_lookback, min_periods=1).max()
        data['range_low'] = data['low'].shift(1).rolling(self.range_lookback, min_periods=1).min()

        # ── ADX for trend strength filtering ──
        data['adx'] = self.calculate_adx(data, self.adx_length)

        # ── Volume average for breakout confirmation ──
        if 'volume' in data.columns:
            data['volume'] = data['volume'].astype(float)
            data['vol_avg'] = data['volume'].rolling(self.volume_lookback, min_periods=1).mean()
        
        return data

    # =========================================================================
    # CORE STRATEGY STATE MACHINE
    # =========================================================================

    def process_candles(self, df: pd.DataFrame) -> List[SignalResult]:
        """
        Runs the full strategy logic over historical candles bar-by-bar
        and tracks state changes identically to Pine Script confirmed bars.
        """
        data = self.compute_indicator_dataframe(df)
        results: List[SignalResult] = []
        
        self.reset_state()
        n = len(data)
        
        for i in range(1, n):
            # Previous bar values (bar index 1 in Pine Script)
            prev_open = data['open'].iloc[i - 1]
            prev_high = data['high'].iloc[i - 1]
            prev_low = data['low'].iloc[i - 1]
            prev_close = data['close'].iloc[i - 1]
            prev_entry_ema = data['entry_ema'].iloc[i - 1]
            
            # Current bar values (bar index 0 in Pine Script)
            curr_open = data['open'].iloc[i]
            curr_high = data['high'].iloc[i]
            curr_low = data['low'].iloc[i]
            curr_close = data['close'].iloc[i]
            curr_entry_ema = data['entry_ema'].iloc[i]
            curr_exit_ema = data['exit_ema'].iloc[i]
            curr_rsi = data['rsi'].iloc[i]
            curr_atr = data['atr'].iloc[i]
            curr_macd_line = data['macd_line'].iloc[i]
            curr_macd_signal = data['macd_signal'].iloc[i]
            
            curr_fema = data['fast_ema'].iloc[i]
            prev_fema = data['fast_ema'].iloc[i - 1]

            # 1. EMA Cut / Cross Entry (Fast 9 EMA cross or 21 EMA body cut)
            prev_body_top = max(prev_open, prev_close)
            prev_body_bottom = min(prev_open, prev_close)
            ema_cutting_candle = (prev_body_top >= prev_entry_ema) and (prev_body_bottom <= prev_entry_ema)
            ema_cross_up = (prev_fema <= prev_entry_ema) and (curr_fema > curr_entry_ema)
            ema_cross_down = (prev_fema >= prev_entry_ema) and (curr_fema < curr_entry_ema)
            
            # 2. Raw Buy/Sell triggers (Strict Directional Breakout)
            raw_buy = False
            raw_sell = False
            
            if ema_cutting_candle or ema_cross_up or ema_cross_down:
                clean_break_high = (curr_high > prev_high) and (curr_close > curr_entry_ema) and (curr_low >= prev_low)
                clean_break_low = (curr_low < prev_low) and (curr_close < curr_entry_ema) and (curr_high <= prev_high)
                
                if clean_break_high:
                    raw_buy = True
                elif clean_break_low:
                    raw_sell = True

            # 2. Trend Continuation Pullback & Bounce
            if not raw_buy and not raw_sell and self.enable_trend_continuation:
                uptrend = (curr_close > curr_entry_ema) and (curr_rsi >= 50)
                downtrend = (curr_close < curr_entry_ema) and (curr_rsi <= 50)

                if uptrend and (prev_low <= curr_fema or prev_low <= curr_entry_ema) and (curr_close > curr_fema) and (curr_high > prev_high):
                    raw_buy = True
                elif uptrend and (curr_high > prev_high and curr_close > curr_fema):
                    raw_buy = True
                elif downtrend and (prev_high >= curr_fema or prev_high >= curr_entry_ema) and (curr_close < curr_fema) and (curr_low < prev_low):
                    raw_sell = True
                elif downtrend and (curr_low < prev_low and curr_close < curr_fema):
                    raw_sell = True

            # 3. Micro Range Breakout (5-Bar High/Low Impulse)
            if not raw_buy and not raw_sell and self.enable_range_breakout and 'range_high' in data.columns:
                r_high = float(data['range_high'].iloc[i])
                r_low = float(data['range_low'].iloc[i])
                if curr_close > r_high and curr_rsi >= 52 and curr_close > curr_entry_ema:
                    raw_buy = True
                elif curr_close < r_low and curr_rsi <= 48 and curr_close < curr_entry_ema:
                    raw_sell = True

            # 4. RSI Extreme Reversal Snap
            if not raw_buy and not raw_sell and self.enable_rsi_reversal:
                if curr_rsi < 32 and curr_close > curr_open and curr_high > prev_high:
                    raw_buy = True
                elif curr_rsi > 68 and curr_close < curr_open and curr_low < prev_low:
                    raw_sell = True

            # ── NEW: Smart Filters — reject false breakouts before entry ──
            if raw_buy or raw_sell:
                # Volume Filter: breakout candle must have above-average volume
                if self.enable_volume_filter and 'vol_avg' in data.columns:
                    curr_vol = float(data['volume'].iloc[i])
                    avg_vol = float(data['vol_avg'].iloc[i])
                    if avg_vol > 0 and curr_vol < (avg_vol * self.volume_multiplier):
                        logger.info(f"[FILTER] Volume {curr_vol:.0f} < {self.volume_multiplier}×avg {avg_vol:.0f} → SKIPPING breakout")
                        raw_buy = False
                        raw_sell = False

                # ADX Filter: only trade breakouts in trending markets (ADX > min_adx)
                if (raw_buy or raw_sell) and self.enable_adx_filter and 'adx' in data.columns:
                    curr_adx = float(data['adx'].iloc[i])
                    if curr_adx < self.min_adx:
                        logger.info(f"[FILTER] ADX {curr_adx:.1f} < {self.min_adx} (choppy market) → SKIPPING breakout")
                        raw_buy = False
                        raw_sell = False

                # Regime Filter: skip entries in volatile or ranging markets
                if (raw_buy or raw_sell) and self.enable_regime_filter:
                    # Use data up to current bar for regime detection
                    regime_slice = data.iloc[:i+1]
                    if len(regime_slice) >= 55:
                        regime = self.detect_regime(regime_slice, self.adx_length)
                        if regime == 'volatile':
                            logger.info(f"[FILTER] Market regime: VOLATILE → SKIPPING breakout")
                            raw_buy = False
                            raw_sell = False
                        elif regime == 'ranging':
                            logger.info(f"[FILTER] Market regime: RANGING → SKIPPING breakout")
                            raw_buy = False
                            raw_sell = False
                    
            exit_long = False
            exit_short = False
            new_buy = False
            new_sell = False
            exit_reasons = []
            
            # 3. Position Management
            if self.position_state == 1:
                # Track highest price
                if self.highest_price is None:
                    self.highest_price = curr_high
                else:
                    self.highest_price = max(self.highest_price, curr_high)
                    
                # Exit Confirmations (Master Unified Exit: Mandatory 21 EMA line close violation + multi-confirmations)
                ema_weak = curr_close < curr_exit_ema
                rsi_weak = curr_rsi < 50
                macd_weak = curr_macd_line < curr_macd_signal
                structure_weak = curr_close < prev_low
                
                long_score = int(ema_weak) + int(rsi_weak) + int(macd_weak) + int(structure_weak)
                
                # Smart exit strictly requires candle closing below 21 EMA + score >= exit_confirmations
                smart_exit = self.enable_smart_exit and ema_weak and (long_score >= self.exit_confirmations)
                if smart_exit:
                    exit_reasons.append(f"SmartExit(ema_break+score={long_score}/{self.exit_confirmations})")
                    
                opposite_exit = self.exit_on_opposite and raw_sell
                if opposite_exit:
                    exit_reasons.append("OppositeSignal(raw_sell)")
                    
                # Profit Protection Trailing Stop
                long_profit_atr = (curr_close - self.entry_price) / curr_atr if curr_atr > 0 else 0
                protection_active = self.enable_protection and (long_profit_atr >= self.activation_atr)
                
                long_candidate_stop = max(self.entry_price, self.highest_price - (curr_atr * self.trail_atr))
                if protection_active:
                    if self.long_trail_stop is None:
                        self.long_trail_stop = long_candidate_stop
                    else:
                        self.long_trail_stop = max(self.long_trail_stop, long_candidate_stop)

                protection_exit = protection_active and (self.long_trail_stop is not None) and (curr_close <= self.long_trail_stop)
                if protection_exit:
                    exit_reasons.append(f"ProfitProtection(stop={self.long_trail_stop:.2f})")
                    
                # Emergency Loss Exit
                emergency_exit = self.enable_emergency and (long_profit_atr <= -self.emergency_atr)
                if emergency_exit:
                    exit_reasons.append(f"EmergencyLoss({long_profit_atr:.2f} ATR)")
                    
                if smart_exit or opposite_exit or protection_exit or emergency_exit:
                    exit_long = True

            elif self.position_state == -1:
                # Track lowest price
                if self.lowest_price is None:
                    self.lowest_price = curr_low
                else:
                    self.lowest_price = min(self.lowest_price, curr_low)
                    
                # Exit Confirmations (Master Unified Exit: Mandatory 21 EMA line close violation + multi-confirmations)
                ema_weak = curr_close > curr_exit_ema
                rsi_weak = curr_rsi > 50
                macd_weak = curr_macd_line > curr_macd_signal
                structure_weak = curr_close > prev_high
                
                short_score = int(ema_weak) + int(rsi_weak) + int(macd_weak) + int(structure_weak)
                
                # Smart exit strictly requires candle closing above 21 EMA + score >= exit_confirmations
                smart_exit = self.enable_smart_exit and ema_weak and (short_score >= self.exit_confirmations)
                if smart_exit:
                    exit_reasons.append(f"SmartExit(ema_break+score={short_score}/{self.exit_confirmations})")
                    
                opposite_exit = self.exit_on_opposite and raw_buy
                if opposite_exit:
                    exit_reasons.append("OppositeSignal(raw_buy)")
                    
                # Profit Protection Trailing Stop
                short_profit_atr = (self.entry_price - curr_close) / curr_atr if curr_atr > 0 else 0
                protection_active = self.enable_protection and (short_profit_atr >= self.activation_atr)
                
                short_candidate_stop = min(self.entry_price, self.lowest_price + (curr_atr * self.trail_atr))
                if protection_active:
                    if self.short_trail_stop is None:
                        self.short_trail_stop = short_candidate_stop
                    else:
                        self.short_trail_stop = min(self.short_trail_stop, short_candidate_stop)

                protection_exit = protection_active and (self.short_trail_stop is not None) and (curr_close >= self.short_trail_stop)
                if protection_exit:
                    exit_reasons.append(f"ProfitProtection(stop={self.short_trail_stop:.2f})")
                    
                # Emergency Loss Exit
                emergency_exit = self.enable_emergency and (short_profit_atr <= -self.emergency_atr)
                if emergency_exit:
                    exit_reasons.append(f"EmergencyLoss({short_profit_atr:.2f} ATR)")
                    
                if smart_exit or opposite_exit or protection_exit or emergency_exit:
                    exit_short = True

            # 4. Handle Position Exits
            exited_this_bar = False
            action = "NONE"
            reason = ""
            
            if exit_long:
                action = "EXIT_LONG"
                reason = " | ".join(exit_reasons)
                self.position_state = 0
                self.entry_price = None
                self.highest_price = None
                self.lowest_price = None
                self.long_trail_stop = None
                self.short_trail_stop = None
                exited_this_bar = True
                
            elif exit_short:
                action = "EXIT_SHORT"
                reason = " | ".join(exit_reasons)
                self.position_state = 0
                self.entry_price = None
                self.highest_price = None
                self.lowest_price = None
                self.long_trail_stop = None
                self.short_trail_stop = None
                exited_this_bar = True

            # 5. Handle New Entries (Only if flat and not exited on same bar)
            if self.position_state == 0 and not exited_this_bar:
                if raw_buy:
                    new_buy = True
                    action = "BUY"
                    reason = "EMA Cut Breakout High"
                    self.position_state = 1
                    self.entry_price = curr_close
                    self.highest_price = curr_high
                    self.lowest_price = None
                    self.long_trail_stop = None
                    self.short_trail_stop = None
                    
                elif raw_sell:
                    new_sell = True
                    action = "SELL"
                    reason = "EMA Cut Breakout Low"
                    self.position_state = -1
                    self.entry_price = curr_close
                    self.lowest_price = curr_low
                    self.highest_price = None
                    self.long_trail_stop = None
                    self.short_trail_stop = None

            metrics = {
                "entry_ema": curr_entry_ema,
                "exit_ema": curr_exit_ema,
                "rsi": curr_rsi,
                "atr": curr_atr,
                "macd_line": curr_macd_line,
                "macd_signal": curr_macd_signal,
                "raw_buy": raw_buy,
                "raw_sell": raw_sell,
                "ema_cutting_candle": ema_cutting_candle
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
            return SignalResult(
                action="NONE",
                reason="Insufficient data",
                price=0.0,
                position_state=self.position_state,
                entry_price=self.entry_price,
                highest_price=self.highest_price,
                lowest_price=self.lowest_price,
                metrics={}
            )

        i = len(data) - 1
        prev_open = float(data['open'].iloc[i - 1])
        prev_high = float(data['high'].iloc[i - 1])
        prev_low = float(data['low'].iloc[i - 1])
        prev_close = float(data['close'].iloc[i - 1])
        prev_entry_ema = float(data['entry_ema'].iloc[i - 1])

        curr_open = float(data['open'].iloc[i])
        curr_high = float(data['high'].iloc[i])
        curr_low = float(data['low'].iloc[i])
        curr_close = float(data['close'].iloc[i])
        curr_entry_ema = float(data['entry_ema'].iloc[i])
        curr_exit_ema = float(data['exit_ema'].iloc[i])
        curr_rsi = float(data['rsi'].iloc[i])
        curr_atr = float(data['atr'].iloc[i])
        curr_macd_line = float(data['macd_line'].iloc[i])
        curr_macd_signal = float(data['macd_signal'].iloc[i])

        curr_fema = float(data['fast_ema'].iloc[i])
        prev_fema = float(data['fast_ema'].iloc[i - 1])

        # 1. EMA Cut / Cross Entry (Fast 9 EMA cross or 21 EMA body cut)
        prev_body_top = max(prev_open, prev_close)
        prev_body_bottom = min(prev_open, prev_close)
        ema_cutting_candle = (prev_body_top >= prev_entry_ema) and (prev_body_bottom <= prev_entry_ema)
        ema_cross_up = (prev_fema <= prev_entry_ema) and (curr_fema > curr_entry_ema)
        ema_cross_down = (prev_fema >= prev_entry_ema) and (curr_fema < curr_entry_ema)

        raw_buy = False
        raw_sell = False

        if ema_cutting_candle or ema_cross_up or ema_cross_down:
            clean_break_high = (curr_high > prev_high) and (curr_close > curr_entry_ema) and (curr_low >= prev_low)
            clean_break_low = (curr_low < prev_low) and (curr_close < curr_entry_ema) and (curr_high <= prev_high)

            if clean_break_high:
                raw_buy = True
            elif clean_break_low:
                raw_sell = True

        # 2. Trend Continuation Pullback & Bounce
        if not raw_buy and not raw_sell and self.enable_trend_continuation:
            uptrend = (curr_close > curr_entry_ema) and (curr_rsi >= 50)
            downtrend = (curr_close < curr_entry_ema) and (curr_rsi <= 50)

            if uptrend and (prev_low <= curr_fema or prev_low <= curr_entry_ema) and (curr_close > curr_fema) and (curr_high > prev_high):
                raw_buy = True
            elif uptrend and (curr_high > prev_high and curr_close > curr_fema):
                raw_buy = True
            elif downtrend and (prev_high >= curr_fema or prev_high >= curr_entry_ema) and (curr_close < curr_fema) and (curr_low < prev_low):
                raw_sell = True
            elif downtrend and (curr_low < prev_low and curr_close < curr_fema):
                raw_sell = True

        # 3. Micro Range Breakout (5-Bar High/Low Impulse)
        if not raw_buy and not raw_sell and self.enable_range_breakout and 'range_high' in data.columns:
            r_high = float(data['range_high'].iloc[i])
            r_low = float(data['range_low'].iloc[i])
            if curr_close > r_high and curr_rsi >= 52 and curr_close > curr_entry_ema:
                raw_buy = True
            elif curr_close < r_low and curr_rsi <= 48 and curr_close < curr_entry_ema:
                raw_sell = True

        # 4. RSI Extreme Reversal Snap
        if not raw_buy and not raw_sell and self.enable_rsi_reversal:
            if curr_rsi < 32 and curr_close > curr_open and curr_high > prev_high:
                raw_buy = True
            elif curr_rsi > 68 and curr_close < curr_open and curr_low < prev_low:
                raw_sell = True

        # ── NEW: Smart Filters for get_latest_signal ──
        if raw_buy or raw_sell:
            # Volume Filter
            if self.enable_volume_filter and 'vol_avg' in data.columns:
                curr_vol = float(data['volume'].iloc[i])
                avg_vol = float(data['vol_avg'].iloc[i])
                if avg_vol > 0 and curr_vol < (avg_vol * self.volume_multiplier):
                    logger.info(f"[FILTER] Volume {curr_vol:.0f} < {self.volume_multiplier}×avg {avg_vol:.0f} → SKIPPING")
                    raw_buy = False
                    raw_sell = False

            # ADX Filter
            if (raw_buy or raw_sell) and self.enable_adx_filter and 'adx' in data.columns:
                curr_adx = float(data['adx'].iloc[i])
                if curr_adx < self.min_adx:
                    logger.info(f"[FILTER] ADX {curr_adx:.1f} < {self.min_adx} → SKIPPING")
                    raw_buy = False
                    raw_sell = False

            # Regime Filter
            if (raw_buy or raw_sell) and self.enable_regime_filter and len(data) >= 55:
                regime = self.detect_regime(data, self.adx_length)
                if regime in ('volatile', 'ranging'):
                    logger.info(f"[FILTER] Regime: {regime.upper()} → SKIPPING")
                    raw_buy = False
                    raw_sell = False

        action = "NONE"
        reason = ""
        stop_loss = None

        # If currently in a Long position
        if self.position_state == 1:
            if self.highest_price is None:
                self.highest_price = curr_high
            else:
                self.highest_price = max(self.highest_price, curr_high)

            # Master Unified Exit: Mandatory 21 EMA line close violation + multi-confirmations
            ema_weak = curr_close < curr_exit_ema
            rsi_weak = curr_rsi < 50
            macd_weak = curr_macd_line < curr_macd_signal
            structure_weak = curr_close < prev_low
            long_score = int(ema_weak) + int(rsi_weak) + int(macd_weak) + int(structure_weak)

            smart_exit = self.enable_smart_exit and ema_weak and (long_score >= self.exit_confirmations)
            opposite_exit = self.exit_on_opposite and raw_sell

            if self.entry_price:
                profit_atr = (curr_close - self.entry_price) / curr_atr if curr_atr > 0 else 0
                emergency_exit = self.enable_emergency and (profit_atr <= -self.emergency_atr)
            else:
                emergency_exit = False

            if smart_exit:
                action = "EXIT_LONG"
                reason = f"SmartExit(ema_break+score={long_score}/{self.exit_confirmations})"
            elif opposite_exit:
                action = "EXIT_LONG"
                reason = "OppositeSignal(SELL)"
            elif emergency_exit:
                action = "EXIT_LONG"
                reason = "EmergencyLoss"

        # If currently in a Short position
        elif self.position_state == -1:
            if self.lowest_price is None:
                self.lowest_price = curr_low
            else:
                self.lowest_price = min(self.lowest_price, curr_low)

            # Master Unified Exit: Mandatory 21 EMA line close violation + multi-confirmations
            ema_weak = curr_close > curr_exit_ema
            rsi_weak = curr_rsi > 50
            macd_weak = curr_macd_line > curr_macd_signal
            structure_weak = curr_close > prev_high
            short_score = int(ema_weak) + int(rsi_weak) + int(macd_weak) + int(structure_weak)

            smart_exit = self.enable_smart_exit and ema_weak and (short_score >= self.exit_confirmations)
            opposite_exit = self.exit_on_opposite and raw_buy

            if self.entry_price:
                profit_atr = (self.entry_price - curr_close) / curr_atr if curr_atr > 0 else 0
                emergency_exit = self.enable_emergency and (profit_atr <= -self.emergency_atr)
            else:
                emergency_exit = False

            if smart_exit:
                action = "EXIT_SHORT"
                reason = f"SmartExit(ema_break+score={short_score}/{self.exit_confirmations})"
            elif opposite_exit:
                action = "EXIT_SHORT"
                reason = "OppositeSignal(BUY)"
            elif emergency_exit:
                action = "EXIT_SHORT"
                reason = "EmergencyLoss"

        # If Flat, evaluate New Entries
        elif self.position_state == 0:
            if raw_buy:
                action = "BUY"
                reason = "EMA Cut Breakout High"
                stop_loss = prev_low
            elif raw_sell:
                action = "SELL"
                reason = "EMA Cut Breakout Low"
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
                "entry_ema": curr_entry_ema,
                "exit_ema": curr_exit_ema,
                "rsi": curr_rsi,
                "atr": curr_atr,
                "macd_line": curr_macd_line,
                "macd_signal": curr_macd_signal,
                "raw_buy": raw_buy,
                "raw_sell": raw_sell,
                "ema_cutting_candle": ema_cutting_candle,
                "stop_loss": stop_loss,
                "prev_high": prev_high,
                "prev_low": prev_low
            }
        )
