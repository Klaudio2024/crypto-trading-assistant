import sqlite3, json, uuid
from datetime import datetime, timezone
DB='trading.db'
def now(): return datetime.now(timezone.utc).isoformat()
def connect():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init():
 c=connect();
 c.executescript("""
 CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY CHECK(id=1), cash REAL NOT NULL, equity_peak REAL NOT NULL, day_start_equity REAL NOT NULL, day_key TEXT NOT NULL, emergency_locked INTEGER NOT NULL DEFAULT 0, daily_locked INTEGER NOT NULL DEFAULT 0, drawdown_locked INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS positions (id TEXT PRIMARY KEY, signal_id TEXT UNIQUE NOT NULL, symbol TEXT NOT NULL, qty REAL NOT NULL, entry REAL NOT NULL, stop REAL NOT NULL, target REAL NOT NULL, entry_fee REAL NOT NULL, entry_slippage REAL NOT NULL, opened_at TEXT NOT NULL, status TEXT NOT NULL, close_price REAL, exit_fee REAL, exit_reason TEXT, closed_at TEXT);
 CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, event TEXT NOT NULL, symbol TEXT, signal_id TEXT, details TEXT NOT NULL);
 """);
 if not c.execute('SELECT 1 FROM account WHERE id=1').fetchone(): c.execute('INSERT INTO account VALUES(1,1000,1000,1000,?,?,0,0,0,?)',(now()[:10],now()))
 c.commit(); c.close()
def event(event,symbol=None,signal_id=None,**details):
 c=connect(); c.execute('INSERT INTO journal(ts,event,symbol,signal_id,details) VALUES(?,?,?,?,?)',(now(),event,symbol,signal_id,json.dumps(details))); c.commit(); c.close()
def account():
 c=connect(); r=dict(c.execute('SELECT * FROM account WHERE id=1').fetchone()); c.close(); return r
def save_account(**changes):
 a=account(); a.update(changes); a['updated_at']=now(); c=connect(); c.execute('UPDATE account SET cash=?,equity_peak=?,day_start_equity=?,day_key=?,emergency_locked=?,daily_locked=?,drawdown_locked=?,updated_at=? WHERE id=1',(a['cash'],a['equity_peak'],a['day_start_equity'],a['day_key'],a['emergency_locked'],a['daily_locked'],a['drawdown_locked'],a['updated_at'])); c.commit(); c.close()
def open_positions():
 c=connect(); rows=[dict(x) for x in c.execute("SELECT * FROM positions WHERE status='OPEN' ORDER BY opened_at DESC")]; c.close(); return rows
def signal_exists(signal_id):
 c=connect(); x=c.execute('SELECT 1 FROM positions WHERE signal_id=?',(signal_id,)).fetchone(); c.close(); return bool(x)
def add_position(p):
 c=connect(); c.execute('INSERT INTO positions(id,signal_id,symbol,qty,entry,stop,target,entry_fee,entry_slippage,opened_at,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(p['id'],p['signal_id'],p['symbol'],p['qty'],p['entry'],p['stop'],p['target'],p['entry_fee'],p['entry_slippage'],now(),'OPEN')); c.commit(); c.close()
def close_position(pid,price,fee,reason):
 c=connect(); c.execute("UPDATE positions SET status='CLOSED',close_price=?,exit_fee=?,exit_reason=?,closed_at=? WHERE id=? AND status='OPEN'",(price,fee,reason,now(),pid)); c.commit(); c.close()
def close_by_id(pid):
 c=connect(); r=c.execute("SELECT * FROM positions WHERE id=? AND status='OPEN'",(pid,)).fetchone(); c.close(); return dict(r) if r else None
def journal():
 c=connect(); rows=[]
 for x in c.execute('SELECT * FROM journal ORDER BY id DESC LIMIT 50'):
  d=dict(x); d['details']=json.loads(d['details']); rows.append(d)
 c.close(); return rows
