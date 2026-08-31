import unittest
import pandas as pd
import numpy as np
from bot.config import config
from bot.strategy_engine import StrategyEngine

class TestStrategyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = StrategyEngine(
            entry_ema_length=5,
            fast_ema_length=3,
            trail_move_unit=3.0,
            trail_step_unit=1.0,
            trail_profit_ratio=1.0 / 3.0,
            exit_on_opposite=True,
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

        self.assertIn("ema21", data.columns)
        self.assertIn("ema9", data.columns)
        self.assertEqual(len(data), n)

    def test_21_ema_cut_and_breakout_buy_signal(self):
        # Construct specific bars where bar 5 cuts 21 EMA and bar 6 breaks high
        bars = [
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            # Bar 5 (index 5): Body cuts EMA 100 (open 99.0, close 101.0, high 101.5, low 98.5)
            {"open": 99.0, "high": 101.5, "low": 98.5, "close": 101.0, "volume": 100},
            # Bar 6 (index 6): Immediately breaks high of Bar 5 (high 103.0 > 101.5)
            {"open": 101.0, "high": 103.0, "low": 100.5, "close": 102.5, "volume": 100},
        ]
        df = pd.DataFrame(bars)
        results = self.engine.process_candles(df)
        
        # The last result should trigger a BUY action
        last_sig = results[-1]
        self.assertEqual(last_sig.action, "BUY")
        self.assertEqual(last_sig.position_state, 1)
        self.assertEqual(self.engine.initial_stop_loss, 98.5)  # Low of cutting candle

    def test_21_ema_cut_and_breakout_sell_signal(self):
        # Construct specific bars where bar 5 cuts 21 EMA and bar 6 breaks low
        bars = [
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            # Bar 5 (index 5): Body cuts EMA 100 (open 101.0, close 99.0, high 101.5, low 98.5)
            {"open": 101.0, "high": 101.5, "low": 98.5, "close": 99.0, "volume": 100},
            # Bar 6 (index 6): Immediately breaks low of Bar 5 (low 97.0 < 98.5)
            {"open": 99.0, "high": 99.5, "low": 97.0, "close": 97.5, "volume": 100},
        ]
        df = pd.DataFrame(bars)
        results = self.engine.process_candles(df)
        
        # The last result should trigger a SELL action
        last_sig = results[-1]
        self.assertEqual(last_sig.action, "SELL")
        self.assertEqual(last_sig.position_state, -1)
        self.assertEqual(self.engine.initial_stop_loss, 101.5)  # High of cutting candle

    def test_1to3_trailing_profit_long(self):
        engine = StrategyEngine(trail_move_unit=3.0, trail_step_unit=1.0, trail_profit_ratio=1.0 / 3.0)
        # Entry at 2000.0, Initial Stop at 1990.0
        engine.sync_position(current_size=1, entry_price=2000.0, stop_loss=1990.0)
        
        # Market moves +3 points in profit (price = 2003.0) -> Trailing Stop should trail +1 point (1991.0)
        stop1 = engine.update_1to3_trailing_stop(current_price=2003.0, high=2003.0)
        self.assertAlmostEqual(stop1, 1991.0, places=2)
        
        # Market moves +15 points in profit (price = 2015.0) -> Trailing Stop should trail +5 points (1995.0)
        stop2 = engine.update_1to3_trailing_stop(current_price=2015.0, high=2015.0)
        self.assertAlmostEqual(stop2, 1995.0, places=2)

        # Market moves +30 points in profit (price = 2030.0) -> Trailing Stop should trail +10 points (2000.0 Breakeven)
        stop3 = engine.update_1to3_trailing_stop(current_price=2030.0, high=2030.0)
        self.assertAlmostEqual(stop3, 2000.0, places=2)

        # Market moves +60 points in profit (price = 2060.0) -> Trailing Stop should trail +20 points (2010.0 Locked Profit)
        stop4 = engine.update_1to3_trailing_stop(current_price=2060.0, high=2060.0)
        self.assertAlmostEqual(stop4, 2010.0, places=2)

    def test_1to3_trailing_profit_short(self):
        engine = StrategyEngine(trail_move_unit=3.0, trail_step_unit=1.0, trail_profit_ratio=1.0 / 3.0)
        # Entry at 2000.0, Initial Stop at 2010.0
        engine.sync_position(current_size=-1, entry_price=2000.0, stop_loss=2010.0)
        
        # Market moves +3 points in profit (price drops to 1997.0) -> Trailing Stop should trail -1 point (2009.0)
        stop1 = engine.update_1to3_trailing_stop(current_price=1997.0, low=1997.0)
        self.assertAlmostEqual(stop1, 2009.0, places=2)

        # Market moves +30 points in profit (price drops to 1970.0) -> Trailing Stop should trail -10 points (2000.0 Breakeven)
        stop2 = engine.update_1to3_trailing_stop(current_price=1970.0, low=1970.0)
        self.assertAlmostEqual(stop2, 2000.0, places=2)

    def test_realtime_intra_candle_trailing_exit(self):
        engine = StrategyEngine(trail_move_unit=3.0, trail_step_unit=1.0, trail_profit_ratio=1.0 / 3.0)
        engine.sync_position(current_size=1, entry_price=3000.0, stop_loss=2990.0)

        # Price rises to 3030 (+30 points profit -> stop moves to 3000.0)
        engine.update_1to3_trailing_stop(3030.0, high=3030.0)
        self.assertAlmostEqual(engine.active_trailing_stop, 3000.0, places=2)

        # Price pulls back and touches 3000.0 -> Exit Long
        sig = engine.check_realtime_exit(3000.0)
        self.assertIsNotNone(sig)
        self.assertEqual(sig.action, "EXIT_LONG")
        self.assertIn("TrailingStop1:3", sig.reason)
        self.assertEqual(engine.position_state, 0)

    def test_opposite_signal_exit_to_flat(self):
        # Create a series where BUY happens, then an opposite SELL breakdown happens
        bars = [
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},
            # Bar 5: Cut EMA -> Bar 6: Buy
            {"open": 99.0, "high": 101.5, "low": 98.5, "close": 101.0, "volume": 100},
            {"open": 101.0, "high": 103.0, "low": 100.5, "close": 102.5, "volume": 100},
            # Bar 7: Cuts EMA downward & breaks low -> Opposite signal triggers exit to Flat
            {"open": 102.0, "high": 102.5, "low": 99.5, "close": 100.0, "volume": 100},
        ]
        df = pd.DataFrame(bars)
        results = self.engine.process_candles(df)
        
        # On Bar 7, position should be exited to Flat (0)
        self.assertEqual(results[-1].action, "EXIT_LONG")
        self.assertEqual(results[-1].position_state, 0)
        self.assertIn("OppositeSignal", results[-1].reason)

    def test_symbol_profiles(self):
        eth_profile = config.get_symbol_profile("ETHUSD")
        self.assertEqual(eth_profile["leverage"], 130)
        self.assertEqual(eth_profile["order_size"], 1)

        xaut_profile = config.get_symbol_profile("XAUTUSD")
        self.assertEqual(xaut_profile["leverage"], 60)
        self.assertIn(xaut_profile["order_size"], [1, 2, 3])

    def test_standalone_performance_stats_calculation(self):
        import bot.standalone_bot as sb
        original_trades = sb.completed_trades
        try:
            sb.completed_trades = [
                {
                    "entry_price": 2880.0,
                    "exit_price": 2890.0,
                    "size": 1,
                    "gross_pnl": 0.10,
                    "fees": 0.0288,
                    "net_pnl": 0.0712,
                    "net_pnl_inr": 6.23,
                    "win": True,
                    "exit_reason": "Trailing Stop"
                },
                {
                    "entry_price": 2890.0,
                    "exit_price": 2885.0,
                    "size": 1,
                    "gross_pnl": -0.05,
                    "fees": 0.0288,
                    "net_pnl": -0.0788,
                    "net_pnl_inr": -6.90,
                    "win": False,
                    "exit_reason": "Trailing Stop"
                }
            ]
            stats = sb.get_performance_stats()
            self.assertEqual(stats["total_trades"], 2)
            self.assertEqual(stats["winning_trades"], 1)
            self.assertEqual(stats["losing_trades"], 1)
            self.assertEqual(stats["win_rate"], 50.0)
            self.assertAlmostEqual(stats["total_fees"], 0.06, places=2)
        finally:
            sb.completed_trades = original_trades

if __name__ == "__main__":
    unittest.main()
