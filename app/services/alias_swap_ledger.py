"""表名别名旧闭包旁路账：只追加记事，展示与主路径同源。"""
from __future__ import annotations

from app.db import get_db
from app.services.alias_swap import dashboard, record_event

_SLUG = "alias_swap"
_TITLE = "表名别名旧闭包"


def append_ledger(ref_id: int, note: str, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (f"{_SLUG}_ledger_{ref_id}", note or _TITLE),
        )
    dash = record_event(f"ref={ref_id} {note}", db_path)
    return {
        "ref_id": ref_id,
        "note": note,
        "panel": dash["chip"],
        "truth": dash["truth"],
    }


def ledger_rows(db_path: str | None = None) -> list[dict]:
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT key, value FROM meta WHERE key LIKE ? ORDER BY key",
            (f"{_SLUG}_ledger_%",),
        ).fetchall()
    chip = dashboard(db_path)["chip"]
    return [{"key": r["key"], "value": r["value"], "chip": chip} for r in rows]


def board(db_path: str | None = None) -> dict:
    dash = dashboard(db_path)
    dash["ledger"] = ledger_rows(db_path)
    return dash
