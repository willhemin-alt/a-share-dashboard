from __future__ import annotations
from datetime import datetime
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.market import nearest_price
from src.ledger import account, save_account, settings, fees, read_trades, rewrite_trades

cfg=settings(); a=account(); today=datetime.now().strftime('%Y-%m-%d')
rows=read_trades(); msgs=[]
for code,pos in list(a['positions'].items()):
    px=nearest_price(code,today,cfg['sell_target_time'],max_minutes=5)
    if not px:
        msgs.append(f'{code}: no verifiable 09:30-09:40 price; position retained')
        continue
    qty=int(pos['quantity']); gross=round(qty*px['price'],2); sf=fees(gross,'sell',cfg)
    buy_gross=round(qty*float(pos['buy_price']),2); total_cost=buy_gross+float(pos['buy_fees'])
    net=gross-sf; pnl=round(net-total_cost,2); ret=round(pnl/total_cost*100,4)
    a['cash']=round(a['cash']+net,2); a['realized_pnl']=round(a['realized_pnl']+pnl,2)
    a['completed_trades']+=1
    if pnl>0: a['winning_trades']+=1
    for r in rows:
        if r['code']==code and r['status']=='OPEN':
            r.update({"sell_date":today,"sell_time":px['timestamp'][11:19],"sell_price":px['price'],"sell_gross":gross,"sell_fees":sf,"pnl":pnl,"return_pct":ret,"status":"CLOSED"}); break
    del a['positions'][code]
    msgs.append(f'{code} sold {qty} @ {px["price"]}; PnL {pnl:+.2f}')
rewrite_trades(rows); save_account(a)
print('\n'.join(msgs) if msgs else 'No open positions.')
