import json
import sqlite3
from datetime import datetime, timezone

DB = "trading.db"


def now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _add_column_if_missing(connection, table, column, definition):
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})")
    }
    if column not in columns:
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def init():
    connection = connect()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            cash REAL NOT NULL,
            equity_peak REAL NOT NULL,
            day_start_equity REAL NOT NULL,
            day_key TEXT NOT NULL,
            emergency_locked INTEGER NOT NULL DEFAULT 0,
            daily_locked INTEGER NOT NULL DEFAULT 0,
            drawdown_locked INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            realized_pnl REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            signal_id TEXT UNIQUE NOT NULL,
            symbol TEXT NOT NULL,
            qty REAL NOT NULL,
            entry REAL NOT NULL,
            stop REAL NOT NULL,
            target REAL NOT NULL,
            entry_fee REAL NOT NULL,
            entry_slippage REAL NOT NULL,
            opened_at TEXT NOT NULL,
            status TEXT NOT NULL,
            close_price REAL,
            exit_fee REAL,
            exit_slippage REAL NOT NULL DEFAULT 0,
            realized_pnl REAL,
            exit_reason TEXT,
            closed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            event TEXT NOT NULL,
            symbol TEXT,
            signal_id TEXT,
            details TEXT NOT NULL
        );
        """
    )

    _add_column_if_missing(
        connection,
        "account",
        "realized_pnl",
        "REAL NOT NULL DEFAULT 0",
    )
    _add_column_if_missing(
        connection,
        "positions",
        "exit_slippage",
        "REAL NOT NULL DEFAULT 0",
    )
    _add_column_if_missing(
        connection,
        "positions",
        "realized_pnl",
        "REAL",
    )

    account_exists = connection.execute(
        "SELECT 1 FROM account WHERE id = 1"
    ).fetchone()

    if not account_exists:
        timestamp = now()
        connection.execute(
            """
            INSERT INTO account (
                id, cash, equity_peak, day_start_equity, day_key,
                emergency_locked, daily_locked, drawdown_locked,
                updated_at, realized_pnl
            )
            VALUES (1, 1000, 1000, 1000, ?, 0, 0, 0, ?, 0)
            """,
            (timestamp[:10], timestamp),
        )

    connection.commit()
    connection.close()


def event(event, symbol=None, signal_id=None, **details):
    connection = connect()
    connection.execute(
        """
        INSERT INTO journal (ts, event, symbol, signal_id, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (now(), event, symbol, signal_id, json.dumps(details)),
    )
    connection.commit()
    connection.close()


def account():
    connection = connect()
    row = connection.execute(
        "SELECT * FROM account WHERE id = 1"
    ).fetchone()
    connection.close()
    return dict(row)


def save_account(**changes):
    allowed_fields = {
        "cash",
        "equity_peak",
        "day_start_equity",
        "day_key",
        "emergency_locked",
        "daily_locked",
        "drawdown_locked",
        "realized_pnl",
    }

    invalid_fields = set(changes) - allowed_fields
    if invalid_fields:
        raise ValueError(
            f"Invalid account fields: {', '.join(sorted(invalid_fields))}"
        )

    if not changes:
        return

    changes["updated_at"] = now()
    fields = list(changes)
    assignments = ", ".join(f"{field} = ?" for field in fields)
    values = [changes[field] for field in fields]

    connection = connect()
    connection.execute(
        f"UPDATE account SET {assignments} WHERE id = 1",
        values,
    )
    connection.commit()
    connection.close()


def open_positions():
    connection = connect()
    rows = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM positions WHERE status = 'OPEN' ORDER BY opened_at DESC"
        )
    ]
    connection.close()
    return rows


def signal_exists(signal_id):
    connection = connect()
    row = connection.execute(
        "SELECT 1 FROM positions WHERE signal_id = ?",
        (signal_id,),
    ).fetchone()
    connection.close()
    return bool(row)


def add_position(position):
    connection = connect()
    connection.execute(
        """
        INSERT INTO positions (
            id, signal_id, symbol, qty, entry, stop, target,
            entry_fee, entry_slippage, opened_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
        """,
        (
            position["id"],
            position["signal_id"],
            position["symbol"],
            position["qty"],
            position["entry"],
            position["stop"],
            position["target"],
            position["entry_fee"],
            position["entry_slippage"],
            now(),
        ),
    )
    connection.commit()
    connection.close()


def calculate_realized_pnl(position, close_price, exit_fee, exit_slippage=0.0):
    gross_pnl = (float(close_price) - float(position["entry"])) * float(
        position["qty"]
    )
    total_costs = (
        float(position["entry_fee"])
        + float(position["entry_slippage"])
        + float(exit_fee)
        + float(exit_slippage)
    )
    return gross_pnl - total_costs


def close_position(pid, price, fee, reason, slippage=0.0):
    position = close_by_id(pid)
    if not position:
        return None

    realized_pnl = calculate_realized_pnl(
        position,
        close_price=price,
        exit_fee=fee,
        exit_slippage=slippage,
    )

    connection = connect()
    cursor = connection.execute(
        """
        UPDATE positions
        SET
            status = 'CLOSED',
            close_price = ?,
            exit_fee = ?,
            exit_slippage = ?,
            realized_pnl = ?,
            exit_reason = ?,
            closed_at = ?
        WHERE id = ? AND status = 'OPEN'
        """,
        (price, fee, slippage, realized_pnl, reason, now(), pid),
    )
    connection.commit()
    connection.close()

    return realized_pnl if cursor.rowcount == 1 else None


def close_by_id(pid):
    connection = connect()
    row = connection.execute(
        "SELECT * FROM positions WHERE id = ? AND status = 'OPEN'",
        (pid,),
    ).fetchone()
    connection.close()
    return dict(row) if row else None


def journal():
    connection = connect()
    rows = []

    for row in connection.execute(
        "SELECT * FROM journal ORDER BY id DESC LIMIT 50"
    ):
        item = dict(row)
        item["details"] = json.loads(item["details"])
        rows.append(item)

    connection.close()
    return rows

def open_paper_position_transaction(position, cash_after, event_details):
    """Atomically debit cash, create an OPEN paper position, and journal it."""
    connection = connect()

    try:
        connection.execute("BEGIN IMMEDIATE")

        existing_signal = connection.execute(
            "SELECT 1 FROM positions WHERE signal_id = ?",
            (position["signal_id"],),
        ).fetchone()

        if existing_signal:
            raise ValueError("Duplicate signal ID.")

        connection.execute(
            """
            UPDATE account
            SET cash = ?, updated_at = ?
            WHERE id = 1
            """,
            (cash_after, now()),
        )

        connection.execute(
            """
            INSERT INTO positions (
                id, signal_id, symbol, qty, entry, stop, target,
                entry_fee, entry_slippage, opened_at, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """,
            (
                position["id"],
                position["signal_id"],
                position["symbol"],
                position["qty"],
                position["entry"],
                position["stop"],
                position["target"],
                position["entry_fee"],
                position["entry_slippage"],
                now(),
            ),
        )

        connection.execute(
            """
            INSERT INTO journal (ts, event, symbol, signal_id, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                now(),
                "PAPER_ENTRY",
                position["symbol"],
                position["signal_id"],
                json.dumps(event_details),
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
