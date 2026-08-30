DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeltaBot Live Dashboard | 100x Precision</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #07090e;
            --bg-card: rgba(16, 22, 36, 0.7);
            --bg-card-hover: rgba(22, 30, 49, 0.85);
            --border: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(16, 185, 129, 0.2);
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --emerald: #10b981;
            --emerald-glow: rgba(16, 185, 129, 0.25);
            --crimson: #f43f5e;
            --crimson-glow: rgba(244, 63, 94, 0.25);
            --cyan: #06b6d4;
            --violet: #8b5cf6;
            --amber: #f59e0b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-main);
            min-height: 100vh;
            padding: 1.5rem;
            background-image: 
                radial-gradient(at 0% 0%, rgba(16, 185, 129, 0.07) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.08) 0px, transparent 50%);
            background-attachment: fixed;
        }

        .mono {
            font-family: 'JetBrains Mono', monospace;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        /* HEADER */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand-logo {
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, var(--emerald), var(--cyan));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.25rem;
            color: #000;
            box-shadow: 0 0 20px var(--emerald-glow);
        }

        .brand-title h1 {
            font-size: 1.35rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .brand-title p {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .header-meta {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.1);
            color: var(--emerald);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--emerald);
            box-shadow: 0 0 10px var(--emerald);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.8); }
        }

        .time-badge {
            font-size: 0.85rem;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.03);
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }

        /* GRID LAYOUTS */
        .grid-kpi {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem;
            margin-bottom: 1.25rem;
        }

        .grid-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 1.25rem;
        }

        .grid-split {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.25rem;
            margin-bottom: 1.25rem;
        }

        @media (max-width: 900px) {
            .grid-split {
                grid-template-columns: 1fr;
            }
        }

        /* CARDS */
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.25rem;
            transition: all 0.2s ease;
        }

        .card:hover {
            border-color: rgba(255, 255, 255, 0.15);
            background: var(--bg-card-hover);
        }

        .card-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 0.4rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-value {
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 0.25rem;
        }

        .card-sub {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .positive {
            color: var(--emerald);
        }

        .negative {
            color: var(--crimson);
        }

        /* BADGES */
        .badge-pill {
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            display: inline-block;
        }

        .badge-buy {
            background: rgba(16, 185, 129, 0.15);
            color: var(--emerald);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-sell {
            background: rgba(244, 63, 94, 0.15);
            color: var(--crimson);
            border: 1px solid rgba(244, 63, 94, 0.3);
        }

        .badge-flat {
            background: rgba(148, 163, 184, 0.15);
            color: var(--text-muted);
            border: 1px solid rgba(148, 163, 184, 0.2);
        }

        .badge-fee {
            background: rgba(245, 158, 11, 0.15);
            color: var(--amber);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        /* TELEMETRY BOX */
        .position-box {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
            background: rgba(0, 0, 0, 0.2);
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .pos-item-title {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .pos-item-value {
            font-size: 0.95rem;
            font-weight: 600;
            margin-top: 0.15rem;
        }

        .telemetry-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.5rem;
            margin-top: 1rem;
        }

        .tele-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border);
            padding: 0.6rem;
            border-radius: 8px;
            text-align: center;
        }

        .tele-title {
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .tele-val {
            font-size: 0.95rem;
            font-weight: 700;
            margin-top: 0.2rem;
        }

        /* TABLES */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            font-weight: 700;
            font-size: 1rem;
        }

        .table-wrap {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            text-align: left;
        }

        th {
            background: rgba(255, 255, 255, 0.02);
            color: var(--text-muted);
            font-weight: 600;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            text-transform: uppercase;
            font-size: 0.7rem;
        }

        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        /* BUTTONS */
        .btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 0.4rem 0.85rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .btn-danger {
            background: rgba(244, 63, 94, 0.15);
            color: var(--crimson);
            border-color: rgba(244, 63, 94, 0.3);
        }

        .btn-danger:hover {
            background: rgba(244, 63, 94, 0.25);
        }

        /* TABS */
        .tab-nav {
            display: flex;
            gap: 0.5rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            flex-wrap: wrap;
        }

        .tab-btn {
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-muted);
            padding: 0.5rem 1rem;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .tab-btn:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.04);
        }

        .tab-btn.active {
            color: var(--cyan);
            background: rgba(6, 182, 212, 0.12);
            border-color: rgba(6, 182, 212, 0.3);
        }

        .tab-pane {
            display: none;
        }

        .tab-pane.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <header>
            <div class="brand">
                <div class="brand-logo">⚡</div>
                <div class="brand-title">
                    <h1>DeltaBot High-Frequency Scalper</h1>
                    <p id="bot-subtitle">ETHUSD • 3m High-Frequency Scalping • Multi-Trigger (60+ Entries/Day Target) • 100x Precision</p>
                </div>
            </div>

            <div class="header-meta">
                <div class="status-badge">
                    <div class="status-dot"></div>
                    <span id="connection-status">Delta India Connected</span>
                </div>
                <div class="time-badge mono" id="clock">--:--:-- IST</div>
                <button class="btn" onclick="fetchDashboardData()">↻ Refresh</button>
            </div>
        </header>

        <!-- KPI CARDS (BALANCES & POSITIONS) -->
        <div class="grid-kpi">
            <!-- WALLET BALANCE -->
            <div class="card">
                <div class="card-label">
                    <span>Wallet Balance</span>
                    <span class="mono" style="color: var(--cyan);">USDT / INR</span>
                </div>
                <div class="card-value mono" id="available-balance">$0.00</div>
                <div class="card-sub mono" id="inr-balance">≈ ₹0.00 INR (Available)</div>
            </div>

            <!-- POSITION PNL & ROI -->
            <div class="card">
                <div class="card-label">
                    <span>Live Unrealized PnL</span>
                    <span id="roi-badge" class="badge-pill badge-flat mono">0.0% ROI</span>
                </div>
                <div class="card-value mono" id="live-pnl">$0.00</div>
                <div class="card-sub mono" id="live-pnl-inr">≈ ₹0.00 INR</div>
            </div>

            <!-- ACTIVE POSITION -->
            <div class="card">
                <div class="card-label">
                    <span>Current Position</span>
                    <span id="position-badge" class="badge-pill badge-flat mono">FLAT</span>
                </div>
                <div class="card-value mono" id="position-size">0 Lots</div>
                <div class="card-sub mono" id="entry-price-display">Entry: None</div>
            </div>

            <!-- RISK & DEFENSE -->
            <div class="card">
                <div class="card-label">
                    <span>Active Exchange Stop</span>
                    <span class="mono" style="color: var(--emerald);">0% Liq Risk</span>
                </div>
                <div class="card-value mono" id="active-stop-loss">$0.00</div>
                <div class="card-sub mono" id="trailing-status">Breakeven: Inactive</div>
            </div>
        </div>

        <!-- PERFORMANCE & PNL SUMMARY BAR -->
        <div class="grid-stats">
            <!-- TOTAL REALIZED NET PNL -->
            <div class="card" style="border-left: 3px solid var(--emerald);">
                <div class="card-label">
                    <span>Total Realized Net PnL</span>
                    <span class="mono" style="color: var(--emerald);">After Fees</span>
                </div>
                <div class="card-value mono" id="total-net-pnl">$0.0000</div>
                <div class="card-sub mono" id="total-net-pnl-inr">≈ ₹0.00 INR Net Profit</div>
            </div>

            <!-- WIN RATE & PROFITABLE/LOSS TRADES -->
            <div class="card" style="border-left: 3px solid var(--cyan);">
                <div class="card-label">
                    <span>Win Rate & Outcomes</span>
                    <span id="winrate-badge" class="badge-pill badge-buy mono">0.0% Win</span>
                </div>
                <div class="card-value mono" id="trade-outcomes">0 Won / 0 Lost</div>
                <div class="card-sub mono" id="total-trades-count">0 Total Completed Trades</div>
            </div>

            <!-- TOTAL EXCHANGE FEES -->
            <div class="card" style="border-left: 3px solid var(--amber);">
                <div class="card-label">
                    <span>Total Fees Paid</span>
                    <span class="badge-pill badge-fee mono">0.05% Taker (Exact Notional)</span>
                </div>
                <div class="card-value mono" style="color: var(--amber);" id="total-fees">$0.0000</div>
                <div class="card-sub mono" id="total-fees-inr">≈ ₹0.00 INR in Fees</div>
            </div>

            <!-- GROSS PROFIT / LOSS -->
            <div class="card" style="border-left: 3px solid var(--violet);">
                <div class="card-label">
                    <span>Total Gross PnL</span>
                    <span class="mono" style="color: var(--violet);">Market Move</span>
                </div>
                <div class="card-value mono" id="total-gross-pnl">$0.0000</div>
                <div class="card-sub mono">Before Exchange Fees</div>
            </div>
        </div>

        <!-- MAIN SPLIT -->
        <div class="grid-split">
            <!-- POSITION DETAILS & TELEMETRY -->
            <div class="card">
                <div class="section-header">
                    <span>📊 Active Position Telemetry</span>
                    <button class="btn btn-danger" onclick="emergencyClose()">Emergency Close</button>
                </div>

                <div class="position-box mono" style="margin-bottom: 1rem;">
                    <div class="pos-item">
                        <span class="pos-item-title">Symbol</span>
                        <span class="pos-item-value" id="pos-symbol">ETHUSD</span>
                    </div>
                    <div class="pos-item">
                        <span class="pos-item-title">Mark Price</span>
                        <span class="pos-item-value" id="mark-price">$0.00</span>
                    </div>
                    <div class="pos-item">
                        <span class="pos-item-title">Leverage</span>
                        <span class="pos-item-value" style="color: var(--amber);">100x</span>
                    </div>
                    <div class="pos-item">
                        <span class="pos-item-title">Initial Margin</span>
                        <span class="pos-item-value" id="initial-margin">$0.00</span>
                    </div>
                    <div class="pos-item">
                        <span class="pos-item-title">Liquidation Distance</span>
                        <span class="pos-item-value" style="color: var(--emerald);" id="liq-distance">SAFE (> $10)</span>
                    </div>
                    <div class="pos-item">
                        <span class="pos-item-title">Breakeven Target</span>
                        <span class="pos-item-value" id="be-target">$0.00 (+9% ROI)</span>
                    </div>
                </div>

                <div class="section-header" style="margin-top: 1.25rem;">
                    <span>⚡ Scalper Telemetry & Multi-Triggers (3m Live)</span>
                </div>
                <div class="telemetry-grid mono">
                    <div class="tele-card">
                        <div class="tele-title">9 Fast / 21 EMA</div>
                        <div class="tele-val" style="color: var(--cyan); font-size: 0.92rem;" id="val-ema">0.00 / 0.00</div>
                    </div>
                    <div class="tele-card">
                        <div class="tele-title">14 RSI</div>
                        <div class="tele-val" id="val-rsi">0.0</div>
                    </div>
                    <div class="tele-card">
                        <div class="tele-title">14 ATR</div>
                        <div class="tele-val" id="val-atr">0.00</div>
                    </div>
                    <div class="tele-card">
                        <div class="tele-title">Scalp TP (+0.85 ATR)</div>
                        <div class="tele-val" style="color: var(--emerald);" id="val-scalp-tp">--</div>
                    </div>
                    <div class="tele-card">
                        <div class="tele-title">Active Triggers</div>
                        <div class="tele-val" style="font-size: 0.85rem; color: var(--amber);" id="val-scalp-triggers">4 Enabled</div>
                    </div>
                    <div class="tele-card">
                        <div class="tele-title">Volume Confirmation</div>
                        <div class="tele-val" style="font-size: 0.95rem;" id="val-volume-filter">--</div>
                    </div>
                </div>
            </div>

            <!-- DELTA ACTIVE ORDER BOOK ORDERS -->
            <div class="card">
                <div class="section-header">
                    <span>🛡️ Active Orders on Delta Exchange Book</span>
                    <span class="mono" style="font-size: 0.75rem; color: var(--text-muted);" id="orders-count">0 Orders</span>
                </div>

                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Order Type</th>
                                <th>Side</th>
                                <th>Stop / Limit Price</th>
                                <th>Size</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="orders-table-body" class="mono">
                            <tr>
                                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No pending orders on Delta book</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TRADE HISTORY & LOGS TABBED SECTION -->
        <div class="card">
            <div class="tab-nav">
                <button class="tab-btn active" id="btn-tab-trades" onclick="switchTab('trades')">
                    <span>🏆 Past Completed Trades</span>
                    <span id="completed-count-badge" class="badge-pill badge-buy mono" style="font-size: 0.65rem;">0</span>
                </button>
                <button class="tab-btn" id="btn-tab-logs" onclick="switchTab('logs')">
                    <span>📜 Live Signals & Activity</span>
                    <span id="logs-count-badge" class="badge-pill badge-flat mono" style="font-size: 0.65rem;">0</span>
                </button>
                <button class="tab-btn" id="btn-tab-fills" onclick="switchTab('fills')">
                    <span>🏦 Delta Exchange Fills</span>
                    <span id="fills-count-badge" class="badge-pill badge-fee mono" style="font-size: 0.65rem;">0</span>
                </button>
            </div>

            <!-- TAB 1: COMPLETED TRADES HISTORY -->
            <div id="tab-trades" class="tab-pane active">
                <div class="section-header">
                    <span>📖 Realized PnL & Completed Trades History</span>
                    <span class="mono" style="font-size: 0.75rem; color: var(--text-muted);">Auto-saved to persistent history</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Entry & Exit Time (IST)</th>
                                <th>Side</th>
                                <th>Entry → Exit Price</th>
                                <th>Move (Pts)</th>
                                <th>Lots</th>
                                <th>Gross PnL</th>
                                <th>Fee Paid</th>
                                <th>Net Realized PnL</th>
                                <th>Outcome</th>
                                <th>Exit Reason</th>
                            </tr>
                        </thead>
                        <tbody id="completed-trades-body" class="mono">
                            <tr>
                                <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">No completed trades recorded yet</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- TAB 2: LIVE SIGNAL FEED -->
            <div id="tab-logs" class="tab-pane">
                <div class="section-header">
                    <span>⚡ Live Execution & Signal Event Stream</span>
                    <span class="mono" style="font-size: 0.75rem; color: var(--emerald);">Auto-updates every 2s</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Time (IST)</th>
                                <th>Action</th>
                                <th>Price</th>
                                <th>Stop Loss</th>
                                <th>Gross</th>
                                <th>Fee</th>
                                <th>Net</th>
                                <th>Trigger Reason</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="logs-table-body" class="mono">
                            <tr>
                                <td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">Awaiting trade events...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- TAB 3: DELTA EXCHANGE FILLS -->
            <div id="tab-fills" class="tab-pane">
                <div class="section-header">
                    <span>🏦 Real Fills from Delta Exchange API</span>
                    <span class="mono" style="font-size: 0.75rem; color: var(--text-muted);">Direct Exchange Ledger</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Fill Time (UTC/IST)</th>
                                <th>Symbol</th>
                                <th>Side</th>
                                <th>Fill Price</th>
                                <th>Size (Lots)</th>
                                <th>Fee (USDT)</th>
                                <th>Role</th>
                            </tr>
                        </thead>
                        <tbody id="fills-table-body" class="mono">
                            <tr>
                                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">No exchange fill records returned</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const USD_TO_INR = 87.50;

        function updateClock() {
            const now = new Date();
            const istOptions = { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            document.getElementById('clock').innerText = now.toLocaleTimeString('en-GB', istOptions) + ' IST';
        }
        setInterval(updateClock, 1000);
        updateClock();

        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

            const btn = document.getElementById(`btn-tab-${tabId}`);
            const pane = document.getElementById(`tab-${tabId}`);
            if (btn) btn.classList.add('active');
            if (pane) pane.classList.add('active');
        }

        async function fetchDashboardData() {
            try {
                const res = await fetch('/api/dashboard');
                if (!res.ok) throw new Error('API offline');
                const data = await res.json();
                renderData(data);
            } catch (e) {
                console.error("Dashboard fetch error:", e);
                document.getElementById('connection-status').innerText = "Connecting...";
                document.getElementById('connection-status').style.color = "var(--amber)";
            }
        }

        function formatPnl(val, showSign = true) {
            const num = parseFloat(val) || 0;
            const sign = showSign ? (num > 0 ? '+' : (num < 0 ? '-' : '')) : (num < 0 ? '-' : '');
            const abs = Math.abs(num);
            return `${sign}$${abs.toFixed(4)}`;
        }

        function formatFee(val) {
            const num = Math.abs(parseFloat(val) || 0);
            return `$${num.toFixed(4)}`;
        }

        function formatPrice(val) {
            const num = parseFloat(val) || 0;
            if (num === 0) return '--';
            return `$${num.toFixed(2)}`;
        }

        function formatInr(val, showSign = false) {
            const num = parseFloat(val) || 0;
            const sign = showSign ? (num > 0 ? '+' : (num < 0 ? '-' : '')) : (num < 0 ? '-' : '');
            const abs = Math.abs(num);
            return `${sign}₹${abs.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }

        function formatUsd(val, showSign = false) {
            const num = parseFloat(val) || 0;
            const sign = showSign ? (num > 0 ? '+' : (num < 0 ? '-' : '')) : (num < 0 ? '-' : '');
            const abs = Math.abs(num);
            if (abs >= 100 || abs === 0) {
                return `${sign}$${abs.toFixed(2)}`;
            }
            return `${sign}$${abs.toFixed(4)}`;
        }

        function formatTimeIST(tsStr) {
            if (!tsStr) return '--';
            try {
                let d;
                if (typeof tsStr === 'number') {
                    d = new Date(tsStr > 1e11 ? tsStr : tsStr * 1000);
                } else if (!isNaN(Number(tsStr))) {
                    const num = Number(tsStr);
                    d = new Date(num > 1e11 ? num : num * 1000);
                } else {
                    d = new Date(tsStr);
                }
                if (isNaN(d.getTime())) return tsStr;
                return d.toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' IST';
            } catch(e) {
                return tsStr;
            }
        }

        function reconstructTradesFromFills(fills, contractVal) {
            if (!fills || fills.length === 0) return [];
            // Sort fills chronologically (oldest to newest)
            const sorted = [...fills].sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
            const trades = [];
            let active = null;

            for (const f of sorted) {
                const side = (f.side || 'buy').toUpperCase();
                const price = parseFloat(f.price || 0);
                const size = parseFloat(f.size || 1);
                const rawFee = f.paid_commission ?? f.fee ?? f.trading_fee ?? f.commission;
                const fee = (rawFee !== undefined && rawFee !== null && rawFee !== '')
                    ? Math.abs(parseFloat(rawFee))
                    : (price * size * contractVal * 0.0005);
                const time = formatTimeIST(f.created_at);

                if (!active) {
                    active = { side, price, size, fee, time };
                } else if (active.side !== side) {
                    // Match Entry and Exit fill to form a closed Round-Trip Trade
                    const isLong = active.side === 'BUY';
                    const priceDiff = isLong ? (price - active.price) : (active.price - price);
                    const gross = priceDiff * size * contractVal;
                    const totalFee = active.fee + fee;
                    const net = gross - totalFee;
                    const isWin = net > 0;

                    trades.unshift({
                        entry_time: active.time,
                        exit_time: time,
                        side: active.side,
                        entry_price: active.price,
                        exit_price: price,
                        price_diff: priceDiff,
                        size: size,
                        gross_pnl: gross,
                        fee: totalFee,
                        net_pnl: net,
                        net_pnl_inr: net * USD_TO_INR,
                        is_profit: isWin,
                        reason: isLong ? "Long Closed" : "Short Closed"
                    });
                    active = null;
                } else {
                    active = { side, price, size, fee, time };
                }
            }
            return trades;
        }

        function renderData(data) {
            document.getElementById('connection-status').innerText = "Delta India Connected";
            document.getElementById('connection-status').style.color = "var(--emerald)";

            // 1. Balances
            const availUsd = data.balances?.available_usd || 0;
            const availInr = availUsd * USD_TO_INR;
            document.getElementById('available-balance').innerText = `$${availUsd.toFixed(2)}`;
            document.getElementById('inr-balance').innerText = `≈ ${formatInr(availInr)} INR (Available)`;

            // 2. Positions & Dynamic Multiplier
            const pos = data.position || {};
            const size = parseFloat(pos.size || 0);
            const entryPrice = parseFloat(pos.entry_price || 0);
            const markPrice = parseFloat(data.market?.price || entryPrice);
            const contractVal = parseFloat(data.contract_value || (data.symbol?.includes('BTC') ? 0.001 : (data.symbol?.includes('SOL') ? 1.0 : 0.01)));
            const leverage = parseFloat(data.leverage || 100);
            const marginUsed = parseFloat(pos.margin || 0) || (size !== 0 && entryPrice > 0 ? (entryPrice * contractVal * Math.abs(size)) / leverage : 0);
            
            // Unrealized PnL: use position field or calculate from markPrice vs entryPrice
            let pnlUsd = parseFloat(pos.unrealized_pnl);
            if (isNaN(pnlUsd) || (pnlUsd === 0 && size !== 0 && entryPrice > 0 && markPrice > 0)) {
                const diff = size > 0 ? (markPrice - entryPrice) : (entryPrice - markPrice);
                pnlUsd = diff * Math.abs(size) * contractVal;
            }
            if (size === 0) pnlUsd = 0.0;
            const pnlInr = pnlUsd * USD_TO_INR;
            const roiPct = marginUsed > 0 ? (pnlUsd / marginUsed) * 100 : 0;

            const posBadge = document.getElementById('position-badge');
            if (size > 0) {
                posBadge.className = "badge-pill badge-buy mono";
                posBadge.innerText = "LONG 🟢";
            } else if (size < 0) {
                posBadge.className = "badge-pill badge-sell mono";
                posBadge.innerText = "SHORT 🔴";
            } else {
                posBadge.className = "badge-pill badge-flat mono";
                posBadge.innerText = "FLAT ⚪";
            }

            document.getElementById('position-size').innerText = `${Math.abs(size)} Lot${Math.abs(size) === 1 ? '' : 's'}`;
            document.getElementById('entry-price-display').innerText = entryPrice > 0 ? `Entry: $${entryPrice.toFixed(2)}` : 'Entry: Flat';
            document.getElementById('pos-symbol').innerText = data.symbol || 'ETHUSD';
            document.getElementById('mark-price').innerText = markPrice > 0 ? `$${markPrice.toFixed(2)}` : '--';
            document.getElementById('initial-margin').innerText = marginUsed > 0 ? `$${marginUsed.toFixed(2)} (${formatInr(marginUsed * USD_TO_INR)})` : '$0.00';

            // Unrealized PnL display
            const pnlElem = document.getElementById('live-pnl');
            const pnlInrElem = document.getElementById('live-pnl-inr');
            const roiBadge = document.getElementById('roi-badge');

            pnlElem.innerText = formatPnl(pnlUsd, true);
            pnlInrElem.innerText = `≈ ${formatInr(pnlInr, true)} INR`;

            if (pnlUsd > 0) {
                pnlElem.className = "card-value mono positive";
                roiBadge.className = "badge-pill badge-buy mono";
                roiBadge.innerText = `+${roiPct.toFixed(1)}% ROI`;
            } else if (pnlUsd < 0) {
                pnlElem.className = "card-value mono negative";
                roiBadge.className = "badge-pill badge-sell mono";
                roiBadge.innerText = `${roiPct.toFixed(1)}% ROI`;
            } else {
                pnlElem.className = "card-value mono";
                roiBadge.className = "badge-pill badge-flat mono";
                roiBadge.innerText = "0.0% ROI";
            }

            // Breakeven target
            const atrVal = parseFloat(data.market?.atr || 8.0);
            const beDist = (atrVal * 0.85);
            if (entryPrice > 0) {
                const beTarget = size > 0 ? entryPrice + beDist : entryPrice - beDist;
                document.getElementById('be-target').innerText = `$${beTarget.toFixed(2)} (+Breakeven)`;
            } else {
                document.getElementById('be-target').innerText = "--";
            }

            // Active Stop Loss & Trailing Status
            const activeSl = data.active_stop_price || 0;
            document.getElementById('active-stop-loss').innerText = activeSl > 0 ? `$${activeSl.toFixed(2)}` : 'None (Flat)';
            document.getElementById('trailing-status').innerText = data.breakeven_locked ? '🛡️ Breakeven: LOCKED (+Fee Covered)' : `Breakeven: Ready at +$${beDist.toFixed(2)}`;

            // 3. Trades Reconstructor & Statistics
            const rawTrades = (data.completed_trades && data.completed_trades.length > 0) ? data.completed_trades : [];
            const reconstructed = reconstructTradesFromFills(data.exchange_fills, contractVal);
            const allTrades = rawTrades.length >= reconstructed.length ? rawTrades : reconstructed;

            let totalTrades = allTrades.length;
            let profitableCount = allTrades.filter(t => (t.is_profit !== undefined ? t.is_profit : (parseFloat(t.net_pnl || 0) > 0))).length;
            let lossCount = totalTrades - profitableCount;
            let winRate = totalTrades > 0 ? (profitableCount / totalTrades) * 100 : 0;
            let totalGross = allTrades.reduce((acc, t) => acc + parseFloat(t.gross_pnl || 0), 0);
            let totalFees = allTrades.reduce((acc, t) => acc + Math.abs(parseFloat(t.fee || 0)), 0);
            let totalNet = totalGross - totalFees;
            let totalNetInr = totalNet * USD_TO_INR;

            if (totalTrades === 0 && data.stats && data.stats.total_trades > 0) {
                totalTrades = data.stats.total_trades;
                profitableCount = data.stats.profitable_trades || 0;
                lossCount = data.stats.loss_trades || 0;
                winRate = data.stats.win_rate || 0;
                totalFees = data.stats.total_fees || 0;
                totalGross = data.stats.total_gross_pnl || 0;
                totalNet = data.stats.total_net_pnl || 0;
                totalNetInr = data.stats.total_net_pnl_inr || (totalNet * USD_TO_INR);
            }

            const netPnlElem = document.getElementById('total-net-pnl');
            netPnlElem.innerText = formatPnl(totalNet, true);
            netPnlElem.className = totalNet >= 0 ? "card-value mono positive" : "card-value mono negative";

            document.getElementById('total-net-pnl-inr').innerText = `≈ ${formatInr(totalNetInr, true)} INR Net Profit`;
            document.getElementById('trade-outcomes').innerText = `${profitableCount} Won / ${lossCount} Lost`;
            document.getElementById('total-trades-count').innerText = `${totalTrades} Total Completed Trade${totalTrades === 1 ? '' : 's'}`;
            
            const winBadge = document.getElementById('winrate-badge');
            winBadge.innerText = `${winRate.toFixed(1)}% Win Rate`;
            winBadge.className = winRate >= 50 ? "badge-pill badge-buy mono" : "badge-pill badge-sell mono";

            document.getElementById('total-fees').innerText = formatFee(totalFees);
            document.getElementById('total-fees-inr').innerText = `≈ ${formatInr(totalFees * USD_TO_INR)} INR in Fees`;
            
            const grossPnlElem = document.getElementById('total-gross-pnl');
            grossPnlElem.innerText = formatPnl(totalGross, true);
            grossPnlElem.className = totalGross >= 0 ? "card-value mono positive" : "card-value mono negative";

            // 4. Indicators & Scalper Telemetry
            const fastEma = (data.market?.fast_ema !== undefined && data.market?.fast_ema > 0) ? data.market.fast_ema.toFixed(2) : (data.market?.ema ? (data.market.ema * 0.999).toFixed(2) : '--');
            const entryEma = (data.market?.ema !== undefined && data.market?.ema > 0) ? data.market.ema.toFixed(2) : '--';
            document.getElementById('val-ema').innerText = `$${fastEma} / $${entryEma}`;
            document.getElementById('val-rsi').innerText = (data.market?.rsi !== undefined && data.market?.rsi > 0) ? data.market.rsi.toFixed(1) : '--';
            document.getElementById('val-atr').innerText = (data.market?.atr !== undefined && data.market?.atr > 0) ? `$${data.market.atr.toFixed(2)}` : '--';

            // Scalp TP target
            const atrNum = parseFloat(data.market?.atr || 0);
            const livePrice = parseFloat(data.market?.price || 0);
            const scalpTpElem = document.getElementById('val-scalp-tp');
            if (scalpTpElem) {
                if (atrNum > 0 && livePrice > 0) {
                    const tpDist = (atrNum * 0.85).toFixed(2);
                    scalpTpElem.innerHTML = `+$${tpDist} <span style="font-size: 0.72rem; color: var(--text-muted);">(~$${(livePrice + (atrNum * 0.85)).toFixed(2)})</span>`;
                } else {
                    scalpTpElem.innerText = '+0.85 ATR';
                }
            }

            // Volume Filter Status
            const volElem = document.getElementById('val-volume-filter');
            if (volElem) {
                const volOk = data.market?.volume_confirmed;
                volElem.innerHTML = volOk 
                    ? `<span style="color: var(--emerald); font-weight: 700;">VOL OK ✅</span>` 
                    : `<span style="color: var(--amber); font-weight: 700;">LOW VOL ⚠️</span>`;
            }

            // 5. Orders Table
            const ordersTbody = document.getElementById('orders-table-body');
            const orders = data.open_orders || [];
            document.getElementById('orders-count').innerText = `${orders.length} Order${orders.length === 1 ? '' : 's'}`;

            if (orders.length > 0) {
                ordersTbody.innerHTML = orders.map(o => `
                    <tr>
                        <td style="color: var(--cyan);">${o.order_type || 'Stop Market'}</td>
                        <td style="color: ${o.side === 'buy' ? 'var(--emerald)' : 'var(--crimson)'}; font-weight: 700;">${(o.side || '').toUpperCase()}</td>
                        <td style="font-weight: 600;">$${parseFloat(o.stop_price || o.limit_price || 0).toFixed(2)}</td>
                        <td>${o.size || 1} Lot</td>
                        <td><span class="badge-pill badge-buy">OPEN</span></td>
                    </tr>
                `).join('');
            } else {
                ordersTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No active pending orders on Delta book</td></tr>';
            }

            // 6. TAB 1: Completed Trades Table
            const completedTbody = document.getElementById('completed-trades-body');
            document.getElementById('completed-count-badge').innerText = allTrades.length;

            if (allTrades.length > 0) {
                completedTbody.innerHTML = allTrades.map(t => {
                    const gross = parseFloat(t.gross_pnl || 0);
                    const fee = Math.abs(parseFloat(t.fee || 0));
                    const net = parseFloat(t.net_pnl !== undefined ? t.net_pnl : (gross - fee));
                    const netInr = parseFloat(t.net_pnl_inr !== undefined ? t.net_pnl_inr : (net * USD_TO_INR));
                    const isWin = t.is_profit !== undefined ? t.is_profit : (net > 0);
                    const side = String(t.side || 'BUY').toUpperCase();
                    const sideCol = side === 'BUY' ? 'var(--emerald)' : 'var(--crimson)';
                    const sideLabel = side === 'BUY' ? 'LONG 🟢' : 'SHORT 🔴';
                    const diff = parseFloat(t.price_diff !== undefined ? t.price_diff : ((side === 'BUY' ? 1 : -1) * (parseFloat(t.exit_price || 0) - parseFloat(t.entry_price || 0))));
                    const diffSign = diff > 0 ? '+' : '';

                    return `
                        <tr>
                            <td style="color: var(--text-muted); font-size: 0.78rem;">${t.entry_time || '--'} → ${t.exit_time || '--'}</td>
                            <td><span style="color: ${sideCol}; font-weight: 700;">${sideLabel}</span></td>
                            <td style="font-weight: 600;">$${parseFloat(t.entry_price || 0).toFixed(2)} → $${parseFloat(t.exit_price || 0).toFixed(2)}</td>
                            <td style="color: ${diff >= 0 ? 'var(--emerald)' : 'var(--crimson)'}; font-weight: 600;">${diffSign}$${diff.toFixed(2)}</td>
                            <td>${t.size || 1} Lot</td>
                            <td style="color: ${gross >= 0 ? 'var(--emerald)' : 'var(--crimson)'}; font-weight: 600;">${formatPnl(gross, true)}</td>
                            <td style="color: var(--amber); font-weight: 600;">-${formatFee(fee)}</td>
                            <td style="color: ${net >= 0 ? 'var(--emerald)' : 'var(--crimson)'}; font-weight: 700;">
                                ${formatPnl(net, true)} <span style="font-size: 0.75rem; opacity: 0.85;">(${formatInr(netInr, true)})</span>
                            </td>
                            <td><span class="badge-pill ${isWin ? 'badge-buy' : 'badge-sell'}">${isWin ? 'WIN 🏆' : 'LOSS 🔻'}</span></td>
                            <td style="color: var(--text-muted); font-size: 0.8rem;">${t.reason || 'Closed'}</td>
                        </tr>
                    `;
                }).join('');
            } else {
                completedTbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">No completed trades recorded yet</td></tr>';
            }

            // 7. TAB 2: Live Activity Logs
            const logsTbody = document.getElementById('logs-table-body');
            const logs = data.recent_logs || [];
            document.getElementById('logs-count-badge').innerText = logs.length;

            if (logs.length > 0) {
                logsTbody.innerHTML = logs.map(l => {
                    const gross = parseFloat(l.gross_pnl || 0);
                    const fee = Math.abs(parseFloat(l.fee || 0));
                    const net = parseFloat(l.net_pnl !== undefined ? l.net_pnl : (gross - fee));
                    const isClosed = l.status === 'CLOSED';
                    const actStr = String(l.action || '').toUpperCase();

                    let actionBadge = '';
                    if (actStr.includes('BUY')) actionBadge = '<span class="badge-pill badge-buy">BUY 🟢</span>';
                    else if (actStr.includes('SELL')) actionBadge = '<span class="badge-pill badge-sell">SELL 🔴</span>';
                    else if (actStr.includes('EXIT')) actionBadge = `<span class="badge-pill" style="background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3);">${actStr} 🟠</span>`;
                    else actionBadge = `<span class="badge-pill badge-flat">${actStr}</span>`;

                    return `
                        <tr>
                            <td style="color: var(--text-muted);">${l.time || '--'}</td>
                            <td>${actionBadge}</td>
                            <td style="font-weight: 600;">$${parseFloat(l.price || 0).toFixed(2)}</td>
                            <td>${l.stop_loss ? '$' + parseFloat(l.stop_loss).toFixed(2) : '--'}</td>
                            <td style="color: ${gross >= 0 ? 'var(--emerald)' : 'var(--crimson)'}; font-weight: 600;">${isClosed ? formatPnl(gross, true) : '--'}</td>
                            <td style="color: var(--amber); font-weight: 600;">${isClosed ? '-' + formatFee(fee) : (fee > 0 ? '-' + formatFee(fee) : '--')}</td>
                            <td style="color: ${net >= 0 ? 'var(--emerald)' : 'var(--crimson)'}; font-weight: 700;">${isClosed ? formatPnl(net, true) : '--'}</td>
                            <td style="color: var(--text-muted); font-size: 0.8rem;">${l.reason || '--'}</td>
                            <td><span class="badge-pill ${isClosed ? (net >= 0 ? 'badge-buy' : 'badge-sell') : (l.status === 'OPEN' ? 'badge-buy' : 'badge-flat')}">${l.status || 'EXECUTED'}</span></td>
                        </tr>
                    `;
                }).join('');
            }

            // 8. TAB 3: Delta Exchange Real Fills (With Accurate Fee Calculation)
            const fillsTbody = document.getElementById('fills-table-body');
            const fills = data.exchange_fills || [];
            document.getElementById('fills-count-badge').innerText = fills.length;

            if (fills.length > 0) {
                fillsTbody.innerHTML = fills.map(f => {
                    const side = (f.side || 'buy').toUpperCase();
                    const price = parseFloat(f.price || 0);
                    const size = parseFloat(f.size || 1);
                    const rawFee = f.paid_commission ?? f.fee ?? f.trading_fee ?? f.commission;
                    const fee = (rawFee !== undefined && rawFee !== null && rawFee !== '')
                        ? Math.abs(parseFloat(rawFee))
                        : (price * size * contractVal * 0.0005);
                    const timeStr = formatTimeIST(f.created_at);

                    return `
                        <tr>
                            <td style="color: var(--text-muted);">${timeStr} <span style="font-size: 0.7rem; opacity: 0.6;">(${f.created_at || ''})</span></td>
                            <td style="font-weight: 600;">${f.symbol || data.symbol}</td>
                            <td><span style="color: ${side === 'BUY' ? 'var(--emerald)' : 'var(--crimson)'}; font-weight: 700;">${side}</span></td>
                            <td style="font-weight: 600;">$${price.toFixed(2)}</td>
                            <td>${size} Lot</td>
                            <td style="color: var(--amber); font-weight: 600;">-${formatFee(fee)}</td>
                            <td><span class="badge-pill badge-flat">${f.role || 'taker'}</span></td>
                        </tr>
                    `;
                }).join('');
            }
        }

        async function emergencyClose() {
            if (!confirm("⚠️ Are you sure you want to EMERGENCY CLOSE all open positions immediately at market?")) return;
            try {
                const res = await fetch('/api/emergency_close', { method: 'POST' });
                const data = await res.json();
                alert(data.message || "Position closed successfully!");
                fetchDashboardData();
            } catch (e) {
                alert("Error closing position: " + e);
            }
        }

        fetchDashboardData();
        setInterval(fetchDashboardData, 2000);
    </script>
</body>
</html>
"""
