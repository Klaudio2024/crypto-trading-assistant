import sqlite3

import pytest

import db


def paper_position(position_id="position-1", signal_id="signal-1"):
    return {
        "id": position_id,
        "signal_id": signal_id,
        "symbol": "BTC/USDT",
        "qty": 0.01,
        "entry": 100.0,
        "stop": 98.0,
        "target": 104.0,
        "entry_fee": 0.1,
        "entry_slippage": 0.05,
    }


def test_open_paper_position_transaction_updates_all_persistent_state(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(db, "DB", str(tmp_path / "paper.db"))
    db.init()

    db.open_paper_position_transaction(
        paper_position(),
        cash_after=998.85,
        event_details={"quantity": 0.01, "entry": 100.0},
    )

    assert db.account()["cash"] == 998.85
    assert len(db.open_positions()) == 1

    entries = [
        item
        for item in db.journal()
        if item["event"] == "PAPER_ENTRY"
    ]
    assert len(entries) == 1
    assert entries[0]["signal_id"] == "signal-1"


def test_failed_paper_entry_transaction_rolls_back_cash_position_and_journal(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(db, "DB", str(tmp_path / "paper.db"))
    db.init()

    db.open_paper_position_transaction(
        paper_position(),
        cash_after=998.85,
        event_details={"quantity": 0.01},
    )

    with pytest.raises(ValueError, match="Duplicate signal ID"):
        db.open_paper_position_transaction(
            paper_position(position_id="position-2", signal_id="signal-1"),
            cash_after=900.0,
            event_details={"quantity": 0.02},
        )

    assert db.account()["cash"] == 998.85
    assert len(db.open_positions()) == 1

    entries = [
        item
        for item in db.journal()
        if item["event"] == "PAPER_ENTRY"
    ]
    assert len(entries) == 1
