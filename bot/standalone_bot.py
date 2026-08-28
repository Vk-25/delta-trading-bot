import time
import pandas as pd
from typing import Optional
from bot.config import config
from bot.delta_client import DeltaExchangeClient
from bot.strategy_engine import StrategyEngine, SignalResult
from bot.utils import logger

class StandaloneBot:
    """
    Independent 24/7 background algorithmic runner.
    Fetches live candles from Delta Exchange, computes strategy logic,
    and executes orders directly on candle close.
    """
    def __init__(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        self.symbol = (symbol or config.TRADING_SYMBOL).strip().upper()
        self.timeframe = timeframe or config.TIMEFRAME
        self.poll_interval = config.POLL_INTERVAL_SECONDS
        
        self.client = DeltaExchangeClient()
        self.strategy = StrategyEngine(
            entry_ema_length=config.ENTRY_EMA_LENGTH,
            exit_ema_length=config.EXIT_EMA_LENGTH,
            rsi_length=config.RSI_LENGTH,
            atr_length=config.ATR_LENGTH,
            enable_smart_exit=config.ENABLE_SMART_EXIT,
            exit_on_opposite=config.EXIT_ON_OPPOSITE,
            exit_confirmations=config.EXIT_CONFIRMATIONS,
            enable_protection=config.ENABLE_PROTECTION,
            activation_atr=config.ACTIVATION_ATR,
            trail_atr=config.TRAIL_ATR,
            enable_emergency=config.ENABLE_EMERGENCY,
            emergency_atr=config.EMERGENCY_ATR
        )
        self.last_processed_timestamp: Optional[int] = None

    def fetch_ohlcv_dataframe(self) -> Optional[pd.DataFrame]:
        """Fetches candles from Delta Exchange and converts to pandas DataFrame."""
        candles_res = self.client.get_candles(self.symbol, resolution=self.timeframe, limit=150)
        result = candles_res.get("result", {})
        
        if not result or "t" not in result or len(result["t"]) == 0:
            logger.warning(f"No candle data returned for {self.symbol} ({self.timeframe})")
            return None

        # Delta chart history format: {"t": [...], "o": [...], "h": [...], "l": [...], "c": [...], "v": [...]}
        df = pd.DataFrame({
            "timestamp": result["t"],
            "open": result["o"],
            "high": result["h"],
            "low": result["l"],
            "close": result["c"],
            "volume": result["v"]
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def execute_signal(self, signal: SignalResult):
        """Dispatches orders to Delta Exchange based on strategy signal."""
        action = signal.action
        if action == "NONE":
            return

        logger.info(f"Executing Strategy Signal: [{action}] | Reason: {signal.reason} | Price: {signal.price}")

        # Check existing position on exchange
        existing_pos = self.client.get_position_for_symbol(self.symbol)
        existing_size = float(existing_pos.get("size", 0)) if existing_pos else 0

        if action == "BUY":
            if existing_size < 0:
                logger.info(f"Closing existing SHORT position ({existing_size})...")
                self.client.close_position(self.symbol)

            logger.info(f"Placing BUY order for {config.ORDER_SIZE} contracts on {self.symbol}...")
            self.client.place_order(
                symbol=self.symbol,
                size=config.ORDER_SIZE,
                side="buy",
                order_type=config.ORDER_TYPE
            )

        elif action == "SELL":
            if existing_size > 0:
                logger.info(f"Closing existing LONG position ({existing_size})...")
                self.client.close_position(self.symbol)

            logger.info(f"Placing SELL order for {config.ORDER_SIZE} contracts on {self.symbol}...")
            self.client.place_order(
                symbol=self.symbol,
                size=config.ORDER_SIZE,
                side="sell",
                order_type=config.ORDER_TYPE
            )

        elif action == "EXIT_LONG":
            if existing_size > 0:
                logger.info(f"Exiting LONG position on {self.symbol}...")
                self.client.close_position(self.symbol)

        elif action == "EXIT_SHORT":
            if existing_size < 0:
                logger.info(f"Exiting SHORT position on {self.symbol}...")
                self.client.close_position(self.symbol)

    def run_cycle(self):
        """Runs a single evaluation cycle."""
        df = self.fetch_ohlcv_dataframe()
        if df is None or len(df) < 30:
            return

        # Note: In live markets, the last candle (index -1) is forming/unconfirmed.
        # The confirmed candle is index -2.
        confirmed_df = df.iloc[:-1].copy()
        latest_timestamp = int(confirmed_df["timestamp"].iloc[-1].timestamp())

        # Only process once per confirmed candle close
        if self.last_processed_timestamp == latest_timestamp:
            return

        self.last_processed_timestamp = latest_timestamp
        candle_time = confirmed_df["timestamp"].iloc[-1]
        close_price = confirmed_df["close"].iloc[-1]

        signal = self.strategy.get_latest_signal(confirmed_df)
        
        logger.info(
            f"Candle Closed [{candle_time}] | Close: {close_price:.2f} | "
            f"RSI: {signal.metrics.get('rsi', 0):.1f} | ATR: {signal.metrics.get('atr', 0):.2f} | "
            f"State: {signal.position_state} | Signal: {signal.action}"
        )

        if signal.action != "NONE":
            self.execute_signal(signal)

    def start(self):
        """Starts the infinite polling loop."""
        logger.info(f"Starting Standalone Bot for {self.symbol} on {self.timeframe} timeframe (Delta Environment: {config.DELTA_ENVIRONMENT})...")
        
        # Verify connection and set leverage
        try:
            self.client.set_leverage(self.symbol, config.LEVERAGE)
        except Exception as e:
            logger.warning(f"Could not set initial leverage: {e}")

        while True:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Error in bot execution cycle: {str(e)}")
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    bot = StandaloneBot()
    bot.start()
