import unittest
import pandas as pd
import numpy as np
from bot.strategy_engine import StrategyEngine

class TestStrategyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = StrategyEngine(
            entry_ema_length=5,
            exit_ema_length=5,
            rsi_length=5,
            atr_length=5,
            enable_smart_exit=True,
            exit_confirmations=2,
            enable_protection=True,
            activation_atr=1.0,
            trail_atr=1.25,
            enable_emergency=True,
            emergency_atr=2.5
        )

    def test_indicator_calculations(self):
        # Create synthetic OHLCV data
        np.random.seed(42)
        n = 50
        closes = 100 + np.cumsum(np.random.randn(n))
        highs = closes + np.random.uniform(0.5, 2.0, n)
        lows = closes - np.random.uniform(0.5, 2.0, n)
        opens = (closes + lows) / 2
        volumes = np.random.uniform(100, 1000, n)

        df = pd.DataFrame({
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes
        })

        data = self.engine.compute_indicator_dataframe(df)

        self.assertIn("entry_ema", data.columns)
        self.assertIn("exit_ema", data.columns)
        self.assertIn("rsi", data.columns)
        self.assertIn("atr", data.columns)
        self.assertIn("macd_line", data.columns)
        self.assertIn("macd_signal", data.columns)

        # RSI values should be between 0 and 100
        self.assertTrue((data["rsi"] >= 0).all() and (data["rsi"] <= 100).all())
        # ATR should be positive
        self.assertTrue((data["atr"] > 0).all())

    def test_ema_cut_and_breakout_buy_signal(self):
        # Construct specific bars where bar 1 cuts EMA and bar 2 breaks high
        bars = [
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            # Bar 5 (index 5): cuts EMA 100 (high 101, low 99)
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 100},
            # Bar 6 (index 6): breaks high of Bar 5 (high 103 > 101)
            {"open": 100.5, "high": 103.0, "low": 100.0, "close": 102.5, "volume": 100},
        ]
        df = pd.DataFrame(bars)
        results = self.engine.process_candles(df)
        
        # The last result should trigger a BUY action
        last_sig = results[-1]
        self.assertEqual(last_sig.action, "BUY")
        self.assertEqual(last_sig.position_state, 1)

    def test_smart_exit_long(self):
        # Create a series where BUY happens, price peaks, and then drops causing weak indicators
        bars = [
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 100},
            # Trigger BUY
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 100},
            {"open": 100.5, "high": 104.0, "low": 100.0, "close": 103.5, "volume": 100},
            # Sharp drop triggering exit indicators
            {"open": 103.5, "high": 103.5, "low": 95.0, "close": 95.5, "volume": 100},
        ]
        df = pd.DataFrame(bars)
        results = self.engine.process_candles(df)
        
        # The last result should be an exit
        last_sig = results[-1]
        self.assertIn(last_sig.action, ["EXIT_LONG", "SELL"])
        self.assertEqual(last_sig.position_state, 0)

    def test_realtime_intra_candle_trailing_exit(self):
        engine = StrategyEngine(activation_atr=0.8, trail_atr=0.6, emergency_atr=2.0)
        engine.sync_position(current_size=1, entry_price=79500.0)
        atr = 30.0

        # Price rises into profit (+1.5 ATR = 79545)
        sig1 = engine.check_realtime_exit(current_price=79545.0, current_atr=atr)
        self.assertIsNone(sig1)
        self.assertEqual(engine.long_trail_stop, 79527.0)

        # Price pulls back to 79525 (below trailing stop)
        sig2 = engine.check_realtime_exit(current_price=79525.0, current_atr=atr)
        self.assertIsNotNone(sig2)
        self.assertEqual(sig2.action, "EXIT_LONG")
        self.assertIn("RealtimeTrailingStop", sig2.reason)

    def test_autobreakeven_zero_loss(self):
        engine = StrategyEngine(enable_breakeven=True, breakeven_atr=0.4, fee_buffer=2.0)
        engine.sync_position(current_size=1, entry_price=79500.0)
        atr = 30.0

        # Price moves +0.5 ATR (79515) -> Breakeven must lock stop to 79500 + 2 = 79502
        sig1 = engine.check_realtime_exit(current_price=79515.0, current_atr=atr)
        self.assertIsNone(sig1)
        self.assertTrue(engine.breakeven_locked)
        self.assertEqual(engine.long_trail_stop, 79502.0)

        # Price drops back towards entry (79501) -> Triggers AutoBreakeven exit with positive profit, zero loss
        sig2 = engine.check_realtime_exit(current_price=79501.0, current_atr=atr)
        self.assertIsNotNone(sig2)
        self.assertEqual(sig2.action, "EXIT_LONG")
        self.assertIn("AutoBreakeven", sig2.reason)

    def test_live_trend_continuation_entry(self):
        engine = StrategyEngine(enable_live_entries=True, enable_trend_continuation=True)
        # Create an uptrend dataset above EMA 20
        bars = [{"open": 100.0 + i, "high": 101.5 + i, "low": 99.5 + i, "close": 101.0 + i, "volume": 100} for i in range(35)]
        # Make the last bar a breakout above previous high
        bars.append({"open": 135.0, "high": 138.0, "low": 134.5, "close": 137.5, "volume": 100})
        df = pd.DataFrame(bars)
        
        live_sig = engine.get_live_signal(df)
        self.assertEqual(live_sig.action, "BUY")
        self.assertIn("TrendContinuation", live_sig.reason)

if __name__ == "__main__":
    unittest.main()
