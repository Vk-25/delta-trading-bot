DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeltaBot | Multi-Asset Live Trading Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #07090e;
            --card-bg: rgba(15, 21, 37, 0.75);
            --card-border: rgba(38, 50, 77, 0.6);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --green: #10b981;
            --green-glow: rgba(16, 185, 129, 0.2);
            --red: #ef4444;
            --red-glow: rgba(239, 68, 68, 0.2);
            --cyan: #06b6d4;
            --cyan-glow: rgba(6, 182, 212, 0.2);
            --gold: #f59e0b;
            --gold-glow: rgba(245, 158, 11, 0.2);
            --purple: #8b5cf6;
            --gray-bg: rgba(51, 65, 85, 0.3);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(245, 158, 11, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(6, 182, 212, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.03) 0%, transparent 60%);
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
        .text-gold { color: var(--gold); }
        .text-muted { color: var(--text-muted); }
        
        .badge-green { background: var(--green-glow); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 8px; border-radius: 5px; font-weight: 600; font-size: 11px; }
        .badge-red { background: var(--red-glow); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.3); padding: 3px 8px; border-radius: 5px; font-weight: 600; font-size: 11px; }
        .badge-gray { background: var(--gray-bg); color: var(--text-secondary); border: 1px solid rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 5px; font-weight: 600; font-size: 11px; }
        .badge-gold { background: var(--gold-glow); color: var(--gold); border: 1px solid rgba(245, 158, 11, 0.3); padding: 3px 8px; border-radius: 5px; font-weight: 600; font-size: 11px; }
        .badge-eth { background: var(--cyan-glow); color: var(--cyan); border: 1px solid rgba(6, 182, 212, 0.3); padding: 3px 8px; border-radius: 5px; font-weight: 600; font-size: 11px; }

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
            backdrop-filter: blur(8px);
        }

        /* HEADER */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 18px;
        }

        .header-left .title-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }

        .header-left h1 {
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #f8fafc, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 13px;
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
            gap: 6px;
        }

        .status-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            font-size: 13px;
        }

        .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }

        .dot.green { background-color: var(--green); box-shadow: 0 0 10px var(--green); }
        .dot.red { background-color: var(--red); box-shadow: 0 0 10px var(--red); }

        .clock {
            font-size: 15px;
            color: var(--text-secondary);
        }

        .btn-refresh {
            background: rgba(255,255,255,0.04);
            border: 1px solid var(--card-border);
            color: var(--text-primary);
            padding: 4px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .btn-refresh:hover {
            background: var(--gray-bg);
            border-color: var(--cyan);
        }

        /* KPI ROW */
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }

        .kpi-card {
            display: flex;
            flex-direction: column;
            gap: 6px;
            position: relative;
            overflow: hidden;
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: transparent;
        }

        .kpi-card.profit::before { background: linear-gradient(90deg, var(--green), var(--cyan)); }
        .kpi-card.wallet::before { background: linear-gradient(90deg, var(--cyan), var(--purple)); }

        .kpi-label {
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .kpi-value {
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }

        .kpi-sub {
            color: var(--text-muted);
            font-size: 13px;
        }

        .kpi-footer {
            margin-top: auto;
            padding-top: 8px;
            border-top: 1px solid rgba(255,255,255,0.04);
            font-size: 12px;
            color: var(--text-muted);
        }

        /* DUAL ASSET TELEMETRY CARDS */
        .dual-assets-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        .asset-card {
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 18px;
            background: var(--card-bg);
            display: flex;
            flex-direction: column;
            gap: 12px;
            position: relative;
        }

        .asset-card.gold-card {
            border-left: 3px solid var(--gold);
        }

        .asset-card.eth-card {
            border-left: 3px solid var(--cyan);
        }

        .asset-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .asset-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 16px;
            font-weight: 700;
        }

        .asset-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            padding: 10px 12px;
            background: rgba(0,0,0,0.25);
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.03);
        }

        .asset-stat-item {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .asset-stat-label {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .asset-stat-val {
            font-size: 14px;
            font-weight: 600;
        }

        /* LIVE POSITION PANEL */
        .position-panel {
            display: none;
            border-color: rgba(16, 185, 129, 0.3);
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.04), rgba(6, 182, 212, 0.02));
        }
        
        .position-panel.active {
            display: block;
        }

        .pos-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
        }

        .pos-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }

        .pos-item {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        .pos-item-label {
            color: var(--text-secondary);
            font-size: 11px;
            text-transform: uppercase;
        }

        .pos-item-value {
            font-size: 15px;
            font-weight: 700;
        }

        .pos-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            justify-content: flex-start;
            border-left: 1px solid var(--card-border);
            padding-left: 24px;
        }

        .unrealized-pnl {
            font-size: 32px;
            font-weight: 800;
            margin: 6px 0;
            letter-spacing: -0.5px;
        }

        .btn-emergency {
            margin-top: auto;
            background: rgba(239, 68, 68, 0.12);
            color: var(--red);
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }

        .btn-emergency:hover {
            background: var(--red);
            color: #fff;
        }

        .ts-bar-container {
            width: 100%;
            height: 8px;
            background: var(--gray-bg);
            border-radius: 4px;
            margin-top: 18px;
            position: relative;
        }

        .ts-marker {
            position: absolute;
            top: -16px;
            transform: translateX(-50%);
            font-size: 10px;
            font-weight: 600;
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
            border-radius: 4px 0 0 4px;
        }
        
        .ts-fill-green {
            position: absolute;
            height: 100%;
            background: var(--green);
            border-radius: 0 4px 4px 0;
        }

        /* STATS & PROFIT BAR */
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 12px;
            padding: 16px 20px;
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
            font-weight: 800;
            margin-top: 4px;
        }

        /* PROTECTION & RISK GUARD */
        .risk-guard {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
            background: rgba(16, 185, 129, 0.03);
            border-color: rgba(16, 185, 129, 0.2);
        }
        
        .risk-guard.disabled {
            border-color: var(--red);
            background: rgba(239, 68, 68, 0.06);
        }

        .rg-center {
            display: flex;
            align-items: center;
            gap: 15px;
            flex: 1;
            justify-content: center;
        }

        .rg-progress {
            width: 180px;
            height: 6px;
            background: var(--gray-bg);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .rg-fill {
            height: 100%;
            background: var(--green);
        }

        /* FILTER & TABS */
        .table-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .tabs-header {
            display: flex;
            gap: 24px;
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-family: inherit;
            font-size: 13px;
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

        .symbol-filter-group {
            display: flex;
            gap: 6px;
            padding-bottom: 8px;
        }

        .filter-btn {
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--card-border);
            color: var(--text-secondary);
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-btn.active, .filter-btn:hover {
            background: var(--gray-bg);
            color: var(--text-primary);
            border-color: var(--cyan);
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
            padding: 10px 12px;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 12px;
            border-bottom: 1px solid var(--card-border);
            text-transform: uppercase;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.02);
        }
        
        tr:hover td {
            background: rgba(255,255,255,0.02);
        }

        .table-row-win { border-left: 2px solid var(--green); background: rgba(16, 185, 129, 0.02); }
        .table-row-loss { border-left: 2px solid var(--red); }
        .table-row-open { border-left: 2px solid var(--cyan); background: rgba(6, 182, 212, 0.04); }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
            font-style: italic;
        }

        /* RESPONSIVE */
        @media (max-width: 950px) {
            .kpi-row { grid-template-columns: repeat(2, 1fr); }
            .dual-assets-grid { grid-template-columns: 1fr; }
            .pos-grid { grid-template-columns: 1fr; }
            .pos-right { border-left: none; border-top: 1px solid var(--card-border); padding-left: 0; padding-top: 20px; align-items: flex-start; }
            .stats-bar { grid-template-columns: repeat(3, 1fr); row-gap: 16px; }
            .stat-item:nth-child(3) { border-right: none; }
        }

        @media (max-width: 600px) {
            .kpi-row { grid-template-columns: 1fr; }
            .stats-bar { grid-template-columns: repeat(2, 1fr); }
            .stat-item:nth-child(even) { border-right: none; }
            .header { flex-direction: column; gap: 16px; align-items: flex-start; }
            .header-right { align-items: flex-start; text-align: left; }
            .risk-guard { flex-direction: column; gap: 12px; align-items: flex-start; }
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
                    <h1>⚡ DeltaBot Multi-Asset</h1>
                    <span class="subtitle" id="el-strategy-name">21 EMA Cut Breakout · 1:3 Trailing Profit</span>
                </div>
                <div class="pill-group">
                    <span class="badge-gold" id="el-env">INDIA</span>
                    <span class="badge-gold">🪙 XAUTUSD (60x · 1-3 Lots)</span>
                    <span class="badge-eth">🔷 ETHUSD (130x · 1 Lot)</span>
                    <span class="badge-gray" id="el-timeframe">5m Timeframe</span>
                </div>
            </div>
            <div class="header-right">
                <div class="status-row">
                    <span class="dot red" id="el-status-dot"></span>
                    <span id="el-status-text">Connecting...</span>
                </div>
                <div class="clock mono" id="el-clock">00:00:00 IST</div>
                <button class="btn-refresh" onclick="fetchData()">Refresh Now</button>
            </div>
        </header>

        <!-- KPI ROW -->
        <div class="kpi-row">
            <!-- Card 1: Wallet -->
            <div class="card kpi-card wallet">
                <div class="kpi-label">Available Balance</div>
                <div class="kpi-value mono" id="el-wallet-usd">--</div>
                <div class="kpi-sub mono" id="el-wallet-inr">--</div>
                <div class="kpi-footer" id="el-wallet-total">Total Balance: --</div>
            </div>

            <!-- Card 2: Win Rate & Edge -->
            <div class="card kpi-card profit">
                <div class="kpi-label">Strategy Win Rate</div>
                <div class="kpi-value mono text-green" id="el-kpi-winrate">--%</div>
                <div class="kpi-sub mono text-cyan" id="el-kpi-pf">Profit Factor: --</div>
                <div class="kpi-footer" id="el-kpi-wins">Winning Trades: --</div>
            </div>

            <!-- Card 3: Today PnL -->
            <div class="card kpi-card profit">
                <div class="kpi-label">Today's Net P&L</div>
                <div class="kpi-value mono" id="el-today-usd">--</div>
                <div class="kpi-sub mono" id="el-today-inr">--</div>
                <div class="kpi-footer" id="el-today-trades">-- trades closed today</div>
            </div>

            <!-- Card 4: All-Time Net Profit -->
            <div class="card kpi-card profit">
                <div class="kpi-label">Total Realized Net Profit</div>
                <div class="kpi-value mono" id="el-alltime-usd">--</div>
                <div class="kpi-sub mono" id="el-alltime-inr">--</div>
                <div class="kpi-footer" id="el-alltime-trades">-- total trades executed</div>
            </div>
        </div>

        <!-- DUAL ASSET TELEMETRY: XAUTUSD (GOLD) & ETHUSD -->
        <div class="dual-assets-grid">
            <!-- Asset 1: Gold (XAUTUSD) -->
            <div class="asset-card gold-card">
                <div class="asset-header">
                    <div class="asset-title">
                        <span>🪙</span>
                        <span>Gold (XAUTUSD)</span>
                        <span class="badge-gold">60x · 1-3 Lots Dynamic</span>
                    </div>
                    <span id="el-gold-badge" class="badge-gray">FLAT</span>
                </div>
                <div class="asset-stats">
                    <div class="asset-stat-item">
                        <span class="asset-stat-label">Entry Price</span>
                        <span class="asset-stat-val mono" id="el-gold-entry">--</span>
                    </div>
                    <div class="asset-stat-item">
                        <span class="asset-stat-label">1:3 Stop</span>
                        <span class="asset-stat-val mono text-amber" id="el-gold-stop">--</span>
                    </div>
                    <div class="asset-stat-item">
                        <span class="asset-stat-label">Position Size</span>
                        <span class="asset-stat-val mono" id="el-gold-size">0 Lots</span>
                    </div>
                </div>
            </div>

            <!-- Asset 2: Ethereum (ETHUSD) -->
            <div class="asset-card eth-card">
                <div class="asset-header">
                    <div class="asset-title">
                        <span>🔷</span>
                        <span>Ethereum (ETHUSD)</span>
                        <span class="badge-eth">130x · 1 Lot</span>
                    </div>
                    <span id="el-eth-badge" class="badge-gray">FLAT</span>
                </div>
                <div class="asset-stats">
                    <div class="asset-stat-item">
                        <span class="asset-stat-label">Entry Price</span>
                        <span class="asset-stat-val mono" id="el-eth-entry">--</span>
                    </div>
                    <div class="asset-stat-item">
                        <span class="asset-stat-label">1:3 Stop</span>
                        <span class="asset-stat-val mono text-amber" id="el-eth-stop">--</span>
                    </div>
                    <div class="asset-stat-item">
                        <span class="asset-stat-label">Position Size</span>
                        <span class="asset-stat-val mono" id="el-eth-size">0 Lots</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- LIVE ACTIVE POSITION PANEL (Visible When in Trade) -->
        <div id="el-pos-panel" class="card position-panel">
            <div class="pos-grid">
                <div class="pos-left">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <div class="kpi-label" style="color: var(--green); font-size: 13px;">🟢 Active Live Trade Telemetry</div>
                        <span id="el-lp-symbol-badge" class="badge-gold">--</span>
                    </div>
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
                            <span class="pos-item-label">1:3 Trailing Stop</span>
                            <span class="pos-item-value mono text-amber" id="el-lp-tstop">--</span>
                        </div>
                        <div class="pos-item">
                            <span class="pos-item-label">Peak Price</span>
                            <span class="pos-item-value mono" id="el-lp-peak">--</span>
                        </div>
                        <div class="pos-item">
                            <span class="pos-item-label">Liquidation Price</span>
                            <span class="pos-item-value mono text-red" id="el-lp-liq">--</span>
                        </div>
                        <div class="pos-item">
                            <span class="pos-item-label">Margin In Trade</span>
                            <span class="pos-item-value mono" id="el-lp-margin">--</span>
                        </div>
                    </div>
                    
                    <!-- Visual Trailing Stop Bar -->
                    <div class="ts-bar-container" id="el-ts-bar"></div>
                </div>
                
                <div class="pos-right">
                    <div class="kpi-label">Live Unrealized Profit</div>
                    <div class="unrealized-pnl mono" id="el-lp-upnl">--</div>
                    <div class="mono" id="el-lp-upnl-inr" style="color: var(--text-secondary); margin-bottom: 5px;">--</div>
                    <div class="mono" id="el-lp-roi" style="color: var(--text-muted); font-size: 13px;">ROI: --</div>
                    
                    <button class="btn-emergency" onclick="emergencyClose()">Market Exit Trade</button>
                </div>
            </div>
        </div>

        <!-- HERO PERFORMANCE STATS BAR -->
        <div class="card stats-bar">
            <div class="stat-item">
                <div class="kpi-label">Win Rate</div>
                <div class="stat-val mono text-green" id="el-st-winrate">--%</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Profit Factor</div>
                <div class="stat-val mono text-cyan" id="el-st-pf">--</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Avg Winner</div>
                <div class="stat-val mono text-green" id="el-st-avgwin">--</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Best Trade</div>
                <div class="stat-val mono text-green" id="el-st-best">--</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Max Win Streak</div>
                <div class="stat-val mono text-green" id="el-st-streak-win">--</div>
            </div>
            <div class="stat-item">
                <div class="kpi-label">Total Fees Paid</div>
                <div class="stat-val mono text-amber" id="el-st-fees">--</div>
            </div>
        </div>

        <!-- CAPITAL PROTECTION & RISK GUARD STATUS BAR -->
        <div class="card risk-guard" id="el-rg-container">
            <div class="status-row" style="min-width: 220px;">
                <span class="dot green" id="el-rg-dot"></span>
                <span id="el-rg-text" style="font-weight: 700; color: var(--green);">Capital Protection: Active</span>
            </div>
            
            <div class="rg-center">
                <span class="kpi-label">Daily Drawdown Buffer:</span>
                <div class="rg-progress">
                    <div class="rg-fill" id="el-rg-bar" style="width: 100%;"></div>
                </div>
                <span class="mono" id="el-rg-loss-txt" style="font-size: 12px; font-weight: 600;">Safe (0.0% / -3.0%)</span>
            </div>
            
            <div style="min-width: 180px; text-align: right;">
                <span class="kpi-label">Loss Circuit-Breaker: </span>
                <span class="mono" id="el-rg-streak" style="font-weight: 600;">0 / 4 Losses</span>
            </div>
        </div>

        <!-- TABBED HISTORY WITH SYMBOL FILTER -->
        <div class="card">
            <div class="table-controls">
                <div class="tabs-header">
                    <button class="tab-btn active" onclick="switchTab('tab-trades')">Trade History</button>
                    <button class="tab-btn" onclick="switchTab('tab-live')">Live Activity</button>
                    <button class="tab-btn" onclick="switchTab('tab-orders')">Open Orders</button>
                    <button class="tab-btn" onclick="switchTab('tab-fills')">Exchange Fills</button>
                </div>
                
                <!-- Symbol Filter Toggle -->
                <div class="symbol-filter-group">
                    <button class="filter-btn active" onclick="setSymbolFilter('ALL')">🌐 All Pairs</button>
                    <button class="filter-btn" onclick="setSymbolFilter('XAUTUSD')">🪙 XAUTUSD Only</button>
                    <button class="filter-btn" onclick="setSymbolFilter('ETHUSD')">🔷 ETHUSD Only</button>
                </div>
            </div>
            
            <!-- Tab 1: Trade History -->
            <div class="tab-content active" id="tab-trades">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Entry Time</th>
                                <th>Exit Time</th>
                                <th>Symbol</th>
                                <th>Side</th>
                                <th>Entry Price</th>
                                <th>Exit Price</th>
                                <th>Points</th>
                                <th>Gross Profit</th>
                                <th>Fee</th>
                                <th>Net PnL</th>
                                <th>Exit Trigger</th>
                                <th>Result</th>
                            </tr>
                        </thead>
                        <tbody id="tb-trades">
                            <tr><td colspan="12" class="empty-state">Loading trade records...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Tab 2: Live Activity -->
            <div class="tab-content" id="tab-live">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Symbol</th>
                                <th>Action</th>
                                <th>Trigger Reason</th>
                                <th>Price</th>
                                <th>Stop Loss</th>
                                <th>Net PnL</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="tb-live">
                            <tr><td colspan="8" class="empty-state">Loading activity logs...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Tab 3: Open Orders -->
            <div class="tab-content" id="tab-orders">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Symbol</th>
                                <th>Type</th>
                                <th>Side</th>
                                <th>Stop / Limit Price</th>
                                <th>Size</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="tb-orders">
                            <tr><td colspan="7" class="empty-state">No open orders on Delta Exchange</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Tab 4: Exchange Fills -->
            <div class="tab-content" id="tab-fills">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Time (UTC)</th>
                                <th>Symbol</th>
                                <th>Side</th>
                                <th>Fill Price</th>
                                <th>Size</th>
                                <th>Fee Paid</th>
                                <th>Role</th>
                            </tr>
                        </thead>
                        <tbody id="tb-fills">
                            <tr><td colspan="7" class="empty-state">No recent exchange fills</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- JAVASCRIPT LOGIC -->
    <script>
        const USD_TO_INR = 87.50;
        let globalDashboardData = null;
        let currentSymbolFilter = 'ALL';

        function formatUSD(val, decimals = 2) {
            if (val === null || val === undefined) return '--';
            const num = Number(val);
            if (isNaN(num)) return '--';
            return (num < 0 ? '-' : (num > 0 ? '+' : '')) + '$' + Math.abs(num).toFixed(decimals);
        }

        function formatINR(val) {
            if (val === null || val === undefined) return '--';
            const num = Number(val);
            if (isNaN(num)) return '--';
            const abs = Math.abs(num).toLocaleString('en-IN', { maximumFractionDigits: 0 });
            return (num < 0 ? '-' : (num > 0 ? '+' : '')) + '₹' + abs;
        }

        function formatPrice(val) {
            if (val === null || val === undefined) return '--';
            const num = Number(val);
            if (isNaN(num)) return '--';
            return num.toFixed(2);
        }

        function formatColorClass(val) {
            if (val === null || val === undefined) return '';
            const num = Number(val);
            if (num > 0) return 'text-green';
            if (num < 0) return 'text-red';
            return 'text-muted';
        }

        function switchTab(tabId) {
            const btns = document.querySelectorAll('.tab-btn');
            for (let i = 0; i < btns.length; i++) btns[i].classList.remove('active');
            
            const contents = document.querySelectorAll('.tab-content');
            for (let i = 0; i < contents.length; i++) contents[i].classList.remove('active');
            
            event.currentTarget.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }

        function setSymbolFilter(sym) {
            currentSymbolFilter = sym;
            const filterBtns = document.querySelectorAll('.filter-btn');
            for (let i = 0; i < filterBtns.length; i++) {
                filterBtns[i].classList.remove('active');
            }
            event.currentTarget.classList.add('active');
            if (globalDashboardData) {
                renderFilteredTables(globalDashboardData);
            }
        }

        function updateClock() {
            const now = new Date();
            const options = { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            const timeString = now.toLocaleTimeString('en-US', options);
            document.getElementById('el-clock').innerText = timeString + ' IST';
        }
        setInterval(updateClock, 1000);
        updateClock();

        function emergencyClose() {
            if (confirm('MARKET EXIT: Are you sure you want to close active positions and cancel all stop orders?')) {
                fetch('/api/emergency_close', { method: 'POST' })
                    .then(function(res) { return res.json(); })
                    .then(function(data) {
                        alert('Position closed and orders cancelled.');
                        fetchData();
                    })
                    .catch(function(err) {
                        alert('Error sending close command: ' + err);
                    });
            }
        }

        function fetchData() {
            fetch('/api/dashboard')
                .then(function(res) {
                    if (!res.ok) throw new Error('Network response was not ok');
                    return res.json();
                })
                .then(function(data) {
                    globalDashboardData = data;
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
                text.innerText = 'Connected (Live 24/7)';
                text.style.color = 'var(--green)';
            } else {
                dot.className = 'dot red';
                text.innerText = 'Connecting...';
                text.style.color = 'var(--red)';
            }
        }

        function getSymbolBadgeHtml(symbol) {
            const sym = (symbol || '').toUpperCase();
            if (sym.includes('XAU')) {
                return '<span class="badge-gold">🪙 ' + sym + '</span>';
            } else if (sym.includes('ETH')) {
                return '<span class="badge-eth">🔷 ' + sym + '</span>';
            }
            return '<span class="badge-gray">' + (symbol || '--') + '</span>';
        }

        function updateDashboard(data) {
            // Header
            document.getElementById('el-env').innerText = data.environment || 'INDIA';
            document.getElementById('el-timeframe').innerText = (data.timeframe || '5m') + ' Timeframe';

            // Wallet
            const wallet = data.wallet || {};
            document.getElementById('el-wallet-usd').innerText = '$' + Number(wallet.available_balance || 0).toFixed(2);
            document.getElementById('el-wallet-inr').innerText = formatINR((wallet.available_balance || 0) * USD_TO_INR);
            document.getElementById('el-wallet-total').innerText = 'Total Balance: $' + Number(wallet.balance || 0).toFixed(2);

            // Performance Stats
            const stats = data.stats || {};
            document.getElementById('el-kpi-winrate').innerText = (stats.win_rate !== undefined ? stats.win_rate.toFixed(1) : '0.0') + '%';
            document.getElementById('el-kpi-pf').innerText = 'Profit Factor: ' + (stats.profit_factor !== undefined ? stats.profit_factor.toFixed(2) : '0.0');
            document.getElementById('el-kpi-wins').innerText = 'Winners: ' + (stats.winning_trades || 0) + ' / ' + (stats.total_trades || 0) + ' Trades';

            // Today Net PnL
            const elTodayUsd = document.getElementById('el-today-usd');
            elTodayUsd.innerText = formatUSD(stats.daily_pnl);
            elTodayUsd.className = 'kpi-value mono ' + formatColorClass(stats.daily_pnl);
            document.getElementById('el-today-inr').innerText = formatINR((stats.daily_pnl || 0) * USD_TO_INR);
            document.getElementById('el-today-trades').innerText = (stats.today_trades || 0) + ' trades closed today';

            // All-Time Net Profit
            const elAlltimeUsd = document.getElementById('el-alltime-usd');
            elAlltimeUsd.innerText = formatUSD(stats.total_net_pnl);
            elAlltimeUsd.className = 'kpi-value mono ' + formatColorClass(stats.total_net_pnl);
            document.getElementById('el-alltime-inr').innerText = formatINR((stats.total_net_pnl || 0) * USD_TO_INR);
            document.getElementById('el-alltime-trades').innerText = (stats.total_trades || 0) + ' total trades executed';

            // Stats Bar
            document.getElementById('el-st-winrate').innerText = (stats.win_rate !== undefined ? stats.win_rate.toFixed(1) : '0.0') + '%';
            document.getElementById('el-st-pf').innerText = stats.profit_factor !== undefined ? stats.profit_factor.toFixed(2) : '0.00';
            document.getElementById('el-st-avgwin').innerText = formatUSD(stats.avg_win);
            document.getElementById('el-st-best').innerText = formatUSD(stats.best_trade);
            document.getElementById('el-st-streak-win').innerText = (stats.max_streak_win || 0) + ' Wins';
            document.getElementById('el-st-fees').innerText = '$' + Number(stats.total_fees || 0).toFixed(2);

            // DUAL ASSET CARDS TELEMETRY
            let activeLivePosition = null;
            let activeLiveSym = null;

            if (data.symbols_data && data.symbols_data.length > 0) {
                for (let i = 0; i < data.symbols_data.length; i++) {
                    const item = data.symbols_data[i];
                    const sym = item.symbol.toUpperCase();
                    const st = item.strategy || {};
                    const pos = item.position || {};

                    if (sym.includes('XAU')) {
                        // Gold
                        const goldBadge = document.getElementById('el-gold-badge');
                        if (st.position_state === 1) {
                            goldBadge.className = 'badge-green';
                            goldBadge.innerText = '🟢 LONG (' + pos.size + ' Lots)';
                            activeLivePosition = item;
                            activeLiveSym = 'XAUTUSD';
                        } else if (st.position_state === -1) {
                            goldBadge.className = 'badge-red';
                            goldBadge.innerText = '🔴 SHORT (' + Math.abs(pos.size) + ' Lots)';
                            activeLivePosition = item;
                            activeLiveSym = 'XAUTUSD';
                        } else {
                            goldBadge.className = 'badge-gray';
                            goldBadge.innerText = '⚪ FLAT (Watching 21 EMA)';
                        }
                        document.getElementById('el-gold-entry').innerText = st.entry_price ? formatPrice(st.entry_price) : '--';
                        document.getElementById('el-gold-stop').innerText = st.active_trailing_stop ? formatPrice(st.active_trailing_stop) : '--';
                        document.getElementById('el-gold-size').innerText = pos.size ? (Math.abs(pos.size) + ' Lots') : '0 Lots';
                    } else if (sym.includes('ETH')) {
                        // ETH
                        const ethBadge = document.getElementById('el-eth-badge');
                        if (st.position_state === 1) {
                            ethBadge.className = 'badge-green';
                            ethBadge.innerText = '🟢 LONG (' + pos.size + ' Lot)';
                            if (!activeLivePosition) { activeLivePosition = item; activeLiveSym = 'ETHUSD'; }
                        } else if (st.position_state === -1) {
                            ethBadge.className = 'badge-red';
                            ethBadge.innerText = '🔴 SHORT (' + Math.abs(pos.size) + ' Lot)';
                            if (!activeLivePosition) { activeLivePosition = item; activeLiveSym = 'ETHUSD'; }
                        } else {
                            ethBadge.className = 'badge-gray';
                            ethBadge.innerText = '⚪ FLAT (Watching 21 EMA)';
                        }
                        document.getElementById('el-eth-entry').innerText = st.entry_price ? formatPrice(st.entry_price) : '--';
                        document.getElementById('el-eth-stop').innerText = st.active_trailing_stop ? formatPrice(st.active_trailing_stop) : '--';
                        document.getElementById('el-eth-size').innerText = pos.size ? (Math.abs(pos.size) + ' Lot') : '0 Lots';
                    }
                }
            }

            // Live Position Panel
            const posPanel = document.getElementById('el-pos-panel');
            if (activeLivePosition && activeLivePosition.strategy && activeLivePosition.strategy.position_state !== 0) {
                posPanel.classList.add('active');
                const st = activeLivePosition.strategy;
                const pos = activeLivePosition.position;
                const sym = activeLivePosition.symbol;
                const lev = activeLivePosition.leverage || 100;

                document.getElementById('el-lp-symbol-badge').innerHTML = getSymbolBadgeHtml(sym);
                document.getElementById('el-lp-entry').innerText = formatPrice(st.entry_price);
                document.getElementById('el-lp-istop').innerText = formatPrice(st.initial_stop_loss);
                document.getElementById('el-lp-tstop').innerText = formatPrice(st.active_trailing_stop);
                
                const peak = st.position_state === 1 ? st.highest_price : st.lowest_price;
                document.getElementById('el-lp-peak').innerText = formatPrice(peak);
                document.getElementById('el-lp-liq').innerText = formatPrice(pos.liquidation_price);
                
                const upnl = pos.unrealized_pnl || 0;
                const elUpnl = document.getElementById('el-lp-upnl');
                elUpnl.innerText = formatUSD(upnl);
                elUpnl.className = 'unrealized-pnl mono ' + formatColorClass(upnl);
                document.getElementById('el-lp-upnl-inr').innerText = formatINR(upnl * USD_TO_INR);
                
                const cv = st.contract_value || 0.001;
                const size = Math.abs(pos.size || 1);
                const ep = st.entry_price || 0;
                const margin = (ep * cv * size) / lev;
                document.getElementById('el-lp-margin').innerText = '$' + margin.toFixed(2) + ' (' + size + ' Lots @ ' + lev + 'x)';

                if (margin > 0) {
                    const roi = (upnl / margin) * 100;
                    document.getElementById('el-lp-roi').innerText = 'Live ROI: ' + (roi >= 0 ? '+' : '') + roi.toFixed(2) + '%';
                    document.getElementById('el-lp-roi').className = 'mono ' + formatColorClass(roi);
                }

                renderTrailingStopBar(st.position_state, st.initial_stop_loss, st.entry_price, st.active_trailing_stop, peak);
            } else {
                posPanel.classList.remove('active');
            }

            // Capital Protection & Risk Guard
            const rg = data.risk_guard || {};
            const rgContainer = document.getElementById('el-rg-container');
            const rgDot = document.getElementById('el-rg-dot');
            const rgText = document.getElementById('el-rg-text');
            
            if (rg.trading_enabled) {
                rgContainer.classList.remove('disabled');
                rgDot.className = 'dot green';
                rgText.innerText = 'Capital Protection: Active';
                rgText.style.color = 'var(--green)';
            } else {
                rgContainer.classList.add('disabled');
                rgDot.className = 'dot red';
                rgText.innerText = 'Protection Triggered: Trading Paused';
                rgText.style.color = 'var(--red)';
            }
            
            const maxLoss = rg.max_daily_loss_pct || 3.0;
            const currentLoss = Math.abs(rg.daily_pnl_pct || 0);
            const remainingSafe = Math.max(0, 100 - (currentLoss / maxLoss) * 100);
            
            document.getElementById('el-rg-loss-txt').innerText = 'Buffer: ' + remainingSafe.toFixed(0) + '% Safe (' + (rg.daily_pnl_pct || 0).toFixed(1) + '% / -' + maxLoss.toFixed(1) + '%)';
            document.getElementById('el-rg-bar').style.width = remainingSafe + '%';
            document.getElementById('el-rg-streak').innerText = (rg.consecutive_losses || 0) + ' / ' + (rg.max_consecutive_losses || 4) + ' Losses';

            // Filtered Tables
            renderFilteredTables(data);
        }

        function renderFilteredTables(data) {
            const filterSym = currentSymbolFilter.toUpperCase();

            // Filter Trades
            let trades = data.completed_trades || [];
            if (filterSym !== 'ALL') {
                trades = trades.filter(function(t) { return (t.symbol || '').toUpperCase().includes(filterSym.substring(0, 3)); });
            }
            renderTable('tb-trades', trades, renderTradeRow);

            // Filter Live Activity
            let logs = data.recent_logs || [];
            if (filterSym !== 'ALL') {
                logs = logs.filter(function(l) { return (l.symbol || '').toUpperCase().includes(filterSym.substring(0, 3)); });
            }
            renderTable('tb-live', logs, renderLiveRow);

            // Filter Open Orders
            let orders = data.open_orders || [];
            if (filterSym !== 'ALL') {
                orders = orders.filter(function(o) { return (o.symbol || '').toUpperCase().includes(filterSym.substring(0, 3)); });
            }
            renderTable('tb-orders', orders, renderOrderRow);

            // Filter Fills
            let fills = data.exchange_fills || [];
            if (filterSym !== 'ALL') {
                fills = fills.filter(function(f) { return (f.symbol || '').toUpperCase().includes(filterSym.substring(0, 3)); });
            }
            renderTable('tb-fills', fills, renderFillRow);
        }

        function renderTrailingStopBar(posState, initialStop, entryPrice, activeStop, peak) {
            const container = document.getElementById('el-ts-bar');
            container.innerHTML = '';

            if (!initialStop || !entryPrice || !activeStop || !peak) return;

            let minPrice, maxPrice;
            if (posState === 1) {
                minPrice = initialStop;
                maxPrice = Math.max(peak, entryPrice * 1.005);
            } else {
                minPrice = Math.min(peak, entryPrice * 0.995);
                maxPrice = initialStop;
            }
            
            const range = Math.abs(maxPrice - minPrice);
            if (range === 0) return;

            function getPct(price) {
                if (posState === 1) return ((price - minPrice) / range) * 100;
                return ((maxPrice - price) / range) * 100;
            }

            const entryPct = getPct(entryPrice);
            const stopPct = getPct(activeStop);

            const redFill = document.createElement('div');
            redFill.className = 'ts-fill-red';
            redFill.style.width = Math.min(100, Math.max(0, entryPct)) + '%';
            redFill.style.left = '0%';
            container.appendChild(redFill);
            
            if (stopPct > entryPct) {
                const greenFill = document.createElement('div');
                greenFill.className = 'ts-fill-green';
                greenFill.style.left = entryPct + '%';
                greenFill.style.width = Math.min(100, (stopPct - entryPct)) + '%';
                container.appendChild(greenFill);
            }

            const mEntry = document.createElement('div');
            mEntry.className = 'ts-marker';
            mEntry.style.left = entryPct + '%';
            mEntry.innerText = 'Entry';
            container.appendChild(mEntry);

            const mStop = document.createElement('div');
            mStop.className = 'ts-marker';
            mStop.style.left = stopPct + '%';
            mStop.style.color = stopPct > entryPct ? 'var(--green)' : 'var(--amber)';
            mStop.innerText = '1:3 Stop';
            container.appendChild(mStop);
        }

        function renderTable(tbodyId, dataArray, rowRenderer) {
            const tbody = document.getElementById(tbodyId);
            tbody.innerHTML = '';
            
            if (!dataArray || dataArray.length === 0) {
                tbody.innerHTML = '<tr><td colspan="12" class="empty-state">No matching trade data found</td></tr>';
                return;
            }
            
            for (let i = 0; i < dataArray.length; i++) {
                tbody.innerHTML += rowRenderer(dataArray[i]);
            }
        }

        function renderTradeRow(t) {
            const rowClass = t.win ? 'table-row-win' : 'table-row-loss';
            const sideBadge = t.side === 'BUY' ? '<span class="badge-green">BUY</span>' : '<span class="badge-red">SELL</span>';
            const resBadge = t.win ? '<span class="badge-green">WIN 🎉</span>' : '<span class="badge-red">LOSS</span>';
            const symBadge = getSymbolBadgeHtml(t.symbol);
            
            return '<tr class="' + rowClass + '">' +
                '<td>' + (t.entry_time || '--') + '</td>' +
                '<td>' + (t.exit_time || '--') + '</td>' +
                '<td>' + symBadge + '</td>' +
                '<td>' + sideBadge + '</td>' +
                '<td class="mono">' + formatPrice(t.entry_price) + '</td>' +
                '<td class="mono">' + formatPrice(t.exit_price) + '</td>' +
                '<td class="mono">' + (t.points !== undefined ? (t.points > 0 ? '+' : '') + t.points.toFixed(2) : '--') + '</td>' +
                '<td class="mono">' + formatUSD(t.gross_pnl) + '</td>' +
                '<td class="mono text-amber">' + formatUSD(t.fees) + '</td>' +
                '<td class="mono ' + formatColorClass(t.net_pnl) + '" style="font-weight:700;">' + formatUSD(t.net_pnl) + '</td>' +
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
            const symBadge = getSymbolBadgeHtml(l.symbol);

            return '<tr class="' + rowClass + '">' +
                '<td>' + (l.time || '--') + '</td>' +
                '<td>' + symBadge + '</td>' +
                '<td>' + actBadge + '</td>' +
                '<td>' + (l.reason || '--') + '</td>' +
                '<td class="mono">' + formatPrice(l.price) + '</td>' +
                '<td class="mono">' + formatPrice(l.stop_loss) + '</td>' +
                '<td class="mono ' + formatColorClass(l.net_pnl) + '">' + formatUSD(l.net_pnl) + '</td>' +
                '<td>' + (l.status === 'OPEN' ? '<span class="badge-green">LIVE IN TRADE</span>' : '<span class="badge-gray">CLOSED</span>') + '</td>' +
            '</tr>';
        }

        function renderOrderRow(o) {
            let sideBadge = '<span class="badge-gray">' + o.side + '</span>';
            if (o.side && o.side.toLowerCase() === 'buy') sideBadge = '<span class="badge-green">BUY</span>';
            if (o.side && o.side.toLowerCase() === 'sell') sideBadge = '<span class="badge-red">SELL</span>';
            const symBadge = getSymbolBadgeHtml(o.symbol);
            
            return '<tr>' +
                '<td>' + (o.id || '--') + '</td>' +
                '<td>' + symBadge + '</td>' +
                '<td>' + (o.order_type || '--') + '</td>' +
                '<td>' + sideBadge + '</td>' +
                '<td class="mono text-amber" style="font-weight:600;">' + formatPrice(o.stop_price || o.limit_price) + '</td>' +
                '<td class="mono">' + (o.size || '--') + '</td>' +
                '<td><span class="badge-green">' + (o.state || 'ACTIVE') + '</span></td>' +
            '</tr>';
        }

        function renderFillRow(f) {
            let sideBadge = '<span class="badge-gray">' + f.side + '</span>';
            if (f.side && f.side.toLowerCase() === 'buy') sideBadge = '<span class="badge-green">BUY</span>';
            if (f.side && f.side.toLowerCase() === 'sell') sideBadge = '<span class="badge-red">SELL</span>';
            const symBadge = getSymbolBadgeHtml(f.symbol);
            
            let timeStr = '--';
            if (f.created_at) {
                const d = new Date(f.created_at);
                timeStr = d.toLocaleTimeString('en-US', { hour12: false });
            }

            return '<tr>' +
                '<td>' + timeStr + '</td>' +
                '<td>' + symBadge + '</td>' +
                '<td>' + sideBadge + '</td>' +
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
