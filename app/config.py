import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Config:
    LAB_NAME = "表血缘影响台"
    SECRET = os.environ.get("SECRET_KEY", "cc-lineage-dev-secret")
    ADMIN_USER = "admin"
    ADMIN_PASSWORD = "123456"
    DEFAULT_DB = str(ROOT / "instance" / "lineage_lab.db")
    COOKIE_NAME = "lineage_session"

    @classmethod
    def database(cls) -> str:
        return os.environ.get("DATABASE_PATH", cls.DEFAULT_DB)
