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
        self.assertIn("DeltaBot Live Dashboard", res.text)
        
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

        payload = {
            "passphrase": "test_secret_phrase",
            "action": "EXIT_LONG",
            "symbol": "BTCUSD"
        }
        res = self.client.post("/webhook", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        mock_delta.close_position.assert_called_once_with("BTCUSD")

if __name__ == "__main__":
    unittest.main()
