"""影响分析：从根节点沿已发布边向下展开。"""
from __future__ import annotations

from app.db import get_db
from app.services import alias_swap
from app.services.errors import ServiceError


def list_jobs(db_path: str | None = None) -> list[dict]:
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT j.*, n.node_code, n.table_name FROM impact_jobs j "
            "JOIN lineage_nodes n ON n.id=j.root_node_id ORDER BY j.id DESC"
        ).fetchall()
        sealed = conn.execute(
            "SELECT COALESCE(SUM(old_edge_count),0) AS s FROM alias_vouchers"
        ).fetchone()["s"]
        items = [dict(r) for r in rows]
        for it in items:
            it["old_name_count"] = int(sealed)
        return items


def job_detail(job_id: int, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        job = conn.execute(
            "SELECT j.*, n.node_code, n.table_name FROM impact_jobs j "
            "JOIN lineage_nodes n ON n.id=j.root_node_id WHERE j.id=?",
            (job_id,),
        ).fetchone()
        if not job:
            raise ServiceError("作业不存在", 404)
        hits = conn.execute(
            "SELECT h.*, n.node_code, n.table_name, n.layer FROM impact_hits h "
            "JOIN lineage_nodes n ON n.id=h.node_id WHERE h.job_id=? ORDER BY h.hop, h.id",
            (job_id,),
        ).fetchall()
        return {"job": dict(job), "hits": [dict(x) for x in hits]}


def start_impact(root_node_id: int, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        root = conn.execute(
            "SELECT * FROM lineage_nodes WHERE id=?", (root_node_id,)
        ).fetchone()
        if not root:
            raise ServiceError("根节点不存在", 404)
        if root["status"] == "停用":
            raise ServiceError("停用节点不可开影响分析", 409)
        running = conn.execute(
            "SELECT id FROM impact_jobs WHERE root_node_id=? AND status IN ('待执行','执行中')",
            (root_node_id,),
        ).fetchone()
        if running:
            raise ServiceError("该根节点已有在途影响作业", 409)
        # 闭包闸门：别名指纹与边号不合时拦住，核齐后才放行
        alias_swap.require_aligned_or_raise(conn=conn)
        seq = conn.execute("SELECT COUNT(*) AS c FROM impact_jobs").fetchone()["c"] + 1
        job_code = f"IMP-{seq:04d}"
        cur = conn.execute(
            "INSERT INTO impact_jobs(job_code, root_node_id, status, message, started_at) "
            "VALUES (?,?,'执行中','展开中',datetime('now'))",
            (job_code, root_node_id),
        )
        job_id = cur.lastrowid
        # BFS downstream via published edges
        seen = {root_node_id: 0}
        queue = [root_node_id]
        while queue:
            cur_id = queue.pop(0)
            hop = seen[cur_id]
            conn.execute(
                "INSERT OR IGNORE INTO impact_hits(job_id, node_id, hop) VALUES (?,?,?)",
                (job_id, cur_id, hop),
            )
            kids = conn.execute(
                "SELECT e.downstream_id FROM lineage_edges e "
                "WHERE e.upstream_id=? AND e.status='已发布'",
                (cur_id,),
            ).fetchall()
            # retired/merged secondary edges still included
            for kid in kids:
                kid_id = int(kid["downstream_id"])
                if kid_id not in seen:
                    seen[kid_id] = hop + 1
                    queue.append(kid_id)
        affected = len(seen)
        conn.execute(
            "UPDATE impact_jobs SET status='成功', affected_count=?, message=?, "
            "finished_at=datetime('now') WHERE id=?",
            (affected, f"影响到 {affected} 个节点", job_id),
        )
        return dict(
            conn.execute(
                "SELECT * FROM impact_jobs WHERE id=?", (job_id,)
            ).fetchone()
        )
