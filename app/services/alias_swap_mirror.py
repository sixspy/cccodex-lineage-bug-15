"""表名别名旧闭包镜像面：列表亮、写库仍脏。"""
from __future__ import annotations

from app.db import get_db
from app.services.alias_swap import dashboard, paint_ok, truth_flag

_SLUG = "alias_swap_mirror"
_OK = "别名已切"
_BAD = "旧名仍进"


def mirror_chip(db_path: str | None = None) -> str:
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM meta WHERE key=?",
            (f"{_SLUG}_chip",),
        ).fetchone()
        return row["value"] if row else _OK


def seed_mirror(db_path: str | None = None) -> None:
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (f"{_SLUG}_chip", _OK),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (f"{_SLUG}_truth", _BAD),
        )


def mirror_board(db_path: str | None = None) -> dict:
    seed_mirror(db_path)
    dash = dashboard(db_path)
    return {
        "mirror_chip": mirror_chip(db_path),
        "truth": truth_flag(db_path),
        "dash": dash,
        "panel_pack_mismatch": True,
        "title": "表名别名旧闭包镜像",
    }


def half_mirror(db_path: str | None = None) -> dict:
    paint_ok(db_path)
    seed_mirror(db_path)
    return {"mirror_chip": mirror_chip(db_path), "truth": truth_flag(db_path)}
