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
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }

        .card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.25rem;
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }

        .card:hover {
            border-color: rgba(255, 255, 255, 0.15);
            background: var(--bg-card-hover);
        }

        .card-label {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #fff;
            line-height: 1.2;
            margin-bottom: 0.25rem;
        }

        .card-sub {
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        .positive {
            color: var(--emerald) !important;
        }
        .negative {
            color: var(--crimson) !important;
        }

        .badge-pill {
            display: inline-block;
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            font-weight: 600;
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
            border: 1px solid rgba(148, 163, 184, 0.3);
        }

        /* MAIN CONTENT SPLIT */
        .grid-split {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }

        @media (max-width: 950px) {
            .grid-split {
                grid-template-columns: 1fr;
            }
        }

        .section-header {
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        /* POSITION HERO */
        .position-box {
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.75rem;
        }

        .pos-item {
            display: flex;
            flex-direction: column;
        }
        .pos-item-title {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }
        .pos-item-value {
            font-size: 1rem;
            font-weight: 600;
            margin-top: 0.2rem;
        }

        /* TELEMETRY METERS */
        .telemetry-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
        }
        .tele-card {
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.85rem;
            text-align: center;
        }
        .tele-title {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }
        .tele-val {
            font-size: 1.15rem;
            font-weight: 700;
            margin-top: 0.25rem;
        }

        /* TABLE */
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
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <header>
            <div class="brand">
                <div class="brand-logo">Δ</div>
                <div class="brand-title">
                    <h1>DeltaBot Live Dashboard</h1>
                    <p>ETHUSD • 15m Timeframe • 100x Precision Strategy (Strict Body Cut)</p>
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

        <!-- KPI CARDS -->
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
                    <span>⚡ Strategy Indicators (5m Live)</span>
                </div>
                <div class="telemetry-grid mono">
                    <div class="tele-card">
                        <div class="tele-title">21 EMA</div>
                        <div class="tele-val" style="color: var(--cyan);" id="val-ema">0.00</div>
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
                        <div class="tele-title">EMA Slope</div>
                        <div class="tele-val" id="val-slope">--</div>
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

        <!-- RECENT ACTIVITY LOGS -->
        <div class="card">
            <div class="section-header">
                <span>📜 Live Execution & Signal Feed</span>
                <span class="mono" style="font-size: 0.75rem; color: var(--emerald);">Auto-updates every 2s</span>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Time (IST)</th>
                            <th>Action</th>
                            <th>Trigger Reason</th>
                            <th>Price</th>
                            <th>Stop Loss / Trailing</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="logs-table-body" class="mono">
                        <tr>
                            <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Awaiting trade events...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const USD_TO_INR = 86.50;

        function updateClock() {
            const now = new Date();
            const istOptions = { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            document.getElementById('clock').innerText = now.toLocaleTimeString('en-GB', istOptions) + ' IST';
        }
        setInterval(updateClock, 1000);
        updateClock();

        async function fetchDashboardData() {
            try {
                const res = await fetch('/api/dashboard');
                if (!res.ok) throw new Error('API offline');
                const data = await res.json();
                renderData(data);
            } catch (e) {
                console.error("Dashboard fetch error:", e);
                document.getElementById('connection-status').innerText = "Connecting...";
            }
        }

        function renderData(data) {
            document.getElementById('connection-status').innerText = "Delta India Connected";

            // 1. Balances
            const availUsd = data.balances?.available_usd || 0;
            const availInr = availUsd * USD_TO_INR;
            document.getElementById('available-balance').innerText = `$${availUsd.toFixed(2)}`;
            document.getElementById('inr-balance').innerText = `≈ ₹${availInr.toFixed(2)} INR (Available)`;

            // 2. Position
            const pos = data.position || {};
            const size = parseFloat(pos.size || 0);
            const entryPrice = parseFloat(pos.entry_price || 0);
            const markPrice = parseFloat(pos.mark_price || data.market?.price || 0);
            const pnlUsd = parseFloat(pos.unrealized_pnl || 0);
            const pnlInr = pnlUsd * USD_TO_INR;

            // Margin & ROI
            const marginUsed = size !== 0 ? (Math.abs(size) * 0.01 * entryPrice) / 100 : 0;
            const roiPct = marginUsed > 0 ? (pnlUsd / marginUsed) * 100 : 0;

            // Update Position Cards
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
            document.getElementById('initial-margin').innerText = marginUsed > 0 ? `$${marginUsed.toFixed(2)} (₹${(marginUsed*USD_TO_INR).toFixed(1)})` : '$0.00';

            // PnL display
            const pnlElem = document.getElementById('live-pnl');
            const pnlInrElem = document.getElementById('live-pnl-inr');
            const roiBadge = document.getElementById('roi-badge');

            pnlElem.innerText = `${pnlUsd >= 0 ? '+' : ''}$${pnlUsd.toFixed(3)}`;
            pnlInrElem.innerText = `≈ ${pnlInr >= 0 ? '+' : ''}₹${pnlInr.toFixed(2)} INR`;

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
            if (entryPrice > 0) {
                const beTarget = size > 0 ? entryPrice + 2.43 : entryPrice - 2.43;
                document.getElementById('be-target').innerText = `$${beTarget.toFixed(2)} (+9% ROI)`;
            } else {
                document.getElementById('be-target').innerText = "--";
            }

            // Active Stop Loss & Trailing Status
            const activeSl = data.active_stop_price || 0;
            document.getElementById('active-stop-loss').innerText = activeSl > 0 ? `$${activeSl.toFixed(2)}` : 'None (Flat)';
            document.getElementById('trailing-status').innerText = data.breakeven_locked ? '🛡️ Breakeven: LOCKED (+Fee Covered)' : 'Breakeven: Ready at +$2.43';

            // Indicators
            document.getElementById('val-ema').innerText = data.market?.ema ? data.market.ema.toFixed(2) : '--';
            document.getElementById('val-rsi').innerText = data.market?.rsi ? data.market.rsi.toFixed(1) : '--';
            document.getElementById('val-atr').innerText = data.market?.atr ? `$${data.market.atr.toFixed(2)}` : '--';
            document.getElementById('val-slope').innerText = data.market?.slope || '--';

            // Orders Table
            const ordersTbody = document.getElementById('orders-table-body');
            const orders = data.open_orders || [];
            document.getElementById('orders-count').innerText = `${orders.length} Order${orders.length === 1 ? '' : 's'}`;

            if (orders.length > 0) {
                ordersTbody.innerHTML = orders.map(o => `
                    <tr>
                        <td style="color: var(--cyan);">${o.order_type || 'Stop Market'}</td>
                        <td style="color: ${o.side === 'buy' ? 'var(--emerald)' : 'var(--crimson)'};">${(o.side || '').toUpperCase()}</td>
                        <td style="font-weight: 600;">$${parseFloat(o.stop_price || o.limit_price || 0).toFixed(2)}</td>
                        <td>${o.size || 1} Lot</td>
                        <td><span class="badge-pill badge-buy">OPEN</span></td>
                    </tr>
                `).join('');
            } else {
                ordersTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No active pending orders on Delta book</td></tr>';
            }

            // Logs Table
            const logsTbody = document.getElementById('logs-table-body');
            const logs = data.recent_logs || [];
            if (logs.length > 0) {
                logsTbody.innerHTML = logs.map(l => `
                    <tr>
                        <td style="color: var(--text-muted);">${l.time}</td>
                        <td style="color: ${l.action.includes('BUY') ? 'var(--emerald)' : (l.action.includes('SELL') ? 'var(--crimson)' : 'var(--amber)')}; font-weight: 700;">${l.action}</td>
                        <td>${l.reason}</td>
                        <td>$${parseFloat(l.price || 0).toFixed(2)}</td>
                        <td style="color: var(--cyan);">${l.stop_loss ? '$' + parseFloat(l.stop_loss).toFixed(2) : '--'}</td>
                        <td><span class="badge-pill badge-buy">EXECUTED</span></td>
                    </tr>
                `).join('');
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

        // Auto poll every 2 seconds
        setInterval(fetchDashboardData, 2000);
        fetchDashboardData();
    </script>
</body>
</html>
"""
