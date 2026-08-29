import asyncio
import datetime
from typing import Optional, Literal, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
import pandas as pd
from bot.config import config
from bot.delta_client import DeltaExchangeClient
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

def log_trade_event(action: str, reason: str, price: float, stop_loss: Optional[float] = None):
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    event = {
        "time": now_ist.strftime("%H:%M:%S IST"),
        "action": action,
        "reason": reason,
        "price": price,
        "stop_loss": stop_loss
    }
    recent_trade_logs.insert(0, event)
    if len(recent_trade_logs) > 50:
        recent_trade_logs.pop()

def process_trade_action(payload: WebhookPayload) -> dict:
    symbol = (payload.symbol or config.TRADING_SYMBOL).strip().upper()
    size = payload.size if payload.size is not None and payload.size > 0 else config.ORDER_SIZE
    order_type = (payload.order_type or config.ORDER_TYPE).lower()
    action = payload.action.upper()

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
        if res.get("success") and payload.stop_loss is not None and float(payload.stop_loss) > 0:
            delta_client.cancel_all_orders(symbol)
            delta_client.place_stop_order(symbol, size, "sell", stop_price=float(payload.stop_loss))
            logger.info(f"🛡️ [WEBHOOK STOP PLACED] Stop-Loss placed on Delta at {float(payload.stop_loss):.2f}")
        
        log_trade_event("BUY", payload.comment or "TradingView Alert", payload.price or 0.0, payload.stop_loss)
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
        if res.get("success") and payload.stop_loss is not None and float(payload.stop_loss) > 0:
            delta_client.cancel_all_orders(symbol)
            delta_client.place_stop_order(symbol, size, "buy", stop_price=float(payload.stop_loss))
            logger.info(f"🛡️ [WEBHOOK STOP PLACED] Stop-Loss placed on Delta at {float(payload.stop_loss):.2f}")
        
        log_trade_event("SELL", payload.comment or "TradingView Alert", payload.price or 0.0, payload.stop_loss)
        return {"action": "SELL", "result": res}

    elif action == "EXIT_LONG":
        if existing_size > 0:
            logger.info(f"Executing EXIT_LONG: closing LONG position ({existing_size})...")
            res = delta_client.close_position(symbol)
            delta_client.cancel_all_orders(symbol)
            log_trade_event("EXIT_LONG", payload.comment or "Signal Exit", payload.price or 0.0)
            return {"action": "EXIT_LONG", "result": res}
        else:
            logger.info("EXIT_LONG received, but no open LONG position found.")
            return {"action": "EXIT_LONG", "message": "No open LONG position"}

    elif action == "EXIT_SHORT":
        if existing_size < 0:
            logger.info(f"Executing EXIT_SHORT: closing SHORT position ({existing_size})...")
            res = delta_client.close_position(symbol)
            delta_client.cancel_all_orders(symbol)
            log_trade_event("EXIT_SHORT", payload.comment or "Signal Exit", payload.price or 0.0)
            return {"action": "EXIT_SHORT", "result": res}
        else:
            logger.info("EXIT_SHORT received, but no open SHORT position found.")
            return {"action": "EXIT_SHORT", "message": "No open SHORT position"}

    elif action == "CLOSE":
        logger.info(f"Executing CLOSE: flattening any open position for {symbol}...")
        res = delta_client.close_position(symbol)
        delta_client.cancel_all_orders(symbol)
        log_trade_event("CLOSE", "Manual Emergency Close", payload.price or 0.0)
        return {"action": "CLOSE", "result": res}

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
    candles_res = delta_client.get_candles(symbol, resolution=config.TIMEFRAME, limit=50)
    market_info = {"price": 0.0, "ema": 0.0, "rsi": 0.0, "atr": 0.0, "slope": "--"}
    c_res = candles_res.get("result", {})
    if c_res and "c" in c_res and len(c_res["c"]) > 25:
        close_series = pd.Series(c_res["c"], dtype=float)
        high_series = pd.Series(c_res["h"], dtype=float)
        low_series = pd.Series(c_res["l"], dtype=float)
        
        live_p = float(close_series.iloc[-1])
        ema_series = close_series.ewm(span=config.ENTRY_EMA_LENGTH, adjust=False).mean()
        live_ema = float(ema_series.iloc[-1])
        prev_ema = float(ema_series.iloc[-2])
        slope_str = "RISING ↗" if live_ema >= prev_ema else "FALLING ↘"

        # RSI
        delta = close_series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi_val = float((100 - (100 / (1 + rs))).iloc[-1])

        # ATR
        prev_c = close_series.shift(1)
        tr1 = high_series - low_series
        tr2 = (high_series - prev_c).abs()
        tr3 = (low_series - prev_c).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_val = float(tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1])

        market_info = {
            "price": live_p,
            "ema": live_ema,
            "rsi": rsi_val,
            "atr": atr_val,
            "slope": slope_str
        }

    # Find active stop loss price from open orders
    active_sl = 0.0
    for o in open_orders:
        if o.get("stop_price"):
            active_sl = float(o.get("stop_price"))
            break

    return {
        "symbol": symbol,
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
