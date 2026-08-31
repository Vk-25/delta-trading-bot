import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BotConfig:
    # Delta Environment: "global" or "india"
    DELTA_ENVIRONMENT: str = os.getenv("DELTA_ENVIRONMENT", "india").strip().lower()
    
    # Delta Base URLs
    GLOBAL_BASE_URL: str = "https://api.delta.exchange"
    INDIA_BASE_URL: str = "https://api.india.delta.exchange"
    
    # Credentials
    DELTA_API_KEY: str = os.getenv("DELTA_API_KEY", "").strip()
    DELTA_API_SECRET: str = os.getenv("DELTA_API_SECRET", "").strip()
    
    # Security
    WEBHOOK_PASSPHRASE: str = os.getenv("WEBHOOK_PASSPHRASE", "").strip()
    
    # Trade execution defaults (supports comma-separated multi-symbols, e.g. "ETHUSD,XAUTUSD")
    TRADING_SYMBOLS_RAW: str = os.getenv("TRADING_SYMBOLS", os.getenv("TRADING_SYMBOL", "ETHUSD,XAUTUSD")).strip().upper()
    TRADING_SYMBOLS: list = [s.strip() for s in TRADING_SYMBOLS_RAW.split(",") if s.strip()]
    TRADING_SYMBOL: str = TRADING_SYMBOLS[0] if TRADING_SYMBOLS else "ETHUSD"
    ORDER_SIZE: int = int(os.getenv("ORDER_SIZE", "1"))
    LEVERAGE: int = int(os.getenv("LEVERAGE", "130"))
    ORDER_TYPE: str = os.getenv("ORDER_TYPE", "market_order").strip()
    
    # Dynamic Symbol Leverage & Lot Sizing Profiles
    # ETHUSD: 130x leverage, 1 lot
    # XAUTUSD / XAUUSD / XAUUSDT: 60x leverage, 1-3 lots (default 1 lot)
    SYMBOL_PROFILES: Dict[str, Dict[str, Any]] = {
        "ETHUSD": {"leverage": 130, "order_size": 1},
        "XAUTUSD": {"leverage": 60, "order_size": int(os.getenv("XAUT_ORDER_SIZE", "1"))},
        "XAUUSD": {"leverage": 60, "order_size": int(os.getenv("XAUT_ORDER_SIZE", "1"))},
        "XAUUSDT": {"leverage": 60, "order_size": int(os.getenv("XAUT_ORDER_SIZE", "1"))},
        "XAUTUSDT": {"leverage": 60, "order_size": int(os.getenv("XAUT_ORDER_SIZE", "1"))},
        "BTCUSD": {"leverage": 100, "order_size": 1},
    }

    # Core Strategy: 21 EMA Cut Breakout with 9 EMA Regular Analysis
    ENTRY_EMA_LENGTH: int = int(os.getenv("ENTRY_EMA_LENGTH", "21"))
    FAST_EMA_LENGTH: int = int(os.getenv("FAST_EMA_LENGTH", "9"))
    TIMEFRAME: str = os.getenv("TIMEFRAME", "5m")
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "1"))

    # 1:3 Trailing Take Profit (For every 3 points market moves, trail stop 1 point)
    ENABLE_TRAILING_PROFIT: bool = os.getenv("ENABLE_TRAILING_PROFIT", "true").lower() in ("true", "1", "yes")
    TRAIL_MOVE_UNIT: float = float(os.getenv("TRAIL_MOVE_UNIT", "3.0"))   # Market moves 3 points
    TRAIL_STEP_UNIT: float = float(os.getenv("TRAIL_STEP_UNIT", "1.0"))   # Stop trails 1 point
    TRAIL_PROFIT_RATIO: float = float(os.getenv("TRAIL_PROFIT_RATIO", str(1.0 / 3.0))) # 1 / 3 = 0.333333...

    # Exit on Opposite Signal (Closes open position to Flat)
    EXIT_ON_OPPOSITE: bool = os.getenv("EXIT_ON_OPPOSITE", "true").lower() in ("true", "1", "yes")

    # Risk & Protection
    FEE_BUFFER_USD: float = float(os.getenv("FEE_BUFFER_USD", "0.50"))
    ENABLE_RISK_GUARD: bool = os.getenv("ENABLE_RISK_GUARD", "true").lower() in ("true", "1", "yes")
    MAX_DAILY_LOSS_PCT: float = float(os.getenv("MAX_DAILY_LOSS_PCT", "3.0"))
    MAX_CONSECUTIVE_LOSSES: int = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "4"))
    
    # Optional Proxy (for static IP routing on Render/VPS)
    STATIC_PROXY_URL: str = os.getenv("STATIC_PROXY_URL", "").strip()

    @classmethod
    def get_base_url(cls) -> str:
        if cls.DELTA_ENVIRONMENT == "india":
            return cls.INDIA_BASE_URL
        return cls.GLOBAL_BASE_URL

    @classmethod
    def get_symbol_profile(cls, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Returns dynamic leverage and order size for the specified symbol."""
        sym = (symbol or cls.TRADING_SYMBOL).strip().upper()
        if sym in cls.SYMBOL_PROFILES:
            return cls.SYMBOL_PROFILES[sym]
        return {"leverage": cls.LEVERAGE, "order_size": cls.ORDER_SIZE}

config = BotConfig()
