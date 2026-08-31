"""
Backtesting Suite for Delta Exchange 100x Precision Bot
Simulates the StrategyEngine over historical candles with realistic taker fees,
contract values, leverage, dynamic stops, auto-breakeven, and trailing profit protection.
"""

import os
import sys
import time
import argparse
import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from bot.config import config
from bot.delta_client import DeltaExchangeClient
from bot.strategy_engine import StrategyEngine, SignalResult
from bot.utils import logger
import logging

def set_log_level(verbose: bool = False):
    if not verbose:
        logger.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.INFO)


class Backtester:
    def __init__(
        self,
        symbol: str = "ETHUSD",
        timeframe: str = "3m",
        initial_balance: float = 1000.0,
        order_size: int = 1,
        leverage: int = 100,
        taker_fee_pct: float = 0.05,
        engine_params: Optional[Dict[str, Any]] = None,
    ):
        self.symbol = symbol.strip().upper()
        self.timeframe = timeframe.strip().lower()
        self.initial_balance = initial_balance
        self.order_size = order_size
        self.leverage = leverage
        self.taker_rate = taker_fee_pct / 100.0
        
        # Contract multiplier
        self.contract_val = self._get_contract_value(self.symbol)
        
        # Strategy engine configuration
        params = engine_params or {}
        self.engine = StrategyEngine(
            entry_ema_length=params.get("entry_ema_length", config.ENTRY_EMA_LENGTH),
            fast_ema_length=params.get("fast_ema_length", config.FAST_EMA_LENGTH),
            trail_move_unit=params.get("trail_move_unit", config.TRAIL_MOVE_UNIT),
            trail_step_unit=params.get("trail_step_unit", config.TRAIL_STEP_UNIT),
            trail_profit_ratio=params.get("trail_profit_ratio", config.TRAIL_PROFIT_RATIO),
            exit_on_opposite=params.get("exit_on_opposite", config.EXIT_ON_OPPOSITE),
            fee_buffer=params.get("fee_buffer", config.FEE_BUFFER_USD),
        )

    def _get_contract_value(self, symbol: str) -> float:
        s = symbol.upper()
        if "ETH" in s:
            return 0.01
        elif "BTC" in s:
            return 0.001
        elif "SOL" in s:
            return 1.0
        return 0.01

    def fetch_delta_candles(self, count: int = 1000) -> Optional[pd.DataFrame]:
        """Fetches candles from Delta Exchange with pagination."""
        resolution_map = {
            "1m": ("1", 60), "1": ("1", 60),
            "3m": ("3", 180), "3": ("3", 180),
            "5m": ("5", 300), "5": ("5", 300),
            "15m": ("15", 900), "15": ("15", 900),
            "30m": ("30", 1800), "30": ("30", 1800),
            "1h": ("60", 3600), "60": ("60", 3600),
            "2h": ("120", 7200), "120": ("120", 7200),
            "4h": ("240", 14400), "240": ("240", 14400),
            "1d": ("D", 86400), "d": ("D", 86400),
        }
        res_code, res_sec = resolution_map.get(self.timeframe, ("15", 900))
        
        all_dfs = []
        needed = count
        end_time = int(time.time())
        
        while needed > 0:
            batch_limit = min(needed, 500)
            start_time = end_time - (res_sec * batch_limit)
            
            params = {
                "symbol": self.symbol,
                "resolution": res_code,
                "from": str(start_time),
                "to": str(end_time)
            }
            try:
                base_url = config.get_base_url()
                resp = requests.get(f"{base_url}/v2/chart/history", params=params, timeout=10)
                data = resp.json()
                result = data.get("result", {})
                if not result or "t" not in result or len(result["t"]) == 0:
                    break
                
                df_batch = pd.DataFrame({
                    "timestamp": result["t"],
                    "open": result["o"],
                    "high": result["h"],
                    "low": result["l"],
                    "close": result["c"],
                    "volume": result["v"]
                })
                all_dfs.append(df_batch)
                
                earliest_t = min(result["t"])
                end_time = earliest_t - 1
                needed -= len(result["t"])
                if len(result["t"]) < batch_limit:
                    break
            except Exception as e:
                logger.warning(f"Error fetching batch from Delta: {e}")
                break

        if not all_dfs:
            return None

        combined = pd.concat(all_dfs, ignore_index=True)
        combined["timestamp"] = pd.to_datetime(combined["timestamp"], unit="s")
        combined.drop_duplicates(subset=["timestamp"], inplace=True)
        combined.sort_values("timestamp", inplace=True)
        combined.reset_index(drop=True, inplace=True)
        return combined

    def fetch_binance_candles(self, count: int = 8640) -> Optional[pd.DataFrame]:
        """Fallback to Binance public OHLCV for large historical ranges with multi-batch pagination."""
        sym_map = {
            "ETHUSD": "ETHUSDT",
            "BTCUSD": "BTCUSDT",
            "SOLUSD": "SOLUSDT",
            "XAUTUSD": "PAXGUSDT",  # Gold asset equivalent on Binance
            "PAXGUSD": "PAXGUSDT",
        }
        binance_sym = sym_map.get(self.symbol, f"{self.symbol}T")
        
        url = "https://api.binance.com/api/v3/klines"
        tf = self.timeframe
        if tf == "1": tf = "1m"
        elif tf == "3": tf = "3m"
        elif tf == "5": tf = "5m"
        elif tf == "15": tf = "15m"
        elif tf == "60": tf = "1h"
        
        all_dfs = []
        needed = count
        end_time_ms = None
        
        while needed > 0:
            batch_limit = min(needed, 1000)
            params = {"symbol": binance_sym, "interval": tf, "limit": batch_limit}
            if end_time_ms is not None:
                params["endTime"] = end_time_ms
                
            try:
                r = requests.get(url, params=params, timeout=10)
                data = r.json()
                if not isinstance(data, list) or len(data) == 0:
                    break
                
                df_batch = pd.DataFrame(data, columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
                ])
                all_dfs.append(df_batch)
                
                earliest_t = int(df_batch["open_time"].iloc[0])
                end_time_ms = earliest_t - 1
                needed -= len(df_batch)
                if len(df_batch) < batch_limit:
                    break
            except Exception as e:
                logger.warning(f"Error fetching from Binance: {e}")
                break

        if not all_dfs:
            return None

        combined = pd.concat(all_dfs, ignore_index=True)
        combined["timestamp"] = pd.to_datetime(combined["open_time"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            combined[col] = combined[col].astype(float)
        combined = combined[["timestamp", "open", "high", "low", "close", "volume"]]
        combined.drop_duplicates(subset=["timestamp"], inplace=True)
        combined.sort_values("timestamp", inplace=True)
        combined.reset_index(drop=True, inplace=True)
        return combined

    def fetch_candles(self, count: int = 1000) -> Optional[pd.DataFrame]:
        """Fetches candles from Delta Exchange, falling back to Binance if needed."""
        print(f"📡 Fetching {count} historical candles for {self.symbol} ({self.timeframe}) from Delta Exchange...")
        df = self.fetch_delta_candles(count=count)
        if df is not None and len(df) >= 50:
            print(f" Successfully loaded {len(df)} candles from Delta Exchange.")
            return df
        
        print("ℹ️ Falling back to Binance public market data for comprehensive historical coverage...")
        df = self.fetch_binance_candles(count=count)
        if df is not None and len(df) >= 50:
            print(f" Successfully loaded {len(df)} candles from Binance ({self.symbol}).")
            return df

        return None

    def calculate_fee(self, price: float) -> float:
        """Delta Exchange Taker fee = Price * Size * Contract_Val * 0.05%."""
        notional = price * self.order_size * self.contract_val
        return notional * self.taker_rate

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Executes full bar-by-bar simulation and computes trade results."""
        signals = self.engine.process_candles(df)
        
        trades = []
        active_trade = None
        equity_curve = [self.initial_balance]
        balance = self.initial_balance
        
        for i, sig in enumerate(signals):
            df_idx = i + 1
            bar = df.iloc[df_idx]
            bar_time = bar["timestamp"]
            
            action = sig.action
            price = sig.price
            reason = sig.reason
            
            # Check entry
            if action in ("BUY", "SELL") and active_trade is None:
                entry_fee = self.calculate_fee(price)
                active_trade = {
                    "trade_id": len(trades) + 1,
                    "side": "LONG" if action == "BUY" else "SHORT",
                    "entry_time": bar_time,
                    "entry_price": price,
                    "entry_fee": entry_fee,
                    "reason_entry": reason,
                    "highest_price": price,
                    "lowest_price": price,
                    "entry_index": df_idx
                }
            
            # Track peak prices intra-trade
            if active_trade is not None:
                active_trade["highest_price"] = max(active_trade["highest_price"], bar["high"])
                active_trade["lowest_price"] = min(active_trade["lowest_price"], bar["low"])
                
                # Check exit
                is_exit = False
                if active_trade["side"] == "LONG" and action in ("EXIT_LONG", "SELL"):
                    is_exit = True
                elif active_trade["side"] == "SHORT" and action in ("EXIT_SHORT", "BUY"):
                    is_exit = True
                    
                if is_exit:
                    exit_price = price
                    exit_fee = self.calculate_fee(exit_price)
                    total_fee = active_trade["entry_fee"] + exit_fee
                    
                    if active_trade["side"] == "LONG":
                        price_diff = exit_price - active_trade["entry_price"]
                    else:
                        price_diff = active_trade["entry_price"] - exit_price
                    
                    gross_pnl = price_diff * self.order_size * self.contract_val
                    net_pnl = gross_pnl - total_fee
                    balance += net_pnl
                    equity_curve.append(balance)
                    
                    notional = active_trade["entry_price"] * self.order_size * self.contract_val
                    pnl_pct = (net_pnl / notional * 100) if notional > 0 else 0.0
                    duration_bars = df_idx - active_trade["entry_index"]
                    
                    trades.append({
                        "trade_id": active_trade["trade_id"],
                        "side": active_trade["side"],
                        "entry_time": str(active_trade["entry_time"]),
                        "exit_time": str(bar_time),
                        "entry_price": round(active_trade["entry_price"], 2),
                        "exit_price": round(exit_price, 2),
                        "price_diff": round(price_diff, 2),
                        "gross_pnl": round(gross_pnl, 4),
                        "fee": round(total_fee, 4),
                        "net_pnl": round(net_pnl, 4),
                        "net_pnl_inr": round(net_pnl * 87.5, 2),
                        "pnl_pct": round(pnl_pct, 2),
                        "is_win": net_pnl > 0,
                        "duration_bars": duration_bars,
                        "entry_reason": active_trade["reason_entry"],
                        "exit_reason": reason,
                        "balance_after": round(balance, 2)
                    })
                    
                    # If this was a reversal entry, initiate new trade
                    if action in ("BUY", "SELL"):
                        entry_fee = self.calculate_fee(price)
                        active_trade = {
                            "trade_id": len(trades) + 1,
                            "side": "LONG" if action == "BUY" else "SHORT",
                            "entry_time": bar_time,
                            "entry_price": price,
                            "entry_fee": entry_fee,
                            "reason_entry": reason,
                            "highest_price": price,
                            "lowest_price": price,
                            "entry_index": df_idx
                        }
                    else:
                        active_trade = None

        return self._compute_metrics(trades, equity_curve, len(df))

    def _compute_metrics(self, trades: List[Dict[str, Any]], equity_curve: List[float], total_bars: int) -> Dict[str, Any]:
        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "message": "No trades generated in the given dataset."
            }

        wins = [t for t in trades if t["is_win"]]
        losses = [t for t in trades if not t["is_win"]]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = round((win_count / total_trades) * 100, 2)
        
        gross_profit = sum(t["gross_pnl"] for t in wins)
        gross_loss = abs(sum(t["gross_pnl"] for t in losses))
        total_fees = sum(t["fee"] for t in trades)
        
        net_pnl = sum(t["net_pnl"] for t in trades)
        net_pnl_inr = net_pnl * 87.5
        
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
        
        avg_win = (sum(t["net_pnl"] for t in wins) / win_count) if win_count > 0 else 0.0
        avg_loss = (sum(t["net_pnl"] for t in losses) / loss_count) if loss_count > 0 else 0.0
        risk_reward_ratio = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0.0
        
        # Drawdown calculation
        eq = np.array(equity_curve)
        peak = np.maximum.accumulate(eq)
        drawdowns = (peak - eq) / peak * 100
        max_dd_pct = round(float(np.max(drawdowns)), 2) if len(drawdowns) > 0 else 0.0
        max_dd_usd = round(float(np.max(peak - eq)), 2) if len(eq) > 0 else 0.0
        
        # Consecutive wins / losses
        max_cons_wins = 0
        max_cons_losses = 0
        curr_w, curr_l = 0, 0
        for t in trades:
            if t["is_win"]:
                curr_w += 1
                curr_l = 0
                max_cons_wins = max(max_cons_wins, curr_w)
            else:
                curr_l += 1
                curr_w = 0
                max_cons_losses = max(max_cons_losses, curr_l)
                
        # Long vs Short
        long_trades = [t for t in trades if t["side"] == "LONG"]
        short_trades = [t for t in trades if t["side"] == "SHORT"]
        long_win_rate = round(len([t for t in long_trades if t["is_win"]]) / len(long_trades) * 100, 2) if long_trades else 0.0
        short_win_rate = round(len([t for t in short_trades if t["is_win"]]) / len(short_trades) * 100, 2) if short_trades else 0.0
        
        returns = [t["pnl_pct"] for t in trades]
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = round(float(np.mean(returns) / np.std(returns) * np.sqrt(total_trades)), 2)
        else:
            sharpe = 0.0

        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "total_bars": total_bars,
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "initial_balance": self.initial_balance,
            "final_balance": round(equity_curve[-1], 2),
            "net_pnl_usd": round(net_pnl, 4),
            "net_pnl_inr": round(net_pnl_inr, 2),
            "return_pct": round((net_pnl / self.initial_balance) * 100, 2),
            "total_fees_usd": round(total_fees, 4),
            "gross_profit_usd": round(gross_profit, 4),
            "gross_loss_usd": round(gross_loss, 4),
            "max_drawdown_pct": max_dd_pct,
            "max_drawdown_usd": max_dd_usd,
            "avg_win_usd": round(avg_win, 4),
            "avg_loss_usd": round(avg_loss, 4),
            "risk_reward_ratio": risk_reward_ratio,
            "sharpe_ratio": sharpe,
            "max_consecutive_wins": max_cons_wins,
            "max_consecutive_losses": max_cons_losses,
            "long_trades_count": len(long_trades),
            "long_win_rate": long_win_rate,
            "short_trades_count": len(short_trades),
            "short_win_rate": short_win_rate,
            "trades": trades
        }


def print_backtest_report(metrics: Dict[str, Any], show_recent_trades: int = 15):
    """Prints a formatted report of backtest results to the terminal."""
    if metrics.get("total_trades", 0) == 0:
        print("\n⚠️ No trades were executed during this backtest period.")
        return

    sym = metrics["symbol"]
    tf = metrics["timeframe"]
    bars = metrics["total_bars"]
    trades = metrics["trades"]
    
    print("\n" + "═" * 72)
    print(f" 🚀 DELTA BOT BACKTEST RESULTS: {sym} ({tf}) | {bars} Bars Analyzed")
    print("═" * 72)
    
    pnl_usd = metrics['net_pnl_usd']
    pnl_inr = metrics['net_pnl_inr']
    ret_pct = metrics['return_pct']
    pnl_sign = "+" if pnl_usd >= 0 else ""
    
    print(f" 💵 Net PnL (USDT)      : {pnl_sign}${pnl_usd:.2f} ({pnl_sign}{ret_pct:.2f}%)")
    print(f" 🇮🇳 Net PnL (INR)       : {pnl_sign}₹{pnl_inr:,.2f}")
    print(f" 🎯 Win Rate            : {metrics['win_rate_pct']}% ({metrics['win_count']} Wins / {metrics['loss_count']} Losses)")
    print(f" 📊 Profit Factor       : {metrics['profit_factor']}")
    print(f" 📉 Max Drawdown        : {metrics['max_drawdown_pct']}% (${metrics['max_drawdown_usd']:.2f})")
    print(f" 📈 Sharpe Ratio        : {metrics['sharpe_ratio']}")
    print("─" * 72)
    print(f" 🔢 Total Trades        : {metrics['total_trades']}")
    print(f" 🟢 Long Trades         : {metrics['long_trades_count']} (Win Rate: {metrics['long_win_rate']}%)")
    print(f" 🔴 Short Trades        : {metrics['short_trades_count']} (Win Rate: {metrics['short_win_rate']}%)")
    print(f" 💸 Total Fees Paid     : ${metrics['total_fees_usd']:.4f}")
    print(f" ⚖️ Risk:Reward Ratio   : 1 : {metrics['risk_reward_ratio']}")
    print(f" 🏆 Avg Win / Avg Loss  : +${metrics['avg_win_usd']:.2f} / -${abs(metrics['avg_loss_usd']):.2f}")
    print(f" 🔥 Max Streak (W/L)    : {metrics['max_consecutive_wins']} Wins / {metrics['max_consecutive_losses']} Losses")
    print("═" * 72)

    if show_recent_trades > 0 and trades:
        print(f"\n📋 LAST {min(show_recent_trades, len(trades))} TRADES LOG:")
        print("─" * 110)
        print(f"{'#':<4} {'Side':<6} {'Entry Time':<20} {'Exit Time':<20} {'Entry':<9} {'Exit':<9} {'Net($)':<9} {'Fee($)':<8} {'Exit Reason':<20}")
        print("─" * 110)
        for t in trades[-show_recent_trades:]:
            side_str = "🟢 BUY" if t['side'] == "LONG" else "🔴 SELL"
            pnl_str = f"+${t['net_pnl']:.2f}" if t['net_pnl'] >= 0 else f"-${abs(t['net_pnl']):.2f}"
            print(f"{t['trade_id']:<4} {side_str:<6} {t['entry_time'][:19]:<20} {t['exit_time'][:19]:<20} {t['entry_price']:<9.2f} {t['exit_price']:<9.2f} {pnl_str:<9} {t['fee']:<8.3f} {t['exit_reason'][:25]:<25}")
        print("─" * 110)


def main():
    parser = argparse.ArgumentParser(description="Backtest Delta Trading Bot Strategy")
    parser.add_argument("--symbol", type=str, default="ETHUSD", help="Trading Symbol (e.g. ETHUSD, XAUTUSD, BTCUSD, SOLUSD)")
    parser.add_argument("--timeframe", type=str, default="5m", help="Timeframe (e.g. 1m, 3m, 5m, 15m, 1h)")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backtest (default: 30)")
    parser.add_argument("--candles", type=int, default=0, help="Optional exact number of candles to fetch (overrides --days)")
    parser.add_argument("--balance", type=float, default=1000.0, help="Initial account balance in USD")
    parser.add_argument("--size", type=int, default=0, help="Order size (contracts). If 0, uses symbol profile default")
    parser.add_argument("--leverage", type=int, default=0, help="Leverage. If 0, uses symbol profile default")
    parser.add_argument("--export", type=str, default="", help="Optional CSV file path to export trade logs")
    parser.add_argument("--verbose", action="store_true", help="Print debug logs")
    
    args = parser.parse_args()
    set_log_level(args.verbose)

    # Dynamic symbol profile resolution
    profile = config.get_symbol_profile(args.symbol)
    order_size = args.size if args.size > 0 else profile.get("order_size", 1)
    leverage = args.leverage if args.leverage > 0 else profile.get("leverage", 100)

    # Calculate required candles based on days and timeframe
    tf_minutes = 5
    if args.timeframe in ("1m", "1"): tf_minutes = 1
    elif args.timeframe in ("3m", "3"): tf_minutes = 3
    elif args.timeframe in ("5m", "5"): tf_minutes = 5
    elif args.timeframe in ("15m", "15"): tf_minutes = 15
    elif args.timeframe in ("30m", "30"): tf_minutes = 30
    elif args.timeframe in ("1h", "60"): tf_minutes = 60

    needed_candles = args.candles if args.candles > 0 else int(args.days * (1440 / tf_minutes))

    bt = Backtester(
        symbol=args.symbol,
        timeframe=args.timeframe,
        initial_balance=args.balance,
        order_size=order_size,
        leverage=leverage
    )

    print(f"\n================================================================================")
    print(f" 🚀 RUNNING 30-DAY (1 MONTH) BACKTEST: {args.symbol.upper()} [{args.timeframe.upper()}]")
    print(f" Profile: {leverage}x Leverage | Size: {order_size} Lot | Target Candles: {needed_candles}")
    print(f"================================================================================")

    df = bt.fetch_candles(count=needed_candles)
    if df is None or len(df) == 0:
        print("❌ Failed to fetch candle data for backtest.")
        sys.exit(1)

    print(f"⚙️ Running simulation across {len(df)} candles ({df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]})...")
    metrics = bt.run(df)
    print_backtest_report(metrics)

    if args.export and metrics.get("trades"):
        try:
            pd.DataFrame(metrics["trades"]).to_csv(args.export, index=False)
            print(f"\n💾 Trade log successfully exported to: {args.export}")
        except Exception as e:
            print(f"\n❌ Error exporting trades: {e}")


if __name__ == "__main__":
    main()
