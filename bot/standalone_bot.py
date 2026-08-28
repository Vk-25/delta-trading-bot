import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pandas as pd
from typing import Optional
from bot.config import config
from bot.delta_client import DeltaExchangeClient
from bot.strategy_engine import StrategyEngine, SignalResult
from bot.utils import logger

class RenderHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"healthy","service":"Delta Standalone Bot","state":"active"}')
        
    def log_message(self, format, *args):
        pass  # Suppress noisy healthcheck logs

def start_render_health_server(port: int):
    try:
        server = HTTPServer(("0.0.0.0", port), RenderHealthHandler)
        logger.info(f"Render Web Service port bound successfully on 0.0.0.0:{port}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Could not bind health port {port}: {e}")

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
            enable_breakeven=config.ENABLE_BREAKEVEN,
            breakeven_atr=config.BREAKEVEN_ATR,
            fee_buffer=config.FEE_BUFFER_USD,
            enable_protection=config.ENABLE_PROTECTION,
            activation_atr=config.ACTIVATION_ATR,
            trail_atr=config.TRAIL_ATR,
            take_profit_atr=config.TAKE_PROFIT_ATR,
            enable_emergency=config.ENABLE_EMERGENCY,
            emergency_atr=config.EMERGENCY_ATR,
            enable_live_entries=config.ENABLE_LIVE_ENTRIES,
            enable_trend_continuation=config.ENABLE_TREND_CONTINUATION
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
        """Dispatches orders to Delta Exchange based on signal action."""
        action = signal.action
        logger.info(f"Executing Strategy Signal: [{action}] | Reason: {signal.reason} | Metrics: {signal.metrics}")

        pos = self.client.get_position_for_symbol(self.symbol)
        existing_size = float(pos.get("size", 0)) if pos else 0

        if action == "BUY":
            if existing_size < 0:
                logger.info(f"Closing existing SHORT position ({existing_size}) before BUY...")
                self.client.close_position(self.symbol)

            logger.info(f"Placing BUY order for {config.ORDER_SIZE} contracts on {self.symbol}...")
            res = self.client.place_order(
                symbol=self.symbol,
                size=config.ORDER_SIZE,
                side="buy",
                order_type=config.ORDER_TYPE
            )
            # Sync strategy state with entry price
            entry_p = float(res.get("result", {}).get("avg_fill_price") or signal.metrics.get("current_price") or 0)
            if entry_p > 0:
                self.strategy.sync_position(config.ORDER_SIZE, entry_p)

        elif action == "SELL":
            if existing_size > 0:
                logger.info(f"Closing existing LONG position ({existing_size}) before SELL...")
                self.client.close_position(self.symbol)

            logger.info(f"Placing SELL order for {config.ORDER_SIZE} contracts on {self.symbol}...")
            res = self.client.place_order(
                symbol=self.symbol,
                size=config.ORDER_SIZE,
                side="sell",
                order_type=config.ORDER_TYPE
            )
            entry_p = float(res.get("result", {}).get("avg_fill_price") or signal.metrics.get("current_price") or 0)
            if entry_p > 0:
                self.strategy.sync_position(-config.ORDER_SIZE, entry_p)

        elif action == "EXIT_LONG":
            if existing_size > 0:
                logger.info(f"Exiting LONG position on {self.symbol}...")
                self.client.close_position(self.symbol)
                self.strategy.reset_state()

        elif action == "EXIT_SHORT":
            if existing_size < 0:
                logger.info(f"Exiting SHORT position on {self.symbol}...")
                self.client.close_position(self.symbol)
                self.strategy.reset_state()

    def run_cycle(self):
        """Runs a single evaluation cycle with real-time profit protection & closed-bar entries."""
        df = self.fetch_ohlcv_dataframe()
        if df is None or len(df) < 30:
            return

        # 1. REAL-TIME INTRA-CANDLE EXIT CHECK (Runs every 1-3 seconds without waiting for candle close)
        if config.ENABLE_INTRA_CANDLE_EXIT and self.strategy.position_state != 0:
            live_price = float(df["close"].iloc[-1])
            atr_series = self.strategy.calculate_atr(df, length=config.ATR_LENGTH)
            latest_atr = float(atr_series.iloc[-1]) if not atr_series.empty else 0

            rt_signal = self.strategy.check_realtime_exit(live_price, latest_atr)
            if rt_signal and rt_signal.action != "NONE":
                logger.info(f"[REAL-TIME PROFIT LOCK] {rt_signal.action} -> {rt_signal.reason} (Price: {live_price:.2f})")
                self.execute_signal(rt_signal)
                return

        # 2. REAL-TIME LIVE ENTRY CHECK (Runs every 1-2 seconds when flat - No 60s delay!)
        if config.ENABLE_LIVE_ENTRIES and self.strategy.position_state == 0:
            live_entry_sig = self.strategy.get_live_signal(df)
            if live_entry_sig and live_entry_sig.action in ("BUY", "SELL"):
                logger.info(f"[REAL-TIME LIVE ENTRY] {live_entry_sig.action} -> {live_entry_sig.reason} (Price: {live_entry_sig.price:.2f})")
                self.execute_signal(live_entry_sig)
                return

        # 3. CONFIRMED CANDLE CLOSE STRATEGY EVALUATION (Runs on every completed bar)
        confirmed_df = df.iloc[:-1].copy()
        latest_timestamp = int(confirmed_df["timestamp"].iloc[-1].timestamp())

        # Only process once per confirmed candle close
        if self.last_processed_timestamp == latest_timestamp:
            return

        self.last_processed_timestamp = latest_timestamp
        candle_time = confirmed_df["timestamp"].iloc[-1]
        candle_ist = candle_time + pd.Timedelta(hours=5, minutes=30)
        close_price = confirmed_df["close"].iloc[-1]

        signal = self.strategy.get_latest_signal(confirmed_df)
        
        logger.info(
            f"Candle Closed [{candle_ist.strftime('%Y-%m-%d %H:%M:%S IST')}] | Close: {close_price:.2f} | "
            f"RSI: {signal.metrics.get('rsi', 0):.1f} | ATR: {signal.metrics.get('atr', 0):.2f} | "
            f"State: {signal.position_state} | Signal: {signal.action}"
        )

        if signal.action != "NONE":
            self.execute_signal(signal)

    def start(self):
        """Starts the infinite polling loop."""
        logger.info(f"Starting Standalone Bot for {self.symbol} on {self.timeframe} timeframe (Delta Environment: {config.DELTA_ENVIRONMENT})...")
        
        # Bind to Render HTTP port if running as a Web Service
        render_port = os.getenv("PORT")
        if render_port:
            try:
                t = threading.Thread(target=start_render_health_server, args=(int(render_port),), daemon=True)
                t.start()
            except Exception as e:
                logger.warning(f"Could not start background health thread: {e}")

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
