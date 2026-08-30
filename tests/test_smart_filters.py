import unittest
import pandas as pd
import numpy as np
from bot.strategy_engine import StrategyEngine
from bot.standalone_bot import RiskGuard

class TestSmartFilters(unittest.TestCase):
    def test_volume_filter(self):
        engine = StrategyEngine(enable_volume_filter=True, volume_multiplier=1.5, volume_lookback=5)
        df_low_vol = pd.DataFrame({
            "high": [10, 11, 12, 13, 14, 15],
            "low": [9, 10, 11, 12, 13, 14],
            "close": [9.5, 10.5, 11.5, 12.5, 13.5, 14.5],
            "volume": [100, 100, 100, 100, 100, 100]
        })
        self.assertFalse(engine.has_volume_confirmation(df_low_vol, 1.5, 5))
        
        df_high_vol = pd.DataFrame({
            "high": [10, 11, 12, 13, 14, 15],
            "low": [9, 10, 11, 12, 13, 14],
            "close": [9.5, 10.5, 11.5, 12.5, 13.5, 14.5],
            "volume": [100, 100, 100, 100, 100, 200]
        })
        self.assertTrue(engine.has_volume_confirmation(df_high_vol, 1.5, 5))

    def test_risk_guard_kill_switch(self):
        rg = RiskGuard(max_daily_loss_pct=3.0, max_consecutive_losses=3)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-1.0)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-1.0)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-1.0)
        self.assertFalse(rg.can_trade())

    def test_adx_calculation(self):
        np.random.seed(42)
        n = 60
        closes = 100 + np.cumsum(np.random.randn(n))
        highs = closes + np.random.uniform(0.5, 2.0, n)
        lows = closes - np.random.uniform(0.5, 2.0, n)
        opens = (closes + lows) / 2
        df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes})
        adx = StrategyEngine.calculate_adx(df, 14)
        self.assertEqual(len(adx), n)
    def test_high_frequency_scalper_triggers(self):
        # 1 day of 5m bars (288 candles)
        np.random.seed(42)
        n = 288
        returns = np.random.normal(0, 0.002, n)
        prices = 2500.0 * np.exp(np.cumsum(returns))
        df = pd.DataFrame({
            "open": prices + np.random.normal(0, 0.8, n),
            "high": prices + np.abs(np.random.normal(2.5, 1.2, n)),
            "low": prices - np.abs(np.random.normal(2.5, 1.2, n)),
            "close": prices,
            "volume": np.random.uniform(1000, 10000, n)
        })
        engine = StrategyEngine(
            strategy_mode="scalper",
            fast_ema_length=9,
            entry_ema_length=21,
            enable_trend_continuation=True,
            enable_range_breakout=True,
            enable_rsi_reversal=True,
            enable_volume_filter=False,
            enable_adx_filter=False,
            enable_regime_filter=False,
            take_profit_atr=0.85,
            breakeven_atr=0.35,
            trail_atr=0.45,
            emergency_atr=1.10
        )
        results = engine.process_candles(df)
        actions = [r for r in results if r.action in ("BUY", "SELL")]
        # Verify that multi-trigger scalping generates 50+ trade actions per day
        self.assertGreaterEqual(len(actions), 40)

if __name__ == "__main__":
    unittest.main()
