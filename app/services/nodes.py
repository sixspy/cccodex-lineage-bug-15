"""血缘节点：登记、列表、停用。"""
from __future__ import annotations

from app.db import get_db
from app.services.errors import ServiceError


def list_nodes(layer: str | None = None, db_path: str | None = None) -> list[dict]:
    with get_db(db_path) as conn:
        if layer:
            rows = conn.execute(
                "SELECT * FROM lineage_nodes WHERE layer=? ORDER BY id",
                (layer,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM lineage_nodes ORDER BY id"
            ).fetchall()
        items = [dict(r) for r in rows]
        for it in items:
            up = conn.execute(
                "SELECT COUNT(*) AS c FROM lineage_edges "
                "WHERE downstream_id=? AND status='已发布'",
                (it["id"],),
            ).fetchone()["c"]
            down = conn.execute(
                "SELECT COUNT(*) AS c FROM lineage_edges "
                "WHERE upstream_id=? AND status='已发布'",
                (it["id"],),
            ).fetchone()["c"]
            it["upstream_count"] = int(up)
            it["downstream_count"] = int(down)
            voucher = conn.execute(
                "SELECT COUNT(*) AS c, COALESCE(SUM(old_edge_count),0) AS s "
                "FROM alias_vouchers WHERE node_id=?",
                (it["id"],),
            ).fetchone()
            it["alias_marker"] = "别名已切" if int(voucher["c"]) > 0 else ""
            it["old_name_count"] = int(voucher["s"])
        return items


def get_node(node_id: int, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM lineage_nodes WHERE id=?", (node_id,)
        ).fetchone()
        if not row:
            raise ServiceError("节点不存在", 404)
        return dict(row)


def register_node(
    node_code: str,
    table_name: str,
    layer: str,
    owner_team: str = "",
    note: str = "",
    db_path: str | None = None,
) -> dict:
    node_code = (node_code or "").strip()
    table_name = (table_name or "").strip()
    layer = (layer or "").strip().upper()
    if not node_code or not table_name:
        raise ServiceError("节点编号与表名必填")
    if layer not in ("ODS", "DWD", "DWS", "ADS"):
        raise ServiceError("层级只许 ODS/DWD/DWS/ADS")
    with get_db(db_path) as conn:
        try:
            cur = conn.execute(
                "INSERT INTO lineage_nodes(node_code, table_name, layer, owner_team, status, note) "
                "VALUES (?,?,?,?,'登记',?)",
                (node_code, table_name, layer, owner_team or "", note or ""),
            )
        except Exception as exc:
            raise ServiceError(f"登记失败：编号可能重复（{exc})") from exc
        return dict(
            conn.execute(
                "SELECT * FROM lineage_nodes WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        )


def activate_node(node_id: int, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM lineage_nodes WHERE id=?", (node_id,)
        ).fetchone()
        if not row:
            raise ServiceError("节点不存在", 404)
        if row["status"] == "停用":
            raise ServiceError("已停用节点不可直接启用", 409)
        conn.execute(
            "UPDATE lineage_nodes SET status='在用' WHERE id=?", (node_id,)
        )
        return dict(
            conn.execute(
                "SELECT * FROM lineage_nodes WHERE id=?", (node_id,)
            ).fetchone()
        )


def retire_node(node_id: int, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM lineage_nodes WHERE id=?", (node_id,)
        ).fetchone()
        if not row:
            raise ServiceError("节点不存在", 404)
        live = conn.execute(
            "SELECT COUNT(*) AS c FROM lineage_edges "
            "WHERE (upstream_id=? OR downstream_id=?) AND status='已发布'",
            (node_id, node_id),
        ).fetchone()["c"]
        if int(live) > 0:
            raise ServiceError("仍有已发布边，不可停用", 409)
        conn.execute(
            "UPDATE lineage_nodes SET status='停用' WHERE id=?", (node_id,)
        )
        return dict(
            conn.execute(
                "SELECT * FROM lineage_nodes WHERE id=?", (node_id,)
            ).fetchone()
        )



def merge_nodes(primary_id: int, secondary_id: int, db_path: str | None = None) -> dict:
    from app.services import alias_swap

    with get_db(db_path) as conn:
        primary = conn.execute(
            "SELECT * FROM lineage_nodes WHERE id=?", (primary_id,)
        ).fetchone()
        secondary = conn.execute(
            "SELECT * FROM lineage_nodes WHERE id=?", (secondary_id,)
        ).fetchone()
        if not primary or not secondary:
            raise ServiceError("主从节点不存在", 404)
        voucher = alias_swap.seal_voucher_conn(
            conn,
            int(secondary["id"]),
            primary["table_name"],
            operator="合并",
            rename=False,
        )
        conn.execute(
            "UPDATE lineage_nodes SET status='停用', note=? WHERE id=?",
            (f"已并入{primary['node_code']}", secondary_id),
        )
        pack_count = conn.execute(
            "SELECT COUNT(*) AS c FROM alias_vouchers"
        ).fetchone()["c"]
        return {
            "primary": dict(primary),
            "secondary_id": secondary_id,
            "chip": "别名已切",
            "old_name_count": voucher["old_edge_count"],
            "pack_count": int(pack_count),
            "message": f"合并已封存旧名：{voucher['voucher_code']}",
        }
