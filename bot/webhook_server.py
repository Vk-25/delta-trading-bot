import asyncio
import datetime
from typing import Optional, Literal, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
import numpy as np
import pandas as pd
from bot.config import config
from bot.delta_client import DeltaExchangeClient
from bot.strategy_engine import StrategyEngine
from bot.utils import logger
from bot.dashboard import DASHBOARD_HTML

app = FastAPI(
    title="Delta Exchange Trading Bot Dashboard & Webhook Server",
    description="Live trading dashboard and webhook execution for 100x Precision Strategy",
    version="2.0.0"
)

delta_client = DeltaExchangeClient()
execution_lock = asyncio.Lock()
recent_trade_logs: List[Dict[str, Any]] = []

class WebhookPayload(BaseModel):
    passphrase: str = Field(..., description="Authentication passphrase matching WEBHOOK_PASSPHRASE")
    action: Literal["BUY", "SELL", "EXIT_LONG", "EXIT_SHORT", "CLOSE"] = Field(..., description="Action to execute")
    symbol: Optional[str] = Field(None, description="Trading pair, e.g. BTCUSD")
    size: Optional[int] = Field(None, description="Order size (contracts). If omitted, uses ORDER_SIZE from config")
    order_type: Optional[str] = Field(None, description="market_order or limit_order")
    price: Optional[float] = Field(None, description="Price at time of trigger")
    stop_loss: Optional[float] = Field(None, description="Stop Loss price (e.g. EMA cut candle low/high)")
    comment: Optional[str] = Field(None, description="Optional note or strategy comment")

import os
import json

TRADE_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "trade_history.json")
webhook_active_tracker: Dict[str, Any] = {}

def load_webhook_trades() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(TRADE_HISTORY_FILE):
            with open(TRADE_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception:
        pass
    return []

def save_webhook_trades(trades: List[Dict[str, Any]]):
    try:
        os.makedirs(os.path.dirname(TRADE_HISTORY_FILE), exist_ok=True)
        with open(TRADE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(trades[:300], f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save trade history: {e}")

def get_webhook_stats(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(trades)
    profitable = len([t for t in trades if t.get("is_profit") or (float(t.get("net_pnl", 0)) > 0)])
    losses = total - profitable
    win_rate = round((profitable / total * 100), 1) if total > 0 else 0.0
    total_fees = round(sum(float(t.get("fee", 0.0144 * 2)) for t in trades), 4)
    total_gross = round(sum(float(t.get("gross_pnl", 0.0)) for t in trades), 4)
    total_net = round(sum(float(t.get("net_pnl", 0.0)) for t in trades), 4)
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

def log_trade_event(action: str, reason: str, price: float, stop_loss: Optional[float] = None, gross_pnl: float = 0.0, fee: float = 0.0, net_pnl: float = 0.0, status: str = "INFO"):
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    event = {
        "time": now_ist.strftime("%H:%M:%S IST"),
        "action": action,
        "reason": reason,
        "price": price,
        "stop_loss": stop_loss,
        "gross_pnl": gross_pnl,
        "fee": fee,
        "net_pnl": net_pnl,
        "net_pnl_inr": round(net_pnl * 87.5, 2),
        "status": status
    }
    recent_trade_logs.insert(0, event)
    if len(recent_trade_logs) > 50:
        recent_trade_logs.pop()

def process_trade_action(payload: WebhookPayload) -> dict:
    global webhook_active_tracker
    symbol = (payload.symbol or config.TRADING_SYMBOL).strip().upper()
    size = payload.size if payload.size is not None and payload.size > 0 else config.ORDER_SIZE
    order_type = (payload.order_type or config.ORDER_TYPE).lower()
    action = payload.action.upper()
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    try:
        contract_val = float(delta_client.get_contract_value(symbol))
    except Exception:
        contract_val = 0.001 if "BTC" in symbol else (1.0 if "SOL" in symbol else 0.01)

    logger.info(f"===> Received TradingView Webhook Action: [{action}] for {symbol} (Size: {size}, Price: {payload.price}, StopLoss: {payload.stop_loss})")

    # Fetch existing position
    existing_pos = delta_client.get_position_for_symbol(symbol)
    existing_size = float(existing_pos.get("size", 0)) if existing_pos else 0

    if action == "BUY":
        # If already holding a Short position, close it first
        if existing_size < 0:
            logger.info(f"Existing SHORT position detected ({existing_size}). Closing before opening LONG...")
            delta_client.close_position(symbol)

        if existing_size > 0:
            logger.info(f"Already in a LONG position ({existing_size}). Placing additional BUY order...")

        res = delta_client.place_order(
            symbol=symbol,
            size=size,
            side="buy",
            order_type=order_type
        )
        entry_p = float(
            res.get("result", {}).get("avg_fill_price") or
            res.get("result", {}).get("average_fill_price") or
            res.get("result", {}).get("price") or
            payload.price or
            0.0
        )
        est_fee = round(max(entry_p * size * contract_val * 0.0005, 0.0144), 4)

        if res.get("success") and payload.stop_loss is not None and float(payload.stop_loss) > 0:
            delta_client.cancel_all_orders(symbol)
            delta_client.place_stop_order(symbol, size, "sell", stop_price=float(payload.stop_loss))
            logger.info(f"🛡️ [WEBHOOK STOP PLACED] Stop-Loss placed on Delta at {float(payload.stop_loss):.2f}")
        
        webhook_active_tracker = {
            "action": "BUY",
            "entry_time": now_ist.strftime("%H:%M:%S IST"),
            "entry_price": entry_p,
            "stop_loss": payload.stop_loss,
            "size": size,
            "fee": est_fee
        }
        log_trade_event("BUY", payload.comment or "TradingView Alert", entry_p, payload.stop_loss, gross_pnl=0.0, fee=est_fee, net_pnl=-est_fee, status="OPEN")
        return {"action": "BUY", "result": res}

    elif action == "SELL":
        # If already holding a Long position, close it first
        if existing_size > 0:
            logger.info(f"Existing LONG position detected ({existing_size}). Closing before opening SHORT...")
            delta_client.close_position(symbol)

        if existing_size < 0:
            logger.info(f"Already in a SHORT position ({existing_size}). Placing additional SELL order...")

        res = delta_client.place_order(
            symbol=symbol,
            size=size,
            side="sell",
            order_type=order_type
        )
        entry_p = float(
            res.get("result", {}).get("avg_fill_price") or
            res.get("result", {}).get("average_fill_price") or
            res.get("result", {}).get("price") or
            payload.price or
            0.0
        )
        est_fee = round(max(entry_p * size * contract_val * 0.0005, 0.0144), 4)

        if res.get("success") and payload.stop_loss is not None and float(payload.stop_loss) > 0:
            delta_client.cancel_all_orders(symbol)
            delta_client.place_stop_order(symbol, size, "buy", stop_price=float(payload.stop_loss))
            logger.info(f"🛡️ [WEBHOOK STOP PLACED] Stop-Loss placed on Delta at {float(payload.stop_loss):.2f}")
        
        webhook_active_tracker = {
            "action": "SELL",
            "entry_time": now_ist.strftime("%H:%M:%S IST"),
            "entry_price": entry_p,
            "stop_loss": payload.stop_loss,
            "size": size,
            "fee": est_fee
        }
        log_trade_event("SELL", payload.comment or "TradingView Alert", entry_p, payload.stop_loss, gross_pnl=0.0, fee=est_fee, net_pnl=-est_fee, status="OPEN")
        return {"action": "SELL", "result": res}

    elif action in ("EXIT_LONG", "EXIT_SHORT", "CLOSE"):
        exit_p = float(payload.price or 0.0)
        entry_p = webhook_active_tracker.get("entry_price") or float(existing_pos.get("entry_price", 0.0) if existing_pos else 0.0) or exit_p
        side = webhook_active_tracker.get("action") or ("BUY" if (action == "EXIT_LONG" or existing_size > 0) else "SELL")
        trade_size = webhook_active_tracker.get("size") or abs(existing_size) or size

        if "LONG" in action or side == "BUY":
            price_diff = exit_p - entry_p if (exit_p > 0 and entry_p > 0) else 0.0
        else:
            price_diff = entry_p - exit_p if (exit_p > 0 and entry_p > 0) else 0.0

        gross_pnl = price_diff * trade_size * contract_val
        entry_fee = webhook_active_tracker.get("fee") or (entry_p * trade_size * contract_val * 0.0005) or 0.0144
        exit_fee = (exit_p * trade_size * contract_val * 0.0005) or 0.0144
        total_fee = round(max(entry_fee + exit_fee, 0.0144 * 2), 4)
        net_pnl = round(gross_pnl - total_fee, 4)
        net_pnl_inr = round(net_pnl * 87.5, 2)
        is_profit = net_pnl > 0

        res = delta_client.close_position(symbol)
        delta_client.cancel_all_orders(symbol)

        if entry_p > 0 and exit_p > 0:
            trades = load_webhook_trades()
            trades.insert(0, {
                "entry_time": webhook_active_tracker.get("entry_time", now_ist.strftime("%H:%M:%S IST")),
                "exit_time": now_ist.strftime("%H:%M:%S IST"),
                "side": side,
                "entry_price": entry_p,
                "exit_price": exit_p,
                "price_diff": round(price_diff, 2),
                "size": trade_size,
                "gross_pnl": round(gross_pnl, 4),
                "fee": total_fee,
                "net_pnl": net_pnl,
                "net_pnl_inr": net_pnl_inr,
                "is_profit": is_profit,
                "reason": payload.comment or f"Signal {action}"
            })
            save_webhook_trades(trades)

        log_trade_event(action, payload.comment or "Signal Exit", exit_p, None, gross_pnl=round(gross_pnl, 4), fee=total_fee, net_pnl=net_pnl, status="CLOSED")
        webhook_active_tracker = {}
        return {"action": action, "result": res}

    else:
        raise ValueError(f"Unknown action: {action}")

@app.get("/", response_class=HTMLResponse)
def get_dashboard_html():
    """Serves the live interactive trading web dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)

@app.get("/api/dashboard")
def get_dashboard_data():
    """API endpoint providing real-time data for the web UI."""
    symbol = config.TRADING_SYMBOL
    
    # 1. Fetch wallet balance
    balances_res = delta_client.get_wallet_balances()
    available_usd = 0.0
    total_usd = 0.0
    if balances_res.get("success") and isinstance(balances_res.get("result"), list):
        for b in balances_res["result"]:
            available_usd += float(b.get("available_balance", 0))
            total_usd += float(b.get("balance", 0))

    # 2. Fetch active position
    pos = delta_client.get_position_for_symbol(symbol) or {}
    
    # 3. Fetch open orders on Delta Exchange
    orders_res = delta_client.get_open_orders(symbol)
    open_orders = orders_res.get("result", []) if isinstance(orders_res.get("result"), list) else []

    # 4. Fetch market candles for live indicators
    candles_res = delta_client.get_candles(symbol, resolution=config.TIMEFRAME, limit=70)
    market_info = {"price": 0.0, "ema": 0.0, "rsi": 0.0, "atr": 0.0, "slope": "--", "adx": 0.0, "regime": "trending", "volume_confirmed": True}
    c_res = candles_res.get("result", {})
    if c_res and "c" in c_res and len(c_res["c"]) > 25:
        df_candles = pd.DataFrame({
            "open": c_res.get("o", c_res["c"]),
            "high": c_res.get("h", c_res["c"]),
            "low": c_res.get("l", c_res["c"]),
            "close": c_res["c"],
            "volume": c_res.get("v", [100.0] * len(c_res["c"]))
        })
        close_series = pd.Series(df_candles["close"], dtype=float)
        
        live_p = float(close_series.iloc[-1])
        fast_ema_series = StrategyEngine.calculate_ema(close_series, config.FAST_EMA_LENGTH)
        live_fema = float(fast_ema_series.iloc[-1])
        ema_series = StrategyEngine.calculate_ema(close_series, config.ENTRY_EMA_LENGTH)
        live_ema = float(ema_series.iloc[-1])
        prev_ema = float(ema_series.iloc[-2]) if len(ema_series) > 1 else live_ema
        slope_str = "RISING ↗" if live_ema >= prev_ema else "FALLING ↘"

        rsi_series = StrategyEngine.calculate_rsi(close_series, config.RSI_LENGTH)
        rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

        atr_series = StrategyEngine.calculate_atr(df_candles, config.ATR_LENGTH)
        atr_val = float(atr_series.iloc[-1]) if not atr_series.empty else 0.0

        adx_series = StrategyEngine.calculate_adx(df_candles, config.ADX_LENGTH)
        adx_val = float(adx_series.iloc[-1]) if not adx_series.empty else 0.0

        regime_val = StrategyEngine.detect_regime(df_candles, config.ADX_LENGTH) if len(df_candles) >= 55 else "trending"
        vol_ok = StrategyEngine.has_volume_confirmation(df_candles, config.VOLUME_MULTIPLIER, config.VOLUME_LOOKBACK)

        market_info = {
            "price": live_p,
            "fast_ema": live_fema,
            "ema": live_ema,
            "rsi": rsi_val,
            "atr": atr_val,
            "slope": slope_str,
            "adx": adx_val,
            "regime": regime_val,
            "volume_confirmed": vol_ok
        }

    # Find active stop loss price from open orders
    active_sl = 0.0
    for o in open_orders:
        if o.get("stop_price"):
            active_sl = float(o.get("stop_price"))
            break

    completed = load_webhook_trades()
    stats = get_webhook_stats(completed)
    fills_res = delta_client.get_fills(symbol, limit=20)
    exchange_fills = fills_res.get("result", []) if (fills_res.get("success") and isinstance(fills_res.get("result"), list)) else []

    return {
        "symbol": symbol,
        "contract_value": delta_client.get_contract_value(symbol),
        "timeframe": config.TIMEFRAME,
        "leverage": config.LEVERAGE,
        "balances": {
            "available_usd": available_usd,
            "total_usd": total_usd
        },
        "position": pos,
        "open_orders": open_orders,
        "active_stop_price": active_sl,
        "breakeven_locked": active_sl > 0 and float(pos.get("entry_price", 0)) > 0 and (
            (float(pos.get("size", 0)) > 0 and active_sl >= float(pos.get("entry_price", 0))) or
            (float(pos.get("size", 0)) < 0 and active_sl <= float(pos.get("entry_price", 0)))
        ),
        "market": market_info,
        "stats": stats,
        "completed_trades": completed,
        "exchange_fills": exchange_fills,
        "recent_logs": recent_trade_logs
    }

@app.post("/api/emergency_close")
def api_emergency_close():
    """Emergency close endpoint called from the web dashboard."""
    symbol = config.TRADING_SYMBOL
    res = delta_client.close_position(symbol)
    delta_client.cancel_all_orders(symbol)
    log_trade_event("EMERGENCY_CLOSE", "Dashboard Button", 0.0)
    return {"success": True, "message": "Position closed and all orders cancelled.", "result": res}

@app.get("/health")
def health_check():
    profile = delta_client.get_profile()
    is_authenticated = profile.get("success", False) if isinstance(profile, dict) else False
    return {
        "status": "healthy",
        "api_connected": is_authenticated,
        "environment": config.DELTA_ENVIRONMENT,
        "base_url": config.get_base_url()
    }

@app.get("/position")
def get_position(symbol: Optional[str] = None):
    target_symbol = symbol or config.TRADING_SYMBOL
    pos = delta_client.get_position_for_symbol(target_symbol)
    return {
        "symbol": target_symbol,
        "position": pos or "No active position"
    }

@app.get("/balances")
def get_balances():
    return delta_client.get_wallet_balances()

@app.post("/webhook")
async def handle_webhook(payload: WebhookPayload):
    # Verify passphrase
    if config.WEBHOOK_PASSPHRASE and payload.passphrase != config.WEBHOOK_PASSPHRASE:
        logger.warning(f"Unauthorized webhook attempt with passphrase: '{payload.passphrase}'")
        raise HTTPException(status_code=401, detail="Invalid passphrase")

    async with execution_lock:
        try:
            result = process_trade_action(payload)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Error processing trade action: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

def start_server(host: str = "0.0.0.0", port: int = 8000):
    logger.info(f"Starting Webhook Server on {host}:{port}...")
    uvicorn.run("bot.webhook_server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    start_server()
