import json
import os
import time
import hmac
import hashlib
import requests
from firebase_functions import https_fn, options
from firebase_admin import initialize_app

initialize_app()

# ==============================================================================
# CONFIGURATION (Set these via environment variables or replace directly)
# ==============================================================================
DELTA_ENV = os.environ.get("DELTA_ENVIRONMENT", "india").strip().lower()
BASE_URL = "https://api.india.delta.exchange" if DELTA_ENV == "india" else "https://api.delta.exchange"

DELTA_API_KEY = os.environ.get("DELTA_API_KEY", "")
DELTA_API_SECRET = os.environ.get("DELTA_API_SECRET", "")
WEBHOOK_PASSPHRASE = os.environ.get("WEBHOOK_PASSPHRASE", "supersecretpassphrase123")
DEFAULT_SYMBOL = os.environ.get("TRADING_SYMBOL", "BTCUSD")
DEFAULT_ORDER_SIZE = int(os.environ.get("ORDER_SIZE", "1"))

def generate_delta_signature(secret: str, method: str, path: str, timestamp: str, payload: dict = None) -> str:
    body_str = json.dumps(payload, separators=(',', ':')) if payload else ''
    signature_data = f"{method.upper()}{timestamp}{path}{body_str}"
    return hmac.new(secret.encode('utf-8'), signature_data.encode('utf-8'), hashlib.sha256).hexdigest()

def delta_request(method: str, path: str, payload: dict = None) -> dict:
    timestamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Firebase-DeltaBot/1.0",
        "api-key": DELTA_API_KEY,
        "timestamp": timestamp,
        "signature": generate_delta_signature(DELTA_API_SECRET, method, path, timestamp, payload)
    }
    url = f"{BASE_URL}{path}"
    
    if method.upper() == "GET":
        res = requests.get(url, headers=headers, timeout=10)
    elif method.upper() == "POST":
        res = requests.post(url, json=payload, headers=headers, timeout=10)
    else:
        return {"success": False, "error": f"Unsupported method: {method}"}
        
    try:
        return res.json()
    except Exception:
        return {"success": False, "status": res.status_code, "text": res.text}

def get_product_id(symbol: str) -> int:
    res = requests.get(f"{BASE_URL}/v2/products", timeout=10).json()
    for p in res.get("result", []):
        if p.get("symbol", "").upper() == symbol.upper():
            return p.get("id")
    return None

def get_open_position(product_id: int) -> dict:
    res = delta_request("GET", "/v2/positions/margined")
    for pos in res.get("result", []):
        if pos.get("product_id") == product_id and abs(float(pos.get("size", 0))) > 0:
            return pos
    return None

def close_position(symbol: str, product_id: int) -> dict:
    pos = get_open_position(product_id)
    if not pos:
        return {"success": True, "message": "No open position to close"}
    
    current_size = float(pos.get("size", 0))
    side = "sell" if current_size > 0 else "buy"
    payload = {
        "product_id": product_id,
        "size": abs(int(current_size)),
        "side": side,
        "order_type": "market_order",
        "reduce_only": True
    }
    return delta_request("POST", "/v2/orders", payload=payload)

# ==============================================================================
# FIREBASE HTTPS FUNCTION: Webhook Receiver for TradingView Alerts
# ==============================================================================
@https_fn.on_request(
    cors=options.CorsOptions(cors_origins="*", cors_methods=["post", "get"]),
    memory=options.MemoryOption.MB_256,
    timeout_sec=60
)
def delta_webhook(req: https_fn.Request) -> https_fn.Response:
    if req.method == "GET":
        return https_fn.Response(json.dumps({"status": "online", "service": "Firebase Delta Bot"}), status=200, mimetype="application/json")

    if req.method != "POST":
        return https_fn.Response("Method Not Allowed", status=405)

    try:
        data = req.get_json(silent=True) or {}
        passphrase = data.get("passphrase")
        
        # Verify passphrase
        if WEBHOOK_PASSPHRASE and passphrase != WEBHOOK_PASSPHRASE:
            return https_fn.Response(json.dumps({"error": "Unauthorized: Invalid Passphrase"}), status=401, mimetype="application/json")

        action = str(data.get("action", "")).upper()
        symbol = str(data.get("symbol", DEFAULT_SYMBOL)).upper()
        size = int(data.get("size", DEFAULT_ORDER_SIZE))
        
        product_id = get_product_id(symbol)
        if not product_id:
            return https_fn.Response(json.dumps({"error": f"Symbol {symbol} not found on Delta"}), status=400, mimetype="application/json")

        existing_pos = get_open_position(product_id)
        existing_size = float(existing_pos.get("size", 0)) if existing_pos else 0

        result = {}
        if action == "BUY":
            if existing_size < 0:
                close_position(symbol, product_id)
            result = delta_request("POST", "/v2/orders", {
                "product_id": product_id,
                "size": size,
                "side": "buy",
                "order_type": "market_order",
                "reduce_only": False
            })

        elif action == "SELL":
            if existing_size > 0:
                close_position(symbol, product_id)
            result = delta_request("POST", "/v2/orders", {
                "product_id": product_id,
                "size": size,
                "side": "sell",
                "order_type": "market_order",
                "reduce_only": False
            })

        elif action == "EXIT_LONG":
            if existing_size > 0:
                result = close_position(symbol, product_id)
            else:
                result = {"message": "No open LONG position"}

        elif action == "EXIT_SHORT":
            if existing_size < 0:
                result = close_position(symbol, product_id)
            else:
                result = {"message": "No open SHORT position"}

        elif action == "CLOSE":
            result = close_position(symbol, product_id)
        else:
            return https_fn.Response(json.dumps({"error": f"Unknown action: {action}"}), status=400, mimetype="application/json")

        return https_fn.Response(json.dumps({"success": True, "action": action, "symbol": symbol, "result": result}), status=200, mimetype="application/json")

    except Exception as e:
        return https_fn.Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")
