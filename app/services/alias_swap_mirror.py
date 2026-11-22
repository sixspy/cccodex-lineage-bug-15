"""表名别名旧闭包镜像面：只读同源视图，不再另写脏状态。"""
from __future__ import annotations

from app.services.alias_swap import dashboard


def mirror_chip(db_path: str | None = None) -> str:
    return dashboard(db_path)["chip"]


def mirror_board(db_path: str | None = None) -> dict:
    dash = dashboard(db_path)
    return {
        "mirror_chip": dash["chip"],
        "truth": dash["truth"],
        "dash": dash,
        "panel_pack_mismatch": False,
        "title": "表名别名旧闭包镜像",
    }


def half_mirror(db_path: str | None = None) -> dict:
    dash = dashboard(db_path)
    return {"mirror_chip": dash["chip"], "truth": dash["truth"]}
