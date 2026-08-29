import os
from typing import Literal
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
    
    # Trade execution defaults
    TRADING_SYMBOL: str = os.getenv("TRADING_SYMBOL", "ETHUSD").strip().upper()
    ORDER_SIZE: int = int(os.getenv("ORDER_SIZE", "1"))
    LEVERAGE: int = int(os.getenv("LEVERAGE", "100"))
    ORDER_TYPE: str = os.getenv("ORDER_TYPE", "market_order").strip()
    
    # Strategy parameters
    ENTRY_EMA_LENGTH: int = int(os.getenv("ENTRY_EMA_LENGTH", "21"))
    ENABLE_SMART_EXIT: bool = os.getenv("ENABLE_SMART_EXIT", "true").lower() in ("true", "1", "yes")
    EXIT_ON_OPPOSITE: bool = os.getenv("EXIT_ON_OPPOSITE", "true").lower() in ("true", "1", "yes")
    EXIT_CONFIRMATIONS: int = int(os.getenv("EXIT_CONFIRMATIONS", "2"))
    EXIT_EMA_LENGTH: int = int(os.getenv("EXIT_EMA_LENGTH", "21"))
    RSI_LENGTH: int = int(os.getenv("RSI_LENGTH", "14"))
    ATR_LENGTH: int = int(os.getenv("ATR_LENGTH", "14"))
    
    # Entry Refinements (Option A: Strict 21 EMA Cut Breakout ONLY)
    ENABLE_LIVE_ENTRIES: bool = os.getenv("ENABLE_LIVE_ENTRIES", "true").lower() in ("true", "1", "yes")
    ENABLE_TREND_CONTINUATION: bool = os.getenv("ENABLE_TREND_CONTINUATION", "false").lower() in ("true", "1", "yes")
    
    # 100x Capital Protection & Zero-Loss Auto-Breakeven (9% ROI Initial Lock)
    ENABLE_BREAKEVEN: bool = os.getenv("ENABLE_BREAKEVEN", "true").lower() in ("true", "1", "yes")
    BREAKEVEN_ATR: float = float(os.getenv("BREAKEVEN_ATR", "0.24"))
    FEE_BUFFER_USD: float = float(os.getenv("FEE_BUFFER_USD", "0.5"))
    
    # 100x Profit Protection & Real-time Trailing Stop
    ENABLE_PROTECTION: bool = os.getenv("ENABLE_PROTECTION", "true").lower() in ("true", "1", "yes")
    ENABLE_INTRA_CANDLE_EXIT: bool = os.getenv("ENABLE_INTRA_CANDLE_EXIT", "true").lower() in ("true", "1", "yes")
    ACTIVATION_ATR: float = float(os.getenv("ACTIVATION_ATR", "0.50"))
    TRAIL_ATR: float = float(os.getenv("TRAIL_ATR", "0.35"))
    TAKE_PROFIT_ATR: float = float(os.getenv("TAKE_PROFIT_ATR", "0.0"))
    
    # 100x Emergency Stop (Strictly placed at 0.45 ATR, $10 before the 0.75% liquidation threshold)
    ENABLE_EMERGENCY: bool = os.getenv("ENABLE_EMERGENCY", "true").lower() in ("true", "1", "yes")
    EMERGENCY_ATR: float = float(os.getenv("EMERGENCY_ATR", "0.45"))
    
    # Standalone Bot Polling
    TIMEFRAME: str = os.getenv("TIMEFRAME", "5m")
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "1"))
    
    # Optional Proxy (for static IP routing on Render)
    STATIC_PROXY_URL: str = os.getenv("STATIC_PROXY_URL", "").strip()

    @classmethod
    def get_base_url(cls) -> str:
        if cls.DELTA_ENVIRONMENT == "india":
            return cls.INDIA_BASE_URL
        return cls.GLOBAL_BASE_URL

config = BotConfig()
