import os
import tempfile

import pytest

from app.seed import seed_if_needed


@pytest.fixture()
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    os.environ["DATABASE_PATH"] = path
    seed_if_needed(path)
    return path
