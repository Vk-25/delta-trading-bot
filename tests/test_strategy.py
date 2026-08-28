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

if __name__ == "__main__":
    unittest.main()
