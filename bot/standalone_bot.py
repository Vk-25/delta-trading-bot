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

TRADE_FEE_PER_ORDER = 0.0144  # Baseline fee
TRADE_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "trade_history.json")

global_bot_instance: Optional['StandaloneBot'] = None
recent_standalone_logs: List[Dict[str, Any]] = []
completed_trades: List[Dict[str, Any]] = []
active_trade_tracker: Dict[str, Any] = {}


class RiskGuard:
    """
    Daily Drawdown Kill-Switch — prevents catastrophic losses.
    Stops all trading after:
      - Daily loss exceeds MAX_DAILY_LOSS_PCT of account
      - MAX_CONSECUTIVE_LOSSES consecutive losing trades
    Resets daily at midnight UTC.
    """
    def __init__(self, max_daily_loss_pct: float = 3.0, max_consecutive_losses: int = 4):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.daily_pnl: float = 0.0
        self.consecutive_losses: int = 0
        self.trading_enabled: bool = True
        self._last_reset_date: Optional[str] = None

    def record_trade(self, pnl_pct: float):
        """Records a completed trade PnL and checks kill-switch conditions."""
        self.daily_pnl += pnl_pct
        if pnl_pct < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        if self.daily_pnl <= -self.max_daily_loss_pct:
            self.trading_enabled = False
            logger.warning(
                f"[RISK GUARD] Daily loss {self.daily_pnl:.2f}% exceeds -{self.max_daily_loss_pct}% limit -> TRADING DISABLED"
            )
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.trading_enabled = False
            logger.warning(
                f"[RISK GUARD] {self.consecutive_losses} consecutive losses -> TRADING DISABLED"
            )

    def can_trade(self) -> bool:
        """Returns True if trading is allowed, auto-resets at midnight UTC."""
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        if self._last_reset_date != today:
            self.daily_pnl = 0.0
            self.consecutive_losses = 0
            self.trading_enabled = True
            self._last_reset_date = today
            logger.info("[RISK GUARD] Daily reset — trading re-enabled")
        return self.trading_enabled

    def get_status(self) -> Dict[str, Any]:
        return {
            "trading_enabled": self.trading_enabled,
            "daily_pnl_pct": round(self.daily_pnl, 2),
            "consecutive_losses": self.consecutive_losses,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_consecutive_losses": self.max_consecutive_losses,
        }


# Global risk guard instance
risk_guard: Optional[RiskGuard] = None

def load_trade_history():
    """Loads historical completed trades from local persistent storage."""
    global completed_trades
    try:
        if os.path.exists(TRADE_HISTORY_FILE):
            with open(TRADE_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    completed_trades = data
                    logger.info(f"Loaded {len(completed_trades)} historical trades from {TRADE_HISTORY_FILE}")
    except Exception as e:
        logger.warning(f"Failed to load trade history from {TRADE_HISTORY_FILE}: {e}")

def save_trade_history():
    """Saves historical completed trades to local persistent storage."""
    try:
        os.makedirs(os.path.dirname(TRADE_HISTORY_FILE), exist_ok=True)
        with open(TRADE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(completed_trades[:300], f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save trade history to {TRADE_HISTORY_FILE}: {e}")

# Load trade history at startup
load_trade_history()

def get_current_contract_value() -> float:
    """Helper to get the contract value multiplier."""
    if global_bot_instance and hasattr(global_bot_instance, "client"):
        return global_bot_instance.client.get_contract_value(config.TRADING_SYMBOL)
    sym = config.TRADING_SYMBOL.strip().upper()
    if "ETH" in sym:
        return 0.01
    elif "BTC" in sym:
        return 0.001
    elif "SOL" in sym:
        return 1.0
    elif "XAUT" in sym:
        return 0.001
    return 0.01

def calculate_order_fee(price: float, size: float, contract_val: float, taker_rate: float = 0.0005) -> float:
    """Exact Delta Exchange taker fee: Price * Size * Contract_Value * 0.05%."""
    if price <= 0 or size <= 0 or contract_val <= 0:
        return 0.0
    notional = price * size * contract_val
    return round(notional * taker_rate, 4)

def log_trade_entry(action: str, reason: str, entry_price: float, stop_loss: Optional[float] = None, size: int = 1):
    global active_trade_tracker
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    contract_val = get_current_contract_value()
    est_fee = calculate_order_fee(entry_price, size, contract_val)
    active_trade_tracker = {
        "action": action,
        "entry_time": now_ist.strftime("%H:%M:%S IST"),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "size": size,
        "fee": est_fee
    }
    event = {
        "time": now_ist.strftime("%H:%M:%S IST"),
        "action": action,
        "reason": reason,
        "price": entry_price,
        "stop_loss": stop_loss,
        "gross_pnl": 0.0,
        "fee": est_fee,
        "net_pnl": -est_fee,
        "net_pnl_inr": round(-est_fee * 87.5, 2),
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
    contract_val = get_current_contract_value()
    
    if "LONG" in action or side == "BUY":
        price_diff = exit_price - entry_p
    else:
        price_diff = entry_p - exit_price
        
    gross_pnl = round(price_diff * size * contract_val, 4)
    entry_fee = active_trade_tracker.get("fee") or calculate_order_fee(entry_p, size, contract_val)
    exit_fee = calculate_order_fee(exit_price, size, contract_val)
    total_fee = round(entry_fee + exit_fee, 4)
    net_pnl = round(gross_pnl - total_fee, 4)
    net_pnl_inr = round(net_pnl * 87.5, 2)
    is_profit = net_pnl > 0
    
    trade_record = {
        "entry_time": active_trade_tracker.get("entry_time", "--"),
        "exit_time": now_ist.strftime("%H:%M:%S IST"),
        "date": now_ist.strftime("%Y-%m-%d"),
        "symbol": config.TRADING_SYMBOL,
        "side": side,
        "entry_price": entry_p,
        "exit_price": exit_price,
        "size": size,
        "points": round(price_diff, 2),
        "gross_pnl": gross_pnl,
        "fees": total_fee,
        "net_pnl": net_pnl,
        "net_pnl_inr": net_pnl_inr,
        "exit_reason": reason,
        "win": is_profit
    }
    
    completed_trades.insert(0, trade_record)
    save_trade_history()
    
    # Record trade with Risk Guard
    if risk_guard is not None:
        pnl_pct = (price_diff / entry_p) * 100.0 if entry_p > 0 else 0.0
        risk_guard.record_trade(pnl_pct)

    event = {
        "time": now_ist.strftime("%H:%M:%S IST"),
        "action": action,
        "reason": reason,
        "price": exit_price,
        "stop_loss": None,
        "gross_pnl": gross_pnl,
        "fee": total_fee,
        "net_pnl": net_pnl,
        "net_pnl_inr": net_pnl_inr,
        "status": "CLOSED"
    }
    recent_standalone_logs.insert(0, event)
    if len(recent_standalone_logs) > 50:
        recent_standalone_logs.pop()
        
    active_trade_tracker = {}

def log_standalone_event(action: str, reason: str, price: float, stop_loss: Optional[float] = None):
    if action in ("BUY", "SELL"):
        log_trade_entry(action, reason, price, stop_loss)
    elif action in ("EXIT_LONG", "EXIT_SHORT"):
        log_trade_exit(action, reason, price)

def get_performance_stats() -> Dict[str, Any]:
    empty = {
        "total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
        "total_net_pnl": 0.0, "total_fees": 0.0, "winning_trades": 0,
        "losing_trades": 0, "daily_pnl": 0.0, "today_trades": 0,
        "avg_win": 0.0, "avg_loss": 0.0, "best_trade": 0.0,
        "worst_trade": 0.0, "max_streak_win": 0, "max_streak_loss": 0
    }
    if not completed_trades:
        return empty
    
    total_trades = len(completed_trades)
    winning_trades = sum(1 for t in completed_trades if t.get("win", False))
    losing_trades = total_trades - winning_trades
    win_rate = round((winning_trades / total_trades) * 100, 1) if total_trades > 0 else 0.0
    
    total_net_pnl = round(sum(t.get("net_pnl", 0.0) for t in completed_trades), 2)
    total_fees = round(sum(t.get("fees", 0.0) for t in completed_trades), 2)
    
    win_pnls = [t.get("net_pnl", 0.0) for t in completed_trades if t.get("net_pnl", 0.0) > 0]
    loss_pnls = [t.get("net_pnl", 0.0) for t in completed_trades if t.get("net_pnl", 0.0) < 0]
    
    gross_profits = sum(win_pnls)
    gross_losses = abs(sum(loss_pnls))
    profit_factor = round(gross_profits / gross_losses, 2) if gross_losses > 0 else (99.9 if gross_profits > 0 else 0.0)
    
    avg_win = round(sum(win_pnls) / len(win_pnls), 4) if win_pnls else 0.0
    avg_loss = round(sum(loss_pnls) / len(loss_pnls), 4) if loss_pnls else 0.0
    
    all_pnls = [t.get("net_pnl", 0.0) for t in completed_trades]
    best_trade = round(max(all_pnls), 4) if all_pnls else 0.0
    worst_trade = round(min(all_pnls), 4) if all_pnls else 0.0
    
    # Calculate max win/loss streaks (completed_trades is newest-first, reverse for chronological)
    max_streak_win = 0
    max_streak_loss = 0
    current_win = 0
    current_loss = 0
    for t in reversed(completed_trades):
        if t.get("win", False):
            current_win += 1
            current_loss = 0
            max_streak_win = max(max_streak_win, current_win)
        else:
            current_loss += 1
            current_win = 0
            max_streak_loss = max(max_streak_loss, current_loss)
    
    today_str = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
    today_trades_list = [t for t in completed_trades if t.get("date") == today_str]
    daily_pnl = round(sum(t.get("net_pnl", 0.0) for t in today_trades_list), 2)
    today_trades = len(today_trades_list)
    
    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_net_pnl": total_net_pnl,
        "total_fees": total_fees,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "daily_pnl": daily_pnl,
        "today_trades": today_trades,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "max_streak_win": max_streak_win,
        "max_streak_loss": max_streak_loss
    }

class RenderHealthHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _build_dashboard_payload(self) -> dict:
        """Builds the complete dashboard API response with all real data."""
        rg_status = risk_guard.get_status() if risk_guard else {
            "trading_enabled": True, "daily_pnl_pct": 0.0,
            "consecutive_losses": 0, "max_daily_loss_pct": 3.0,
            "max_consecutive_losses": 4
        }
        pos_info = {"size": 0, "entry_price": 0.0, "unrealized_pnl": 0.0, "liquidation_price": 0.0}
        wallet_info = {"balance": 0.0, "available_balance": 0.0}
        open_orders_list = []
        exchange_fills_list = []
        contract_val = 0.01

        bot = global_bot_instance
        if bot:
            try:
                # Wallet balances (real from Delta API)
                wallets = bot.client.get_balances()
                for w in wallets:
                    if w.get("asset_symbol") in ("USDT", "USD"):
                        wallet_info = {
                            "balance": float(w.get("balance") or 0.0),
                            "available_balance": float(w.get("available_balance") or 0.0)
                        }
                        break
            except Exception as e:
                logger.warning(f"Error fetching wallet: {e}")

            try:
                # Position (real from Delta API)
                pos = bot.client.get_position_for_symbol(bot.symbol)
                if pos:
                    pos_info = {
                        "size": float(pos.get("size", 0)),
                        "entry_price": float(pos.get("entry_price") or 0.0),
                        "unrealized_pnl": float(pos.get("unrealized_pnl") or 0.0),
                        "liquidation_price": float(pos.get("liquidation_price") or 0.0)
                    }
            except Exception as e:
                logger.warning(f"Error fetching position: {e}")

            try:
                # Contract value (real from Delta API)
                contract_val = bot.client.get_contract_value(bot.symbol)
            except Exception:
                contract_val = get_current_contract_value()

            try:
                # Open orders (real from Delta API)
                orders = bot.client.get_open_orders(bot.symbol)
                if isinstance(orders, list):
                    open_orders_list = [{
                        "id": str(o.get("id", "")),
                        "order_type": o.get("order_type", "unknown"),
                        "side": o.get("side", ""),
                        "stop_price": float(o.get("stop_price") or 0.0),
                        "limit_price": float(o.get("limit_price") or o.get("price") or 0.0),
                        "size": int(o.get("size") or 0),
                        "state": o.get("state", "open")
                    } for o in orders]
            except Exception as e:
                logger.warning(f"Error fetching open orders: {e}")

            try:
                # Exchange fills (real from Delta API)
                fills = bot.client.get_fills(bot.symbol, limit=50)
                if isinstance(fills, list):
                    exchange_fills_list = [{
                        "id": str(f.get("id", "")),
                        "created_at": f.get("created_at", ""),
                        "side": f.get("side", ""),
                        "price": str(f.get("fill_price") or f.get("price", "0")),
                        "size": int(f.get("size") or 0),
                        "fee": str(f.get("commission") or f.get("fee", "0")),
                        "role": f.get("role", "taker"),
                        "symbol": bot.symbol
                    } for f in fills]
            except Exception as e:
                logger.warning(f"Error fetching fills: {e}")

        # Strategy engine state
        strategy_state = {
            "position_state": 0,
            "entry_price": None,
            "initial_stop_loss": None,
            "active_trailing_stop": None,
            "highest_price": None,
            "lowest_price": None,
            "contract_value": contract_val
        }
        if bot:
            strategy_state = {
                "position_state": bot.strategy.position_state,
                "entry_price": bot.strategy.entry_price,
                "initial_stop_loss": bot.strategy.initial_stop_loss,
                "active_trailing_stop": bot.strategy.active_trailing_stop,
                "highest_price": bot.strategy.highest_price,
                "lowest_price": bot.strategy.lowest_price,
                "contract_value": contract_val
            }

        now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)

        return {
            # Identity
            "environment": config.DELTA_ENVIRONMENT.upper(),
            "symbol": bot.symbol if bot else config.TRADING_SYMBOL,
            "timeframe": bot.timeframe if bot else config.TIMEFRAME,
            "leverage": getattr(bot, "leverage", config.LEVERAGE) if bot else config.LEVERAGE,
            "strategy_name": "21 EMA Cut Breakout",
            "trailing_ratio": "1:3",
            # Real data
            "wallet": wallet_info,
            "position": pos_info,
            "strategy": strategy_state,
            "open_orders": open_orders_list,
            "exchange_fills": exchange_fills_list[:50],
            # Computed stats
            "stats": get_performance_stats(),
            "risk_guard": rg_status,
            # Activity logs
            "recent_logs": recent_standalone_logs[:20],
            "completed_trades": completed_trades[:50],
            # Server time
            "server_time": now_ist.strftime("%Y-%m-%dT%H:%M:%S+05:30")
        }

    def do_GET(self):
        if self.path in ("/", "/dashboard"):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
        elif self.path == "/healthz":
            self._send_json({"status": "ok", "time": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        elif self.path in ("/api/dashboard", "/api/status"):
            self._send_json(self._build_dashboard_payload())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/emergency_close":
            bot = global_bot_instance
            if not bot:
                self._send_json({"success": False, "message": "Bot not initialized"}, 503)
                return
            try:
                logger.warning("[EMERGENCY CLOSE] Manual emergency close triggered from dashboard!")
                bot.client.close_position(bot.symbol)
                bot.client.cancel_all_orders(bot.symbol)
                bot.strategy.reset_state()
                bot.last_exchange_stop_price = None
                log_standalone_event("EXIT_LONG", "EmergencyClose(Dashboard)", 0.0)
                self._send_json({"success": True, "message": "Position closed and orders cancelled"})
            except Exception as e:
                logger.error(f"[EMERGENCY CLOSE] Failed: {e}")
                self._send_json({"success": False, "message": str(e)}, 500)
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
    and executes orders directly with 1:3 trailing profit management.
    """
    def __init__(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        global global_bot_instance, risk_guard
        global_bot_instance = self
        self.symbol = (symbol or config.TRADING_SYMBOL).strip().upper()
        self.timeframe = timeframe or config.TIMEFRAME
        self.poll_interval = config.POLL_INTERVAL_SECONDS
        
        # Resolve dynamic symbol profile (ETHUSD 130x, XAUTUSD 60x)
        profile = config.get_symbol_profile(self.symbol)
        self.leverage = profile.get("leverage", config.LEVERAGE)
        self.order_size = profile.get("order_size", config.ORDER_SIZE)

        self.client = DeltaExchangeClient()
        self.strategy = StrategyEngine(
            entry_ema_length=config.ENTRY_EMA_LENGTH,
            fast_ema_length=config.FAST_EMA_LENGTH,
            trail_move_unit=config.TRAIL_MOVE_UNIT,
            trail_step_unit=config.TRAIL_STEP_UNIT,
            trail_profit_ratio=config.TRAIL_PROFIT_RATIO,
            exit_on_opposite=config.EXIT_ON_OPPOSITE,
            fee_buffer=config.FEE_BUFFER_USD,
        )
        self.last_processed_timestamp: Optional[int] = None
        self.last_entry_candle_timestamp: Optional[int] = None
        self.last_exchange_stop_price: Optional[float] = None

        # Initialize Risk Guard
        if config.ENABLE_RISK_GUARD:
            risk_guard = RiskGuard(
                max_daily_loss_pct=config.MAX_DAILY_LOSS_PCT,
                max_consecutive_losses=config.MAX_CONSECUTIVE_LOSSES,
            )
            logger.info(
                f"[RISK GUARD] Initialized: Max daily loss {config.MAX_DAILY_LOSS_PCT}%, "
                f"Max consecutive losses {config.MAX_CONSECUTIVE_LOSSES}"
            )

    def fetch_ohlcv_dataframe(self) -> Optional[pd.DataFrame]:
        """Fetches candles from Delta Exchange and converts to pandas DataFrame."""
        candles_res = self.client.get_candles(self.symbol, resolution=self.timeframe, limit=350)
        result = candles_res.get("result", {})
        
        if not result or "t" not in result or len(result["t"]) == 0:
            logger.warning(f"No candle data returned for {self.symbol} ({self.timeframe})")
            return None

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

    def sync_exchange_trailing_stop(self, live_price: Optional[float] = None):
        """Updates the real Stop-Loss order on Delta Exchange as the 1:3 trailing stop moves."""
        if self.strategy.position_state == 1 and self.strategy.active_trailing_stop:
            new_sl = round(self.strategy.active_trailing_stop, 2)
            if live_price is not None and new_sl >= (live_price - 0.10):
                return

            if self.last_exchange_stop_price is None or (new_sl - self.last_exchange_stop_price) >= 0.20:
                logger.info(f"[UPDATING DELTA STOP] Moving real Long Stop-Loss on Delta to {new_sl:.2f}")
                self.client.cancel_all_orders(self.symbol)
                res = self.client.place_stop_order(self.symbol, self.order_size, "sell", stop_price=new_sl)
                if res.get("success"):
                    self.last_exchange_stop_price = new_sl

        elif self.strategy.position_state == -1 and self.strategy.active_trailing_stop:
            new_sl = round(self.strategy.active_trailing_stop, 2)
            if live_price is not None and new_sl <= (live_price + 0.10):
                return

            if self.last_exchange_stop_price is None or (self.last_exchange_stop_price - new_sl) >= 0.20:
                logger.info(f"[UPDATING DELTA STOP] Moving real Short Stop-Loss on Delta to {new_sl:.2f}")
                self.client.cancel_all_orders(self.symbol)
                res = self.client.place_stop_order(self.symbol, self.order_size, "buy", stop_price=new_sl)
                if res.get("success"):
                    self.last_exchange_stop_price = new_sl

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

            logger.info(f"Placing BUY order for {self.order_size} contracts on {self.symbol} ({self.leverage}x)...")
            res = self.client.place_order(
                symbol=self.symbol,
                size=self.order_size,
                side="buy",
                order_type=config.ORDER_TYPE
            )
            if res.get("success"):
                entry_p = float(
                    res.get("result", {}).get("avg_fill_price") or
                    res.get("result", {}).get("average_fill_price") or
                    res.get("result", {}).get("price") or
                    signal.price or
                    0.0
                )
                explicit_sl = signal.metrics.get("stop_loss") or signal.metrics.get("prev_low") or (entry_p - 4.0)
                initial_sl = round(float(explicit_sl), 2)
                
                self.strategy.sync_position(self.order_size, entry_p if entry_p > 0 else None, stop_loss=initial_sl)
                logger.info(f"[DELTA STOP PLACED] Submitting Stop-Loss at EMA Cut Low ({initial_sl:.2f}) on Delta...")
                self.client.cancel_all_orders(self.symbol)
                self.client.place_stop_order(self.symbol, self.order_size, "sell", stop_price=initial_sl)
                self.last_exchange_stop_price = initial_sl
                log_standalone_event("BUY", signal.reason, entry_p, initial_sl)
            else:
                logger.error(f"BUY order failed to execute on Delta Exchange: {res.get('error')}")
                self.strategy.reset_state()

        elif action == "SELL":
            if existing_size > 0:
                logger.info(f"Closing existing LONG position ({existing_size}) before SELL...")
                self.client.close_position(self.symbol)

            logger.info(f"Placing SELL order for {self.order_size} contracts on {self.symbol} ({self.leverage}x)...")
            res = self.client.place_order(
                symbol=self.symbol,
                size=self.order_size,
                side="sell",
                order_type=config.ORDER_TYPE
            )
            if res.get("success"):
                entry_p = float(
                    res.get("result", {}).get("avg_fill_price") or
                    res.get("result", {}).get("average_fill_price") or
                    res.get("result", {}).get("price") or
                    signal.price or
                    0.0
                )
                explicit_sl = signal.metrics.get("stop_loss") or signal.metrics.get("prev_high") or (entry_p + 4.0)
                initial_sl = round(float(explicit_sl), 2)

                self.strategy.sync_position(-self.order_size, entry_p if entry_p > 0 else None, stop_loss=initial_sl)
                logger.info(f"[DELTA STOP PLACED] Submitting Stop-Loss at EMA Cut High ({initial_sl:.2f}) on Delta...")
                self.client.cancel_all_orders(self.symbol)
                self.client.place_stop_order(self.symbol, self.order_size, "buy", stop_price=initial_sl)
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
        if df is None or len(df) < 25:
            return

        # 1. REAL-TIME INTRA-CANDLE EXIT & 1:3 TRAILING STOP SYNC
        if self.strategy.position_state != 0:
            live_price = float(df["close"].iloc[-1])
            rt_signal = self.strategy.check_realtime_exit(live_price)
            if rt_signal and rt_signal.action != "NONE":
                logger.info(f"[1:3 TRAILING EXIT] {rt_signal.action} -> {rt_signal.reason} (Price: {live_price:.2f})")
                self.execute_signal(rt_signal)
                return
            else:
                self.sync_exchange_trailing_stop(live_price=live_price)

        # 2. REAL-TIME LIVE ENTRY CHECK (Strictly 1 Entry Per 5m Candle on High/Low Break)
        if risk_guard is not None and not risk_guard.can_trade():
            if self.strategy.position_state == 0:
                return

        if self.strategy.position_state == 0:
            if self.last_exchange_stop_price is not None:
                self.client.cancel_all_orders(self.symbol)
                self.last_exchange_stop_price = None

            curr_candle_ts = int(df["timestamp"].iloc[-1].timestamp())
            if self.last_entry_candle_timestamp != curr_candle_ts:
                live_entry_sig = self.strategy.get_live_signal(df)
                if live_entry_sig and live_entry_sig.action in ("BUY", "SELL"):
                    logger.info(f"[21 EMA CUT ENTRY] {live_entry_sig.action} -> {live_entry_sig.reason} (Price: {live_entry_sig.price:.2f})")
                    self.last_entry_candle_timestamp = curr_candle_ts
                    self.execute_signal(live_entry_sig)
                    return

        # 3. CONFIRMED CANDLE CLOSE STRATEGY EVALUATION
        confirmed_df = df.iloc[:-1].copy()
        latest_timestamp = int(confirmed_df["timestamp"].iloc[-1].timestamp())

        if self.last_processed_timestamp == latest_timestamp:
            return

        self.last_processed_timestamp = latest_timestamp
        candle_time = confirmed_df["timestamp"].iloc[-1]
        candle_ist = candle_time + pd.Timedelta(hours=5, minutes=30)
        close_price = confirmed_df["close"].iloc[-1]

        signal = self.strategy.get_latest_signal(confirmed_df)

        logger.info(
            f"Candle Closed [{candle_ist.strftime('%Y-%m-%d %H:%M:%S IST')}] | Close: {close_price:.2f} | "
            f"EMA21: {signal.metrics.get('ema21', 0):.2f} | EMA9: {signal.metrics.get('ema9', 0):.2f} | "
            f"State: {signal.position_state} | Signal: {signal.action}"
        )

        if signal.action != "NONE":
            if signal.action in ("BUY", "SELL") and risk_guard is not None and not risk_guard.can_trade():
                logger.warning(f"[RISK GUARD] Blocked {signal.action} — daily limit reached")
            else:
                self.execute_signal(signal)

    def start(self):
        """Starts the infinite polling loop."""
        logger.info(f"Starting Standalone Bot for {self.symbol} on {self.timeframe} (Leverage: {self.leverage}x, Size: {self.order_size} Lot, Delta Env: {config.DELTA_ENVIRONMENT})...")
        
        # Bind to Render HTTP port if running as a Web Service
        render_port = os.getenv("PORT")
        if render_port:
            try:
                t = threading.Thread(target=start_render_health_server, args=(int(render_port),), daemon=True)
                t.start()
            except Exception as e:
                logger.warning(f"Could not start background health thread: {e}")

        # Set leverage
        try:
            self.client.set_leverage(self.symbol, self.leverage)
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
