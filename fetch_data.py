#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick data fetch test for ETH daily report"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests, json

COINGECKO = "https://api.coingecko.com/api/v3"

# 1. ETH price
try:
    url = (f"{COINGECKO}/simple/price?ids=ethereum"
           "&vs_currencies=usd,cny"
           "&include_24hr_change=true"
           "&include_market_cap=true"
           "&include_24hr_vol=true")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    eth = r.json()["ethereum"]
    price_usd = eth["usd"]
    price_cny = eth.get("cny", price_usd * 7.24)
    change_24h = eth.get("usd_24h_change", 0)
    mcap = eth.get("usd_market_cap", 0)
    vol_24h = eth.get("usd_24h_vol", 0)
    print(f"ETH Price: ${price_usd:,.2f}")
    print(f"24h Change: {change_24h:.2f}%")
    print(f"CNY: ¥{price_cny:,.2f}")
    print(f"Mcap: ${mcap:,.0f}")
    print(f"Vol: ${vol_24h:,.0f}")
except Exception as e:
    print(f"ETH price error: {e}")
    price_usd = 0

# 2. Yesterday OHLC
yesterday_close = price_usd
try:
    url = f"{COINGECKO}/coins/ethereum/ohlc?vs_currency=usd&days=2"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    ohlc = r.json()
    if len(ohlc) >= 2:
        yesterday_close = float(ohlc[-2][4])
        print(f"Yesterday close: ${yesterday_close:,.2f}")
except Exception as e:
    print(f"OHLC error: {e}")

# 3. Binance funding
funding_rate = 0.01
try:
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    for item in r.json():
        if item.get("symbol") == "ETHUSDT":
            funding_rate = float(item.get("lastFundingRate", 0)) * 100
            print(f"Funding rate: {funding_rate:.4f}%")
            break
except Exception as e:
    print(f"Funding error: {e}, using default")

# 4. CoinGlass OI (likely timeout/rate-limit)
oi_usd = 0
oi_chg = 0
try:
    url = "https://open-api.coinglass.com/public/v2/open_interest?symbol=ETH"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("data"):
        item = data["data"][0]
        oi_usd = float(item.get("openInterest", 0))
        oi_chg = float(item.get("openInterestChange", 0))
        print(f"OI: ${oi_usd:,.0f}, chg: {oi_chg:.2f}%")
except Exception as e:
    print(f"OI error: {e}")

# 5. CoinGlass liquidation (likely timeout/rate-limit)
liq_total = 0
liq_long_pct = 50
try:
    url = "https://open-api.coinglass.com/public/v2/liquidation?symbol=ETH"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("data"):
        item = data["data"][0]
        liq_total = float(item.get("total", 0))
        liq_long_pct = float(item.get("longPercent", 50))
        print(f"Liq: ${liq_total:,.0f}, long%: {liq_long_pct:.0f}%")
except Exception as e:
    print(f"Liq error: {e}")

# Save results to JSON for the main script
result = {
    "price_usd": price_usd,
    "price_cny": price_cny if price_usd else 0,
    "change_24h": change_24h if price_usd else 0,
    "mcap": mcap if price_usd else 0,
    "vol_24h": vol_24h if price_usd else 0,
    "yesterday_close": yesterday_close,
    "funding_rate": funding_rate,
    "oi_usd": oi_usd,
    "oi_chg": oi_chg,
    "liq_total": liq_total,
    "liq_long_pct": liq_long_pct,
}

out_path = r"C:\Users\ZhuanZ（无密码）\mk-trading\ETH\fetch_result.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"Data saved to {out_path}")
print("DONE")
