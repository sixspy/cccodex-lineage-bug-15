from app.services import coverage, impact, notify, nodes


def test_impact_and_notify_chain(db_path):
    root = next(n for n in nodes.list_nodes(db_path=db_path) if n["node_code"] == "N-DWD-ORD")
    job = impact.start_impact(int(root["id"]), db_path=db_path)
    assert job["status"] == "成功"
    assert job["affected_count"] >= 2
    detail = impact.job_detail(int(job["id"]), db_path=db_path)
    assert len(detail["hits"]) >= 2
    sent = notify.dispatch_for_job(int(job["id"]), db_path=db_path)
    assert sent["sent"] >= 1


def test_coverage_report(db_path):
    rep = coverage.run_coverage(db_path=db_path)
    assert rep["node_count"] >= 5
    assert "孤儿" in rep["summary"] or "节点" in rep["summary"]
