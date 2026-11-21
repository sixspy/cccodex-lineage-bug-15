"""下游通知：按影响作业命中节点发站内通知。"""
from __future__ import annotations

from app.db import get_db
from app.services.errors import ServiceError


def list_notifies(job_id: int | None = None, db_path: str | None = None) -> list[dict]:
    with get_db(db_path) as conn:
        if job_id:
            rows = conn.execute(
                "SELECT n.*, nd.node_code, nd.table_name, j.job_code FROM notify_logs n "
                "JOIN lineage_nodes nd ON nd.id=n.node_id "
                "JOIN impact_jobs j ON j.id=n.job_id WHERE n.job_id=? ORDER BY n.id DESC",
                (job_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT n.*, nd.node_code, nd.table_name, j.job_code FROM notify_logs n "
                "JOIN lineage_nodes nd ON nd.id=n.node_id "
                "JOIN impact_jobs j ON j.id=n.job_id ORDER BY n.id DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def dispatch_for_job(job_id: int, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        job = conn.execute(
            "SELECT * FROM impact_jobs WHERE id=?", (job_id,)
        ).fetchone()
        if not job:
            raise ServiceError("作业不存在", 404)
        if job["status"] != "成功":
            raise ServiceError("仅成功影响作业可发通知", 409)
        existing = conn.execute(
            "SELECT COUNT(*) AS c FROM notify_logs WHERE job_id=?", (job_id,)
        ).fetchone()["c"]
        if int(existing) > 0:
            raise ServiceError("该作业已发过通知", 409)
        hits = conn.execute(
            "SELECT h.node_id, n.node_code, n.table_name, n.owner_team "
            "FROM impact_hits h JOIN lineage_nodes n ON n.id=h.node_id "
            "WHERE h.job_id=? AND h.hop>0 ORDER BY h.hop",
            (job_id,),
        ).fetchall()
        if not hits:
            raise ServiceError("无下游命中，无需通知", 409)
        sent = 0
        for h in hits:
            body = (
                f"影响作业 {job['job_code']} 命中下游 {h['node_code']} "
                f"（{h['table_name']}），请值班核对。"
            )
            conn.execute(
                "INSERT INTO notify_logs(job_id, node_id, channel, status, body) "
                "VALUES (?,?, '站内','已发',?)",
                (job_id, h["node_id"], body),
            )
            sent += 1
        return {"job_id": job_id, "sent": sent}
