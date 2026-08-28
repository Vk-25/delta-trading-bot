import time
import requests
import json
from typing import Any, Dict, List, Optional, Tuple
from bot.config import config
from bot.utils import generate_delta_signature, logger

class DeltaExchangeClient:
    """
    Client for Delta Exchange REST API v2 (supports both Global and India).
    Handles authentication, signature generation, product resolution,
    market/limit order placement, leverage setting, and candle history retrieval.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 15
    ):
        self.api_key = api_key or config.DELTA_API_KEY
        self.api_secret = api_secret or config.DELTA_API_SECRET
        self.base_url = (base_url or config.get_base_url()).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        if config.STATIC_PROXY_URL:
            self.session.proxies.update({
                "http": config.STATIC_PROXY_URL,
                "https": config.STATIC_PROXY_URL
            })
            logger.info(f"Using outbound proxy for Delta Exchange: {config.STATIC_PROXY_URL}")
        self._product_cache: Dict[str, Dict[str, Any]] = {}
        self._product_id_map: Dict[int, str] = {}
        self._products_cached_at: float = 0
        
    def _get_headers(
        self,
        method: str,
        path: str,
        query_string: str = "",
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Builds authenticated request headers with HMAC-SHA256 signature."""
        timestamp = str(int(time.time()))
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "DeltaExchange-TradingBot/1.0",
            "api-key": self.api_key,
            "timestamp": timestamp
        }
        
        if self.api_key and self.api_secret:
            signature = generate_delta_signature(
                secret=self.api_secret,
                method=method,
                path=path,
                timestamp=timestamp,
                query_string=query_string,
                payload=payload
            )
            headers["signature"] = signature
            
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        auth_required: bool = True
    ) -> Dict[str, Any]:
        """Internal request dispatcher with signature handling and error checking."""
        url = f"{self.base_url}{endpoint}"
        query_string = ""
        if params:
            # Build query string
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            
        headers = self._get_headers(
            method=method,
            path=endpoint,
            query_string=query_string,
            payload=payload
        ) if auth_required else {
            "Content-Type": "application/json",
            "User-Agent": "DeltaExchange-TradingBot/1.0"
        }

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, json=payload, headers=headers, timeout=self.timeout)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=payload, headers=headers, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            try:
                data = response.json() if response.text and response.text.strip() else {}
            except Exception:
                data = {"raw_text": response.text, "error": response.text or f"HTTP status {response.status_code}"}

            if not response.ok:
                error_obj = data.get("error") if isinstance(data, dict) else response.text
                if isinstance(error_obj, dict):
                    error_msg = error_obj.get("message") or error_obj.get("code") or str(error_obj)
                elif isinstance(error_obj, str):
                    error_msg = error_obj
                else:
                    error_msg = str(error_obj) or response.text or f"HTTP {response.status_code}"
                logger.error(f"Delta API error [{response.status_code}] on {method} {endpoint}: {error_msg}")
                return {"success": False, "status_code": response.status_code, "error": error_msg, "raw": data}
            
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP Request failed on {method} {endpoint}: {str(e)}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # ACCOUNT & PRODUCTS
    # =========================================================================

    def get_profile(self) -> Dict[str, Any]:
        """Fetches account profile and verification status."""
        return self._request("GET", "/v2/profile")

    def get_wallet_balances(self) -> Dict[str, Any]:
        """Fetches wallet assets and available margin balances."""
        return self._request("GET", "/v2/wallet/balances")

    def get_products(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetches and caches product definitions (contract specifications)."""
        now = time.time()
        if not force_refresh and self._product_cache and (now - self._products_cached_at < 3600):
            return list(self._product_cache.values())

        res = self._request("GET", "/v2/products", auth_required=False)
        result = res.get("result", [])
        if isinstance(result, list):
            self._product_cache = {}
            self._product_id_map = {}
            for p in result:
                sym = p.get("symbol")
                pid = p.get("id")
                if sym and pid:
                    self._product_cache[sym.upper()] = p
                    self._product_id_map[pid] = sym.upper()
            self._products_cached_at = now
            return result
        return []

    def get_product(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Resolves symbol (e.g. BTCUSD) to product dictionary."""
        sym_clean = symbol.strip().upper()
        if sym_clean in self._product_cache:
            return self._product_cache[sym_clean]
        
        self.get_products(force_refresh=True)
        return self._product_cache.get(sym_clean)

    def get_product_id(self, symbol: str) -> Optional[int]:
        """Resolves symbol (e.g. BTCUSD) to numeric product ID."""
        prod = self.get_product(symbol)
        if prod:
            return prod.get("id")
        return None

    # =========================================================================
    # LEVERAGE & POSITIONS
    # =========================================================================

    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Sets leverage for a specific symbol."""
        product_id = self.get_product_id(symbol)
        if not product_id:
            return {"success": False, "error": f"Unknown product symbol: {symbol}"}

        payload = {
            "product_id": product_id,
            "leverage": str(leverage)
        }
        res = self._request("POST", "/v2/orders/leverage", payload=payload)
        logger.info(f"Set leverage for {symbol} (product_id={product_id}) to {leverage}x: {res.get('success', False)}")
        return res

    def get_positions(self) -> Dict[str, Any]:
        """Fetches all open positions for the user."""
        return self._request("GET", "/v2/positions/margined")

    def get_position_for_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches current open position for a specific symbol."""
        product_id = self.get_product_id(symbol)
        if not product_id:
            return None

        res = self.get_positions()
        result = res.get("result", [])
        if isinstance(result, list):
            for pos in result:
                if pos.get("product_id") == product_id:
                    size = float(pos.get("size", 0))
                    if abs(size) > 0:
                        return pos
        return None

    # =========================================================================
    # ORDERS & EXECUTION
    # =========================================================================

    def place_order(
        self,
        symbol: str,
        size: int,
        side: str,
        order_type: str = "market_order",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        Places an order on Delta Exchange.
        side: 'buy' or 'sell'
        order_type: 'market_order' or 'limit_order'
        size: number of contracts (integer)
        """
        product_id = self.get_product_id(symbol)
        if not product_id:
            return {"success": False, "error": f"Symbol not found: {symbol}"}

        payload: Dict[str, Any] = {
            "product_id": product_id,
            "size": int(size),
            "side": side.lower().strip(),
            "order_type": order_type.lower().strip(),
            "reduce_only": bool(reduce_only)
        }
        
        if limit_price is not None:
            payload["limit_price"] = str(limit_price)
            
        if stop_price is not None:
            payload["stop_price"] = str(stop_price)

        logger.info(f"Submitting {side.upper()} order for {size} {symbol} ({order_type}, reduce_only={reduce_only})...")
        res = self._request("POST", "/v2/orders", payload=payload)
        
        if res.get("success"):
            order_info = res.get("result", {})
            logger.info(f"Order SUCCESS: ID={order_info.get('id')} Status={order_info.get('state')} Size={order_info.get('size')}")
        else:
            logger.error(f"Order FAILED: {res.get('error')}")
            
        return res

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """Closes open position for a symbol using a reduce_only market order."""
        pos = self.get_position_for_symbol(symbol)
        if not pos:
            logger.info(f"No open position found to close for {symbol}.")
            return {"success": True, "message": "No open position to close"}

        current_size = float(pos.get("size", 0))
        if current_size == 0:
            return {"success": True, "message": "Position is already flat"}

        # If current_size > 0 (Long), we sell to close.
        # If current_size < 0 (Short), we buy to close.
        close_side = "sell" if current_size > 0 else "buy"
        abs_size = abs(int(current_size))

        logger.info(f"Closing existing {'LONG' if current_size > 0 else 'SHORT'} position of {abs_size} contracts on {symbol}...")
        return self.place_order(
            symbol=symbol,
            size=abs_size,
            side=close_side,
            order_type="market_order",
            reduce_only=True
        )

    # =========================================================================
    # CANDLES & MARKET DATA (FOR STANDALONE BOT)
    # =========================================================================

    def get_candles(
        self,
        symbol: str,
        resolution: str = "15m",
        limit: int = 200
    ) -> Dict[str, Any]:
        """
        Fetches historical OHLCV candles from Delta Exchange.
        Resolution: '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'
        """
        resolution_map = {
            "1m": ("1", 60),
            "1": ("1", 60),
            "3m": ("3", 180),
            "3": ("3", 180),
            "5m": ("5", 300),
            "5": ("5", 300),
            "15m": ("15", 900),
            "15": ("15", 900),
            "30m": ("30", 1800),
            "30": ("30", 1800),
            "1h": ("60", 3600),
            "60": ("60", 3600),
            "2h": ("120", 7200),
            "120": ("120", 7200),
            "4h": ("240", 14400),
            "240": ("240", 14400),
            "6h": ("360", 21600),
            "360": ("360", 21600),
            "1d": ("D", 86400),
            "D": ("D", 86400),
            "1w": ("W", 604800),
            "W": ("W", 604800),
        }
        res_code, res_sec = resolution_map.get(str(resolution).lower(), ("15", 900))
        end_time = int(time.time())
        start_time = end_time - (res_sec * limit)

        params = {
            "symbol": symbol.strip().upper(),
            "resolution": res_code,
            "from": str(start_time),
            "to": str(end_time)
        }
        
        # Public market data endpoint
        return self._request("GET", "/v2/chart/history", params=params, auth_required=False)
