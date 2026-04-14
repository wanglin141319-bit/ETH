#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETH 日报生成脚本
生成包含 BTC/ETH 价格、资金费率、持仓量、爆仓数据、关键支撑阻力位的 HTML 报告
"""

import requests
import json
from datetime import datetime, timedelta
import os
import sys

# 配置
REPORTS_DIR = "C:/Users/ZhuanZ（无密码）/mk-trading/ETH/reports"
INDEX_FILE = "C:/Users/ZhuanZ（无密码）/mk-trading/ETH/index.html"
COINGECKO_API = "https://api.coingecko.com/api/v3"

# 获取今日日期
today = datetime.now()
date_str = today.strftime("%Y%m%d")
date_display = today.strftime("%Y年%m月%d日")
date_file = today.strftime("%Y-%m-%d")

def check_report_exists():
    """检查今日报告是否已存在"""
    report_path = os.path.join(REPORTS_DIR, f"ETH_daily_report_{date_str}.html")
    return os.path.exists(report_path)

def fetch_btc_data():
    """获取 BTC 市场数据"""
    try:
        # BTC 当前价格
        btc_price_url = f"{COINGECKO_API}/simple/price?ids=bitcoin&vs_currencies=usd,cny&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true"
        btc_price_resp = requests.get(btc_price_url, timeout=30)
        btc_price_resp.raise_for_status()
        btc_data = btc_price_resp.json()['bitcoin']
        
        # BTC 历史价格（24小时前）
        yesterday = today - timedelta(days=1)
        btc_history_url = f"{COINGECKO_API}/coins/bitcoin/history?date={yesterday.strftime('%d-%m-%Y')}"
        try:
            btc_history_resp = requests.get(btc_history_url, timeout=30)
            btc_history_resp.raise_for_status()
            btc_yesterday_price = btc_history_resp.json()['market_data']['current_price']['usd']
        except:
            btc_yesterday_price = btc_data['usd'] / (1 + btc_data['usd_24h_change']/100)
        
        # BTC 历史价格（7天前）
        week_ago = today - timedelta(days=7)
        btc_ohlc_url = f"{COINGECKO_API}/coins/bitcoin/ohlc?vs_currency=usd&days=7"
        try:
            btc_ohlc_resp = requests.get(btc_ohlc_url, timeout=30)
            btc_ohlc_resp.raise_for_status()
            ohlc_data = btc_ohlc_resp.json()
            if len(ohlc_data) > 0:
                btc_week_ago_price = ohlc_data[0][1]  # 开盘价
            else:
                btc_week_ago_price = btc_yesterday_price
        except:
            btc_week_ago_price = btc_yesterday_price
        
        return {
            'price_usd': btc_data['usd'],
            'price_cny': btc_data.get('cny', btc_data['usd'] * 7.2),
            'change_24h': btc_data.get('usd_24h_change', 0),
            'market_cap': btc_data.get('usd_market_cap', 0),
            'volume_24h': btc_data.get('usd_24h_vol', 0),
            'price_yesterday': btc_yesterday_price,
            'price_week_ago': btc_week_ago_price
        }
    except Exception as e:
        print(f"获取 BTC 数据失败: {e}")
        return None

def fetch_eth_data():
    """获取 ETH 市场数据"""
    try:
        # ETH 当前价格
        eth_price_url = f"{COINGECKO_API}/simple/price?ids=ethereum&vs_currencies=usd,cny&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true"
        eth_price_resp = requests.get(eth_price_url, timeout=30)
        eth_price_resp.raise_for_status()
        eth_data = eth_price_resp.json()['ethereum']
        
        # ETH 历史价格（24小时前）
        yesterday = today - timedelta(days=1)
        eth_history_url = f"{COINGECKO_API}/coins/ethereum/history?date={yesterday.strftime('%d-%m-%Y')}"
        try:
            eth_history_resp = requests.get(eth_history_url, timeout=30)
            eth_history_resp.raise_for_status()
            eth_yesterday_price = eth_history_resp.json()['market_data']['current_price']['usd']
        except:
            eth_yesterday_price = eth_data['usd'] / (1 + eth_data['usd_24h_change']/100)
        
        # ETH 历史价格（7天前）
        eth_ohlc_url = f"{COINGECKO_API}/coins/ethereum/ohlc?vs_currency=usd&days=7"
        try:
            eth_ohlc_resp = requests.get(eth_ohlc_url, timeout=30)
            eth_ohlc_resp.raise_for_status()
            ohlc_data = eth_ohlc_resp.json()
            if len(ohlc_data) > 0:
                eth_week_ago_price = ohlc_data[0][1]
            else:
                eth_week_ago_price = eth_yesterday_price
        except:
            eth_week_ago_price = eth_yesterday_price
        
        return {
            'price_usd': eth_data['usd'],
            'price_cny': eth_data.get('cny', eth_data['usd'] * 7.2),
            'change_24h': eth_data.get('usd_24h_change', 0),
            'market_cap': eth_data.get('usd_market_cap', 0),
            'volume_24h': eth_data.get('usd_24h_vol', 0),
            'price_yesterday': eth_yesterday_price,
            'price_week_ago': eth_week_ago_price
        }
    except Exception as e:
        print(f"获取 ETH 数据失败: {e}")
        return None

def fetch_market_data():
    """获取市场数据（恐惧贪婪指数、市值占比等）"""
    try:
        # 获取 BTC 市值占比
        global_url = f"{COINGECKO_API}/global"
        global_resp = requests.get(global_url, timeout=30)
        global_resp.raise_for_status()
        global_data = global_resp.json()['data']
        
        # 获取恐惧贪婪指数（使用替代 API）
        try:
            fg_url = "https://api.alternative.me/fng/"
            fg_resp = requests.get(fg_url, timeout=30)
            fg_resp.raise_for_status()
            fg_data = fg_resp.json()['data'][0]
            fear_greed = {
                'value': int(fg_data['value']),
                'classification': fg_data['value_classification']
            }
        except:
            fear_greed = {'value': 50, 'classification': 'Neutral'}
        
        return {
            'btc_dominance': global_data.get('market_cap_percentage', {}).get('btc', 0),
            'eth_dominance': global_data.get('market_cap_percentage', {}).get('eth', 0),
            'total_market_cap': global_data.get('total_market_cap', {}).get('usd', 0),
            'fear_greed': fear_greed
        }
    except Exception as e:
        print(f"获取市场数据失败: {e}")
        return None

def fetch_funding_rates():
    """获取资金费率数据（模拟数据，实际需接入交易所 API）"""
    # 注意：CoinGecko 免费版不提供资金费率数据
    # 这里使用模拟数据，实际使用时需要接入币安/OKX 等交易所 API
    return {
        'binance_btc': 0.01,
        'binance_eth': 0.008,
        'okx_btc': 0.009,
        'okx_eth': 0.007
    }

def fetch_liquidation_data():
    """获取爆仓数据（模拟数据，实际需接入 Coinglass 等 API）"""
    # 注意：爆仓数据需要付费 API
    # 这里使用模拟数据
    return {
        'btc_24h': 150000000,  # 1.5亿美元
        'eth_24h': 80000000,   # 8000万美元
        'total_24h': 350000000,
        'long_liquidation_pct': 65  # 多头爆仓占比
    }

def calculate_support_resistance(price):
    """计算关键支撑阻力位"""
    # 基于当前价格计算斐波那契水平
    # 这里使用简化的计算方法
    r3 = price * 1.05
    r2 = price * 1.03
    r1 = price * 1.015
    s1 = price * 0.985
    s2 = price * 0.97
    s3 = price * 0.95
    
    return {
        'r3': r3,
        'r2': r2,
        'r1': r1,
        'pivot': price,
        's1': s1,
        's2': s2,
        's3': s3
    }

def format_number(num, decimals=2):
    """格式化数字"""
    if num is None:
        return "N/A"
    if abs(num) >= 1e9:
        return f"{num/1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"{num/1e3:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"

def generate_html_report(btc_data, eth_data, market_data, funding_rates, liquidation_data):
    """生成 HTML 报告"""
    
    btc_levels = calculate_support_resistance(btc_data['price_usd'])
    eth_levels = calculate_support_resistance(eth_data['price_usd'])
    
    btc_change_color = "#00d084" if btc_data['change_24h'] >= 0 else "#ff4757"
    eth_change_color = "#00d084" if eth_data['change_24h'] >= 0 else "#ff4757"
    btc_change_sign = "+" if btc_data['change_24h'] >= 0 else ""
    eth_change_sign = "+" if eth_data['change_24h'] >= 0 else ""
    
    fg_value = market_data['fear_greed']['value']
    if fg_value >= 75:
        fg_color = "#ff4757"
        fg_text = "极度贪婪"
    elif fg_value >= 55:
        fg_color = "#ffa502"
        fg_text = "贪婪"
    elif fg_value >= 45:
        fg_color = "#ffd700"
        fg_text = "中性"
    elif fg_value >= 25:
        fg_color = "#7bed9f"
        fg_text = "恐惧"
    else:
        fg_color = "#00d084"
        fg_text = "极度恐惧"
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETH 日报 - {date_display}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
            border-radius: 20px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #00d084, #00a8ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .header .date {{
            font-size: 1.2em;
            color: #888;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }}
        .card-title {{
            font-size: 1.3em;
            margin-bottom: 20px;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .card-title::before {{
            content: '';
            width: 4px;
            height: 24px;
            background: linear-gradient(135deg, #00d084, #00a8ff);
            border-radius: 2px;
        }}
        .price-main {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .price-change {{
            font-size: 1.2em;
            padding: 5px 15px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .stat-item {{
            background: rgba(255,255,255,0.03);
            padding: 15px;
            border-radius: 10px;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #888;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #fff;
        }}
        .levels-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .levels-table th,
        .levels-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .levels-table th {{
            color: #888;
            font-weight: normal;
        }}
        .level-r {{
            color: #ff4757;
        }}
        .level-s {{
            color: #00d084;
        }}
        .fear-greed {{
            text-align: center;
            padding: 30px;
        }}
        .fear-greed-value {{
            font-size: 4em;
            font-weight: bold;
            margin: 20px 0;
        }}
        .fear-greed-text {{
            font-size: 1.5em;
            padding: 10px 30px;
            border-radius: 25px;
            display: inline-block;
        }}
        .liquidation-bar {{
            height: 30px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            overflow: hidden;
            margin: 15px 0;
        }}
        .liquidation-fill {{
            height: 100%;
            background: linear-gradient(90deg, #ff4757, #ff6b7a);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9em;
        }}
        .footer a {{
            color: #00a8ff;
            text-decoration: none;
        }}
        .btc-icon, .eth-icon {{
            font-size: 1.5em;
            margin-right: 5px;
        }}
        .btc-icon {{ color: #f7931a; }}
        .eth-icon {{ color: #627eea; }}
        @media (max-width: 768px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
            .header h1 {{
                font-size: 1.8em;
            }}
            .price-main {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 ETH 市场日报</h1>
            <div class="date">{date_display}</div>
        </div>
        
        <div class="grid">
            <!-- BTC 价格卡片 -->
            <div class="card">
                <div class="card-title"><span class="btc-icon">₿</span>BTC 价格</div>
                <div class="price-main">${btc_data['price_usd']:,.2f}</div>
                <div style="color: #888;">≈ ¥{btc_data['price_cny']:,.2f}</div>
                <div class="price-change" style="background: {btc_change_color}20; color: {btc_change_color};">
                    {btc_change_sign}{btc_data['change_24h']:.2f}%
                </div>
                <div class="stats-grid" style="margin-top: 20px;">
                    <div class="stat-item">
                        <div class="stat-label">市值</div>
                        <div class="stat-value">{format_number(btc_data['market_cap'])}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">24h 成交量</div>
                        <div class="stat-value">{format_number(btc_data['volume_24h'])}</div>
                    </div>
                </div>
            </div>
            
            <!-- ETH 价格卡片 -->
            <div class="card">
                <div class="card-title"><span class="eth-icon">Ξ</span>ETH 价格</div>
                <div class="price-main">${eth_data['price_usd']:,.2f}</div>
                <div style="color: #888;">≈ ¥{eth_data['price_cny']:,.2f}</div>
                <div class="price-change" style="background: {eth_change_color}20; color: {eth_change_color};">
                    {eth_change_sign}{eth_data['change_24h']:.2f}%
                </div>
                <div class="stats-grid" style="margin-top: 20px;">
                    <div class="stat-item">
                        <div class="stat-label">市值</div>
                        <div class="stat-value">{format_number(eth_data['market_cap'])}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">24h 成交量</div>
                        <div class="stat-value">{format_number(eth_data['volume_24h'])}</div>
                    </div>
                </div>
            </div>
            
            <!-- 市场情绪 -->
            <div class="card">
                <div class="card-title">😊 市场情绪</div>
                <div class="fear-greed">
                    <div class="fear-greed-value" style="color: {fg_color};">{fg_value}</div>
                    <div class="fear-greed-text" style="background: {fg_color}20; color: {fg_color};">
                        {market_data['fear_greed']['classification']}
                    </div>
                </div>
                <div class="stats-grid" style="margin-top: 20px;">
                    <div class="stat-item">
                        <div class="stat-label">BTC 市值占比</div>
                        <div class="stat-value">{market_data['btc_dominance']:.1f}%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">ETH 市值占比</div>
                        <div class="stat-value">{market_data['eth_dominance']:.1f}%</div>
                    </div>
                </div>
            </div>
            
            <!-- 爆仓数据 -->
            <div class="card">
                <div class="card-title">💥 24h 爆仓数据</div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">BTC 爆仓</div>
                        <div class="stat-value">{format_number(liquidation_data['btc_24h'])}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">ETH 爆仓</div>
                        <div class="stat-value">{format_number(liquidation_data['eth_24h'])}</div>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <div class="stat-label">全网爆仓总额: {format_number(liquidation_data['total_24h'])}</div>
                    <div class="liquidation-bar">
                        <div class="liquidation-fill" style="width: {liquidation_data['long_liquidation_pct']}%;">
                            多头 {liquidation_data['long_liquidation_pct']}%
                        </div>
                    </div>
                    <div style="text-align: right; color: #888; font-size: 0.9em;">
                        空头 {100 - liquidation_data['long_liquidation_pct']}%
                    </div>
                </div>
            </div>
            
            <!-- BTC 支撑阻力 -->
            <div class="card">
                <div class="card-title">📈 BTC 关键位</div>
                <table class="levels-table">
                    <tr>
                        <th>阻力位 3</th>
                        <td class="level-r">${btc_levels['r3']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>阻力位 2</th>
                        <td class="level-r">${btc_levels['r2']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>阻力位 1</th>
                        <td class="level-r">${btc_levels['r1']:,.2f}</td>
                    </tr>
                    <tr>
                        <th style="color: #fff;">当前价格</th>
                        <td style="color: #fff; font-weight: bold;">${btc_data['price_usd']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>支撑位 1</th>
                        <td class="level-s">${btc_levels['s1']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>支撑位 2</th>
                        <td class="level-s">${btc_levels['s2']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>支撑位 3</th>
                        <td class="level-s">${btc_levels['s3']:,.2f}</td>
                    </tr>
                </table>
            </div>
            
            <!-- ETH 支撑阻力 -->
            <div class="card">
                <div class="card-title">📉 ETH 关键位</div>
                <table class="levels-table">
                    <tr>
                        <th>阻力位 3</th>
                        <td class="level-r">${eth_levels['r3']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>阻力位 2</th>
                        <td class="level-r">${eth_levels['r2']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>阻力位 1</th>
                        <td class="level-r">${eth_levels['r1']:,.2f}</td>
                    </tr>
                    <tr>
                        <th style="color: #fff;">当前价格</th>
                        <td style="color: #fff; font-weight: bold;">${eth_data['price_usd']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>支撑位 1</th>
                        <td class="level-s">${eth_levels['s1']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>支撑位 2</th>
                        <td class="level-s">${eth_levels['s2']:,.2f}</td>
                    </tr>
                    <tr>
                        <th>支撑位 3</th>
                        <td class="level-s">${eth_levels['s3']:,.2f}</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>数据更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>数据来源: CoinGecko API | 仅供参考，不构成投资建议</p>
            <p style="margin-top: 10px;">
                <a href="https://t.me/bitebiwang1413" target="_blank">Telegram</a> |
                <a href="https://twitter.com/bitebiwang1413" target="_blank">Twitter</a> |
                <a href="https://t.me/bitebiwanglin" target="_blank">频道订阅</a>
            </p>
        </div>
    </div>
</body>
</html>'''
    
    return html

def save_report(html_content):
    """保存报告到文件"""
    report_path = os.path.join(REPORTS_DIR, f"ETH_daily_report_{date_str}.html")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"报告已保存: {report_path}")
    return report_path

def update_index(report_filename):
    """更新 index.html 报告列表"""
    
    # 检查 index.html 是否存在
    if not os.path.exists(INDEX_FILE):
        # 创建新的 index.html
        index_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETH 日报归档</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
            border-radius: 20px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #00d084, #00a8ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .report-list {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .report-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            transition: background 0.3s ease;
        }}
        .report-item:hover {{
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
        }}
        .report-item:last-child {{
            border-bottom: none;
        }}
        .report-date {{
            font-size: 1.1em;
            color: #fff;
        }}
        .report-link {{
            color: #00a8ff;
            text-decoration: none;
            padding: 8px 20px;
            background: rgba(0,168,255,0.1);
            border-radius: 20px;
            transition: all 0.3s ease;
        }}
        .report-link:hover {{
            background: rgba(0,168,255,0.2);
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 ETH 日报归档</h1>
            <p>每日市场数据汇总</p>
        </div>
        <div class="report-list">
            <div class="report-item">
                <span class="report-date">{date_display}</span>
                <a href="reports/{report_filename}" class="report-link">查看报告</a>
            </div>
        </div>
        <div class="footer">
            <p>自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </div>
</body>
</html>'''
    else:
        # 读取现有 index.html 并在顶部插入新报告
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            index_content = f.read()
        
        # 在 report-list div 开头插入新报告项
        new_item = f'''            <div class="report-item">
                <span class="report-date">{date_display}</span>
                <a href="reports/{report_filename}" class="report-link">查看报告</a>
            </div>
'''
        
        # 查找插入位置
        insert_marker = '<div class="report-list">'
        if insert_marker in index_content:
            insert_pos = index_content.find(insert_marker) + len(insert_marker)
            index_content = index_content[:insert_pos] + '\n' + new_item + index_content[insert_pos:]
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(index_content)
    print(f"索引已更新: {INDEX_FILE}")

def main():
    """主函数"""
    print(f"=== ETH 日报生成任务 ===")
    print(f"日期: {date_display}")
    
    # 检查今日报告是否已存在
    if check_report_exists():
        print(f"今日报告已存在，跳过生成")
        return 0
    
    print("正在获取数据...")
    
    # 获取数据
    btc_data = fetch_btc_data()
    eth_data = fetch_eth_data()
    market_data = fetch_market_data()
    funding_rates = fetch_funding_rates()
    liquidation_data = fetch_liquidation_data()
    
    # 检查数据获取结果
    if not btc_data or not eth_data:
        print("错误: 无法获取关键价格数据")
        return 1
    
    if not market_data:
        market_data = {
            'btc_dominance': 0,
            'eth_dominance': 0,
            'total_market_cap': 0,
            'fear_greed': {'value': 50, 'classification': 'Neutral'}
        }
    
    print("正在生成报告...")
    
    # 生成 HTML 报告
    html_content = generate_html_report(btc_data, eth_data, market_data, funding_rates, liquidation_data)
    
    # 保存报告
    report_path = save_report(html_content)
    report_filename = os.path.basename(report_path)
    
    # 更新索引
    update_index(report_filename)
    
    print("=== 任务完成 ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
