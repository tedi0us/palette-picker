"""Persistence.

- Working state: one JSON file per browser session under data/state/<sid>.json,
  cached in memory. Holds the scheme, view flags and an undo/redo history.
- Submissions: appended to data/submissions.json.
"""

from __future__ import annotations

import base64
import json
import threading
import time
import uuid
from pathlib import Path

import color
import siteplan
from presets import DEFAULT_OPTIONS, TOKEN_KEYS, default_scheme

DATA_DIR = Path(__file__).parent / "data"
STATE_DIR = DATA_DIR / "state"
DB_FILE = DATA_DIR / "submissions.json"
PLAN_STATE_DIR = DATA_DIR / "plan_state"
PLANS_FILE = DATA_DIR / "plans.json"

_lock = threading.Lock()
_cache: dict[str, dict] = {}
_plan_cache: dict[str, dict] = {}

MAX_HISTORY = 80


def _ensure_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_FILE.exists():
        DB_FILE.write_text("[]\n")
    if not PLANS_FILE.exists():
        PLANS_FILE.write_text("[]\n")


_ensure_dirs()


# --------------------------------------------------------------- scheme hygiene

def normalize_scheme(scheme: dict) -> dict:
    scheme = dict(scheme or {})
    scheme.setdefault("meta", {})
    scheme["meta"].setdefault("name", "Untitled scheme")
    for theme in ("light", "dark"):
        colors = dict(scheme.get(theme) or {})
        for key in TOKEN_KEYS:
            if colors.get(key):
                colors[key] = color.normalize_hex(colors[key])
            else:
                colors[key] = colors.get("surface", "#eeeeee") if key == "surfaceAlt" else "#888888"
        scheme[theme] = colors
    opts = dict(DEFAULT_OPTIONS)
    opts.update(scheme.get("options") or {})
    try:
        opts["radius"] = max(0, min(28, int(opts["radius"])))
        opts["font_scale"] = max(0.85, min(1.2, float(opts["font_scale"])))
    except (TypeError, ValueError):
        opts = dict(DEFAULT_OPTIONS)
    scheme["options"] = opts
    return scheme


def _blank_state() -> dict:
    scheme = normalize_scheme(default_scheme())
    return {
        "scheme": scheme,
        "theme": "light",
        "device": "desktop",
        "view": "preview",
        "fmt": "css",
        "ramp_scale": True,
        "history": [json.dumps(scheme)],
        "hist_ptr": 0,
        "expanded": [],
        "sent": False,
    }


# --------------------------------------------------------------- state io

def new_sid() -> str:
    return uuid.uuid4().hex


def _path(sid: str) -> Path:
    return STATE_DIR / f"{sid}.json"


def load_state(sid: str) -> dict:
    with _lock:
        if sid in _cache:
            return _cache[sid]
        p = _path(sid)
        if p.exists():
            try:
                st = json.loads(p.read_text())
                st["scheme"] = normalize_scheme(st.get("scheme", {}))
                st.setdefault("history", [json.dumps(st["scheme"])])
                st.setdefault("hist_ptr", len(st["history"]) - 1)
                for k, v in _blank_state().items():
                    if k not in ("scheme", "history", "hist_ptr"):
                        st.setdefault(k, v)
                _cache[sid] = st
                return st
            except (ValueError, OSError):
                pass
        st = _blank_state()
        _cache[sid] = st
        _persist(sid, st)
        return st


def save_state(sid: str, st: dict) -> None:
    with _lock:
        _cache[sid] = st
        _persist(sid, st)


def _persist(sid: str, st: dict) -> None:
    try:
        _path(sid).write_text(json.dumps(st))
    except OSError:
        pass


# --------------------------------------------------------------- history

def record_history(st: dict) -> None:
    snap = json.dumps(st["scheme"])
    hist = st["history"][: st["hist_ptr"] + 1]
    if hist and hist[-1] == snap:
        return
    hist.append(snap)
    if len(hist) > MAX_HISTORY:
        hist = hist[-MAX_HISTORY:]
    st["history"] = hist
    st["hist_ptr"] = len(hist) - 1


def can_undo(st: dict) -> bool:
    return st["hist_ptr"] > 0


def can_redo(st: dict) -> bool:
    return st["hist_ptr"] < len(st["history"]) - 1


def undo(st: dict) -> None:
    if can_undo(st):
        st["hist_ptr"] -= 1
        st["scheme"] = normalize_scheme(json.loads(st["history"][st["hist_ptr"]]))


def redo(st: dict) -> None:
    if can_redo(st):
        st["hist_ptr"] += 1
        st["scheme"] = normalize_scheme(json.loads(st["history"][st["hist_ptr"]]))


def replace_scheme(st: dict, scheme: dict, record: bool = True) -> None:
    st["scheme"] = normalize_scheme(scheme)
    if record:
        record_history(st)


# --------------------------------------------------------------- share links

def encode_scheme(scheme: dict) -> str:
    raw = json.dumps(scheme, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_scheme(token: str) -> dict | None:
    try:
        pad = "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(token + pad)
        return normalize_scheme(json.loads(raw))
    except (ValueError, TypeError):
        return None


# --------------------------------------------------------------- submissions

def add_submission(client: str, notes: str, user_agent: str, scheme: dict) -> dict:
    row = {
        "id": uuid.uuid4().hex,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "client": (client or "").strip()[:120],
        "notes": (notes or "").strip()[:4000],
        "user_agent": (user_agent or "")[:400],
        "scheme": normalize_scheme(scheme),
    }
    with _lock:
        rows = list_submissions()
        rows.append(row)
        DB_FILE.write_text(json.dumps(rows, indent=2) + "\n")
    return row


def list_submissions() -> list[dict]:
    try:
        data = json.loads(DB_FILE.read_text())
    except (ValueError, OSError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        if not isinstance(row, dict):
            continue
        row.setdefault("created_at", row.get("createdAt", ""))
        row.setdefault("user_agent", row.get("userAgent", ""))
        row.setdefault("client", "")
        row.setdefault("notes", "")
        row["scheme"] = normalize_scheme(row.get("scheme", {}))
        out.append(row)
    return out


def delete_submission(sub_id: str) -> int:
    with _lock:
        rows = list_submissions()
        kept = [r for r in rows if r.get("id") != sub_id]
        DB_FILE.write_text(json.dumps(kept, indent=2) + "\n")
        return len(rows) - len(kept)


# --------------------------------------------------------------- site plans
#
# Same shape as the palette side: one working-state file per session under
# data/plan_state/<sid>.json, submitted outlines appended to data/plans.json.

def _blank_plan_state() -> dict:
    return {"plan": siteplan.normalize_plan(siteplan.default_plan()), "sent": False}


def _plan_path(sid: str) -> Path:
    return PLAN_STATE_DIR / f"{sid}.json"


def load_plan_state(sid: str) -> dict:
    with _lock:
        if sid in _plan_cache:
            return _plan_cache[sid]
        p = _plan_path(sid)
        if p.exists():
            try:
                st = json.loads(p.read_text())
                st["plan"] = siteplan.normalize_plan(st.get("plan", {}))
                st.setdefault("sent", False)
                _plan_cache[sid] = st
                return st
            except (ValueError, OSError):
                pass
        st = _blank_plan_state()
        _plan_cache[sid] = st
        _persist_plan(sid, st)
        return st


def save_plan_state(sid: str, st: dict) -> None:
    with _lock:
        _plan_cache[sid] = st
        _persist_plan(sid, st)


def _persist_plan(sid: str, st: dict) -> None:
    try:
        _plan_path(sid).write_text(json.dumps(st))
    except OSError:
        pass


def add_plan(client: str, notes: str, user_agent: str, plan: dict,
             ref_name: str = "", ref_scheme: dict | None = None) -> dict:
    row = {
        "id": uuid.uuid4().hex,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "client": (client or "").strip()[:120],
        "notes": (notes or "").strip()[:4000],
        "user_agent": (user_agent or "")[:400],
        "ref_name": (ref_name or "").strip()[:160],
        "ref_scheme": normalize_scheme(ref_scheme or default_scheme()),
        "plan": siteplan.normalize_plan(plan),
    }
    with _lock:
        rows = list_plans()
        rows.append(row)
        PLANS_FILE.write_text(json.dumps(rows, indent=2) + "\n")
    return row


def list_plans() -> list[dict]:
    try:
        data = json.loads(PLANS_FILE.read_text())
    except (ValueError, OSError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        if not isinstance(row, dict):
            continue
        row.setdefault("created_at", "")
        row.setdefault("user_agent", "")
        row.setdefault("client", "")
        row.setdefault("notes", "")
        row.setdefault("ref_name", "")
        row["ref_scheme"] = normalize_scheme(row.get("ref_scheme") or default_scheme())
        row["plan"] = siteplan.normalize_plan(row.get("plan", {}))
        out.append(row)
    return out


def delete_plan(plan_id: str) -> int:
    with _lock:
        rows = list_plans()
        kept = [r for r in rows if r.get("id") != plan_id]
        PLANS_FILE.write_text(json.dumps(kept, indent=2) + "\n")
        return len(rows) - len(kept)
