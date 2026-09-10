from pathlib import Path
import json, csv, html
ROOT=Path(__file__).resolve().parents[1]
a=json.loads((ROOT/'data/account.json').read_text(encoding='utf-8'))
with (ROOT/'data/trades.csv').open(encoding='utf-8') as f: trades=list(csv.DictReader(f))
positions=a['positions']; pos_value=sum(float(p['quantity'])*float(p['buy_price']) for p in positions.values())
total=a['cash']+pos_value
cum=(total/100000-1)*100
win=(a['winning_trades']/a['completed_trades']*100) if a['completed_trades'] else 0
rows=''.join(f"<tr><td>{html.escape(r['code'])}</td><td>{html.escape(r['name'])}</td><td>{r['buy_date']} {r['buy_time']}</td><td>{r['buy_price']}</td><td>{r['quantity']}</td><td>{r['sell_price']}</td><td>{r['pnl']}</td><td>{r['status']}</td></tr>" for r in reversed(trades[-50:]))
posrows=''.join(f"<tr><td>{c}</td><td>{html.escape(p['name'])}</td><td>{p['quantity']}</td><td>{p['buy_price']}</td><td>{html.escape(p.get('reason',''))}</td></tr>" for c,p in positions.items()) or '<tr><td colspan="5">空仓</td></tr>'
page=f'''<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A股模拟账户</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:1100px;margin:30px auto;padding:0 16px;background:#f6f7f9;color:#15171a}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}.card{{background:white;border-radius:14px;padding:18px;box-shadow:0 1px 4px #0001}}.v{{font-size:24px;font-weight:700;margin-top:8px}}table{{width:100%;border-collapse:collapse;background:white;margin-top:12px}}th,td{{padding:10px;border-bottom:1px solid #eee;text-align:left;font-size:14px}}h1,h2{{margin-top:28px}}small{{color:#666}}</style></head><body><h1>杨永兴模拟仓</h1><small>连续账本｜初始资金 ¥100,000｜仅模拟，不构成投资建议</small><div class="grid"><div class="card">总资产<div class="v">¥{total:,.2f}</div></div><div class="card">现金<div class="v">¥{a['cash']:,.2f}</div></div><div class="card">持仓成本市值<div class="v">¥{pos_value:,.2f}</div></div><div class="card">累计盈亏<div class="v">¥{a['realized_pnl']:,.2f}</div></div><div class="card">累计收益率<div class="v">{cum:.2f}%</div></div><div class="card">胜率<div class="v">{win:.1f}%</div></div></div><h2>当前持仓</h2><table><tr><th>代码</th><th>名称</th><th>数量</th><th>买入价</th><th>理由</th></tr>{posrows}</table><h2>交易历史</h2><table><tr><th>代码</th><th>名称</th><th>买入</th><th>买价</th><th>数量</th><th>卖价</th><th>盈亏</th><th>状态</th></tr>{rows or '<tr><td colspan="8">暂无正式交易</td></tr>'}</table></body></html>'''
(ROOT/'docs/index.html').write_text(page,encoding='utf-8')
print('docs/index.html updated')
