import asyncio
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
import uvicorn
from bot.config import config
from bot.delta_client import DeltaExchangeClient
from bot.utils import logger

app = FastAPI(
    title="Delta Exchange Trading Bot Webhook Server",
    description="Webhook server to execute TradingView alerts based on EMA Cut Breakout strategy",
    version="1.0.0"
)

delta_client = DeltaExchangeClient()
execution_lock = asyncio.Lock()

class WebhookPayload(BaseModel):
    passphrase: str = Field(..., description="Authentication passphrase matching WEBHOOK_PASSPHRASE")
    action: Literal["BUY", "SELL", "EXIT_LONG", "EXIT_SHORT", "CLOSE"] = Field(..., description="Action to execute")
    symbol: Optional[str] = Field(None, description="Trading pair, e.g. BTCUSD")
    size: Optional[int] = Field(None, description="Order size (contracts). If omitted, uses ORDER_SIZE from config")
    order_type: Optional[str] = Field(None, description="market_order or limit_order")
    price: Optional[float] = Field(None, description="Price at time of trigger")
    comment: Optional[str] = Field(None, description="Optional note or strategy comment")

def process_trade_action(payload: WebhookPayload) -> dict:
    symbol = (payload.symbol or config.TRADING_SYMBOL).strip().upper()
    size = payload.size if payload.size is not None and payload.size > 0 else config.ORDER_SIZE
    order_type = (payload.order_type or config.ORDER_TYPE).lower()
    action = payload.action.upper()

    logger.info(f"===> Received TradingView Webhook Action: [{action}] for {symbol} (Size: {size}, Price: {payload.price})")

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
        return {"action": "SELL", "result": res}

    elif action == "EXIT_LONG":
        if existing_size > 0:
            logger.info(f"Executing EXIT_LONG: closing LONG position ({existing_size})...")
            res = delta_client.close_position(symbol)
            return {"action": "EXIT_LONG", "result": res}
        else:
            logger.info("EXIT_LONG received, but no open LONG position found.")
            return {"action": "EXIT_LONG", "message": "No open LONG position"}

    elif action == "EXIT_SHORT":
        if existing_size < 0:
            logger.info(f"Executing EXIT_SHORT: closing SHORT position ({existing_size})...")
            res = delta_client.close_position(symbol)
            return {"action": "EXIT_SHORT", "result": res}
        else:
            logger.info("EXIT_SHORT received, but no open SHORT position found.")
            return {"action": "EXIT_SHORT", "message": "No open SHORT position"}

    elif action == "CLOSE":
        logger.info(f"Executing CLOSE: flattening any open position for {symbol}...")
        res = delta_client.close_position(symbol)
        return {"action": "CLOSE", "result": res}

    else:
        raise ValueError(f"Unknown action: {action}")

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Delta Exchange Trading Bot Webhook Receiver",
        "environment": config.DELTA_ENVIRONMENT,
        "symbol": config.TRADING_SYMBOL
    }

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
