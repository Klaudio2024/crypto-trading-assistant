from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from models import RiskSettings, TradePlan
import db
from risk import position_size, validate, RiskError

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    yield


app=FastAPI(
    title='Crypto Trading Assistant',
    version='0.2.0',
    lifespan=lifespan,
)
S=RiskSettings()
class Signal(BaseModel):
 signal_id:str|None=None; symbol:str='BTC/USDT'; entry:float=60000; stop:float=59000; target:float=62000; confidence:int=Field(70,ge=0,le=100); regime:str='TRENDING'; reason:str='Manual paper-test signal'; timeframe:str='15m'; market_fresh:bool=True
class Price(BaseModel): price:float=Field(gt=0)
def equity(a,positions): return a['cash']+sum(p['qty']*p['entry'] for p in positions)
def portfolio():
 a=db.account(); ps=db.open_positions(); invested=sum(p['qty']*p['entry'] for p in ps); e=equity(a,ps); dd=max(0,(a['equity_peak']-e)/a['equity_peak']) if a['equity_peak'] else 0
 return {'mode':'PAPER_TRADING','live_execution':False,'cash':round(a['cash'],2),'invested':round(invested,2),'total_equity':round(e,2),'open_positions':len(ps),'exposure':round(invested/max(e,1),4),'drawdown':round(dd,4),'locked':bool(a['emergency_locked'] or a['daily_locked'] or a['drawdown_locked']),'positions':ps,'limits':{'risk_per_trade':S.risk_per_trade,'daily_loss_limit':S.daily_loss_limit,'max_drawdown':S.max_drawdown,'max_positions':S.max_positions,'max_total_exposure':S.max_total_exposure}}
@app.get('/',response_class=HTMLResponse)
def home(): return HTMLResponse(open('app/static/index.html',encoding='utf-8').read())
@app.get('/api/status')
def status(): return portfolio()
@app.get('/api/journal')
def journal(): return db.journal()
@app.post('/api/emergency-stop')
def stop(): db.save_account(emergency_locked=1); db.event('EMERGENCY_STOP'); return {'status':'LOCKED','message':'Emergency Stop activated. Existing paper positions remain open; no new entries are allowed.'}
@app.post('/api/restart-paper')
def restart(): db.save_account(emergency_locked=0); db.event('PAPER_RESTART'); return {'status':'PAPER_TRADING','message':'Paper mode restarted. Daily and drawdown locks remain protected.'}
def _execute_paper_signal(s: Signal):
 db.init(); a=db.account(); ps=db.open_positions(); sid=s.signal_id or str(uuid4()); plan=TradePlan(sid,s.symbol,s.entry,s.stop,s.target,s.confidence,s.regime,s.reason,s.timeframe)
 if db.signal_exists(sid): db.event('SIGNAL_REJECTED',s.symbol,sid,reason='Duplicate signal ID'); return {'accepted':False,'reason':'Trade rejected because this signal was already processed.'}
 ok,reason=validate(S,plan,a,ps,s.market_fresh)
 if not ok: db.event('SIGNAL_REJECTED',s.symbol,sid,reason=reason); return {'accepted':False,'reason':reason}
 e=equity(a,ps)
 try: q=position_size(S,e,a['cash'],s.entry,s.stop)
 except RiskError as x: raise HTTPException(422,str(x))
 gross=q*s.entry; fee=gross*S.fee_rate; slip=gross*S.slippage_rate
 if gross< S.min_notional or q<=0: reason='Trade rejected because quantity or notional is below the paper-exchange minimum.'; db.event('SIGNAL_REJECTED',s.symbol,sid,reason=reason); return {'accepted':False,'reason':reason}
 if gross+fee+slip>a['cash']: reason='Trade rejected because available virtual balance is insufficient.'; db.event('SIGNAL_REJECTED',s.symbol,sid,reason=reason); return {'accepted':False,'reason':reason}
 db.save_account(cash=a['cash']-gross-fee-slip); db.add_position({'id':str(uuid4()),'signal_id':sid,'symbol':s.symbol,'qty':q,'entry':s.entry,'stop':s.stop,'target':s.target,'entry_fee':fee,'entry_slippage':slip}); db.event('PAPER_ENTRY',s.symbol,sid,quantity=q,entry=s.entry,stop=s.stop,target=s.target,fee=fee,slippage=slip,reason=s.reason)
 return {'accepted':True,'signal_id':sid,'quantity':q,'risk_usdt':round(e*S.risk_per_trade,2),'estimated_fee':round(fee,4),'estimated_slippage':round(slip,4),'reason':'Paper position opened after all risk checks.'}
@app.post('/api/positions/{position_id}/close')
def close(position_id:str,p:Price):
 pos=db.close_by_id(position_id)
 if not pos: raise HTTPException(404,'Open paper position not found.')
 gross=p.price*pos['qty']; fee=gross*S.fee_rate; pnl=gross-fee-(pos['entry']*pos['qty'])-pos['entry_fee']-pos['entry_slippage']; a=db.account(); cash=a['cash']+gross-fee; ps=[x for x in db.open_positions() if x['id']!=position_id]; eq=cash+sum(x['qty']*x['entry'] for x in ps); peak=max(a['equity_peak'],eq); daily_loss=max(0,a['day_start_equity']-eq); db.save_account(cash=cash,equity_peak=peak,daily_locked=int(daily_loss>=a['day_start_equity']*S.daily_loss_limit),drawdown_locked=int((peak-eq)/peak>=S.max_drawdown)); db.close_position(position_id,p.price,fee,'MANUAL_CLOSE'); db.event('PAPER_EXIT',pos['symbol'],pos['signal_id'],exit_price=p.price,net_pnl=round(pnl,4),reason='MANUAL_CLOSE'); return {'closed':True,'net_pnl':round(pnl,4)}
try:
    from .market_data import MarketDataError, quote
    from .strategy import evaluate
except ImportError:
    from market_data import MarketDataError, quote
    from strategy import evaluate


@app.get("/api/market")
def market(symbol: str = "BTC/USDT"):
    try:
        return quote(symbol)
    except MarketDataError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )


@app.get("/api/strategy")
def strategy_status(symbol: str = "BTC/USDT"):
    decision = evaluate(symbol)

    db.event(
        "STRATEGY_DECISION",
        decision["symbol"],
        None,
        action=decision["action"],
        confidence=decision["confidence"],
        reason=decision["reason"],
    )

    return decision


@app.post("/api/strategy/paper")
def strategy_paper(symbol: str = "BTC/USDT"):
    decision = evaluate(symbol)

    db.event(
        "STRATEGY_DECISION",
        decision["symbol"],
        None,
        action=decision["action"],
        confidence=decision["confidence"],
        reason=decision["reason"],
    )

    if decision["action"] != "BUY":
        return {
            "opened": False,
            "decision": decision,
            "reason": (
                "No paper position was opened because "
                "the strategy did not return BUY."
            ),
        }

    signal = Signal(
        signal_id=str(uuid4()),
        symbol=str(decision["symbol"]),
        entry=float(decision["entry"]),
        stop=float(decision["stop"]),
        target=float(decision["target"]),
        confidence=int(decision["confidence"]),
        regime="TRENDING",
        reason=str(decision["reason"]),
        timeframe=str(decision["timeframe"]),
        market_fresh=bool(decision["market_fresh"]),
    )

    result = _execute_paper_signal(signal)

    return {
        "opened": bool(result["accepted"]),
        "decision": decision,
        "paper_result": result,
    }


@app.post("/api/market/monitor")
def monitor_positions():
    results = []

    for position in db.open_positions():
        try:
            current_quote = quote(position["symbol"])
            exit_price = float(current_quote["bid"])

            if exit_price <= float(position["stop"]):
                result = close(
                    position["id"],
                    Price(price=exit_price),
                )

                db.event(
                    "STOP_LOSS_TRIGGERED",
                    position["symbol"],
                    position["signal_id"],
                    exit_price=exit_price,
                    stop=float(position["stop"]),
                )

                results.append(
                    {
                        "position_id": position["id"],
                        "action": "STOP_LOSS",
                        "exit_price": exit_price,
                        "result": result,
                    }
                )

            elif exit_price >= float(position["target"]):
                result = close(
                    position["id"],
                    Price(price=exit_price),
                )

                db.event(
                    "TAKE_PROFIT_TRIGGERED",
                    position["symbol"],
                    position["signal_id"],
                    exit_price=exit_price,
                    target=float(position["target"]),
                )

                results.append(
                    {
                        "position_id": position["id"],
                        "action": "TAKE_PROFIT",
                        "exit_price": exit_price,
                        "result": result,
                    }
                )

            else:
                results.append(
                    {
                        "position_id": position["id"],
                        "action": "HOLD",
                        "market_price": exit_price,
                        "stop": float(position["stop"]),
                        "target": float(position["target"]),
                    }
                )

        except MarketDataError as exc:
            results.append(
                {
                    "position_id": position["id"],
                    "action": "NO_ACTION",
                    "reason": str(exc),
                }
            )

    return {
        "mode": "PAPER_TRADING",
        "live_execution": False,
        "checked_positions": len(results),
        "results": results,
    }
from ai_service import ai_status as get_ai_status
from ai_service import analyze_symbol


@app.get("/api/ai/status")
def ai_status_endpoint():
    return {
        "mode": "PAPER_TRADING",
        "live_execution": False,
        "ai": get_ai_status(),
    }


@app.get("/api/ai/analyze")
def ai_analyze_endpoint(symbol: str = "BTC/USDT"):
    return {
        "mode": "PAPER_TRADING",
        "live_execution": False,
        "analysis": analyze_symbol(symbol),
    }