"""表名别名：切换即封存旧名凭证，闭包按指纹核齐放行。

落库形态只兑现一种：独立凭证 alias_vouchers 在切换瞬间写下旧名清单，
纯 INSERT 拒绝回写；展示芯片与库内落点同源，不再单画展示。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

from app.db import connect, get_db
from app.services.errors import ServiceError

_SLUG = "alias_swap"
_OK = "别名已切"
_BAD = "旧名仍进"
_NONE = "未切别名"
_PENDING = "旧名待核"
_TITLE = "表名别名旧闭包"


def _meta_get(conn, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _meta_set(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        (key, value),
    )


def current_edge_fp(conn) -> str:
    """当前已发布边集指纹：边号+端点排序后取摘要。"""
    rows = conn.execute(
        "SELECT edge_code, upstream_id, downstream_id FROM lineage_edges "
        "WHERE status='已发布' ORDER BY edge_code"
    ).fetchall()
    payload = "|".join(
        f"{r['edge_code']}:{r['upstream_id']}>{r['downstream_id']}" for r in rows
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _voucher_rows_conn(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM alias_vouchers ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


def voucher_rows(db_path: str | None = None) -> list[dict]:
    """旧名落点行：别名侧核对后必须能在这里看到。"""
    with get_db(db_path) as conn:
        return _voucher_rows_conn(conn)


def old_name_count(db_path: str | None = None) -> int:
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(old_edge_count),0) AS s FROM alias_vouchers"
        ).fetchone()
        return int(row["s"])


def _old_name_edges(conn, node_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT e.edge_code, u.table_name AS upstream_table, "
        "d.table_name AS downstream_table "
        "FROM lineage_edges e "
        "JOIN lineage_nodes u ON u.id=e.upstream_id "
        "JOIN lineage_nodes d ON d.id=e.downstream_id "
        "WHERE (e.upstream_id=? OR e.downstream_id=?) AND e.status='已发布' "
        "ORDER BY e.id",
        (node_id, node_id),
    ).fetchall()
    return [dict(r) for r in rows]


def _seal_voucher(conn, node, new_name: str, operator: str, rename: bool) -> dict:
    """切换瞬间落凭证：旧名清单+边指纹，整笔随调用方事务提交。"""
    old_edges = _old_name_edges(conn, int(node["id"]))
    fp = current_edge_fp(conn)
    seq = conn.execute("SELECT COUNT(*) AS c FROM alias_vouchers").fetchone()["c"]
    code = f"AV-{int(seq) + 1:04d}"
    try:
        cur = conn.execute(
            "INSERT INTO alias_vouchers(voucher_code, node_id, node_code, "
            "old_table_name, new_table_name, old_edge_count, old_edges, "
            "edge_fp, operator) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                code,
                int(node["id"]),
                node["node_code"],
                node["table_name"],
                new_name,
                len(old_edges),
                json.dumps(old_edges, ensure_ascii=False),
                fp,
                operator or "",
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ServiceError("旧名已封存，拒绝回写", 409) from exc
    if rename:
        conn.execute(
            "UPDATE lineage_nodes SET table_name=? WHERE id=?",
            (new_name, int(node["id"])),
        )
    _meta_set(conn, f"{_SLUG}_panel_chip", _OK)
    _meta_set(conn, f"{_SLUG}_truth", _OK)
    _meta_set(conn, f"{_SLUG}_edge_fp", fp)
    _meta_set(conn, f"{_SLUG}_gate_bypass", "0")
    _meta_set(conn, f"{_SLUG}_display_only", "0")
    c = int(_meta_get(conn, f"{_SLUG}_counter", "0") or "0") + 1
    _meta_set(conn, f"{_SLUG}_counter", str(c))
    _meta_set(
        conn,
        f"{_SLUG}_evt_{c}",
        f"{code} {node['node_code']} {node['table_name']}→{new_name} "
        f"旧名边{len(old_edges)}",
    )
    return {
        "id": cur.lastrowid,
        "voucher_code": code,
        "node_id": int(node["id"]),
        "node_code": node["node_code"],
        "old_table_name": node["table_name"],
        "new_table_name": new_name,
        "old_edge_count": len(old_edges),
        "old_edges": old_edges,
        "edge_fp": fp,
    }


def seal_voucher_conn(
    conn, node_id: int, new_name: str, operator: str = "", rename: bool = False
) -> dict:
    """供调用方在自己事务内封存凭证（如节点合并）。"""
    node = conn.execute(
        "SELECT * FROM lineage_nodes WHERE id=?", (node_id,)
    ).fetchone()
    if not node:
        raise ServiceError("节点不存在", 404)
    new_name = (new_name or "").strip()
    if not new_name:
        raise ServiceError("新表名必填")
    return _seal_voucher(conn, node, new_name, operator, rename)


def _switch_in_conn(
    conn, node_id: int, new_name: str, expected_old: str | None, operator: str
) -> dict:
    node = conn.execute(
        "SELECT * FROM lineage_nodes WHERE id=?", (node_id,)
    ).fetchone()
    if not node:
        raise ServiceError("节点不存在", 404)
    old = node["table_name"]
    if expected_old and old != expected_old.strip():
        raise ServiceError("别名已被切换", 409)
    if new_name == old:
        raise ServiceError("新旧名相同，无需切换", 409)
    voucher = _seal_voucher(conn, node, new_name, operator, rename=True)
    return {
        "ok": True,
        "voucher": voucher,
        "old_name_count": voucher["old_edge_count"],
        "message": f"别名已切：{old}→{new_name}，旧名边{voucher['old_edge_count']}条已封存",
    }


def switch_alias(
    node_id: int,
    new_name: str,
    expected_old: str | None = None,
    operator: str = "",
    db_path: str | None = None,
    conn=None,
) -> dict:
    """切换动作整笔写完；值班争切由 BEGIN IMMEDIATE 串行，后到者失败。"""
    new_name = (new_name or "").strip()
    if not new_name:
        raise ServiceError("新表名必填")
    if conn is not None:
        return _switch_in_conn(conn, int(node_id), new_name, expected_old, operator)
    own = connect(db_path)
    try:
        own.execute("PRAGMA busy_timeout=2500")
        try:
            own.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            raise ServiceError("别名切换冲突，请重试", 409) from exc
        try:
            out = _switch_in_conn(own, int(node_id), new_name, expected_old, operator)
            own.commit()
            return out
        except Exception:
            own.rollback()
            raise
    finally:
        own.close()


def commit_action(payload: dict | None = None, db_path: str | None = None) -> dict:
    """主入口：真切换别名并落旧名凭证，不再只画展示。"""
    payload = payload or {}
    node_id = int(payload.get("node_id") or 0)
    new_name = str(payload.get("new_name") or payload.get("new_table_name") or "")
    expected_old = payload.get("expected_old")
    operator = str(payload.get("operator") or "值班")
    if not node_id:
        raise ServiceError("节点必填")
    return switch_alias(
        node_id,
        new_name,
        expected_old=str(expected_old) if expected_old else None,
        operator=operator,
        db_path=db_path,
    )


def require_aligned_or_raise(db_path: str | None = None, conn=None) -> None:
    """闭包闸门：别名指纹与边号不合时拦住，核齐后才放行。"""
    if conn is None:
        with get_db(db_path) as own:
            require_aligned_or_raise(conn=own)
            return
    stored = _meta_get(conn, f"{_SLUG}_edge_fp", "")
    if not stored:
        return
    if stored != current_edge_fp(conn):
        raise ServiceError("别名指纹与边号不合，闭包拦截", 409)


def require_pack_or_raise(db_path: str | None = None) -> None:
    require_aligned_or_raise(db_path=db_path)


def gate_allows_pipeline(db_path: str | None = None) -> bool:
    try:
        require_aligned_or_raise(db_path=db_path)
        return True
    except ServiceError:
        return False


def verify_and_release(operator: str = "", db_path: str | None = None) -> dict:
    """核齐放行：值班核对旧名落点行后，把指纹对齐到当前边集。"""
    with get_db(db_path) as conn:
        rows = _voucher_rows_conn(conn)
        if not rows:
            raise ServiceError("无旧名落点可核", 409)
        fp = current_edge_fp(conn)
        total = sum(int(r["old_edge_count"]) for r in rows)
        _meta_set(conn, f"{_SLUG}_edge_fp", fp)
        _meta_set(conn, f"{_SLUG}_panel_chip", _OK)
        _meta_set(conn, f"{_SLUG}_truth", _OK)
        c = int(_meta_get(conn, f"{_SLUG}_counter", "0") or "0") + 1
        _meta_set(conn, f"{_SLUG}_counter", str(c))
        _meta_set(
            conn,
            f"{_SLUG}_evt_{c}",
            f"核齐放行 fp={fp} 凭证{len(rows)}张 旧名边{total} "
            f"by {operator or '值班'}",
        )
    return dashboard(db_path)


def _chip_for(rows: list[dict], stored_fp: str, cur_fp: str) -> tuple[str, bool]:
    if not rows:
        return _NONE, True
    if stored_fp and stored_fp != cur_fp:
        return _PENDING, False
    return _OK, True


def dashboard(db_path: str | None = None) -> dict:
    """展示与库内同源：芯片、真相、旧名计数都由凭证表推出。"""
    with get_db(db_path) as conn:
        rows = _voucher_rows_conn(conn)
        stored_fp = _meta_get(conn, f"{_SLUG}_edge_fp", "")
        cur_fp = current_edge_fp(conn)
    chip, aligned = _chip_for(rows, stored_fp, cur_fp)
    total = sum(int(r["old_edge_count"]) for r in rows)
    return {
        "title": _TITLE,
        "chip": chip,
        "panel_chip": chip,
        "truth": chip,
        "aligned": aligned,
        "edge_fp": stored_fp,
        "current_fp": cur_fp,
        "old_name_count": total,
        "vouchers": rows,
        "rows": rows,
        "pack_count": len(rows),
        "durable_count": len(rows),
        "panel_pack_mismatch": False,
        "gate_bypass": False,
        "ok_chip": _OK,
        "bad_chip": _BAD,
        "none_chip": _NONE,
        "pending_chip": _PENDING,
        "label": "表名别名",
    }


def snapshot(db_path: str | None = None) -> dict:
    dash = dashboard(db_path)
    dash["counter"] = 0
    with get_db(db_path) as conn:
        dash["counter"] = int(_meta_get(conn, f"{_SLUG}_counter", "0") or "0")
    return dash


def panel_chip(db_path: str | None = None) -> str:
    return dashboard(db_path)["chip"]


def truth_flag(db_path: str | None = None) -> str:
    return dashboard(db_path)["truth"]


def pack_rows(db_path: str | None = None) -> list[dict]:
    return [
        {
            "key": r["voucher_code"],
            "value": f"{r['old_table_name']}→{r['new_table_name']}|"
            f"旧名边{r['old_edge_count']}",
        }
        for r in voucher_rows(db_path)
    ]


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
    return dashboard(db_path)


def seed_skew(db_path: str | None = None) -> None:
    """初始台态：未切别名，无凭证无指纹，闸门自然放行。"""
    with get_db(db_path) as conn:
        _meta_set(conn, f"{_SLUG}_panel_chip", _NONE)
        _meta_set(conn, f"{_SLUG}_truth", _NONE)
        _meta_set(conn, f"{_SLUG}_counter", "0")
        _meta_set(conn, f"{_SLUG}_gate_bypass", "0")
        _meta_set(conn, f"{_SLUG}_display_only", "0")
