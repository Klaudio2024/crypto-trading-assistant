from app.models import RiskSettings,TradePlan
from app.risk import position_size,validate
def plan(): return TradePlan('x','BTC/USDT',100,98,104,70,'TRENDING','test')
def account(): return {'emergency_locked':0,'daily_locked':0,'drawdown_locked':0,'cash':1000}
def test_size_includes_costs(): assert 0<position_size(RiskSettings(),1000,1000,100,98)<2.5
def test_duplicate_symbol_blocks(): assert not validate(RiskSettings(),plan(),account(),[{'symbol':'BTC/USDT'}])[0]
def test_invalid_stop_blocks(): assert not validate(RiskSettings(),TradePlan('x','BTC/USDT',100,101,104,70,'T','x'),account(),[])[0]
def test_lock_blocks(): a=account();a['emergency_locked']=1;assert not validate(RiskSettings(),plan(),a,[])[0]
def test_stale_blocks(): assert not validate(RiskSettings(),plan(),account(),[],False)[0]
