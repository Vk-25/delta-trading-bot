import sys
from bot.config import config
from bot.delta_client import DeltaExchangeClient
from bot.utils import logger

def test_delta_connection():
    print("=" * 65)
    print("DELTA EXCHANGE BOT - CONNECTION & ACCOUNT DIAGNOSTICS")
    print("=" * 65)
    print(f"Environment    : {config.DELTA_ENVIRONMENT.upper()}")
    print(f"Base URL       : {config.get_base_url()}")
    print(f"Trading Symbol : {config.TRADING_SYMBOL}")
    print(f"Order Size     : {config.ORDER_SIZE}")
    print(f"Leverage       : {config.LEVERAGE}x")
    print("-" * 65)

    if not config.DELTA_API_KEY or not config.DELTA_API_SECRET:
        print("WARNING: DELTA_API_KEY or DELTA_API_SECRET is missing in .env file!")
        print("Please edit .env and fill in your API credentials from Delta Exchange.")
        print("-" * 65)
        
    client = DeltaExchangeClient()

    # 1. Test public product resolution
    print("[1/4] Checking Product Catalog for symbol...")
    prod = client.get_product(config.TRADING_SYMBOL)
    if prod:
        print(f" SUCCESS: Found {config.TRADING_SYMBOL} (Product ID: {prod.get('id')}, Tick: {prod.get('tick_size')}, Contract Value: {prod.get('contract_value')})")
    else:
        print(f" FAILED: Symbol '{config.TRADING_SYMBOL}' not found on Delta Exchange {config.DELTA_ENVIRONMENT} catalog.")

    # 2. Test authenticated profile
    print("\n[2/4] Testing API Key Authentication (Profile)...")
    profile = client.get_profile()
    if profile.get("success"):
        res = profile.get("result", {})
        print(f" SUCCESS: Authenticated as User ID: {res.get('id')} | Email: {res.get('email', 'N/A')}")
    else:
        print(f" FAILED: {profile.get('error', 'Authentication failed')}")

    # 3. Test wallet balances
    print("\n[3/4] Fetching Wallet Balances...")
    balances = client.get_wallet_balances()
    if balances.get("success"):
        res = balances.get("result", [])
        if isinstance(res, list) and len(res) > 0:
            for b in res:
                print(f" -> Asset: {b.get('asset_symbol')} | Balance: {b.get('balance')} | Available: {b.get('available_balance')}")
        else:
            print(" -> No asset balance records returned (Account may be newly created or 0 balance).")
    else:
        print(f" FAILED to fetch balances: {balances.get('error')}")

    # 4. Check active positions
    print("\n[4/4] Checking Active Positions...")
    pos = client.get_position_for_symbol(config.TRADING_SYMBOL)
    if pos:
        print(f" -> Active Position: Size = {pos.get('size')} | Entry = {pos.get('entry_price')} | Unrealized PnL = {pos.get('unrealized_pnl')}")
    else:
        print(f" -> No active position currently open for {config.TRADING_SYMBOL}.")

    print("=" * 65)
    print("DIAGNOSTICS COMPLETED.")
    print("=" * 65)

if __name__ == "__main__":
    test_delta_connection()
