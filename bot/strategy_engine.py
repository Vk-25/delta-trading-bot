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
        entry_ema_length: int = 20,
        exit_ema_length: int = 20,
        rsi_length: int = 14,
        atr_length: int = 14,
        enable_smart_exit: bool = True,
        exit_on_opposite: bool = True,
        exit_confirmations: int = 2,
        enable_breakeven: bool = True,
        breakeven_atr: float = 0.4,
        fee_buffer: float = 2.0,
        enable_protection: bool = True,
        activation_atr: float = 0.8,
        trail_atr: float = 0.6,
        take_profit_atr: float = 0.0,
        enable_emergency: bool = True,
        emergency_atr: float = 2.0,
        enable_live_entries: bool = True,
        enable_trend_continuation: bool = True
    ):
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

        ema_series = self.calculate_ema(df['close'], self.entry_ema_length)
        rsi_series = self.calculate_rsi(df['close'], self.rsi_length)
        atr_series = self.calculate_atr(df, self.atr_length)
        macd_line, macd_sig, _ = self.calculate_macd(df['close'])

        live_close = float(df['close'].iloc[-1])
        live_high = float(df['high'].iloc[-1])
        live_low = float(df['low'].iloc[-1])
        live_ema = float(ema_series.iloc[-1])
        live_rsi = float(rsi_series.iloc[-1])
        live_atr = float(atr_series.iloc[-1])
        live_macd = float(macd_line.iloc[-1])
        live_signal_line = float(macd_sig.iloc[-1])

        prev_high = float(df['high'].iloc[-2])
        prev_low = float(df['low'].iloc[-2])
        prev_close = float(df['close'].iloc[-2])
        prev_ema = float(ema_series.iloc[-2])

        action = "NONE"
        reason = ""

        # Only evaluate entries if currently flat (or looking to reverse)
        if self.position_state == 0:
            # 1. Live EMA Cut Breakout Entry
            ema_cut_prev = (prev_high >= prev_ema) and (prev_low <= prev_ema)
            live_bullish_cut_breakout = ema_cut_prev and (live_high > prev_high) and (live_close >= live_ema)
            live_bearish_cut_breakout = ema_cut_prev and (live_low < prev_low) and (live_close <= live_ema)

            if live_bullish_cut_breakout:
                action = "BUY"
                reason = "LiveEMACutBreakout(High)"
            elif live_bearish_cut_breakout:
                action = "SELL"
                reason = "LiveEMACutBreakout(Low)"

            # 2. Live Trend Continuation / Momentum Re-entry (No waiting for EMA Cut)
            elif self.enable_trend_continuation:
                uptrend = (live_close > live_ema) and (live_rsi >= 50) and (live_macd >= live_signal_line)
                downtrend = (live_close < live_ema) and (live_rsi <= 50) and (live_macd <= live_signal_line)

                # Bullish continuation: Higher high breakout or EMA bounce
                if uptrend and (live_high > prev_high):
                    action = "BUY"
                    reason = "LiveTrendContinuation(UptrendBreakout)"
                elif uptrend and (prev_low <= live_ema and live_close > live_ema):
                    action = "BUY"
                    reason = "LiveTrendContinuation(EMABounce)"

                # Bearish continuation: Lower low breakdown or EMA rejection
                elif downtrend and (live_low < prev_low):
                    action = "SELL"
                    reason = "LiveTrendContinuation(DowntrendBreakdown)"
                elif downtrend and (prev_high >= live_ema and live_close < live_ema):
                    action = "SELL"
                    reason = "LiveTrendContinuation(EMARejection)"

            if action == "BUY":
                self.position_state = 1
                self.entry_price = live_close
                self.highest_price = live_close
                self.long_trail_stop = None
                self.breakeven_locked = False
            elif action == "SELL":
                self.position_state = -1
                self.entry_price = live_close
                self.lowest_price = live_close
                self.short_trail_stop = None
                self.breakeven_locked = False

        return SignalResult(
            action=action,
            reason=reason,
            price=live_close,
            position_state=self.position_state,
            entry_price=self.entry_price,
            highest_price=self.highest_price,
            lowest_price=self.lowest_price,
            metrics={"rsi": live_rsi, "atr": live_atr, "ema": live_ema, "live_price": live_close}
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

    def compute_indicator_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Appends all strategy indicators to a copy of the OHLCV DataFrame.
        DataFrame must contain columns: 'open', 'high', 'low', 'close', 'volume'
        """
        data = df.copy()
        for col in ['open', 'high', 'low', 'close']:
            data[col] = data[col].astype(float)
            
        data['entry_ema'] = self.calculate_ema(data['close'], self.entry_ema_length)
        data['exit_ema'] = self.calculate_ema(data['close'], self.exit_ema_length)
        data['rsi'] = self.calculate_rsi(data['close'], self.rsi_length)
        data['atr'] = self.calculate_atr(data, self.atr_length)
        
        macd_line, macd_signal, macd_hist = self.calculate_macd(data['close'], 12, 26, 9)
        data['macd_line'] = macd_line
        data['macd_signal'] = macd_signal
        data['macd_hist'] = macd_hist
        
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
            prev_high = data['high'].iloc[i - 1]
            prev_low = data['low'].iloc[i - 1]
            prev_close = data['close'].iloc[i - 1]
            prev_entry_ema = data['entry_ema'].iloc[i - 1]
            
            # Current bar values (bar index 0 in Pine Script)
            curr_high = data['high'].iloc[i]
            curr_low = data['low'].iloc[i]
            curr_close = data['close'].iloc[i]
            curr_entry_ema = data['entry_ema'].iloc[i]
            curr_exit_ema = data['exit_ema'].iloc[i]
            curr_rsi = data['rsi'].iloc[i]
            curr_atr = data['atr'].iloc[i]
            curr_macd_line = data['macd_line'].iloc[i]
            curr_macd_signal = data['macd_signal'].iloc[i]
            
            # 1. EMA Cut Candle condition on previous candle
            ema_cutting_candle = (prev_high >= prev_entry_ema) and (prev_low <= prev_entry_ema)
            
            # 2. Raw Buy/Sell triggers
            raw_buy = False
            raw_sell = False
            
            if ema_cutting_candle:
                break_high = curr_high > prev_high
                break_low = curr_low < prev_low
                
                if break_high and break_low:
                    if curr_close > prev_close:
                        raw_buy = True
                    elif curr_close < prev_close:
                        raw_sell = True
                elif break_high:
                    raw_buy = True
                elif break_low:
                    raw_sell = True
                    
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
                    
                # Exit Confirmations (Weakness score out of 4)
                ema_weak = curr_close < curr_exit_ema
                rsi_weak = curr_rsi < 50
                macd_weak = curr_macd_line < curr_macd_signal
                structure_weak = curr_close < prev_low
                
                long_score = int(ema_weak) + int(rsi_weak) + int(macd_weak) + int(structure_weak)
                
                smart_exit = self.enable_smart_exit and (long_score >= self.exit_confirmations)
                if smart_exit:
                    exit_reasons.append(f"SmartExit(score={long_score}/{self.exit_confirmations})")
                    
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
                    
                # Exit Confirmations (Weakness score out of 4)
                ema_weak = curr_close > curr_exit_ema
                rsi_weak = curr_rsi > 50
                macd_weak = curr_macd_line > curr_macd_signal
                structure_weak = curr_close > prev_high
                
                short_score = int(ema_weak) + int(rsi_weak) + int(macd_weak) + int(structure_weak)
                
                smart_exit = self.enable_smart_exit and (short_score >= self.exit_confirmations)
                if smart_exit:
                    exit_reasons.append(f"SmartExit(score={short_score}/{self.exit_confirmations})")
                    
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
        """Processes candle DataFrame and returns the latest signal."""
        results = self.process_candles(df)
        if results:
            return results[-1]
        return SignalResult(
            action="NONE",
            reason="Insufficient data",
            price=0.0,
            position_state=0,
            entry_price=None,
            highest_price=None,
            lowest_price=None,
            metrics={}
        )
