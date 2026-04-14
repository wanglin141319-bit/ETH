#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETH Daily Report v2.0 - Complete rewrite with 7 sections"""

import requests, json, os, sys, subprocess, re
from datetime import datetime, timedelta
from pathlib import Path

ETH_DIR   = Path(r"C:/Users/ZhuanZ（无密码）/mk-trading/ETH")
REPORTS   = ETH_DIR / "reports"
DATA_FILE = ETH_DIR / "strategy_data.json"
INDEX     = ETH_DIR / "index.html"
COINGECKO = "https://api.coingecko.com/api/v3"
COINGLASS = "https://open-api.coinglass.com/public/v2"

today    = datetime.now()
DATE_STR = today.strftime("%Y%m%d")
DATE_DISP = today.strftime("%Y年%m月%d日")
DATE_FILE = today.strftime("%Y-%m-%d")
REPORT_PATH = REPORTS / f"ETH_daily_report_{DATE_STR}.html"


# ─── JSON 数据持久化 ─────────────────────────────────────────

def load_data():
    if not DATA_FILE.exists():
        return default_data()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def default_data():
    return {"strategy_history": [], "trade_log": [], "error_log": [], "monthly_stats": {}}

def get_last_14(data):
    hist = data.get("strategy_history", [])
    out = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        rec = next((r for r in hist if r.get("date") == ds), None)
        if rec:
            out.append(rec)
        else:
            out.append({"date": ds, "date_display": d.strftime("%m月%d日"), "filled": False})
    return out


# ─── 数据获取 ────────────────────────────────────────────────

def fetch_eth():
    try:
        url = (f"{COINGECKO}/simple/price?ids=ethereum"
               "&vs_currencies=usd,cny"
               "&include_24hr_change=true"
               "&include_market_cap=true"
               "&include_24hr_vol=true")
        r = requests.get(url, timeout=30); r.raise_for_status()
        d = r.json()["ethereum"]
        return {"price_usd": d["usd"],
                "price_cny": d.get("cny", d["usd"]*7.24),
                "change_24h": d.get("usd_24h_change", 0),
                "mcap": d.get("usd_market_cap", 0),
                "vol_24h": d.get("usd_24h_vol", 0)}
    except Exception as e:
        print(f"[WARN] ETH价格: {e}")
        return {"price_usd": 0, "price_cny": 0, "change_24h": 0, "mcap": 0, "vol_24h": 0}

def fetch_yesterday_eth(price_usd):
    try:
        url = f"{COINGECKO}/coins/ethereum/ohlc?vs_currency=usd&days=2"
        r = requests.get(url, timeout=30); r.raise_for_status()
        ohlc = r.json()
        if len(ohlc) >= 2:
            return float(ohlc[-2][4])
    except: pass
    return price_usd

def fetch_funding():
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        r = requests.get(url, timeout=15); r.raise_for_status()
        for item in r.json():
            if item.get("symbol") == "ETHUSDT":
                return float(item.get("lastFundingRate", 0)) * 100
    except: pass
    return 0.0100

def fetch_oi():
    try:
        url = f"{COINGLASS}/open_interest?symbol=ETH"
        r = requests.get(url, timeout=15); r.raise_for_status()
        data = r.json()
        if data.get("data"):
            item = data["data"][0]
            return {"usd": float(item.get("openInterest", 0)),
                    "chg": float(item.get("openInterestChange", 0))}
    except: pass
    return {"usd": 0, "chg": 0}

def fetch_liq():
    try:
        url = f"{COINGLASS}/liquidation?symbol=ETH"
        r = requests.get(url, timeout=15); r.raise_for_status()
        data = r.json()
        if data.get("data"):
            item = data["data"][0]
            total = float(item.get("total", 0))
            lp = float(item.get("longPercent", 50))
            return {"total": total, "long_pct": lp, "short_pct": 100-lp}
    except: pass
    return {"total": 0, "long_pct": 50, "short_pct": 50}

def calc_levels(price):
    return {
        "r3": round(price*1.05, 2), "r2": round(price*1.03, 2),
        "r1": round(price*1.015, 2), "pivot": round(price, 2),
        "s1": round(price*0.985, 2), "s2": round(price*0.97, 2),
        "s3": round(price*0.95, 2)
    }


# ─── 今日记录生成 ────────────────────────────────────────────

def build_today(ec, ey, f, oi_d, liq_d, lv):
    rec = {
        "date": DATE_FILE, "date_display": DATE_DISP, "filled": True,
        "price_current": ec["price_usd"], "price_yesterday": round(ey, 2),
        "change_24h": round(ec["change_24h"], 2),
        "change_sign": "+" if ec["change_24h"] >= 0 else "",
        "funding_rate": round(f, 4),
        "open_interest_usd": oi_d["usd"], "open_interest_chg": round(oi_d["chg"], 2),
        "liquidation_usd": liq_d["total"], "liq_long_pct": liq_d["long_pct"],
        "levels": lv,
        "direction": "", "entry_price": 0, "stop_loss": 0, "take_profit": 0,
        "review": "", "error_type": "", "error_desc": ""
    }
    # 合并用户已有填写
    data = load_data()
    existing = next((r for r in data["strategy_history"] if r.get("date") == DATE_FILE), None)
    if existing:
        for k in ["direction","entry_price","stop_loss","take_profit","review","error_type","error_desc"]:
            if existing.get(k):
                rec[k] = existing[k]
    return rec


# ─── 统计 ────────────────────────────────────────────────────

def win_rate(log):
    if not log: return {"total":0,"win":0,"loss":0,"rate":0,"avg_win":0,"avg_loss":0}
    wins, losses = [], []
    for t in log:
        pnl = t.get("pnl_pct", 0)
        (wins if pnl > 0 else losses).append(pnl)
    return {
        "total": len(log), "win": len(wins), "loss": len(losses),
        "rate": round(len(wins)/len(log)*100, 1) if log else 0,
        "avg_win": round(sum(wins)/len(wins), 2) if wins else 0,
        "avg_loss": round(sum(losses)/len(losses), 2) if losses else 0
    }

def monthly_review(log, data):
    this_m = f"{today.year}-{today.month:02d}"
    mlog = [t for t in log if str(t.get("date","")[:7]) == this_m]
    wr = win_rate(mlog)
    total_pnl = sum(t.get("pnl_pct", 0) for t in mlog)
    errs = [e for e in data.get("error_log",[]) if str(e.get("date","")[:7]) == this_m]
    return {
        "month": this_m, "trades": len(mlog), "win_rate": wr["rate"],
        "total_pnl_pct": round(total_pnl, 2),
        "error_count": len(errs),
        "biggest_win": max((t["pnl_pct"] for t in mlog), default=0),
        "biggest_loss": min((t["pnl_pct"] for t in mlog), default=0)
    }


# ─── Twitter 素材 ────────────────────────────────────────────

def twitter_copy(ec, ey, lv, rec, f, wr, mr):
    s = "+" if ec["change_24h"] >= 0 else ""
    emoji = "ETH" if ec["change_24h"] >= 0 else "ETH"
    d_map = {"多头":"LONG","空头":"SHORT","观望":"WAIT","震荡":"RANGE","":"TBD"}
    direction = d_map.get(rec.get("direction",""), rec.get("direction","—"))
    entry_info = f"Entry: ${rec['entry_price']:,.2f}" if rec.get("entry_price") else ""
    return (
        f"{emoji} Daily Report {today.strftime('%Y-%m-%d')}\n\n"
        f"Price: ${ec['price_usd']:,.2f} ({s}{ec['change_24h']:.2f}% 24h)\n"
        f"Yesterday: ${ey:,.2f}\n"
        f"Funding Rate: {f:.4f}%\n"
        f"R1: ${lv['r1']:,.2f} | S1: ${lv['s1']:,.2f}\n\n"
        f"Bias: {direction}\n"
        f"{entry_info}\n\n"
        f"This Month: {mr['trades']} trades | Win Rate: {mr['win_rate']:.1f}%\n"
        f"Total PnL: {mr['total_pnl_pct']:+.2f}% | Errors: {mr['error_count']}\n\n"
        f"#ETH #Ethereum #CryptoTrading"
    )


# ─── 辅助函数 ────────────────────────────────────────────────

def fn(n, d=2):
    if not n: return "N/A"
    a = abs(n)
    if a >= 1e9: return f"${n/1e9:.{d}f}B"
    if a >= 1e6: return f"${n/1e6:.{d}f}M"
    if a >= 1e3: return f"${n/1e3:.{d}f}K"
    return f"{n:.{d}f}"

def c(v): return "#f85149" if v < 0 else "#3fb950"

def sec(icon, text):
    return f'<div class="sec-title"><span class="sec-icon">{icon}</span><span>{text}</span></div>'

def sc(label, value, sub="", cls=""):
    return (f'<div class="stat-card {cls}">'
            f'<div class="stat-lbl">{label}</div>'
            f'<div class="stat-val">{value}</div>'
            f'{f"<div class=stat-sub>{sub}</div>" if sub else ""}</div>')


# ─── HTML 生成 ────────────────────────────────────────────────

def gen_html(ec, ey, f, oi_d, liq_d, lv, data, rec, wr, mr):
    last14 = get_last_14(data)
    trade_log = data.get("trade_log", [])
    error_log  = data.get("error_log", [])
    tw = twitter_copy(ec, ey, lv, rec, f, wr, mr)
    chg_c = c(ec["change_24h"])
    sign = "+" if ec["change_24h"] >= 0 else ""

    # 14天行
    hrows = ""
    for day in last14:
        d = day.get("date_display","")
        if day.get("filled"):
            chg = day.get("change_24h", 0)
            cs = "+" if chg >= 0 else ""
            cc = c(chg)
            dm = {"多头":"&#128998;做多","空头":"&#129001;做空","观望":"&#9208;观望","震荡":"&#129504;震荡","":"—"}
            direction = dm.get(day.get("direction",""), day.get("direction","—"))
            rev = (day.get("review","") or "暂无")[:40]
            err_tag = (f'<span class="err-tag">&#9888; {day.get("error_type","")}</span>'
                       if day.get("error_type") else "")
            entry = (f"入场 ${day.get('entry_price',0):,.0f}"
                     if day.get("entry_price") else "")
            hrows += f"""<tr>
<td>{d}</td>
<td style="color:{cc}">{cs}{chg:.2f}%</td>
<td>{direction}</td>
<td>{entry}</td>
<td class="review-cell">{rev}</td>
<td>{err_tag}</td>
</tr>"""
        else:
            hrows += f"""<tr class="empty-row"><td>{d}</td><td colspan="5" class="empty-cell">— 无记录 —</td></tr>"""

    # 错误
    erows = ""
    for err in error_log[-10:][::-1]:
        erows += f"""<div class="error-card">
<div class="error-header"><span class="err-date">{err.get('date','')}</span>
<span class="err-type">{err.get('type','')}</span></div>
<div class="err-desc">{err.get('desc','')}</div></div>"""
    if not erows: erows = '<div class="empty-msg">暂无错误记录，保持良好习惯！</div>'

    # 交易
    tcards = ""
    for t in trade_log[-5:][::-1]:
        pc = c(t.get("pnl_pct", 0))
        ps = "+" if t.get("pnl_pct", 0) >= 0 else ""
        di = {"多头":"&#128998;","空头":"&#129001;","震荡":"&#129504;","观望":"&#9208;"}.get(t.get("direction",""), "&#128202;")
        tcards += f"""<div class="trade-card">
<div class="trade-dir">{di} {t.get('direction','')}</div>
<div class="trade-price">入 ${t.get('entry',0):,.2f} → 出 ${t.get('exit',0):,.2f}</div>
<div class="trade-pnl" style="color:{pc}">{ps}{t.get('pnl_pct',0):+.2f}%</div></div>"""
    if not tcards: tcards = '<div class="empty-msg">暂无交易记录</div>'

    mpnl_c = c(mr["total_pnl_pct"])
    wr_c = c(wr["rate"]-50)

    # CSS（避免在 f-string 中使用 {{}} 包裹含 - 的内容，改用字符串拼接）
    media_css_open  = "@media(max-width:768px){.levels-wrap"
    media_css_body  = ",.edit-row,.edit-row3{grid-template-columns:1fr}}"
    media_css_close = "}"
    media_block = media_css_open + media_css_body + media_css_close

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ETH 日报 {DATE_DISP}</title>
<style>
:root{{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#e6edf3;
       --muted:#8b949e;--accent:#58a6ff;--green:#3fb950;--red:#f85149;
       --yellow:#d29922;--purple:#bc8cff}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'PingFang SC','Microsoft YaHei',sans-serif;
      background:var(--bg);color:var(--text);min-height:100vh;padding:20px}}
.wrap{{max-width:1100px;margin:0 auto}}

/* Hero */
.hero{{background:var(--card);border:1px solid var(--border);border-radius:16px;
        padding:30px 35px;margin-bottom:24px}}
.hero-top{{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px}}
.hero-title{{font-size:1.8em;font-weight:700;color:#fff}}
.hero-sub{{color:var(--muted);margin-top:4px;font-size:.9em}}
.hero-badge{{padding:6px 16px;border-radius:20px;font-size:.85em;
             background:{chg_c}22;color:{chg_c};border:1px solid {chg_c}44}}
.price-block{{display:flex;gap:40px;flex-wrap:wrap;margin-top:20px}}
.price-main{{font-size:2.6em;font-weight:700;color:#fff;letter-spacing:-1px}}
.price-label{{color:var(--muted);font-size:.8em;margin-bottom:4px}}
.price-yest{{font-size:1.4em;color:var(--muted)}}

/* Cards */
.card{{background:var(--card);border:1px solid var(--border);border-radius:12px;
       padding:22px 24px;margin-bottom:20px}}
.sec-title{{display:flex;align-items:center;gap:10px;font-size:1.15em;font-weight:600;
            color:#fff;margin-bottom:18px;padding-bottom:12px;border-bottom:1px solid var(--border)}}
.sec-icon{{font-size:1.2em}}

/* Stats */
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}}
.stat-card{{background:#1c2128;border:1px solid var(--border);border-radius:10px;padding:14px 16px}}
.stat-lbl{{color:var(--muted);font-size:.8em;margin-bottom:6px}}
.stat-val{{font-size:1.4em;font-weight:700;color:#fff}}
.stat-sub{{color:var(--muted);font-size:.75em;margin-top:4px}}

/* Levels */
.levels-wrap{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.level-col h4{{font-size:.9em;color:var(--muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:1px}}
.level-row{{display:flex;justify-content:space-between;padding:8px 12px;
            border-radius:8px;margin-bottom:6px;background:#1c2128}}
.level-r{{color:var(--red)}}.level-s{{color:var(--green)}}.level-p{{color:#fff;font-weight:600}}

/* Liq */
.liq-bar{{height:22px;background:#1c2128;border-radius:11px;overflow:hidden;margin:12px 0}}
.liq-fill{{height:100%;background:linear-gradient(90deg,var(--red),#ff6b6b);
           display:flex;align-items:center;padding-left:10px;color:#fff;
           font-size:.8em;font-weight:600;width:{liq_d['long_pct']:.0f}%;transition:width .6s}}

/* Table */
table{{width:100%;border-collapse:collapse;font-size:.9em}}
th{{text-align:left;padding:10px 12px;color:var(--muted);border-bottom:1px solid var(--border);font-weight:500}}
td{{padding:10px 12px;border-bottom:1px solid #21262d}}
tr:last-child td{{border-bottom:none}}
.empty-row td{{opacity:.4}}
.empty-cell{{text-align:center;color:var(--muted)}}
.review-cell{{color:var(--muted);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.err-tag{{background:var(--red)22;color:var(--red);padding:2px 8px;border-radius:10px;font-size:.8em}}

/* Winrate */
.winrate-ring{{display:flex;align-items:center;gap:30px;flex-wrap:wrap}}
.ring{{position:relative;width:120px;height:120px;flex-shrink:0}}
.ring svg{{transform:rotate(-90deg);width:120px;height:120px}}
.ring-center{{position:absolute;inset:0;display:flex;flex-direction:column;
               align-items:center;justify-content:center}}
.ring-pct{{font-size:1.6em;font-weight:700;color:#fff}}
.ring-label{{font-size:.75em;color:var(--muted)}}
.winrate-cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;flex:1}}

/* Month */
.month-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}}

/* Error */
.error-card{{background:#1c2128;border:1px solid var(--border);border-radius:10px;
              padding:14px 16px;margin-bottom:10px}}
.error-header{{display:flex;justify-content:space-between;margin-bottom:6px}}
.err-date{{color:var(--muted);font-size:.85em}}
.err-type{{background:var(--red)22;color:var(--red);padding:2px 10px;border-radius:10px;font-size:.8em}}
.err-desc{{color:var(--text);font-size:.9em;line-height:1.5}}

/* Trade */
.trade-list{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.trade-card{{background:#1c2128;border:1px solid var(--border);border-radius:10px;padding:14px 16px}}
.trade-dir{{font-weight:600;margin-bottom:8px}}
.trade-price{{color:var(--muted);font-size:.85em;margin-bottom:6px}}
.trade-pnl{{font-size:1.2em;font-weight:700}}

/* Twitter */
.tw-box{{background:#1c2128;border:1px solid var(--border);border-radius:12px;padding:20px;
         font-family:monospace;font-size:.9em;line-height:1.8;white-space:pre-wrap;
         color:var(--text);position:relative}}
.tw-copy-btn{{position:absolute;top:14px;right:14px;padding:6px 16px;
              background:var(--accent)22;color:var(--accent);border:1px solid var(--accent)44;
              border-radius:8px;cursor:pointer;font-size:.8em}}
.tw-footer{{margin-top:12px;padding-top:12px;border-top:1px solid var(--border);color:var(--muted);font-size:.8em}}

/* Edit */
.edit-zone{{background:#1c2128;border:1px solid var(--yellow)44;border-radius:12px;
            padding:20px;margin-bottom:20px}}
.edit-zone h4{{color:var(--yellow);margin-bottom:14px;font-size:.95em}}
.edit-row{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}}
.edit-field label{{display:block;color:var(--muted);font-size:.8em;margin-bottom:4px}}
.edit-field input,.edit-field select,.edit-field textarea{{
    width:100%;background:#0d1117;border:1px solid var(--border);border-radius:8px;
    padding:8px 12px;color:var(--text);font-size:.9em;outline:none}}
.edit-field input:focus,.edit-field select:focus,.edit-field textarea:focus{{border-color:var(--accent)}}
.edit-field textarea{{resize:vertical;min-height:70px}}
.save-btn{{padding:10px 28px;background:var(--accent);color:#fff;border:none;
           border-radius:8px;cursor:pointer;font-size:.9em;font-weight:600;
           float:right;margin-top:8px}}
.save-btn:hover{{opacity:.85}}

.empty-msg{{color:var(--muted);text-align:center;padding:30px;font-size:.9em}}

{media_block}
</style>
</head>
<body>
<div class="wrap">

<!-- HERO -->
<div class="hero">
  <div class="hero-top">
    <div>
      <div class="hero-title">ETH Daily Report</div>
      <div class="hero-sub">{DATE_DISP} &nbsp;|&nbsp; 数据来源：CoinGecko</div>
    </div>
    <div class="hero-badge">{sign}{ec['change_24h']:.2f}% (24h)</div>
  </div>
  <div class="price-block">
    <div><div class="price-label">当前价格</div><div class="price-main">${ec['price_usd']:,.2f}</div></div>
    <div><div class="price-label">≈ CNY</div><div class="price-main" style="font-size:1.8em">¥{ec['price_cny']:,.2f}</div></div>
    <div><div class="price-label">昨日收盘</div><div class="price-yest">${ey:,.2f}</div></div>
  </div>
</div>

<!-- S1: 数据面板 -->
<div class="card">
  {sec("&#128202;", "1. 数据统计面板")}
  <div class="stat-grid">
    {sc("当前价格", f"${ec['price_usd']:,.2f}")}
    {sc("昨日收盘", f"${ey:,.2f}")}
    {sc("24h涨跌", f"{sign}{ec['change_24h']:.2f}%", "CoinGecko")}
    {sc("资金费率", f"{f:.4f}%", "Binance 8h")}
    {sc("未平仓合约", fn(oi_d['usd']), f"OI变化 {oi_d['chg']:+.2f}%", "CoinGlass")}
    {sc("24h爆仓", fn(liq_d['total']), f"多{liq_d['long_pct']:.0f}%/空{liq_d['short_pct']:.0f}%", "CoinGlass")}
    {sc("市值", fn(ec['mcap']), "USD")}
    {sc("24h成交量", fn(ec['vol_24h']), "USD")}
  </div>
</div>

<!-- 支撑阻力 -->
<div class="card">
  {sec("&#128205;", "关键支撑阻力位")}
  <div class="levels-wrap">
    <div class="level-col">
      <h4>阻力位 Resistance</h4>
      <div class="level-row level-r"><span>R3</span><span>${lv['r3']:,.2f}</span></div>
      <div class="level-row level-r"><span>R2</span><span>${lv['r2']:,.2f}</span></div>
      <div class="level-row level-r"><span>R1</span><span>${lv['r1']:,.2f}</span></div>
      <div class="level-row level-p"><span>Pivot</span><span>${lv['pivot']:,.2f}</span></div>
    </div>
    <div class="level-col">
      <h4>支撑位 Support</h4>
      <div class="level-row level-s"><span>S1</span><span>${lv['s1']:,.2f}</span></div>
      <div class="level-row level-s"><span>S2</span><span>${lv['s2']:,.2f}</span></div>
      <div class="level-row level-s"><span>S3</span><span>${lv['s3']:,.2f}</span></div>
    </div>
  </div>
</div>

<!-- 爆仓 -->
<div class="card">
  {sec("&#128165;", "24h 爆仓分布")}
  <div class="liq-bar"><div class="liq-fill">多头 {liq_d['long_pct']:.0f}%</div></div>
  <div style="display:flex;justify-content:space-between;color:var(--muted);font-size:.85em">
    <span>&#129001; 空头 {liq_d['short_pct']:.0f}%</span>
    <span>全网爆仓 {fn(liq_d['total'])}</span>
  </div>
</div>

<!-- S2: 14天追踪 -->
<div class="card">
  {sec("&#128197;", "2. 14天策略追踪")}
  <div style="overflow-x:auto">
  <table>
    <thead><tr><th>日期</th><th>涨跌</th><th>方向</th><th>入场</th><th>复盘小结</th><th>错误</th></tr></thead>
    <tbody>{hrows}</tbody>
  </table>
  </div>
</div>

<!-- S3: 错误 -->
<div class="card">
  {sec("&#9888;", "3. 错误统计（近10条）")}
  {erows}
</div>

<!-- S4: 方向 -->
<div class="card">
  {sec("&#127919;", "4. 做单方向与入场点位（最近5笔）")}
  <div class="trade-list">{tcards}</div>
</div>

<!-- S5: 胜率+月回顾 -->
<div class="card">
  {sec("&#128200;", "5. 胜率计算 & 月度回顾")}
  <div style="margin-bottom:24px">
    <div style="color:var(--muted);font-size:.9em;margin-bottom:14px">总体胜率</div>
    <div class="winrate-ring">
      <div class="ring">
        <svg viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="50" fill="none" stroke="#21262d" stroke-width="12"/>
          <circle cx="60" cy="60" r="50" fill="none" stroke="{wr_c}"
            stroke-width="12"
            stroke-dasharray="{3.14*50*wr['rate']/100} {3.14*100}"
            stroke-linecap="round"/>
        </svg>
        <div class="ring-center">
          <div class="ring-pct">{wr['rate']:.1f}%</div>
          <div class="ring-label">胜率</div>
        </div>
      </div>
      <div class="winrate-cards">
        {sc("总交易次数", str(wr['total']))}
        {sc("盈利次数", str(wr['win']), "", "green")}
        {sc("亏损次数", str(wr['loss']), "", "red")}
        {sc("平均盈利", f"+{wr['avg_win']:.2f}%", "胜局均值", "green")}
        {sc("平均亏损", f"{wr['avg_loss']:.2f}%", "败局均值", "red")}
      </div>
    </div>
  </div>
  <div>
    <div style="color:var(--muted);font-size:.9em;margin-bottom:14px">{mr['month']} 月度回顾</div>
    <div class="month-grid">
      {sc("交易次数", str(mr['trades']))}
      {sc("月胜率", f"{mr['win_rate']:.1f}%", "", "green" if mr['win_rate']>=50 else "red")}
      {sc("月盈亏", f"{mr['total_pnl_pct']:+.2f}%", "累计收益率", "green" if mr['total_pnl_pct']>=0 else "red")}
      {sc("最大盈利", f"+{mr['biggest_win']:.2f}%", "", "green")}
      {sc("最大亏损", f"{mr['biggest_loss']:.2f}%", "", "red")}
      {sc("本月错误", f"{mr['error_count']}次", "", "red")}
    </div>
  </div>
</div>

<!-- S6: Twitter -->
<div class="card">
  {sec("&#128039;", "6. 英文推特素材")}
  <div class="tw-box" id="tw-box">{tw}<button class="tw-copy-btn" onclick="copyTw()">Copy</button></div>
  <div class="tw-footer">复制后可直接发推 &nbsp;|&nbsp; 完整数据请参考上方各板块</div>
</div>

<!-- S7: 手动填写 -->
<div class="edit-zone">
  <h4>&#128221; 每日手动填写（保存后刷新报告）</h4>
  <div class="edit-row">
    <div class="edit-field">
      <label>今日方向</label>
      <select id="f-direction">
        <option value="">— 选择方向 —</option>
        <option value="多头">&#128998; 多头 LONG</option>
        <option value="空头">&#129001; 空头 SHORT</option>
        <option value="震荡">&#129504; 震荡 RANGE</option>
        <option value="观望">&#9208; 观望 WAIT</option>
      </select>
    </div>
    <div class="edit-field">
      <label>入场价格</label>
      <input type="number" id="f-entry" step="0.01" placeholder="如 3456.78">
    </div>
  </div>
  <div class="edit-row">
    <div class="edit-field">
      <label>止损价格</label>
      <input type="number" id="f-stop" step="0.01" placeholder="如 3400.00">
    </div>
    <div class="edit-field">
      <label>止盈价格</label>
      <input type="number" id="f-target" step="0.01" placeholder="如 3600.00">
    </div>
  </div>
  <div class="edit-field" style="margin-bottom:12px">
    <label>今日复盘小结</label>
    <textarea id="f-review" placeholder="记录分析思路、决策依据、盈亏情况..."></textarea>
  </div>
  <div class="edit-row">
    <div class="edit-field">
      <label>错误类型</label>
      <select id="f-err-type">
        <option value="">— 无错误 —</option>
        <option value="重仓">&#9888; 重仓</option>
        <option value="逆势">&#9888; 逆势</option>
        <option value="不止损">&#9888; 不止损</option>
        <option value="追单">&#9888; 追单</option>
        <option value="扛单">&#9888; 扛单</option>
        <option value="其他">&#9888; 其他</option>
      </select>
    </div>
    <div class="edit-field">
      <label>错误描述（简短）</label>
      <input type="text" id="f-err-desc" placeholder="如：在阻力位上方追多被止损">
    </div>
  </div>
  <button class="save-btn" onclick="saveEntry()">&#128190; 保存</button>
  <div style="clear:both"></div>
</div>

</div>
<script>
const DATE_FILE = "{DATE_FILE}";
function saveEntry() {{
  const entry = {{
    date: DATE_FILE,
    direction: document.getElementById('f-direction').value,
    entry_price: parseFloat(document.getElementById('f-entry').value) || 0,
    stop_loss: parseFloat(document.getElementById('f-stop').value) || 0,
    take_profit: parseFloat(document.getElementById('f-target').value) || 0,
    review: document.getElementById('f-review').value,
    error_type: document.getElementById('f-err-type').value,
    error_desc: document.getElementById('f-err-desc').value,
  }};
  const blob = new Blob([JSON.stringify(entry, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'ETH_entry_' + DATE_FILE + '.json';
  a.click();
  alert('已生成填写文件，请复制内容追加到 strategy_data.json');
}}
function copyTw() {{
  const text = document.getElementById('tw-box').innerText.replace('Copy','').trim();
  navigator.clipboard.writeText(text).then(()=>alert('已复制推文！'));
}}
</script>
</body>
</html>"""
    return html


# ─── 索引更新 ────────────────────────────────────────────────

def update_index(name):
    if not INDEX.exists():
        body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>ETH 日报归档</title>
<style>
body{{font-family:sans-serif;background:#0d1117;color:#e6edf3;padding:20px}}
.wrap{{max-width:700px;margin:0 auto}}
.hero{{text-align:center;padding:40px;background:#161b22;border:1px solid #30363d;border-radius:16px;margin-bottom:24px}}
.hero h1{{font-size:1.8em;margin-bottom:8px}}
.report-list{{background:#161b22;border:1px solid #30363d;border-radius:12px;overflow:hidden}}
.report-item{{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid #21262d}}
.report-item:last-child{{border-bottom:none}}
.report-link{{color:#58a6ff;text-decoration:none;padding:6px 16px;background:#58a6ff11;border-radius:20px}}
</style>
</head>
<body><div class="wrap">
<div class="hero"><h1>&#128202; ETH 日报归档</h1><p>每日策略追踪与复盘</p></div>
<div class="report-list">
<div class="report-item"><span class="report-date">{DATE_DISP}</span><a href="reports/{name}" class="report-link">查看报告</a></div>
</div>
</div></body></html>"""
    else:
        with open(INDEX, "r", encoding="utf-8") as f:
            body = f.read()
        new_item = f'<div class="report-item"><span class="report-date">{DATE_DISP}</span><a href="reports/{name}" class="report-link">查看报告</a></div>'
        body = re.sub(r'(<div class="report-list">)',
                      r'\1\n            ' + new_item, body)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"✅ 索引已更新: {INDEX}")


# ─── Git 推送 ───────────────────────────────────────────────

def git_push():
    for cmd in [
        ["git", "add", "."],
        ["git", "commit", "-m", f"feat: ETH日报 {DATE_DISP}"],
        ["git", "push", "origin", "master"],
    ]:
        r = subprocess.run(cmd, cwd=str(ETH_DIR), capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stderr:
            print(f"[WARN] {' '.join(cmd)}: {r.stderr.strip()}")


# ─── 主流程 ─────────────────────────────────────────────────

def main():
    print(f"=== ETH 日报 {DATE_DISP} ===")
    if REPORT_PATH.exists():
        print(f"今日报告已存在: {REPORT_PATH}")
        return 0

    REPORTS.mkdir(parents=True, exist_ok=True)
    print("📡 获取数据...")
    ec  = fetch_eth()
    if not ec["price_usd"]:
        print("[ERROR] 无法获取ETH价格"); return 1
    ey  = fetch_yesterday_eth(ec["price_usd"])
    f   = fetch_funding()
    oi  = fetch_oi()
    liq = fetch_liq()
    lv  = calc_levels(ec["price_usd"])

    data = load_data()
    rec  = build_today(ec, ey, f, oi, liq, lv)
    # 追加今日记录（去重）
    data["strategy_history"] = [
        r for r in data["strategy_history"] if r.get("date") != DATE_FILE
    ] + [rec]
    # 保留180天
    cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    data["strategy_history"] = [r for r in data["strategy_history"] if r.get("date","0") >= cutoff]
    save_data(data)

    wr = win_rate(data.get("trade_log", []))
    mr = monthly_review(data.get("trade_log", []), data)

    print("📝 生成报告...")
    html = gen_html(ec, ey, f, oi, liq, lv, data, rec, wr, mr)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 报告已保存: {REPORT_PATH}")
    update_index(REPORT_PATH.name)
    print("🔄 推送 GitHub...")
    git_push()
    print("=== 完成 ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
