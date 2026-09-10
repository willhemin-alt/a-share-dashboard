from __future__ import annotations
import csv, json
from datetime import datetime
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from src.market import nearest_price
from src.ledger import account, save_account, settings, affordable_qty, fees, append_trade, new_trade_id

cfg = settings(); a = account()
cand = json.loads((ROOT/'config/candidates.json').read_text(encoding='utf-8'))
trade_date = cand.get('trade_date') or datetime.now().strftime('%Y-%m-%d')
selected = []
if cand.get('market_ok'):
    selected = [x for x in cand.get('candidates', []) if x.get('approved')][:3]

positions_value_before = 0.0
max_total_value = cfg['max_total_weight'] * (a['cash'] + positions_value_before)
used = 0.0
notes=[]
for x in selected:
    code=str(x['code']).zfill(6); name=x.get('name',code)
    if code in a['positions']:
        continue
    px = nearest_price(code, trade_date, cfg['buy_target_time'], max_minutes=5)
    if not px:
        notes.append(f'{code}: no verifiable price near {cfg["buy_target_time"]}')
        continue
    total_assets = a['cash'] + used
    target = min(cfg['max_stock_weight']*total_assets, max_total_value-used)
    qty = affordable_qty(a['cash'], px['price'], target, cfg)
    if qty <= 0: continue
    gross=round(qty*px['price'],2); f=fees(gross,'buy',cfg); cost=gross+f
    a['cash']=round(a['cash']-cost,2)
    a['positions'][code]={"name":name,"quantity":qty,"buy_price":px['price'],"buy_date":trade_date,"buy_time":px['timestamp'][11:19],"buy_fees":f,"reason":x.get('reason','')}
    append_trade({"trade_id":new_trade_id(),"code":code,"name":name,"buy_date":trade_date,"buy_time":px['timestamp'][11:19],"buy_price":px['price'],"quantity":qty,"buy_gross":gross,"buy_fees":f,"status":"OPEN","reason":x.get('reason','')})
    used += gross
    notes.append(f'{code} bought {qty} @ {px["price"]}')
save_account(a)
with (ROOT/'data/decisions.csv').open('a',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow([trade_date,'tail',cand.get('market_ok',False),'|'.join([str(x.get('code')) for x in selected]), cand.get('market_note','')+'; '+'; '.join(notes)])
print('\n'.join(notes) if notes else 'No trade. Account unchanged.')
