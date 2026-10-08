import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import store  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Keep session state and submissions out of the real data/ directory.
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(store, "DB_FILE", tmp_path / "submissions.json")
    monkeypatch.setattr(store, "PLAN_STATE_DIR", tmp_path / "plan_state")
    monkeypatch.setattr(store, "PLANS_FILE", tmp_path / "plans.json")
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
