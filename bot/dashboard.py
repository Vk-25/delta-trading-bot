DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeltaBot Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0e17;
            --card-bg: rgba(20, 27, 45, 0.7);
            --card-border: rgba(45, 55, 72, 0.6);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --green: #10b981;
            --green-dim: rgba(16, 185, 129, 0.2);
            --red: #ef4444;
            --red-dim: rgba(239, 68, 68, 0.2);
            --cyan: #06b6d4;
            --amber: #f59e0b;
            --gray-bg: rgba(71, 85, 105, 0.2);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-dark);
            background-image: radial-gradient(circle at 15% 50%, rgba(6, 182, 212, 0.04) 0%, transparent 50%),
                              radial-gradient(circle at 85% 30%, rgba(16, 185, 129, 0.04) 0%, transparent 50%);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            line-height: 1.5;
            min-height: 100vh;
            padding: 20px;
        }

        .mono {
            font-family: 'JetBrains Mono', monospace;
        }

        .text-green { color: var(--green); }
        .text-red { color: var(--red); }
        .text-cyan { color: var(--cyan); }
        .text-amber { color: var(--amber); }
        .text-muted { color: var(--text-muted); }
        
        .badge-green { background: var(--green-dim); color: var(--green); padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }
        .badge-red { background: var(--red-dim); color: var(--red); padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }
        .badge-gray { background: var(--gray-bg); color: var(--text-secondary); padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }
        .badge-amber { background: rgba(245, 158, 11, 0.2); color: var(--amber); padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }
        .badge-cyan { background: rgba(6, 182, 212, 0.2); color: var(--cyan); padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
        }

        /* HEADER */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 20px;
            margin-bottom: 5px;
        }

        .header-left .title-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }

        .header-left h1 {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 14px;
            border-left: 2px solid var(--card-border);
            padding-left: 12px;
        }

        .pill-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .header-right {
            text-align: right;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
        }

        .status-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 500;
        }

        .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }

        .dot.green { background-color: var(--green); box-shadow: 0 0 8px var(--green); }
        .dot.red { background-color: var(--red); box-shadow: 0 0 8px var(--red); }

        .clock {
            font-size: 16px;
            color: var(--text-secondary);
        }

        .btn-refresh {
            background: transparent;
            border: 1px solid var(--card-border);
            color: var(--text-primary);
            padding: 4px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        
        .btn-refresh:hover {
            background: var(--gray-bg);
        }

        /* KPI ROW */
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }

        .kpi-card {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .kpi-label {
            color: var(--text-secondary);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .kpi-value {
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -1px;
        }

        .kpi-sub {
            color: var(--text-muted);
            font-size: 14px;
        }

        .kpi-footer {
            margin-top: auto;
            padding-top: 12px;
            border-top: 1px solid rgba(255,255,255,0.05);
            font-size: 12px;
            color: var(--text-muted);
        }

        /* LIVE POSITION PANEL */
        .position-panel {
            display: none; /* hidden by default */
        }
        
        .position-panel.active {
            display: block;
            border-color: rgba(6, 182, 212, 0.3);
            background: linear-gradient(to right, rgba(6, 182, 212, 0.05), transparent);
        }

        .pos-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
        }

        .pos-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }

        .pos-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .pos-item-label {
            color: var(--text-secondary);
            font-size: 12px;
        }

        .pos-item-value {
            font-size: 16px;
            font-weight: 600;
        }

        .pos-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            justify-content: flex-start;
            border-left: 1px solid var(--card-border);
            padding-left: 30px;
        }

        .unrealized-pnl {
            font-size: 36px;
            font-weight: 700;
            margin: 10px 0;
            letter-spacing: -1px;
        }

        .btn-emergency {
            margin-top: auto;
            background: rgba(239, 68, 68, 0.1);
            color: var(--red);
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }

        .btn-emergency:hover {
            background: var(--red);
            color: #fff;
        }

        .ts-bar-container {
            width: 100%;
            height: 6px;
            background: var(--gray-bg);
            border-radius: 3px;
            margin-top: 20px;
            position: relative;
        }

        .ts-marker {
            position: absolute;
            top: -15px;
            transform: translateX(-50%);
            font-size: 10px;
            color: var(--text-secondary);
            white-space: nowrap;
        }
        
        .ts-marker::after {
            content: '';
            display: block;
            width: 2px;
            height: 10px;
            background: var(--text-secondary);
            margin: 2px auto 0;
        }
        
        .ts-fill-red {
            position: absolute;
            height: 100%;
            background: var(--red);
            border-radius: 3px 0 0 3px;
        }
        
        .ts-fill-green {
            position: absolute;
            height: 100%;
            background: var(--green);
            border-radius: 0 3px 3px 0;
        }

        /* STATS BAR */
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 15px;
            padding: 15px 20px;
        }

        .stat-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            border-right: 1px solid var(--card-border);
        }
        
        .stat-item:last-child {
            border-right: none;
        }

        .stat-val {
            font-size: 20px;
            font-weight: 700;
            margin-top: 4px;
        }

        /* RISK GUARD */
        .risk-guard {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
        }
        
        .risk-guard.disabled {
            border-color: var(--red);
            background: rgba(239, 68, 68, 0.05);
        }

        .rg-center {
            display: flex;
            align-items: center;
            gap: 15px;
            flex: 1;
            justify-content: center;
        }

        .rg-progress {
            width: 200px;
            height: 6px;
            background: var(--gray-bg);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .rg-fill {
            height: 100%;
            background: var(--amber);
        }

        /* TABS & TABLES */
        .tabs-header {
            display: flex;
            gap: 30px;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 20px;
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-family: inherit;
            font-size: 14px;
            font-weight: 600;
            padding: 10px 0;
            cursor: pointer;
            position: relative;
        }

        .tab-btn.active {
            color: var(--text-primary);
        }

        .tab-btn.active::after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 100%;
            height: 2px;
            background: var(--cyan);
        }

        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        th {
            text-align: left;
            padding: 12px;
            color: var(--text-secondary);
            font-weight: 500;
            border-bottom: 1px solid var(--card-border);
        }

        td {
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.02);
        }
        
        tr:hover td {
            background: rgba(255,255,255,0.02);
        }

        .table-row-win { border-left: 2px solid var(--green); }
        .table-row-loss { border-left: 2px solid var(--red); }
        .table-row-open { border-left: 2px solid var(--cyan); background: rgba(6, 182, 212, 0.05); }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
            font-style: italic;
        }

        /* RESPONSIVE */
        @media (max-width: 900px) {
            .kpi-row { grid-template-columns: repeat(2, 1fr); }
            .pos-grid { grid-template-columns: 1fr; }
            .pos-right { border-left: none; border-top: 1px solid var(--card-border); padding-left: 0; padding-top: 20px; align-items: flex-start; }
            .stats-bar { grid-template-columns: repeat(3, 1fr); row-gap: 20px; }
            .stat-item:nth-child(3) { border-right: none; }
        }

        @media (max-width: 600px) {
            .kpi-row { grid-template-columns: 1fr; }
            .stats-bar { grid-template-columns: repeat(2, 1fr); }
            .stat-item:nth-child(even) { border-right: none; }
            .header { flex-direction: column; gap: 20px; }
            .header-right { align-items: flex-start; text-align: left; }
            .risk-guard { flex-direction: column; gap: 15px; align-items: flex-start; }
            .rg-center { width: 100%; justify-content: flex-start; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <header class="header">
            <div class="header-left">
                <div class="title-row">
                    <h1>⚡ DeltaBot</h1>
                    <span class="subtitle" id="el-strategy-name">Loading strategy...</span>
                </div>
                <div class="pill-group">
                    <span class="badge-amber" id="el-env">--</span>
                    <span class="badge-cyan" id="el-symbol">--</span>
                    <span class="badge-gray" id="el-timeframe">--</span>
                    <span class="badge-gray" id="el-leverage">--x</span>
                </div>
            </div>
            <div class="header-right">
                <div class="status-row">
                    <span class="dot red" id="el-status-dot"></span>
                    <span id="el-status-text">Disconnected</span>
                </div>
                <div class="clock mono" id="el-clock">00:00:00 IST</div>
                <button class="btn-refresh" onclick="fetchData()">Refresh Now</button>
            </div>
        </header>

        <!-- KPI ROW -->
        <div class="kpi-row">
            <!-- Card 1: Wallet -->
            <div class="card kpi-card">
                <div class="kpi-label">Wallet Balance</div>
                <div class="kpi-value mono" id="el-wallet-usd">--</div>
                <div class="kpi-sub mono" id="el-wallet-inr">--</div>
                <div class="kpi-footer" id="el-wallet-total">Total: --</div>
            </div>

            <!-- Card 2: Position -->
            <div class="card kpi-card">
                <div class="kpi-label">Position Status</div>
                <div style="margin-top: 4px;">
                    <span id="el-pos-badge" class="badge-gray">FLAT</span>
                </div>
                <div class="kpi-value mono" id="el-pos-entry" style="font-size: 20px; margin-top: 8px;">--</div>
                <div class="kpi-footer" id="el-pos-size">No Active Position</div>
            </div>

            <!-- Card 3: Today PnL -->
            <div class="card kpi-card">
                <div class="kpi-label">Today's P&L</div>
                <div class="kpi-value mono" id="el-today-usd">--</div>
                <div class="kpi-sub mono" id="el-today-inr">--</div>
                <div class="kpi-footer" id="el-today-trades">-- trades today</div>
            </div>

            <!-- Card 4: All-Time PnL -->
            <div class="card kpi-card">
                <div class="kpi-label">All-Time P&L</div>
                <div class="kpi-value mono" id="el-alltime-usd">--</div>
                <div class="kpi-sub mono" id="el-alltime-inr">--</div>
                <div class="kpi-footer" id="el-alltime-trades">-- total trades</div>
            </div>
        </div>

        <!-- LIVE POSITION PANEL -->
        <div id="el-pos-panel" class="card position-panel">
            <div class="pos-grid">
                <div class="pos-left">
                    <div class="kpi-label" style="margin-bottom: 15px; color: var(--cyan);">Live Trade Active</div>
                    <div class="pos-details">
                        <div class="pos-item">
                            <span class="pos-item-label">Entry Price</span>
                            <span class="pos-item-value mono" id="el-lp-entry">--</span>
                        </div>
                        <div class="pos-item">
                            <span class="pos-item-label">Initial Stop</span>
                            <span class="pos-item-value mono text-red" id="el-lp-istop">--</span>
                        </div>
                        <div class="pos-item">
                            <span class="pos-item-label">Active Trailing Stop</span>
                            <span class="pos-item-value mono text-amber" id="el-lp-tstop">--</span>
                        </div>
                        <div class="pos-item">
                            <span class="pos-item-label">Peak/Trough Price</span>
                            <span class="pos-item-value mono" id="el-lp-peak">--</span>
                        </div>
                        <div class="pos-item">
                            <span class="pos-item-label">Liquidation Price</span>
                            <span class="pos-item-value mono text-red" id="el-lp-liq">--</span>
                        </div>
                    </div>
                    
                    <!-- Visual Trailing Stop Bar -->
                    <div class="ts-bar-container" id="el-ts-bar">
                        <!-- Markers will be injected here via JS -->
                    </div>
                </div>
                
                <div class="pos-right">
                    <div class="kpi-label">Unrealized P&L</div>
                    <div class="unrealized-pnl mono" id="el-lp-upnl">--</div>
                    <div class="mono" id="el-lp-upnl-inr" style="color: var(--text-secondary); margin-bottom: 5px;">--</div>
                    <div class="mono" id="el-lp-roi" style="color: var(--text-muted); font-size: 13px;">ROI: --</div>
                    <div class="mono" id="el-lp-margin" style="color: var(--text-muted); font-size: 13px;">Margin: --</div>
                    
                    <button class="btn-emergency" onclick="emergencyClose()">Emergency Close</button>
                </div>
            </div>
        </div>

        <!-- STATS BAR -->
        <div class="card stats-bar">
            <div class="stat-item">
                <div class="kpi-label">Win Rate</div>
                <div class="stat-val mono" id="el-st-winrate">--%</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Profit Factor</div>
                <div class="stat-val mono" id="el-st-pf">--</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Avg Win</div>
                <div class="stat-val mono text-green" id="el-st-avgwin">--</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Avg Loss</div>
                <div class="stat-val mono text-red" id="el-st-avgloss">--</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Best Trade</div>
                <div class="stat-val mono text-green" id="el-st-best">--</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Worst Trade</div>
                <div class="stat-val mono text-red" id="el-st-worst">--</div>
            </div>
        </div>

        <!-- RISK GUARD -->
        <div class="card risk-guard" id="el-rg-container">
            <div class="status-row" style="min-width: 180px;">
                <span class="dot" id="el-rg-dot"></span>
                <span id="el-rg-text" style="font-weight: 600;">Risk Guard</span>
            </div>
            
            <div class="rg-center">
                <span class="kpi-label">Daily Loss</span>
                <div class="rg-progress">
                    <div class="rg-fill" id="el-rg-bar" style="width: 0%;"></div>
                </div>
                <span class="mono" id="el-rg-loss-txt" style="font-size: 12px;">-- / --</span>
            </div>
            
            <div style="min-width: 150px; text-align: right;">
                <span class="kpi-label">Loss Streak: </span>
                <span class="mono" id="el-rg-streak">-- / --</span>
            </div>
        </div>

        <!-- TABBED HISTORY -->
        <div class="card">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="switchTab('tab-trades')">Trade History</button>
                <button class="tab-btn" onclick="switchTab('tab-live')">Live Activity</button>
                <button class="tab-btn" onclick="switchTab('tab-orders')">Open Orders</button>
                <button class="tab-btn" onclick="switchTab('tab-fills')">Exchange Fills</button>
            </div>
            
            <div class="tab-content active" id="tab-trades">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Entry Time</th>
                                <th>Exit Time</th>
                                <th>Side</th>
                                <th>Entry Price</th>
                                <th>Exit Price</th>
                                <th>Points</th>
                                <th>Gross PnL</th>
                                <th>Fee</th>
                                <th>Net PnL</th>
                                <th>Exit Reason</th>
                                <th>Result</th>
                            </tr>
                        </thead>
                        <tbody id="tb-trades">
                            <tr><td colspan="11" class="empty-state">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="tab-content" id="tab-live">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Action</th>
                                <th>Reason</th>
                                <th>Price</th>
                                <th>Stop Loss</th>
                                <th>Gross PnL</th>
                                <th>Fee</th>
                                <th>Net PnL</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="tb-live">
                            <tr><td colspan="9" class="empty-state">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="tab-content" id="tab-orders">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Type</th>
                                <th>Side</th>
                                <th>Stop Price</th>
                                <th>Size</th>
                                <th>State</th>
                            </tr>
                        </thead>
                        <tbody id="tb-orders">
                            <tr><td colspan="6" class="empty-state">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="tab-content" id="tab-fills">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Side</th>
                                <th>Price</th>
                                <th>Size</th>
                                <th>Fee</th>
                                <th>Role</th>
                            </tr>
                        </thead>
                        <tbody id="tb-fills">
                            <tr><td colspan="6" class="empty-state">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const USD_TO_INR = 87.50;
        let fetchTimer = null;

        // Number formatters
        function formatUSD(val, decimals = 2) {
            if (val === null || val === undefined) return '--';
            const num = Number(val);
            const isNeg = num < 0;
            return (isNeg ? '-' : '') + '$' + Math.abs(num).toFixed(decimals);
        }

        function formatINR(val) {
            if (val === null || val === undefined) return '--';
            const num = Number(val);
            const isNeg = num < 0;
            return (isNeg ? '-' : '') + '\u20B9' + Math.abs(num).toLocaleString('en-IN', { maximumFractionDigits: 0 });
        }

        function formatPrice(val) {
            if (val === null || val === undefined) return '--';
            return Number(val).toFixed(2);
        }
        
        function formatColorClass(val) {
            if (val === null || val === undefined) return '';
            const num = Number(val);
            if (num > 0) return 'text-green';
            if (num < 0) return 'text-red';
            return '';
        }

        // Tab Switching
        function switchTab(tabId) {
            const btns = document.querySelectorAll('.tab-btn');
            for (let i = 0; i < btns.length; i++) {
                btns[i].classList.remove('active');
            }
            
            const contents = document.querySelectorAll('.tab-content');
            for (let i = 0; i < contents.length; i++) {
                contents[i].classList.remove('active');
            }
            
            event.currentTarget.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }

        // IST Clock
        function updateClock() {
            const now = new Date();
            const options = { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            const timeString = now.toLocaleTimeString('en-US', options);
            document.getElementById('el-clock').innerText = timeString + ' IST';
        }
        setInterval(updateClock, 1000);
        updateClock();

        // Emergency Close
        function emergencyClose() {
            if (confirm('EMERGENCY CLOSE: Are you sure you want to market close the active position?')) {
                fetch('/api/emergency_close', { method: 'POST' })
                    .then(function(res) { return res.json(); })
                    .then(function(data) {
                        alert('Emergency close command sent successfully.');
                        fetchData();
                    })
                    .catch(function(err) {
                        alert('Error sending emergency close command: ' + err);
                    });
            }
        }

        // Main Data Fetch
        function fetchData() {
            fetch('/api/dashboard')
                .then(function(res) {
                    if (!res.ok) throw new Error('Network response was not ok');
                    return res.json();
                })
                .then(function(data) {
                    updateDashboard(data);
                    setConnectionStatus(true);
                })
                .catch(function(err) {
                    console.error('Fetch error:', err);
                    setConnectionStatus(false);
                });
        }

        function setConnectionStatus(isConnected) {
            const dot = document.getElementById('el-status-dot');
            const text = document.getElementById('el-status-text');
            if (isConnected) {
                dot.className = 'dot green';
                text.innerText = 'Connected';
            } else {
                dot.className = 'dot red';
                text.innerText = 'Disconnected';
            }
        }

        function updateDashboard(data) {
            // Header
            document.getElementById('el-strategy-name').innerText = data.strategy_name || '--';
            document.getElementById('el-env').innerText = data.environment || '--';
            
            let symDisplay = data.symbol || '--';
            if (data.symbols && data.symbols.length > 1) {
                symDisplay = data.symbols.join(' + ');
            }
            document.getElementById('el-symbol').innerText = symDisplay;
            document.getElementById('el-timeframe').innerText = data.timeframe || '--';
            document.getElementById('el-leverage').innerText = (data.leverage || '--') + 'x';

            // Wallet
            const wallet = data.wallet || {};
            document.getElementById('el-wallet-usd').innerText = formatUSD(wallet.available_balance);
            document.getElementById('el-wallet-inr').innerText = formatINR((wallet.available_balance || 0) * USD_TO_INR);
            document.getElementById('el-wallet-total').innerText = 'Total: ' + formatUSD(wallet.balance);

            // Active Symbol Resolution
            let activeSymData = null;
            if (data.symbols_data && data.symbols_data.length > 0) {
                for (let i = 0; i < data.symbols_data.length; i++) {
                    if (data.symbols_data[i].strategy && data.symbols_data[i].strategy.position_state !== 0) {
                        activeSymData = data.symbols_data[i];
                        break;
                    }
                }
                if (!activeSymData) {
                    activeSymData = data.symbols_data[0];
                }
            }

            const strategy = activeSymData ? activeSymData.strategy : (data.strategy || {});
            const posState = strategy.position_state || 0;
            const currentPosition = activeSymData ? activeSymData.position : (data.position || {});
            const currentSymbol = activeSymData ? activeSymData.symbol : (data.symbol || '');
            const currentLeverage = activeSymData ? activeSymData.leverage : (data.leverage || '--');

            // Position Card
            const posBadge = document.getElementById('el-pos-badge');
            const posEntry = document.getElementById('el-pos-entry');
            const posSize = document.getElementById('el-pos-size');
            
            if (posState === 1) {
                posBadge.className = 'badge-green';
                posBadge.innerText = (currentSymbol ? currentSymbol + ' ' : '') + 'LONG';
                posEntry.innerText = formatPrice(strategy.entry_price);
                posSize.innerText = 'Size: ' + (currentPosition ? currentPosition.size : '--') + ' Lots (' + currentLeverage + 'x)';
            } else if (posState === -1) {
                posBadge.className = 'badge-red';
                posBadge.innerText = (currentSymbol ? currentSymbol + ' ' : '') + 'SHORT';
                posEntry.innerText = formatPrice(strategy.entry_price);
                posSize.innerText = 'Size: ' + (currentPosition ? currentPosition.size : '--') + ' Lots (' + currentLeverage + 'x)';
            } else {
                posBadge.className = 'badge-gray';
                posBadge.innerText = 'FLAT';
                posEntry.innerText = '--';
                posSize.innerText = (data.symbols && data.symbols.length > 1 ? data.symbols.join(', ') + ' Monitoring' : 'No Active Position');
            }

            // PnL Cards
            const stats = data.stats || {};
            
            const elTodayUsd = document.getElementById('el-today-usd');
            elTodayUsd.innerText = formatUSD(stats.daily_pnl);
            elTodayUsd.className = 'kpi-value mono ' + formatColorClass(stats.daily_pnl);
            document.getElementById('el-today-inr').innerText = formatINR((stats.daily_pnl || 0) * USD_TO_INR);
            document.getElementById('el-today-trades').innerText = (stats.today_trades || 0) + ' trades today';

            const elAlltimeUsd = document.getElementById('el-alltime-usd');
            elAlltimeUsd.innerText = formatUSD(stats.total_net_pnl);
            elAlltimeUsd.className = 'kpi-value mono ' + formatColorClass(stats.total_net_pnl);
            document.getElementById('el-alltime-inr').innerText = formatINR((stats.total_net_pnl || 0) * USD_TO_INR);
            document.getElementById('el-alltime-trades').innerText = (stats.total_trades || 0) + ' total trades';

            // Live Position Panel
            const posPanel = document.getElementById('el-pos-panel');
            if (posState !== 0 && currentPosition) {
                posPanel.classList.add('active');
                
                document.getElementById('el-lp-entry').innerText = formatPrice(strategy.entry_price);
                document.getElementById('el-lp-istop').innerText = formatPrice(strategy.initial_stop_loss);
                document.getElementById('el-lp-tstop').innerText = formatPrice(strategy.active_trailing_stop);
                
                const peak = posState === 1 ? strategy.highest_price : strategy.lowest_price;
                document.getElementById('el-lp-peak').innerText = formatPrice(peak);
                document.getElementById('el-lp-liq').innerText = formatPrice(currentPosition.liquidation_price);
                
                const upnl = currentPosition.unrealized_pnl || 0;
                const elUpnl = document.getElementById('el-lp-upnl');
                elUpnl.innerText = formatUSD(upnl);
                elUpnl.className = 'unrealized-pnl mono ' + formatColorClass(upnl);
                document.getElementById('el-lp-upnl-inr').innerText = formatINR(upnl * USD_TO_INR);
                
                // Margin & ROI
                const cv = strategy.contract_value || 0.01;
                const lev = currentLeverage || 1;
                const size = Math.abs(currentPosition.size || 0);
                const ep = strategy.entry_price || 0;
                
                let margin = 0;
                if (lev > 0) {
                    margin = (ep * cv * size) / lev;
                }
                
                document.getElementById('el-lp-margin').innerText = 'Margin Used: ' + formatUSD(margin) + ' (' + currentSymbol + ')';
                
                if (margin > 0) {
                    const roi = (upnl / margin) * 100;
                    document.getElementById('el-lp-roi').innerText = 'ROI: ' + roi.toFixed(2) + '%';
                    document.getElementById('el-lp-roi').className = 'mono ' + formatColorClass(roi);
                } else {
                    document.getElementById('el-lp-roi').innerText = 'ROI: --%';
                    document.getElementById('el-lp-roi').className = 'mono';
                }

                // Trailing Stop Visual Bar
                renderTrailingStopBar(posState, strategy.initial_stop_loss, strategy.entry_price, strategy.active_trailing_stop, peak);

            } else {
                posPanel.classList.remove('active');
            }

            // Stats Bar
            document.getElementById('el-st-winrate').innerText = (stats.win_rate !== undefined ? stats.win_rate.toFixed(1) : '--') + '%';
            document.getElementById('el-st-pf').innerText = stats.profit_factor !== undefined ? stats.profit_factor.toFixed(2) : '--';
            document.getElementById('el-st-avgwin').innerText = formatUSD(stats.avg_win);
            document.getElementById('el-st-avgloss').innerText = formatUSD(stats.avg_loss);
            document.getElementById('el-st-best').innerText = formatUSD(stats.best_trade);
            document.getElementById('el-st-worst').innerText = formatUSD(stats.worst_trade);

            // Risk Guard
            const rg = data.risk_guard || {};
            const rgContainer = document.getElementById('el-rg-container');
            const rgDot = document.getElementById('el-rg-dot');
            const rgText = document.getElementById('el-rg-text');
            
            if (rg.trading_enabled) {
                rgContainer.classList.remove('disabled');
                rgDot.className = 'dot green';
                rgText.innerText = 'Trading Active';
            } else {
                rgContainer.classList.add('disabled');
                rgDot.className = 'dot red';
                rgText.innerText = 'Trading Disabled';
            }
            
            const dLoss = rg.daily_pnl_pct !== undefined ? rg.daily_pnl_pct : 0;
            const mLoss = rg.max_daily_loss_pct || 1;
            document.getElementById('el-rg-loss-txt').innerText = dLoss.toFixed(2) + '% / -' + mLoss.toFixed(2) + '%';
            
            let prog = 0;
            if (dLoss < 0) {
                prog = (Math.abs(dLoss) / mLoss) * 100;
                if (prog > 100) prog = 100;
            }
            document.getElementById('el-rg-bar').style.width = prog + '%';
            
            document.getElementById('el-rg-streak').innerText = (rg.consecutive_losses || 0) + ' / ' + (rg.max_consecutive_losses || '--');

            // Tables
            renderTable('tb-trades', data.completed_trades, renderTradeRow);
            renderTable('tb-live', data.recent_logs, renderLiveRow);
            renderTable('tb-orders', data.open_orders, renderOrderRow);
            renderTable('tb-fills', data.exchange_fills, renderFillRow);
        }

        function renderTrailingStopBar(posState, initialStop, entryPrice, activeStop, peak) {
            const container = document.getElementById('el-ts-bar');
            container.innerHTML = ''; // clear

            if (!initialStop || !entryPrice || !activeStop || !peak) return;

            // Define range min and max for the bar
            let minPrice, maxPrice;
            if (posState === 1) {
                minPrice = initialStop;
                maxPrice = Math.max(peak, entryPrice * 1.01); // fallback max if peak is close
            } else {
                minPrice = Math.min(peak, entryPrice * 0.99);
                maxPrice = initialStop;
            }
            
            const range = Math.abs(maxPrice - minPrice);
            if (range === 0) return;

            function getPct(price) {
                if (posState === 1) {
                    return ((price - minPrice) / range) * 100;
                } else {
                    return ((maxPrice - price) / range) * 100;
                }
            }

            const entryPct = getPct(entryPrice);
            const stopPct = getPct(activeStop);

            // Draw segments
            // Red segment from initial stop (0%) to entry price
            const redFill = document.createElement('div');
            redFill.className = 'ts-fill-red';
            redFill.style.width = Math.min(100, Math.max(0, entryPct)) + '%';
            redFill.style.left = '0%';
            container.appendChild(redFill);
            
            // Green segment from entry to active stop if stop is in profit
            if (stopPct > entryPct) {
                const greenFill = document.createElement('div');
                greenFill.className = 'ts-fill-green';
                greenFill.style.left = entryPct + '%';
                greenFill.style.width = Math.min(100, (stopPct - entryPct)) + '%';
                container.appendChild(greenFill);
            }

            // Entry marker
            const mEntry = document.createElement('div');
            mEntry.className = 'ts-marker';
            mEntry.style.left = entryPct + '%';
            mEntry.innerText = 'Entry';
            container.appendChild(mEntry);

            // Stop marker
            const mStop = document.createElement('div');
            mStop.className = 'ts-marker';
            mStop.style.left = stopPct + '%';
            mStop.style.color = stopPct > entryPct ? 'var(--green)' : 'var(--amber)';
            mStop.innerText = 'Stop';
            container.appendChild(mStop);
        }

        // Table Renderers
        function renderTable(tbodyId, dataArray, rowRenderer) {
            const tbody = document.getElementById(tbodyId);
            tbody.innerHTML = '';
            
            if (!dataArray || dataArray.length === 0) {
                tbody.innerHTML = '<tr><td colspan="12" class="empty-state">No data available</td></tr>';
                return;
            }
            
            for (let i = 0; i < dataArray.length; i++) {
                tbody.innerHTML += rowRenderer(dataArray[i]);
            }
        }

        function renderTradeRow(t) {
            const rowClass = t.win ? 'table-row-win' : 'table-row-loss';
            const sideBadge = t.side === 'BUY' ? '<span class="badge-green">BUY</span>' : '<span class="badge-red">SELL</span>';
            const resBadge = t.win ? '<span class="badge-green">WIN</span>' : '<span class="badge-red">LOSS</span>';
            const symBadge = t.symbol ? '<span class="badge-gray" style="margin-right:6px;">' + t.symbol + '</span>' : '';
            
            return '<tr class="' + rowClass + '">' +
                '<td>' + (t.entry_time || '--') + '</td>' +
                '<td>' + (t.exit_time || '--') + '</td>' +
                '<td>' + symBadge + sideBadge + '</td>' +
                '<td class="mono">' + formatPrice(t.entry_price) + '</td>' +
                '<td class="mono">' + formatPrice(t.exit_price) + '</td>' +
                '<td class="mono">' + (t.points !== undefined ? t.points.toFixed(2) : '--') + '</td>' +
                '<td class="mono">' + formatUSD(t.gross_pnl) + '</td>' +
                '<td class="mono text-amber">' + formatUSD(t.fees) + '</td>' +
                '<td class="mono ' + formatColorClass(t.net_pnl) + '">' + formatUSD(t.net_pnl) + '</td>' +
                '<td>' + (t.exit_reason || '--') + '</td>' +
                '<td>' + resBadge + '</td>' +
            '</tr>';
        }

        function renderLiveRow(l) {
            let rowClass = '';
            if (l.status === 'OPEN') rowClass = 'table-row-open';
            
            let actBadge = '<span class="badge-gray">' + l.action + '</span>';
            if (l.action === 'BUY') actBadge = '<span class="badge-green">BUY</span>';
            if (l.action === 'SELL') actBadge = '<span class="badge-red">SELL</span>';
            const symBadge = l.symbol ? '<span class="badge-gray" style="margin-right:6px;">' + l.symbol + '</span>' : '';

            return '<tr class="' + rowClass + '">' +
                '<td>' + (l.time || '--') + '</td>' +
                '<td>' + symBadge + actBadge + '</td>' +
                '<td>' + (l.reason || '--') + '</td>' +
                '<td class="mono">' + formatPrice(l.price) + '</td>' +
                '<td class="mono">' + formatPrice(l.stop_loss) + '</td>' +
                '<td class="mono">' + formatUSD(l.gross_pnl) + '</td>' +
                '<td class="mono text-amber">' + formatUSD(l.fee) + '</td>' +
                '<td class="mono ' + formatColorClass(l.net_pnl) + '">' + formatUSD(l.net_pnl) + '</td>' +
                '<td>' + (l.status || '--') + '</td>' +
            '</tr>';
        }

        function renderOrderRow(o) {
            let sideBadge = '<span class="badge-gray">' + o.side + '</span>';
            if (o.side && o.side.toLowerCase() === 'buy') sideBadge = '<span class="badge-green">BUY</span>';
            if (o.side && o.side.toLowerCase() === 'sell') sideBadge = '<span class="badge-red">SELL</span>';
            const symBadge = o.symbol ? '<span class="badge-gray" style="margin-right:6px;">' + o.symbol + '</span>' : '';
            
            return '<tr>' +
                '<td>' + (o.id || '--') + '</td>' +
                '<td>' + (o.order_type || '--') + '</td>' +
                '<td>' + symBadge + sideBadge + '</td>' +
                '<td class="mono">' + formatPrice(o.stop_price || o.limit_price) + '</td>' +
                '<td class="mono">' + (o.size || '--') + '</td>' +
                '<td>' + (o.state || '--') + '</td>' +
            '</tr>';
        }

        function renderFillRow(f) {
            let sideBadge = '<span class="badge-gray">' + f.side + '</span>';
            if (f.side && f.side.toLowerCase() === 'buy') sideBadge = '<span class="badge-green">BUY</span>';
            if (f.side && f.side.toLowerCase() === 'sell') sideBadge = '<span class="badge-red">SELL</span>';
            const symBadge = f.symbol ? '<span class="badge-gray" style="margin-right:6px;">' + f.symbol + '</span>' : '';
            
            let timeStr = '--';
            if (f.created_at) {
                const d = new Date(f.created_at);
                timeStr = d.toLocaleTimeString('en-US', { hour12: false });
            }

            return '<tr>' +
                '<td>' + timeStr + '</td>' +
                '<td>' + symBadge + sideBadge + '</td>' +
                '<td class="mono">' + formatPrice(f.price) + '</td>' +
                '<td class="mono">' + (f.size || '--') + '</td>' +
                '<td class="mono text-amber">' + formatUSD(f.fee) + '</td>' +
                '<td>' + (f.role || '--') + '</td>' +
            '</tr>';
        }

        // Initial Start
        fetchData();
        setInterval(fetchData, 2000);

    </script>
</body>
</html>
"""
