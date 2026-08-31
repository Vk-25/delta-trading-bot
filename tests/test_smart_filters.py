import unittest
from bot.standalone_bot import RiskGuard
from bot.config import config

class TestRiskGuardAndProfiles(unittest.TestCase):
    def test_risk_guard_kill_switch_daily_loss(self):
        rg = RiskGuard(max_daily_loss_pct=3.0, max_consecutive_losses=4)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-1.0)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-1.5)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-1.0)  # Total daily loss = -3.5%
        self.assertFalse(rg.can_trade())

    def test_risk_guard_kill_switch_consecutive_losses(self):
        rg = RiskGuard(max_daily_loss_pct=10.0, max_consecutive_losses=3)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-0.1)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-0.1)
        self.assertTrue(rg.can_trade())
        rg.record_trade(-0.1)  # 3 consecutive losses
        self.assertFalse(rg.can_trade())

    def test_symbol_profiles_leverage(self):
        eth_prof = config.get_symbol_profile("ETHUSD")
        self.assertEqual(eth_prof["leverage"], 130)
        self.assertEqual(eth_prof["order_size"], 1)

        xaut_prof = config.get_symbol_profile("XAUTUSD")
        self.assertEqual(xaut_prof["leverage"], 60)
        self.assertGreaterEqual(xaut_prof["order_size"], 1)

if __name__ == "__main__":
    unittest.main()
