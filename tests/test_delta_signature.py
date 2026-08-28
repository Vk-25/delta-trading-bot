import unittest
from bot.utils import generate_delta_signature

class TestDeltaSignature(unittest.TestCase):
    def test_signature_deterministic(self):
        secret = "my_test_secret_key"
        method = "POST"
        path = "/v2/orders"
        timestamp = "1700000000"
        payload = {"product_id": 123, "size": 1, "side": "buy"}
        
        sig1 = generate_delta_signature(secret, method, path, timestamp, payload=payload)
        sig2 = generate_delta_signature(secret, method, path, timestamp, payload=payload)
        
        self.assertEqual(sig1, sig2)
        self.assertEqual(len(sig1), 64)  # SHA256 hex string length

    def test_get_signature_with_query(self):
        secret = "my_test_secret_key"
        method = "GET"
        path = "/v2/positions"
        timestamp = "1700000000"
        query_string = "product_id=123"
        
        sig = generate_delta_signature(secret, method, path, timestamp, query_string=query_string)
        self.assertTrue(isinstance(sig, str))
        self.assertEqual(len(sig), 64)

if __name__ == "__main__":
    unittest.main()
