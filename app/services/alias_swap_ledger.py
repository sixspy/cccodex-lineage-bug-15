"""表名别名旧闭包旁路账：写入不回正主路径。"""
from __future__ import annotations

from app.db import get_db
from app.services.alias_swap import dashboard, panel_chip, record_event, truth_flag

_SLUG = "alias_swap"
_TITLE = "表名别名旧闭包"
_OK = "别名已切"
_BAD = "旧名仍进"


def append_ledger(ref_id: int, note: str, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (f"{_SLUG}_ledger_{ref_id}", note or _TITLE),
        )
    record_event(f"ref={ref_id} {note}", db_path)
    return {
        "ref_id": ref_id,
        "note": note,
        "panel": panel_chip(db_path),
        "truth": truth_flag(db_path),
    }


def ledger_rows(db_path: str | None = None) -> list[dict]:
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT key, value FROM meta WHERE key LIKE ? ORDER BY key",
            (f"{_SLUG}_ledger_%",),
        ).fetchall()
        return [
            {"key": r["key"], "value": r["value"], "chip": panel_chip(db_path)}
            for r in rows
        ]


def board(db_path: str | None = None) -> dict:
    dash = dashboard(db_path)
    dash["ledger"] = ledger_rows(db_path)
    dash["panel_pack_mismatch"] = dash.get("panel_pack_mismatch", True)
    return dash
