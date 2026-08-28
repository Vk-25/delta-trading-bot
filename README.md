# Delta Exchange Trading Bot: EMA Cut Breakout [Universal Smart Exit]

An automated trading bot engineered specifically for **Delta Exchange** (supporting both **Delta Exchange Global** and **Delta Exchange India**). The bot executes trades based on the algorithmic indicator and risk-management logic of `EMA_Cut_Breakout_Universal_Smart_Exit_FIXED`.

---

## Key Features

- **Dual Operating Modes**:
  1. **TradingView Webhook Mode** (FastAPI): Receives formatted JSON webhook alerts triggered by TradingView and places/closes orders on Delta Exchange instantly.
  2. **Standalone Algorithmic Bot**: Runs 24/7 independently, streaming live candles directly from Delta Exchange, calculating all indicators, and managing state transitions without needing TradingView.
- **Support for Delta Global & Delta India**: Full support for `api.delta.exchange` and `api.india.delta.exchange`.
- **Exact Indicator Logic**:
  - 20 EMA Cut candle identification (`high[1] >= EMA[1]` and `low[1] <= EMA[1]`)
  - Breakout confirmation triggers (`high > high[1]` / `low < low[1]`)
  - Multi-confirmation Smart Exit scoring (Exit EMA, RSI, MACD, Price Structure)
  - ATR-based Trailing Profit Protection ($1.0\times$ ATR activation, $1.25\times$ ATR trailing stop)
  - Emergency Loss Protection stop-out ($2.5\times$ ATR)
- **Built-in Safety**: HMAC-SHA256 authenticated API requests, passphrase verification on webhooks, concurrency locking, and reduce-only position closing.

---

## Directory Structure

```
d:/DT SCRIPT/
├── bot/
│   ├── __init__.py
│   ├── config.py                 # Configuration loader (API keys, pairs, sizing, risk)
│   ├── delta_client.py           # Authenticated Delta Exchange REST API client
│   ├── strategy_engine.py        # Python indicator math & state machine
│   ├── webhook_server.py         # FastAPI Webhook receiver for TradingView alerts
│   ├── standalone_bot.py         # Standalone 24/7 background runner
│   ├── test_connection.py        # Diagnostic tool for Delta credentials & balance
│   └── utils.py                  # HMAC-SHA256 signature generator & logger
├── tests/
│   ├── test_delta_signature.py   # Signature validation unit tests
│   ├── test_strategy.py          # Strategy & indicator math tests
│   └── test_webhook.py           # FastAPI endpoint integration tests
├── .env.example                  # Environment variables template
├── .env                          # Local configuration (API keys, etc.)
├── requirements.txt              # Project dependencies
├── tv_alert_indicator.pine       # Pine Script with preconfigured Webhook JSON alerts
└── README.md                     # Full documentation
```

---

## 1. Setup & Installation

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` (if not already done) and enter your credentials:
```ini
# DELTA ENVIRONMENT: 'global' or 'india'
DELTA_ENVIRONMENT=india

# API Keys from Delta Exchange (Settings -> API Keys)
DELTA_API_KEY=your_api_key_here
DELTA_API_SECRET=your_api_secret_here

# Passphrase for Webhook Security
WEBHOOK_PASSPHRASE=supersecretpassphrase123

# Trade Configuration
TRADING_SYMBOL=BTCUSD
ORDER_SIZE=1
LEVERAGE=10
ORDER_TYPE=market_order

# Strategy Parameters (EMA Cut Breakout Universal Smart Exit)
ENTRY_EMA_LENGTH=20
ENABLE_SMART_EXIT=true
EXIT_ON_OPPOSITE=true
EXIT_CONFIRMATIONS=2
EXIT_EMA_LENGTH=20
RSI_LENGTH=14
ATR_LENGTH=14

# Profit Protection Trailing ATR
ENABLE_PROTECTION=true
ACTIVATION_ATR=1.0
TRAIL_ATR=1.25

# Emergency Exit
ENABLE_EMERGENCY=true
EMERGENCY_ATR=2.5

# Standalone Bot Polling
TIMEFRAME=15m
POLL_INTERVAL_SECONDS=10
```

---

## 2. Test Connection & Diagnostics

Run the connection test tool to verify your API credentials, fetch wallet balances, and inspect active positions on Delta Exchange:

```bash
python -m bot.test_connection
```

Example output:
```
=================================================================
DELTA EXCHANGE BOT - CONNECTION & ACCOUNT DIAGNOSTICS
=================================================================
Environment    : INDIA
Base URL       : https://api.india.delta.exchange
Trading Symbol : BTCUSD
Order Size     : 1
Leverage       : 10x
-----------------------------------------------------------------
[1/4] Checking Product Catalog for symbol...
 SUCCESS: Found BTCUSD (Product ID: 27, Tick: 0.5, Contract Value: 0.001)

[2/4] Testing API Key Authentication (Profile)...
 SUCCESS: Authenticated as User ID: 123456 | Email: trader@example.com

[3/4] Fetching Wallet Balances...
 -> Asset: USDT | Balance: 500.00 | Available: 480.50

[4/4] Checking Active Positions...
 -> No active position currently open for BTCUSD.
=================================================================
DIAGNOSTICS COMPLETED.
=================================================================
```

---

## 3. Mode A: TradingView Webhook Mode

### 1. Start the Webhook Server
```bash
python -m bot.webhook_server
```
The server will start listening at `http://0.0.0.0:8000`.

### 2. Expose the Server to the Internet (if running locally)
If running on your local machine, use [ngrok](https://ngrok.com/) to expose port 8000:
```bash
ngrok http 8000
```
Copy your forwarding URL (e.g. `https://abc123xyz.ngrok-free.app`). Your webhook endpoint will be:
`https://abc123xyz.ngrok-free.app/webhook`

### 3. Load Indicator in TradingView
1. Open TradingView and open Pine Editor.
2. Paste the contents of `tv_alert_indicator.pine` into the editor and click **Add to chart**.
3. In indicator settings, set your **Webhook Passphrase** (same as in `.env`).

### 4. Create Alerts in TradingView
Click **Create Alert** on your chart:
- **Condition**: Select `EMA Cut Breakout [Universal Smart Exit] - DELTA BOT`
- **Trigger**: Any alert function call (or specific alert condition like `DELTA BUY Alert`, `DELTA SELL Alert`, etc.)
- **Webhook URL**: Check "Webhook URL" and paste your ngrok / server URL: `https://your-server.com/webhook`
- **Message**: If using `alertcondition`, paste:
```json
{"passphrase": "supersecretpassphrase123", "action": "BUY", "symbol": "{{ticker}}", "price": {{close}}}
```

---

## 4. Mode B: Standalone Algorithmic Bot

No TradingView alert setup or subscription needed. The standalone bot streams candle data from Delta Exchange, runs the strategy locally, and manages orders 24/7.

### Start the Standalone Bot:
```bash
python -m bot.standalone_bot
```

The bot will:
1. Set the configured leverage on Delta Exchange for your trading symbol.
2. Fetch candle data every polling interval.
3. Automatically evaluate closed candles.
4. Execute `BUY`, `SELL`, `EXIT_LONG`, and `EXIT_SHORT` signals directly.

---

## 5. Running Tests

Run all unit tests and integration tests with:
```bash
python -m unittest discover -s tests -v
```

All 9 test suites verify:
- HMAC-SHA256 signature generation
- EMA, Wilder RSI, Wilder ATR, MACD indicator calculation
- 20 EMA Cut & Breakout triggers
- Smart Exit score thresholding
- FastAPI webhook authentication and order execution routing

---

## 6. Running 24/7 in the Cloud (When Computer is OFF)

To keep your bot running nonstop without keeping your personal computer turned on:

1. **Deploy on any Linux Cloud VPS (AWS Free Tier, Hetzner, DigitalOcean, Hostinger)**:
   - Run our 1-click installer:
     ```bash
     chmod +x deploy/setup_vps.sh
     ./deploy/setup_vps.sh
     ```
   - This sets up a **24/7 background system service** with automatic restart on crash/reboot.
2. **Deploy with Docker**:
   ```bash
   docker compose up -d
   ```
3. **Deploy on Render.com (1-Click Platform)**:
   - Connect your repository to Render as a **Background Worker** with start command `python -m bot.standalone_bot`.

For full step-by-step instructions, see the [24/7 Cloud Deployment Guide](deploy/cloud_deployment_guide.md).

