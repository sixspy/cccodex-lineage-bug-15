from app.services import edges, nodes


def test_seed_has_nodes(db_path):
    items = nodes.list_nodes(db_path=db_path)
    assert len(items) >= 5
    assert any(x["layer"] == "DWS" for x in items)


def test_seed_has_published_edges(db_path):
    items = edges.list_edges(db_path=db_path)
    published = [e for e in items if e["status"] == "已发布"]
    assert len(published) >= 4
