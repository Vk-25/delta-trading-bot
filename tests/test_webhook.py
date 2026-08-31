import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from bot.webhook_server import app
from bot.config import config

class TestWebhookServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        config.WEBHOOK_PASSPHRASE = "test_secret_phrase"

    def test_root_and_health(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("DeltaBot Dashboard", res.text)
        
        health_res = self.client.get("/health")
        self.assertEqual(health_res.status_code, 200)
        self.assertEqual(health_res.json()["status"], "healthy")

    def test_unauthorized_webhook(self):
        payload = {
            "passphrase": "wrong_passphrase",
            "action": "BUY",
            "symbol": "BTCUSD"
        }
        res = self.client.post("/webhook", json=payload)
        self.assertEqual(res.status_code, 401)

    @patch("bot.webhook_server.delta_client")
    def test_authorized_buy_webhook(self, mock_delta):
        mock_delta.get_position_for_symbol.return_value = None
        mock_delta.place_order.return_value = {"success": True, "result": {"id": 12345, "state": "filled"}}
        mock_delta.get_contract_value.return_value = 0.001

        payload = {
            "passphrase": "test_secret_phrase",
            "action": "BUY",
            "symbol": "BTCUSD",
            "size": 2,
            "price": 65000.0
        }
        res = self.client.post("/webhook", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["action"], "BUY")
        mock_delta.place_order.assert_called_once()

    @patch("bot.webhook_server.delta_client")
    def test_exit_long_webhook(self, mock_delta):
        mock_delta.get_position_for_symbol.return_value = {"size": 2, "entry_price": 64000.0}
        mock_delta.close_position.return_value = {"success": True, "result": {"state": "closed"}}
        mock_delta.get_contract_value.return_value = 0.001

        payload = {
            "passphrase": "test_secret_phrase",
            "action": "EXIT_LONG",
            "symbol": "BTCUSD",
            "price": 65000.0
        }
        res = self.client.post("/webhook", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        mock_delta.close_position.assert_called_once_with("BTCUSD")

    def test_webhook_stats_and_fee_calculation(self):
        from bot.webhook_server import get_webhook_stats
        # Test with sample trades
        trades = [
            {
                "entry_price": 2800.0,
                "exit_price": 2850.0,
                "price_diff": 50.0,
                "gross_pnl": 0.50,
                "fee": 0.0288,
                "net_pnl": 0.4712,
                "is_profit": True
            },
            {
                "entry_price": 2850.0,
                "exit_price": 2830.0,
                "price_diff": -20.0,
                "gross_pnl": -0.20,
                "fee": 0.0288,
                "net_pnl": -0.2288,
                "is_profit": False
            }
        ]
        stats = get_webhook_stats(trades)
        self.assertEqual(stats["total_trades"], 2)
        self.assertEqual(stats["profitable_trades"], 1)
        self.assertEqual(stats["loss_trades"], 1)
        self.assertEqual(stats["win_rate"], 50.0)
        self.assertAlmostEqual(stats["total_fees"], 0.0576, places=4)
        self.assertAlmostEqual(stats["total_gross_pnl"], 0.30, places=4)
        self.assertAlmostEqual(stats["total_net_pnl"], 0.2424, places=4)
        self.assertAlmostEqual(stats["total_net_pnl_inr"], round(0.2424 * 87.5, 2), places=2)

    def test_dashboard_contains_updated_fee_and_functions(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("function formatUSD", res.text)
        self.assertIn("function formatINR", res.text)
        self.assertIn("function formatPrice", res.text)
        self.assertIn("/api/dashboard", res.text)

if __name__ == "__main__":
    unittest.main()
