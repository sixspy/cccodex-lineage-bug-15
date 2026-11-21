import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS lineage_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  node_code TEXT NOT NULL UNIQUE,
  table_name TEXT NOT NULL,
  layer TEXT NOT NULL CHECK (layer IN ('ODS','DWD','DWS','ADS')),
  owner_team TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK (status IN ('登记','在用','停用')),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lineage_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  edge_code TEXT NOT NULL UNIQUE,
  upstream_id INTEGER NOT NULL REFERENCES lineage_nodes(id),
  downstream_id INTEGER NOT NULL REFERENCES lineage_nodes(id),
  transform_kind TEXT NOT NULL DEFAULT '直抽',
  status TEXT NOT NULL CHECK (status IN ('草稿','已发布','已作废')),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(upstream_id, downstream_id)
);

CREATE TABLE IF NOT EXISTS impact_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_code TEXT NOT NULL UNIQUE,
  root_node_id INTEGER NOT NULL REFERENCES lineage_nodes(id),
  status TEXT NOT NULL CHECK (status IN ('待执行','执行中','成功','失败')),
  affected_count INTEGER NOT NULL DEFAULT 0,
  message TEXT NOT NULL DEFAULT '',
  started_at TEXT,
  finished_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS impact_hits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER NOT NULL REFERENCES impact_jobs(id),
  node_id INTEGER NOT NULL REFERENCES lineage_nodes(id),
  hop INTEGER NOT NULL DEFAULT 0,
  UNIQUE(job_id, node_id)
);

CREATE TABLE IF NOT EXISTS notify_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER NOT NULL REFERENCES impact_jobs(id),
  node_id INTEGER NOT NULL REFERENCES lineage_nodes(id),
  channel TEXT NOT NULL DEFAULT '站内',
  status TEXT NOT NULL CHECK (status IN ('待发','已发','失败')),
  body TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS coverage_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  summary TEXT NOT NULL,
  node_count INTEGER NOT NULL,
  edge_count INTEGER NOT NULL,
  orphan_count INTEGER NOT NULL,
  uncovered_edges INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lab_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or Config.database()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db(db_path: str | None = None):
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(db_path: str | None = None) -> None:
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA)
