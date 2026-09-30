import sqlite3
DB='trading.db'
def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, ts TEXT DEFAULT CURRENT_TIMESTAMP, symbol TEXT, status TEXT, regime TEXT, confidence INTEGER, entry REAL, stop REAL, target REAL, quantity REAL, reason TEXT)")
    return c
def log(symbol,status,regime,confidence,entry,stop,target,quantity,reason):
    c=connect(); c.execute("INSERT INTO journal(symbol,status,regime,confidence,entry,stop,target,quantity,reason) VALUES(?,?,?,?,?,?,?,?,?)",(symbol,status,regime,confidence,entry,stop,target,quantity,reason)); c.commit(); c.close()
def latest():
    c=connect(); rows=[dict(x) for x in c.execute("SELECT * FROM journal ORDER BY id DESC LIMIT 20")]; c.close(); return rows
