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
    TRADING_SYMBOL: str = os.getenv("TRADING_SYMBOL", "BTCUSD").strip().upper()
    ORDER_SIZE: int = int(os.getenv("ORDER_SIZE", "1"))
    LEVERAGE: int = int(os.getenv("LEVERAGE", "10"))
    ORDER_TYPE: str = os.getenv("ORDER_TYPE", "market_order").strip()
    
    # Strategy parameters
    ENTRY_EMA_LENGTH: int = int(os.getenv("ENTRY_EMA_LENGTH", "20"))
    ENABLE_SMART_EXIT: bool = os.getenv("ENABLE_SMART_EXIT", "true").lower() in ("true", "1", "yes")
    EXIT_ON_OPPOSITE: bool = os.getenv("EXIT_ON_OPPOSITE", "true").lower() in ("true", "1", "yes")
    EXIT_CONFIRMATIONS: int = int(os.getenv("EXIT_CONFIRMATIONS", "2"))
    EXIT_EMA_LENGTH: int = int(os.getenv("EXIT_EMA_LENGTH", "20"))
    RSI_LENGTH: int = int(os.getenv("RSI_LENGTH", "14"))
    ATR_LENGTH: int = int(os.getenv("ATR_LENGTH", "14"))
    
    # Profit Protection
    ENABLE_PROTECTION: bool = os.getenv("ENABLE_PROTECTION", "true").lower() in ("true", "1", "yes")
    ACTIVATION_ATR: float = float(os.getenv("ACTIVATION_ATR", "1.0"))
    TRAIL_ATR: float = float(os.getenv("TRAIL_ATR", "1.25"))
    
    # Emergency Exit
    ENABLE_EMERGENCY: bool = os.getenv("ENABLE_EMERGENCY", "true").lower() in ("true", "1", "yes")
    EMERGENCY_ATR: float = float(os.getenv("EMERGENCY_ATR", "2.5"))
    
    # Standalone Bot Polling
    TIMEFRAME: str = os.getenv("TIMEFRAME", "1m")
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "3"))
    
    # Optional Proxy (for static IP routing on Render)
    STATIC_PROXY_URL: str = os.getenv("STATIC_PROXY_URL", "").strip()

    @classmethod
    def get_base_url(cls) -> str:
        if cls.DELTA_ENVIRONMENT == "india":
            return cls.INDIA_BASE_URL
        return cls.GLOBAL_BASE_URL

config = BotConfig()
