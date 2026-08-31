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

def get_current_contract_value(symbol: Optional[str] = None) -> float:
    """Helper to get the contract value multiplier for a specific symbol."""
    sym = (symbol or config.TRADING_SYMBOL).strip().upper()
    if global_bot_instance and hasattr(global_bot_instance, "client"):
        return global_bot_instance.client.get_contract_value(sym)
    if "ETH" in sym:
        return 0.01
    elif "BTC" in sym:
        return 0.001
    elif "SOL" in sym:
        return 1.0
    elif "XAU" in sym or "XAUT" in sym:
        return 0.001
    return 0.01

def calculate_order_fee(price: float, size: float, contract_val: float, taker_rate: float = 0.0005) -> float:
    """Exact Delta Exchange taker fee: Price * Size * Contract_Value * 0.05%."""
    if price <= 0 or size <= 0 or contract_val <= 0:
        return 0.0
    notional = price * size * contract_val
    return round(notional * taker_rate, 4)

def log_trade_entry(action: str, reason: str, entry_price: float, stop_loss: Optional[float] = None, size: int = 1, symbol: Optional[str] = None):
    global active_trade_tracker
    sym = (symbol or config.TRADING_SYMBOL).strip().upper()
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    contract_val = get_current_contract_value(sym)
    est_fee = calculate_order_fee(entry_price, size, contract_val)
    active_trade_tracker[sym] = {
        "action": action,
        "symbol": sym,
        "entry_time": now_ist.strftime("%H:%M:%S IST"),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "size": size,
        "fee": est_fee
    }
    event = {
        "time": now_ist.strftime("%H:%M:%S IST"),
        "symbol": sym,
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

def log_trade_exit(action: str, reason: str, exit_price: float, symbol: Optional[str] = None):
    global active_trade_tracker
    sym = (symbol or config.TRADING_SYMBOL).strip().upper()
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    
    tracker = active_trade_tracker.get(sym, {})
    entry_p = tracker.get("entry_price") or exit_price
    side = tracker.get("action") or ("BUY" if "LONG" in action else "SELL")
    size = tracker.get("size") or config.ORDER_SIZE
    contract_val = get_current_contract_value(sym)
    
    if "LONG" in action or side == "BUY":
        price_diff = exit_price - entry_p
    else:
        price_diff = entry_p - exit_price
        
    gross_pnl = round(price_diff * size * contract_val, 4)
    entry_fee = tracker.get("fee") or calculate_order_fee(entry_p, size, contract_val)
    exit_fee = calculate_order_fee(exit_price, size, contract_val)
    total_fee = round(entry_fee + exit_fee, 4)
    net_pnl = round(gross_pnl - total_fee, 4)
    net_pnl_inr = round(net_pnl * 87.5, 2)
    is_profit = net_pnl > 0
    
    trade_record = {
        "entry_time": tracker.get("entry_time", "--"),
        "exit_time": now_ist.strftime("%H:%M:%S IST"),
        "date": now_ist.strftime("%Y-%m-%d"),
        "symbol": sym,
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
        "symbol": sym,
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
        
    if sym in active_trade_tracker:
        del active_trade_tracker[sym]

def log_standalone_event(action: str, reason: str, price: float, stop_loss: Optional[float] = None, symbol: Optional[str] = None):
    if action in ("BUY", "SELL"):
        log_trade_entry(action, reason, price, stop_loss, symbol=symbol)
    elif action in ("EXIT_LONG", "EXIT_SHORT"):
        log_trade_exit(action, reason, price, symbol=symbol)

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
        """Builds the complete dashboard API response with multi-symbol real data."""
        rg_status = risk_guard.get_status() if risk_guard else {
            "trading_enabled": True, "daily_pnl_pct": 0.0,
            "consecutive_losses": 0, "max_daily_loss_pct": 3.0,
            "max_consecutive_losses": 4
        }
        wallet_info = {"balance": 0.0, "available_balance": 0.0}
        open_orders_list = []
        exchange_fills_list = []
        symbols_data = []

        bot = global_bot_instance
        active_symbols = bot.symbols if bot else config.TRADING_SYMBOLS

        if bot:
            try:
                # Wallet balances (real from Delta API)
                wallets_res = bot.client.get_wallet_balances()
                wallets = wallets_res.get("result", []) if isinstance(wallets_res, dict) else (wallets_res if isinstance(wallets_res, list) else [])
                for w in wallets:
                    if isinstance(w, dict) and w.get("asset_symbol") in ("USDT", "USD", "INR", "USDC"):
                        wallet_info = {
                            "balance": float(w.get("balance") or 0.0),
                            "available_balance": float(w.get("available_balance") or w.get("balance") or 0.0)
                        }
                        if w.get("asset_symbol") in ("USDT", "USD"):
                            break
            except Exception as e:
                logger.warning(f"Error fetching wallet: {e}")

            # Iterate all active trading symbols
            for sym in active_symbols:
                trader = bot.traders.get(sym)
                pos_info = {"size": 0, "entry_price": 0.0, "unrealized_pnl": 0.0, "liquidation_price": 0.0}
                contract_val = 0.01

                try:
                    pos = bot.client.get_position_for_symbol(sym)
                    if pos:
                        pos_info = {
                            "size": float(pos.get("size", 0)),
                            "entry_price": float(pos.get("entry_price") or 0.0),
                            "unrealized_pnl": float(pos.get("unrealized_pnl") or 0.0),
                            "liquidation_price": float(pos.get("liquidation_price") or 0.0)
                        }
                except Exception as e:
                    logger.warning(f"Error fetching position for {sym}: {e}")

                try:
                    contract_val = bot.client.get_contract_value(sym)
                except Exception:
                    contract_val = get_current_contract_value(sym)

                try:
                    orders = bot.client.get_open_orders(sym)
                    if isinstance(orders, list):
                        for o in orders:
                            open_orders_list.append({
                                "id": str(o.get("id", "")),
                                "symbol": sym,
                                "order_type": o.get("order_type", "unknown"),
                                "side": o.get("side", ""),
                                "stop_price": float(o.get("stop_price") or 0.0),
                                "limit_price": float(o.get("limit_price") or o.get("price") or 0.0),
                                "size": int(o.get("size") or 0),
                                "state": o.get("state", "open")
                            })
                except Exception as e:
                    logger.warning(f"Error fetching open orders for {sym}: {e}")

                try:
                    fills = bot.client.get_fills(sym, limit=25)
                    if isinstance(fills, list):
                        for f in fills:
                            exchange_fills_list.append({
                                "id": str(f.get("id", "")),
                                "created_at": f.get("created_at", ""),
                                "symbol": sym,
                                "side": f.get("side", ""),
                                "price": str(f.get("fill_price") or f.get("price", "0")),
                                "size": int(f.get("size") or 0),
                                "fee": str(f.get("commission") or f.get("fee", "0")),
                                "role": f.get("role", "taker")
                            })
                except Exception as e:
                    logger.warning(f"Error fetching fills for {sym}: {e}")

                strat_info = {
                    "position_state": trader.strategy.position_state if trader else 0,
                    "entry_price": trader.strategy.entry_price if trader else None,
                    "initial_stop_loss": trader.strategy.initial_stop_loss if trader else None,
                    "active_trailing_stop": trader.strategy.active_trailing_stop if trader else None,
                    "highest_price": trader.strategy.highest_price if trader else None,
                    "lowest_price": trader.strategy.lowest_price if trader else None,
                    "contract_value": contract_val
                }

                symbols_data.append({
                    "symbol": sym,
                    "leverage": trader.leverage if trader else config.LEVERAGE,
                    "order_size": trader.order_size if trader else config.ORDER_SIZE,
                    "position": pos_info,
                    "strategy": strat_info
                })

        # Primary symbol telemetry for backward compatibility
        primary_sym = active_symbols[0] if active_symbols else "ETHUSD"
        primary_sym_data = symbols_data[0] if symbols_data else {
            "symbol": primary_sym,
            "leverage": config.LEVERAGE,
            "order_size": config.ORDER_SIZE,
            "position": {"size": 0, "entry_price": 0.0, "unrealized_pnl": 0.0, "liquidation_price": 0.0},
            "strategy": {"position_state": 0, "entry_price": None, "initial_stop_loss": None, "active_trailing_stop": None, "highest_price": None, "lowest_price": None, "contract_value": 0.01}
        }

        now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)

        return {
            # Identity
            "environment": config.DELTA_ENVIRONMENT.upper(),
            "symbol": primary_sym,
            "symbols": active_symbols,
            "symbols_data": symbols_data,
            "timeframe": bot.timeframe if bot else config.TIMEFRAME,
            "leverage": primary_sym_data.get("leverage", config.LEVERAGE),
            "strategy_name": "21 EMA Cut Breakout",
            "trailing_ratio": "1:3",
            # Real data
            "wallet": wallet_info,
            "position": primary_sym_data.get("position", {}),
            "strategy": primary_sym_data.get("strategy", {}),
            "open_orders": open_orders_list,
            "exchange_fills": sorted(exchange_fills_list, key=lambda x: x.get("created_at", ""), reverse=True)[:50],
            # Computed stats
            "stats": get_performance_stats(),
            "risk_guard": rg_status,
            # Activity logs
            "recent_logs": recent_standalone_logs[:25],
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
                for sym, trader in bot.traders.items():
                    try:
                        bot.client.close_position(sym)
                        bot.client.cancel_all_orders(sym)
                        trader.strategy.reset_state()
                        trader.last_exchange_stop_price = None
                        log_standalone_event("EXIT_LONG", "EmergencyClose(Dashboard)", 0.0, symbol=sym)
                    except Exception as e:
                        logger.error(f"[EMERGENCY CLOSE] Failed on {sym}: {e}")
                self._send_json({"success": True, "message": "All positions closed and orders cancelled"})
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

class SymbolTrader:
    """
    Manages isolated 21 EMA cut strategy calculation, 1:3 trailing stops,
    and Delta Exchange order execution for an individual symbol.
    """
    def __init__(self, symbol: str, client: DeltaExchangeClient, timeframe: Optional[str] = None):
        self.symbol = symbol.strip().upper()
        self.client = client
        self.timeframe = timeframe or config.TIMEFRAME
        
        # Dynamic profile (ETHUSD 130x, XAUTUSD 60x, etc.)
        profile = config.get_symbol_profile(self.symbol)
        self.leverage = profile.get("leverage", config.LEVERAGE)
        self.order_size = profile.get("order_size", config.ORDER_SIZE)
        self.current_entry_size: int = self.order_size

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
        active_size = self.current_entry_size or self.order_size
        if self.strategy.position_state == 1 and self.strategy.active_trailing_stop:
            new_sl = round(self.strategy.active_trailing_stop, 2)
            if live_price is not None and new_sl >= (live_price - 0.10):
                return

            if self.last_exchange_stop_price is None or (new_sl - self.last_exchange_stop_price) >= 0.20:
                logger.info(f"[{self.symbol}] Moving real Long Stop-Loss on Delta to {new_sl:.2f} (Size: {active_size} Lots)")
                self.client.cancel_all_orders(self.symbol)
                res = self.client.place_stop_order(self.symbol, active_size, "sell", stop_price=new_sl)
                if res.get("success"):
                    self.last_exchange_stop_price = new_sl

        elif self.strategy.position_state == -1 and self.strategy.active_trailing_stop:
            new_sl = round(self.strategy.active_trailing_stop, 2)
            if live_price is not None and new_sl <= (live_price + 0.10):
                return

            if self.last_exchange_stop_price is None or (self.last_exchange_stop_price - new_sl) >= 0.20:
                logger.info(f"[{self.symbol}] Moving real Short Stop-Loss on Delta to {new_sl:.2f} (Size: {active_size} Lots)")
                self.client.cancel_all_orders(self.symbol)
                res = self.client.place_stop_order(self.symbol, active_size, "buy", stop_price=new_sl)
                if res.get("success"):
                    self.last_exchange_stop_price = new_sl

    def execute_signal(self, signal: SignalResult):
        """Dispatches orders to Delta Exchange based on signal action."""
        action = signal.action
        logger.info(f"[{self.symbol}] Executing Strategy Signal: [{action}] | Reason: {signal.reason} | Metrics: {signal.metrics}")

        pos = self.client.get_position_for_symbol(self.symbol)
        existing_size = float(pos.get("size", 0)) if pos else 0

        # Calculate dynamic lot size for XAUTUSD (up to 3 lots)
        target_size = self.order_size
        if "XAU" in self.symbol and config.ENABLE_DYNAMIC_LOTS:
            dyn_lots = signal.metrics.get("dynamic_lots")
            if dyn_lots and isinstance(dyn_lots, int) and dyn_lots > 0:
                target_size = max(config.MIN_XAUT_LOTS, min(config.MAX_XAUT_LOTS, dyn_lots))
                logger.info(f"[{self.symbol}] ⚡ Dynamic Sizing: Scaled up to {target_size} Lots (Quality Score: {dyn_lots}/3)")
        self.current_entry_size = target_size

        if action == "BUY":
            if existing_size < 0:
                logger.info(f"[{self.symbol}] Closing existing SHORT position ({existing_size}) before BUY...")
                self.client.close_position(self.symbol)

            logger.info(f"[{self.symbol}] Placing BUY order for {target_size} contracts ({self.leverage}x)...")
            res = self.client.place_order(
                symbol=self.symbol,
                size=target_size,
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
                
                self.strategy.sync_position(target_size, entry_p if entry_p > 0 else None, stop_loss=initial_sl)
                logger.info(f"[{self.symbol}] [DELTA STOP PLACED] Stop-Loss at EMA Cut Low ({initial_sl:.2f}) for {target_size} Lots...")
                self.client.cancel_all_orders(self.symbol)
                self.client.place_stop_order(self.symbol, target_size, "sell", stop_price=initial_sl)
                self.last_exchange_stop_price = initial_sl
                log_standalone_event("BUY", signal.reason, entry_p, initial_sl, symbol=self.symbol)
            else:
                logger.error(f"[{self.symbol}] BUY order failed on Delta Exchange: {res.get('error')}")
                self.strategy.reset_state()

        elif action == "SELL":
            if existing_size > 0:
                logger.info(f"[{self.symbol}] Closing existing LONG position ({existing_size}) before SELL...")
                self.client.close_position(self.symbol)

            logger.info(f"[{self.symbol}] Placing SELL order for {target_size} contracts ({self.leverage}x)...")
            res = self.client.place_order(
                symbol=self.symbol,
                size=target_size,
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

                self.strategy.sync_position(-target_size, entry_p if entry_p > 0 else None, stop_loss=initial_sl)
                logger.info(f"[{self.symbol}] [DELTA STOP PLACED] Stop-Loss at EMA Cut High ({initial_sl:.2f}) for {target_size} Lots...")
                self.client.cancel_all_orders(self.symbol)
                self.client.place_stop_order(self.symbol, target_size, "buy", stop_price=initial_sl)
                self.last_exchange_stop_price = initial_sl
                log_standalone_event("SELL", signal.reason, entry_p, initial_sl, symbol=self.symbol)
            else:
                logger.error(f"[{self.symbol}] SELL order failed on Delta Exchange: {res.get('error')}")
                self.strategy.reset_state()

        elif action == "EXIT_LONG":
            if existing_size > 0:
                logger.info(f"[{self.symbol}] Exiting LONG position...")
                self.client.close_position(self.symbol)
            self.client.cancel_all_orders(self.symbol)
            self.strategy.reset_state()
            self.last_exchange_stop_price = None
            log_standalone_event("EXIT_LONG", signal.reason, signal.price, symbol=self.symbol)

        elif action == "EXIT_SHORT":
            if existing_size < 0:
                logger.info(f"[{self.symbol}] Exiting SHORT position...")
                self.client.close_position(self.symbol)
            self.client.cancel_all_orders(self.symbol)
            self.strategy.reset_state()
            self.last_exchange_stop_price = None
            log_standalone_event("EXIT_SHORT", signal.reason, signal.price, symbol=self.symbol)

    def run_cycle(self):
        """Runs a single evaluation cycle for this symbol."""
        df = self.fetch_ohlcv_dataframe()
        if df is None or len(df) < 25:
            return

        # 1. REAL-TIME INTRA-CANDLE EXIT & 1:3 TRAILING STOP SYNC
        if self.strategy.position_state != 0:
            live_price = float(df["close"].iloc[-1])
            rt_signal = self.strategy.check_realtime_exit(live_price)
            if rt_signal and rt_signal.action != "NONE":
                logger.info(f"[{self.symbol}] [1:3 TRAILING EXIT] {rt_signal.action} -> {rt_signal.reason} (Price: {live_price:.2f})")
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
                    logger.info(f"[{self.symbol}] [21 EMA CUT ENTRY] {live_entry_sig.action} -> {live_entry_sig.reason} (Price: {live_entry_sig.price:.2f})")
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
            f"[{self.symbol}] Candle Closed [{candle_ist.strftime('%Y-%m-%d %H:%M:%S IST')}] | Close: {close_price:.2f} | "
            f"EMA21: {signal.metrics.get('ema21', 0):.2f} | EMA9: {signal.metrics.get('ema9', 0):.2f} | "
            f"State: {signal.position_state} | Signal: {signal.action}"
        )

        if signal.action != "NONE":
            if signal.action in ("BUY", "SELL") and risk_guard is not None and not risk_guard.can_trade():
                logger.warning(f"[{self.symbol}] [RISK GUARD] Blocked {signal.action} — daily limit reached")
            else:
                self.execute_signal(signal)

class StandaloneBot:
    """
    Independent 24/7 background algorithmic runner supporting multi-symbol simultaneous trading.
    Monitors ETHUSD (130x), XAUTUSD (60x), etc., computing strategy logic and managing 1:3 trailing stops.
    """
    def __init__(self, symbols: Optional[List[str]] = None, timeframe: Optional[str] = None):
        global global_bot_instance, risk_guard
        global_bot_instance = self
        
        # List of symbols to trade simultaneously
        if symbols:
            self.symbols = [s.strip().upper() for s in symbols]
        else:
            self.symbols = config.TRADING_SYMBOLS

        self.timeframe = timeframe or config.TIMEFRAME
        self.poll_interval = config.POLL_INTERVAL_SECONDS
        self.client = DeltaExchangeClient()

        # Initialize an isolated trader instance for each symbol
        self.traders: Dict[str, SymbolTrader] = {
            sym: SymbolTrader(sym, self.client, self.timeframe) for sym in self.symbols
        }

        # Backward compatibility properties (for single-symbol callers/tests)
        self.symbol = self.symbols[0] if self.symbols else "ETHUSD"
        primary_trader = self.traders.get(self.symbol)
        self.strategy = primary_trader.strategy if primary_trader else None
        self.leverage = primary_trader.leverage if primary_trader else config.LEVERAGE
        self.order_size = primary_trader.order_size if primary_trader else config.ORDER_SIZE

        # Initialize Risk Guard
        if config.ENABLE_RISK_GUARD and risk_guard is None:
            risk_guard = RiskGuard(
                max_daily_loss_pct=config.MAX_DAILY_LOSS_PCT,
                max_consecutive_losses=config.MAX_CONSECUTIVE_LOSSES,
            )
            logger.info(
                f"[RISK GUARD] Initialized: Max daily loss {config.MAX_DAILY_LOSS_PCT}%, "
                f"Max consecutive losses {config.MAX_CONSECUTIVE_LOSSES}"
            )

    @property
    def last_exchange_stop_price(self):
        primary_trader = self.traders.get(self.symbol)
        return primary_trader.last_exchange_stop_price if primary_trader else None

    @last_exchange_stop_price.setter
    def last_exchange_stop_price(self, val):
        primary_trader = self.traders.get(self.symbol)
        if primary_trader:
            primary_trader.last_exchange_stop_price = val

    def fetch_ohlcv_dataframe(self) -> Optional[pd.DataFrame]:
        """Backward compatibility method for primary symbol."""
        primary_trader = self.traders.get(self.symbol)
        return primary_trader.fetch_ohlcv_dataframe() if primary_trader else None

    def sync_exchange_trailing_stop(self, live_price: Optional[float] = None):
        """Backward compatibility method for primary symbol."""
        primary_trader = self.traders.get(self.symbol)
        if primary_trader:
            primary_trader.sync_exchange_trailing_stop(live_price)

    def execute_signal(self, signal: SignalResult):
        """Backward compatibility method for primary symbol."""
        primary_trader = self.traders.get(self.symbol)
        if primary_trader:
            primary_trader.execute_signal(signal)

    def run_cycle(self):
        """Executes one evaluation cycle across ALL configured symbols in parallel."""
        for sym, trader in self.traders.items():
            try:
                trader.run_cycle()
            except Exception as e:
                logger.error(f"Error in cycle for {sym}: {str(e)}")

    def start(self):
        """Starts the infinite multi-symbol polling loop."""
        symbols_str = ", ".join([f"{sym} ({t.leverage}x, {t.order_size} Lot)" for sym, t in self.traders.items()])
        logger.info(f"Starting Multi-Symbol Standalone Bot for [{symbols_str}] on {self.timeframe} (Delta Env: {config.DELTA_ENVIRONMENT})...")
        
        # Bind to Render HTTP port if running as a Web Service
        render_port = os.getenv("PORT")
        if render_port:
            try:
                t = threading.Thread(target=start_render_health_server, args=(int(render_port),), daemon=True)
                t.start()
            except Exception as e:
                logger.warning(f"Could not start background health thread: {e}")

        # Set leverage for all active symbols
        for sym, trader in self.traders.items():
            try:
                self.client.set_leverage(sym, trader.leverage)
                logger.info(f"[{sym}] Leverage successfully set to {trader.leverage}x")
            except Exception as e:
                logger.warning(f"[{sym}] Could not set leverage: {e}")

        while True:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Error in multi-symbol bot execution cycle: {str(e)}")
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    bot = StandaloneBot()
    bot.start()

