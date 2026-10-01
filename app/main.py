from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .models import RiskSettings, TradePlan
from .risk import size_position, check_trade, RiskError
from . import db

app=FastAPI(title="Crypto Trading Assistant", version="0.1.0")
settings=RiskSettings(); state={"mode":"PAPER_TRADING","locked":False,"daily_pnl":0.0,"weekly_pnl":0.0,"drawdown":0.0,"open_positions":0,"balance":1000.0}
class Signal(BaseModel):
    symbol:str="BTC/USDT"; entry:float=60000; stop:float=59000; target:float=62000
    confidence:int=Field(default=70, ge=0, le=100); regime:str="TRENDING"; reason:str="Demo paper-trading signal"
@app.get('/', response_class=HTMLResponse)
def home(): return HTMLResponse(open('app/static/index.html').read())
@app.get('/api/status')
def status(): return {**state,"safety":{"leverage":0,"margin":False,"futures":False,"live_execution":False},"limits":{"risk_per_trade":"0.5%","daily_loss":"2%","weekly_loss":"5%","max_drawdown":"10%"}}
@app.get('/api/journal')
def journal(): return db.latest()
@app.post('/api/emergency-stop')
def emergency_stop(): state['locked']=True; return {"status":"LOCKED","message":"Emergency stop activated. New entries are blocked."}
@app.post('/api/restart-paper')
def restart(): state['locked']=False; return {"status":"PAPER_TRADING","message":"Paper mode restarted; live execution remains disabled."}
@app.post('/api/paper-signal')
def paper_signal(s:Signal):
    plan=TradePlan(s.symbol,s.entry,s.stop,s.target,s.confidence,s.regime,s.reason)
    ok,reason=check_trade(settings,plan,state['daily_pnl'],state['weekly_pnl'],state['drawdown'],state['open_positions'],emergency=state['locked'])
    if not ok:
        db.log(s.symbol,'REJECTED',s.regime,s.confidence,s.entry,s.stop,s.target,0,reason); return {"accepted":False,"reason":reason}
    try: q=size_position(settings,s.entry,s.stop,state['balance'])
    except RiskError as e: raise HTTPException(422,str(e))
    if q<=0: reason='Trade rejected because available balance is insufficient.'; db.log(s.symbol,'REJECTED',s.regime,s.confidence,s.entry,s.stop,s.target,0,reason); return {"accepted":False,"reason":reason}
    state['open_positions']+=1; db.log(s.symbol,'PAPER_OPEN',s.regime,s.confidence,s.entry,s.stop,s.target,q,reason)
    return {"accepted":True,"mode":"PAPER_TRADING","quantity":q,"risk_amount":settings.capital*settings.risk_per_trade,"reason":reason}
