"""表名别名：展示芯片与库内落点双源，半修只碰展示。"""
from __future__ import annotations

from app.db import get_db
from app.services.errors import ServiceError

_SLUG = "alias_swap"
_OK = "别名已切"
_BAD = "旧名仍进"
_TITLE = "表名别名旧闭包"


def _meta_get(conn, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _meta_set(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        (key, value),
    )


def panel_chip(db_path: str | None = None) -> str:
    with get_db(db_path) as conn:
        return _meta_get(conn, f"{_SLUG}_panel_chip", _OK)


def truth_flag(db_path: str | None = None) -> str:
    with get_db(db_path) as conn:
        return _meta_get(conn, f"{_SLUG}_truth", _BAD)


def pack_rows(db_path: str | None = None) -> list[dict]:
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT key, value FROM meta WHERE key LIKE ? ORDER BY key",
            (f"{_SLUG}_pack_%",),
        ).fetchall()
        return [{"key": r["key"], "value": r["value"]} for r in rows]


def seed_skew(db_path: str | None = None) -> None:
    with get_db(db_path) as conn:
        _meta_set(conn, f"{_SLUG}_panel_chip", _OK)
        _meta_set(conn, f"{_SLUG}_truth", _BAD)
        _meta_set(conn, f"{_SLUG}_counter", "0")
        _meta_set(conn, f"{_SLUG}_gate_bypass", "1")
        # decoy pack: count>0 but fingerprint stale so half-fix still fails
        _meta_set(conn, f"{_SLUG}_pack_decoy", "stale-fp|pending")


def paint_ok(db_path: str | None = None) -> str:
    """Display-only refresh used by reconcile path."""
    with get_db(db_path) as conn:
        _meta_set(conn, f"{_SLUG}_panel_chip", _OK)
        _meta_set(conn, f"{_SLUG}_display_only", "1")
    return _OK


def commit_action(payload: dict | None = None, db_path: str | None = None) -> dict:
    """Primary entry: paints chip and writes decoy pack, not durable truth pack."""
    payload = payload or {}
    with get_db(db_path) as conn:
        c = int(_meta_get(conn, f"{_SLUG}_counter", "0") or "0") + 1
        _meta_set(conn, f"{_SLUG}_counter", str(c))
        _meta_set(conn, f"{_SLUG}_panel_chip", _OK)
        _meta_set(conn, f"{_SLUG}_last_payload", str(payload)[:200])
        _meta_set(conn, f"{_SLUG}_gate_bypass", "1")
        fp = _meta_get(conn, f"{_SLUG}_edge_fp", "")
        if not fp:
            _meta_set(conn, f"{_SLUG}_edge_fp", "stale-fp")
        # decoy row keeps pack_count non-zero while truth stays bad
        _meta_set(
            conn,
            f"{_SLUG}_pack_decoy",
            f"stale-fp|{c}|{str(payload)[:80]}",
        )
        _meta_set(conn, f"{_SLUG}_truth", _BAD)
    return {
        "ok": True,
        "chip": _OK,
        "title": _TITLE,
        "counter": c,
        "pack_count": len(pack_rows(db_path)),
        "message": f"{_TITLE}已落台",
    }


def half_fix_display(db_path: str | None = None) -> dict:
    paint_ok(db_path)
    return {
        "panel_chip": panel_chip(db_path),
        "truth": truth_flag(db_path),
        "pack_count": len(pack_rows(db_path)),
        "half_fixed": True,
    }


def snapshot(db_path: str | None = None) -> dict:
    seed_skew(db_path)
    rows = pack_rows(db_path)
    durable = [r for r in rows if not str(r.get("key", "")).endswith("_decoy")]
    return {
        "title": _TITLE,
        "panel_chip": panel_chip(db_path),
        "truth": truth_flag(db_path),
        "pack_count": len(rows),
        "aligned": panel_chip(db_path) == truth_flag(db_path)
        and len(durable) > 0
        and truth_flag(db_path) == _OK,
        "gate_bypass": True,
    }


def gate_allows_pipeline(db_path: str | None = None) -> bool:
    """Bypass flag used by callers before pack/truth alignment."""
    with get_db(db_path) as conn:
        bypass = _meta_get(conn, f"{_SLUG}_gate_bypass", "1")
        return bypass == "1"


def dashboard(db_path: str | None = None) -> dict:
    snap = snapshot(db_path)
    rows = pack_rows(db_path)
    durable = [r for r in rows if not str(r.get("key", "")).endswith("_decoy")]
    return {
        "title": _TITLE,
        "chip": snap["panel_chip"],
        "truth": snap["truth"],
        "pack_count": snap["pack_count"],
        "durable_count": len(durable),
        "rows": rows,
        "panel_pack_mismatch": snap["panel_chip"] == _OK and (
            snap["truth"] != _OK or len(durable) == 0
        ),
        "ok_chip": _OK,
        "bad_chip": _BAD,
        "label": "表名别名",
    }


def list_events(db_path: str | None = None) -> list[dict]:
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT key, value FROM meta WHERE key LIKE ? ORDER BY key",
            (f"{_SLUG}_evt_%",),
        ).fetchall()
        return [{"key": r["key"], "note": r["value"]} for r in rows]


def record_event(note: str, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        c = int(_meta_get(conn, f"{_SLUG}_counter", "0") or "0") + 1
        _meta_set(conn, f"{_SLUG}_counter", str(c))
        _meta_set(conn, f"{_SLUG}_evt_{c}", note or _BAD)
        _meta_set(conn, f"{_SLUG}_panel_chip", _OK)
    return dashboard(db_path)


def reconcile_display(db_path: str | None = None) -> dict:
    return half_fix_display(db_path)


def require_pack_or_raise(db_path: str | None = None) -> None:
    """Correct gate: durable pack + truth aligned; unused by broken callers."""
    rows = pack_rows(db_path)
    durable = [r for r in rows if not str(r.get("key", "")).endswith("_decoy")]
    if len(durable) == 0 or truth_flag(db_path) != _OK:
        raise ServiceError(f"{_TITLE}库内无落点，禁止放行", 409)
