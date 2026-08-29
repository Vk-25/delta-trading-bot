import os
import time
import json
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pandas as pd
from typing import Optional, List, Dict, Any
from bot.config import config
from bot.delta_client import DeltaExchangeClient
from bot.strategy_engine import StrategyEngine, SignalResult
from bot.utils import logger
from bot.dashboard import DASHBOARD_HTML

TRADE_FEE_PER_ORDER = 0.0143  # USDT fee per trade

global_bot_instance: Optional['StandaloneBot'] = None
recent_standalone_logs: List[Dict[str, Any]] = []
completed_trades: List[Dict[str, Any]] = []
active_trade_tracker: Dict[str, Any] = {}

def log_trade_entry(action: str, reason: str, entry_price: float, stop_loss: Optional[float] = None, size: int = 1):
    global active_trade_tracker
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    active_trade_tracker = {
        "action": action,
        "entry_time": now_ist.strftime("%H:%M:%S IST"),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "size": size,
        "fee": TRADE_FEE_PER_ORDER
    }
    event = {
        "time": now_ist.strftime("%H:%M:%S IST"),
        "action": action,
        "reason": reason,
        "price": entry_price,
        "stop_loss": stop_loss,
        "gross_pnl": 0.0,
        "fee": TRADE_FEE_PER_ORDER,
        "net_pnl": -TRADE_FEE_PER_ORDER,
        "net_pnl_inr": round(-TRADE_FEE_PER_ORDER * 87.5, 2),
        "status": "OPEN"
    }
    recent_standalone_logs.insert(0, event)
    if len(recent_standalone_logs) > 50:
        recent_standalone_logs.pop()

def log_trade_exit(action: str, reason: str, exit_price: float):
    global active_trade_tracker
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    
    entry_p = active_trade_tracker.get("entry_price") or exit_price
    side = active_trade_tracker.get("action") or ("BUY" if "LONG" in action else "SELL")
    size = active_trade_tracker.get("size") or config.ORDER_SIZE
    
    # Delta ETHUSD Inverse / Point Value: 1 contract = 0.001 ETH
    if "LONG" in action or side == "BUY":
        price_diff = exit_price - entry_p
    else:
        price_diff = entry_p - exit_price
        
    gross_pnl = price_diff * size * 0.001
    total_fee = TRADE_FEE_PER_ORDER
    net_pnl = gross_pnl - total_fee
    net_pnl_inr = net_pnl * 87.5
    is_profit = net_pnl > 0
    
    trade_record = {
        "entry_time": active_trade_tracker.get("entry_time", now_ist.strftime("%H:%M:%S IST")),
        "exit_time": now_ist.strftime("%H:%M:%S IST"),
        "side": side,
        "entry_price": entry_p,
        "exit_price": exit_price,
        "price_diff": round(price_diff, 2),
        "size": size,
        "gross_pnl": round(gross_pnl, 4),
        "fee": total_fee,
        "net_pnl": round(net_pnl, 4),
        "net_pnl_inr": round(net_pnl_inr, 2),
        "is_profit": is_profit,
        "reason": reason
    }
    completed_trades.insert(0, trade_record)
    if len(completed_trades) > 100:
        completed_trades.pop()
        
    event = {
        "time": now_ist.strftime("%H:%M:%S IST"),
        "action": action,
        "reason": reason,
        "price": exit_price,
        "stop_loss": None,
        "gross_pnl": round(gross_pnl, 4),
        "fee": total_fee,
        "net_pnl": round(net_pnl, 4),
        "net_pnl_inr": round(net_pnl_inr, 2),
        "is_profit": is_profit,
        "status": "CLOSED"
    }
    recent_standalone_logs.insert(0, event)
    if len(recent_standalone_logs) > 50:
        recent_standalone_logs.pop()
        
    active_trade_tracker = {}

def get_performance_stats() -> Dict[str, Any]:
    total = len(completed_trades)
    profitable = len([t for t in completed_trades if t.get("is_profit")])
    losses = len([t for t in completed_trades if not t.get("is_profit")])
    win_rate = round((profitable / total * 100), 1) if total > 0 else 0.0
    total_fees = round(total * TRADE_FEE_PER_ORDER, 4)
    total_gross = round(sum(t.get("gross_pnl", 0.0) for t in completed_trades), 4)
    total_net = round(sum(t.get("net_pnl", 0.0) for t in completed_trades), 4)
    total_net_inr = round(total_net * 87.5, 2)
    
    return {
        "total_trades": total,
        "profitable_trades": profitable,
        "loss_trades": losses,
        "win_rate": win_rate,
        "total_fees": total_fees,
        "total_gross_pnl": total_gross,
        "total_net_pnl": total_net,
        "total_net_pnl_inr": total_net_inr
    }

def log_standalone_event(action: str, reason: str, price: float, stop_loss: Optional[float] = None):
    if action in ("BUY", "SELL"):
        log_trade_entry(action, reason, price, stop_loss)
    elif action in ("EXIT_LONG", "EXIT_SHORT", "EMERGENCY_CLOSE"):
        log_trade_exit(action, reason, price)
    else:
        now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
        event = {
            "time": now_ist.strftime("%H:%M:%S IST"),
            "action": action,
            "reason": reason,
            "price": price,
            "stop_loss": stop_loss,
            "gross_pnl": 0.0,
            "fee": 0.0,
            "net_pnl": 0.0,
            "net_pnl_inr": 0.0,
            "status": "INFO"
        }
        recent_standalone_logs.insert(0, event)
        if len(recent_standalone_logs) > 50:
            recent_standalone_logs.pop()

class RenderHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy","service":"Delta Standalone Bot","state":"active"}')
            return

        elif self.path == "/api/dashboard":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            if not global_bot_instance:
                self.wfile.write(json.dumps({"status": "starting"}).encode("utf-8"))
                return

            try:
                bot = global_bot_instance
                # 1. Balances
                balances_res = bot.client.get_wallet_balances()
                available_usd = 0.0
                total_usd = 0.0
                if balances_res.get("success") and isinstance(balances_res.get("result"), list):
                    for b in balances_res["result"]:
                        available_usd += float(b.get("available_balance", 0))
                        total_usd += float(b.get("balance", 0))

                # 2. Position
                pos = bot.client.get_position_for_symbol(bot.symbol) or {}

                # 3. Open orders on Delta
                orders_res = bot.client.get_open_orders(bot.symbol)
                open_orders = orders_res.get("result", []) if isinstance(orders_res.get("result"), list) else []

                # 4. Market indicators
                df = bot.fetch_ohlcv_dataframe()
                market_info = {"price": 0.0, "ema": 0.0, "rsi": 0.0, "atr": 0.0, "slope": "--"}
                if df is not None and len(df) > 25:
                    close_s = df["close"]
                    live_p = float(close_s.iloc[-1])
                    ema_s = close_s.ewm(span=config.ENTRY_EMA_LENGTH, adjust=False).mean()
                    live_ema = float(ema_s.iloc[-1])
                    prev_ema = float(ema_s.iloc[-2])
                    slope_str = "RISING ↗" if live_ema >= prev_ema else "FALLING ↘"

                    rsi_s = bot.strategy.calculate_rsi(close_s, config.RSI_LENGTH)
                    atr_s = bot.strategy.calculate_atr(df, config.ATR_LENGTH)

                    market_info = {
                        "price": live_p,
                        "ema": live_ema,
                        "rsi": float(rsi_s.iloc[-1]) if not rsi_s.empty else 0.0,
                        "atr": float(atr_s.iloc[-1]) if not atr_s.empty else 0.0,
                        "slope": slope_str
                    }

                active_sl = bot.last_exchange_stop_price or 0.0
                if active_sl == 0.0:
                    for o in open_orders:
                        if o.get("stop_price"):
                            active_sl = float(o.get("stop_price"))
                            break

                payload = {
                    "symbol": bot.symbol,
                    "timeframe": bot.timeframe,
                    "leverage": config.LEVERAGE,
                    "balances": {
                        "available_usd": available_usd,
                        "total_usd": total_usd
                    },
                    "position": pos,
                    "open_orders": open_orders,
                    "active_stop_price": active_sl,
                    "breakeven_locked": bot.strategy.breakeven_locked,
                    "market": market_info,
                    "stats": get_performance_stats(),
                    "completed_trades": completed_trades,
                    "recent_logs": recent_standalone_logs
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/emergency_close":
            if global_bot_instance:
                global_bot_instance.client.close_position(global_bot_instance.symbol)
                global_bot_instance.client.cancel_all_orders(global_bot_instance.symbol)
                global_bot_instance.strategy.reset_state()
                global_bot_instance.last_exchange_stop_price = None
                log_standalone_event("EMERGENCY_CLOSE", "Dashboard Button", 0.0)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"success":true,"message":"Position closed and all orders cancelled."}')
            return
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress noisy healthcheck logs

def start_render_health_server(port: int):
    try:
        server = HTTPServer(("0.0.0.0", port), RenderHealthHandler)
        logger.info(f"Render Dashboard & Health server bound on 0.0.0.0:{port}")
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
        global global_bot_instance
        global_bot_instance = self
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
        self.last_entry_candle_timestamp: Optional[int] = None
        self.last_exchange_stop_price: Optional[float] = None

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

    def sync_exchange_trailing_stop(self, current_atr: float, live_price: Optional[float] = None):
        """Updates the real Stop-Loss order on Delta Exchange as the trailing stop moves."""
        if self.strategy.position_state == 1 and self.strategy.long_trail_stop:
            new_sl = round(self.strategy.long_trail_stop, 2)
            # Long stop must be strictly below current market price
            if live_price is not None and new_sl >= (live_price - 0.10):
                return

            if self.last_exchange_stop_price is None or (new_sl - self.last_exchange_stop_price) >= 0.20:
                logger.info(f"🛡️ [UPDATING DELTA STOP] Moving real Long Stop-Loss on Delta to {new_sl:.2f}")
                self.client.cancel_all_orders(self.symbol)
                res = self.client.place_stop_order(self.symbol, config.ORDER_SIZE, "sell", stop_price=new_sl)
                if res.get("success"):
                    self.last_exchange_stop_price = new_sl

        elif self.strategy.position_state == -1 and self.strategy.short_trail_stop:
            new_sl = round(self.strategy.short_trail_stop, 2)
            # Short stop must be strictly above current market price
            if live_price is not None and new_sl <= (live_price + 0.10):
                return

            if self.last_exchange_stop_price is None or (self.last_exchange_stop_price - new_sl) >= 0.20:
                logger.info(f"🛡️ [UPDATING DELTA STOP] Moving real Short Stop-Loss on Delta to {new_sl:.2f}")
                self.client.cancel_all_orders(self.symbol)
                res = self.client.place_stop_order(self.symbol, config.ORDER_SIZE, "buy", stop_price=new_sl)
                if res.get("success"):
                    self.last_exchange_stop_price = new_sl

    def execute_signal(self, signal: SignalResult, current_atr: float = 8.0):
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
            # Only sync position if the order actually succeeded on Delta Exchange
            if res.get("success"):
                entry_p = float(
                    res.get("result", {}).get("avg_fill_price") or
                    res.get("result", {}).get("average_fill_price") or
                    res.get("result", {}).get("price") or
                    signal.price or
                    signal.metrics.get("live_price") or
                    signal.metrics.get("current_price") or
                    0.0
                )
                self.strategy.sync_position(config.ORDER_SIZE, entry_p if entry_p > 0 else None)
                
                # Stop Loss strictly placed at Low of EMA cutting candle (Pinpoint accuracy)
                explicit_sl = signal.metrics.get("stop_loss")
                if explicit_sl is not None and float(explicit_sl) < (entry_p - 0.20):
                    initial_sl = round(float(explicit_sl), 2)
                else:
                    initial_sl = round(entry_p - (current_atr * config.EMERGENCY_ATR if current_atr > 0 else 4.0), 2)

                self.strategy.long_trail_stop = initial_sl
                logger.info(f"🛡️ [DELTA STOP PLACED] Submitting Real Stop-Loss Order at EMA Cut Low ({initial_sl:.2f}) on Delta...")
                self.client.cancel_all_orders(self.symbol)
                self.client.place_stop_order(self.symbol, config.ORDER_SIZE, "sell", stop_price=initial_sl)
                self.last_exchange_stop_price = initial_sl
                log_standalone_event("BUY", signal.reason, entry_p, initial_sl)
            else:
                logger.error(f"BUY order failed to execute on Delta Exchange: {res.get('error')}")
                self.strategy.reset_state()

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
            # Only sync position if the order actually succeeded on Delta Exchange
            if res.get("success"):
                entry_p = float(
                    res.get("result", {}).get("avg_fill_price") or
                    res.get("result", {}).get("average_fill_price") or
                    res.get("result", {}).get("price") or
                    signal.price or
                    signal.metrics.get("live_price") or
                    signal.metrics.get("current_price") or
                    0.0
                )
                self.strategy.sync_position(-config.ORDER_SIZE, entry_p if entry_p > 0 else None)
                
                # Stop Loss strictly placed at High of EMA cutting candle (Pinpoint accuracy)
                explicit_sl = signal.metrics.get("stop_loss")
                if explicit_sl is not None and float(explicit_sl) > (entry_p + 0.20):
                    initial_sl = round(float(explicit_sl), 2)
                else:
                    initial_sl = round(entry_p + (current_atr * config.EMERGENCY_ATR if current_atr > 0 else 4.0), 2)

                self.strategy.short_trail_stop = initial_sl
                logger.info(f"🛡️ [DELTA STOP PLACED] Submitting Real Stop-Loss Order at EMA Cut High ({initial_sl:.2f}) on Delta...")
                self.client.cancel_all_orders(self.symbol)
                self.client.place_stop_order(self.symbol, config.ORDER_SIZE, "buy", stop_price=initial_sl)
                self.last_exchange_stop_price = initial_sl
                log_standalone_event("SELL", signal.reason, entry_p, initial_sl)
            else:
                logger.error(f"SELL order failed to execute on Delta Exchange: {res.get('error')}")
                self.strategy.reset_state()

        elif action == "EXIT_LONG":
            if existing_size > 0:
                logger.info(f"Exiting LONG position on {self.symbol}...")
                self.client.close_position(self.symbol)
            self.client.cancel_all_orders(self.symbol)
            self.strategy.reset_state()
            self.last_exchange_stop_price = None
            log_standalone_event("EXIT_LONG", signal.reason, signal.price)

        elif action == "EXIT_SHORT":
            if existing_size < 0:
                logger.info(f"Exiting SHORT position on {self.symbol}...")
                self.client.close_position(self.symbol)
            self.client.cancel_all_orders(self.symbol)
            self.strategy.reset_state()
            self.last_exchange_stop_price = None
            log_standalone_event("EXIT_SHORT", signal.reason, signal.price)

    def run_cycle(self):
        """Runs a single evaluation cycle with real-time profit protection & closed-bar entries."""
        df = self.fetch_ohlcv_dataframe()
        if df is None or len(df) < 30:
            return

        # 1. REAL-TIME INTRA-CANDLE EXIT & TRAILING STOP SYNC (Runs every 1-2 seconds)
        atr_series = self.strategy.calculate_atr(df, length=config.ATR_LENGTH)
        latest_atr = float(atr_series.iloc[-1]) if not atr_series.empty else 8.0

        if config.ENABLE_INTRA_CANDLE_EXIT and self.strategy.position_state != 0:
            live_price = float(df["close"].iloc[-1])

            rt_signal = self.strategy.check_realtime_exit(live_price, latest_atr)
            if rt_signal and rt_signal.action != "NONE":
                logger.info(f"[REAL-TIME PROFIT LOCK] {rt_signal.action} -> {rt_signal.reason} (Price: {live_price:.2f})")
                self.execute_signal(rt_signal, current_atr=latest_atr)
                return
            else:
                # Keep real stop order on Delta Exchange synced with trailing stop / breakeven
                self.sync_exchange_trailing_stop(latest_atr, live_price=live_price)

        # 2. REAL-TIME LIVE ENTRY CHECK (Runs every 1-2 seconds when flat - Single Entry Per 5m Candle!)
        if config.ENABLE_LIVE_ENTRIES and self.strategy.position_state == 0:
            # Sweep any leftover orders if flat
            if self.last_exchange_stop_price is not None:
                self.client.cancel_all_orders(self.symbol)
                self.last_exchange_stop_price = None

            curr_candle_ts = int(df["timestamp"].iloc[-1].timestamp())
            # Only enter ONCE per 5m candle
            if self.last_entry_candle_timestamp != curr_candle_ts:
                live_entry_sig = self.strategy.get_live_signal(df)
                if live_entry_sig and live_entry_sig.action in ("BUY", "SELL"):
                    logger.info(f"[REAL-TIME LIVE ENTRY] {live_entry_sig.action} -> {live_entry_sig.reason} (Price: {live_entry_sig.price:.2f})")
                    self.last_entry_candle_timestamp = curr_candle_ts
                    self.execute_signal(live_entry_sig, current_atr=latest_atr)
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
            self.execute_signal(signal, current_atr=latest_atr)

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
