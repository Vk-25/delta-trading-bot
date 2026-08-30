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
            emergency_atr=2.5,
            # Disable new smart filters for legacy tests (tested separately)
            enable_volume_filter=False,
            enable_adx_filter=False,
            enable_regime_filter=False,
            enable_mtf_alignment=False,
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
        engine = StrategyEngine(activation_atr=0.8, trail_atr=0.6, take_profit_atr=0.0, emergency_atr=2.0)
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
        engine = StrategyEngine(enable_breakeven=True, breakeven_atr=0.25, fee_buffer=0.5, activation_atr=0.50, trail_atr=0.40, take_profit_atr=0.0)
        engine.sync_position(current_size=1, entry_price=2450.0)
        atr = 10.0

        # Price moves +0.35 ATR (2453.5) -> Breakeven must lock stop to covers 0.12% fee (2450 + 2.94 = 2452.94)
        sig1 = engine.check_realtime_exit(current_price=2453.5, current_atr=atr)
        self.assertIsNone(sig1)
        self.assertTrue(engine.breakeven_locked)
        self.assertEqual(engine.long_trail_stop, 2452.94)

        # Price drops back towards entry (2451.0) -> Triggers AutoBreakeven exit with positive profit, zero loss
        sig2 = engine.check_realtime_exit(current_price=2451.0, current_atr=atr)
        self.assertIsNotNone(sig2)
        self.assertEqual(sig2.action, "EXIT_LONG")
        self.assertIn("AutoBreakeven", sig2.reason)

    def test_100x_anti_liquidation_emergency_stop(self):
        engine = StrategyEngine(emergency_atr=0.45, enable_emergency=True)
        engine.sync_position(current_size=1, entry_price=2450.0)
        atr = 10.0  # 0.45 ATR = $4.50 distance (far safer than the $18.37 liquidation limit)

        # Price drops to 2445.0 (-$5.00 = -0.5 ATR) -> MUST fire RealtimeEmergencyStop before liquidation
        sig = engine.check_realtime_exit(current_price=2445.0, current_atr=atr)
        self.assertIsNotNone(sig)
        self.assertEqual(sig.action, "EXIT_LONG")
        self.assertIn("RealtimeEmergencyStop", sig.reason)

    def test_standalone_performance_stats_calculation(self):
        import bot.standalone_bot as sb
        # Mock completed_trades
        original_trades = sb.completed_trades
        try:
            sb.completed_trades = [
                {
                    "entry_price": 2880.0,
                    "exit_price": 2890.0,
                    "price_diff": 10.0,
                    "size": 1,
                    "gross_pnl": 0.10,
                    "fee": 0.0288,
                    "net_pnl": 0.0712,
                    "net_pnl_inr": 6.23,
                    "is_profit": True,
                    "reason": "Smart Exit"
                },
                {
                    "entry_price": 2890.0,
                    "exit_price": 2885.0,
                    "price_diff": -5.0,
                    "size": 1,
                    "gross_pnl": -0.05,
                    "fee": 0.0288,
                    "net_pnl": -0.0788,
                    "net_pnl_inr": -6.90,
                    "is_profit": False,
                    "reason": "Trailing Stop"
                }
            ]
            stats = sb.get_performance_stats()
            self.assertEqual(stats["total_trades"], 2)
            self.assertEqual(stats["profitable_trades"], 1)
            self.assertEqual(stats["loss_trades"], 1)
            self.assertEqual(stats["win_rate"], 50.0)
            self.assertAlmostEqual(stats["total_fees"], 0.0576, places=4)
            self.assertAlmostEqual(stats["total_gross_pnl"], 0.05, places=4)
            self.assertAlmostEqual(stats["total_net_pnl"], -0.0076, places=4)
            self.assertAlmostEqual(stats["total_net_pnl_inr"], round(-0.0076 * 87.5, 2), places=2)
        finally:
            sb.completed_trades = original_trades

if __name__ == "__main__":
    unittest.main()
