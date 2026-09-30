from app.models import RiskSettings, TradePlan
from app.risk import size_position, check_trade
def plan(c=70): return TradePlan('BTC/USDT',100,98,104,c,'TRENDING','test')
def test_position_size(): assert size_position(RiskSettings(),100,98,1000)==2.5
def test_daily_limit_blocks():
 ok,msg=check_trade(RiskSettings(),plan(),-20,0,0,0); assert not ok and 'daily loss' in msg
def test_low_confidence_blocks(): assert not check_trade(RiskSettings(),plan(59),0,0,0,0)[0]
def test_emergency_blocks(): assert not check_trade(RiskSettings(),plan(),0,0,0,0,emergency=True)[0]
def test_invalid_stop_blocks():
 p=TradePlan('BTC/USDT',100,101,104,70,'TRENDING','x'); assert not check_trade(RiskSettings(),p,0,0,0,0)[0]
