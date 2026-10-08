"""Palette Picker — Flask + HTMX.

A LAN tool for a client to choose a website color scheme. The server renders
HTML; HTMX swaps fragments. The only browser JS is static/js/app.js (clipboard,
keyboard shortcuts, optional eyedropper) plus vendored htmx.

Run:  .venv/bin/python app.py           (http://0.0.0.0:4173)
"""

from __future__ import annotations

import os
import random
import socket

from flask import (Flask, Response, make_response, render_template, request)

import color
import exporters
import presets
import siteplan
import store

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

SID_COOKIE = "pp_sid"

# ------------------------------------------------------------- template glue

app.jinja_env.globals.update(
    color=color,
    presets=presets,
    exporters=exporters,
    store=store,
    RAMP_STEPS=color.RAMP_STEPS,
    TOKEN_GROUPS=presets.TOKEN_GROUPS,
    TOKEN_META=presets.TOKEN_META,
    RAMPED_TOKENS=presets.RAMPED_TOKENS,
    MATRIX_FG=presets.MATRIX_FG,
    MATRIX_BG=presets.MATRIX_BG,
    PRESETS=presets.PRESETS,
    HARMONY_TYPES=presets.HARMONY_TYPES,
    FORMATS=exporters.FORMATS,
    siteplan=siteplan,
    BLOCK_TYPES=siteplan.BLOCK_TYPES,
    BLOCK_META=siteplan.BLOCK_META,
)


@app.template_filter("kebab")
def _kebab(s: str) -> str:
    import re
    return re.sub(r"([a-z])([A-Z])", r"\1-\2", s).lower()


# ------------------------------------------------------------- session plumbing

def _get_state():
    """Return (sid, state, is_new)."""
    sid = request.cookies.get(SID_COOKIE)
    is_new = not sid
    if is_new:
        sid = store.new_sid()
    return sid, store.load_state(sid), is_new


def _finish(sid: str, st: dict, is_new: bool, html: str) -> Response:
    store.save_state(sid, st)
    resp = make_response(html)
    if is_new:
        resp.set_cookie(SID_COOKIE, sid, max_age=60 * 60 * 24 * 30,
                        samesite="Lax", httponly=True)
    return resp


def workspace(st: dict) -> str:
    return render_template("_workspace.html", st=st, scheme=st["scheme"])


def live(st: dict) -> str:
    return render_template("_live.html", st=st, scheme=st["scheme"])


# --------------------------------------------------------------------- pages

@app.get("/")
def index():
    sid, st, is_new = _get_state()
    token = request.args.get("s")
    if token:
        decoded = store.decode_scheme(token)
        if decoded:
            store.replace_scheme(st, decoded)
            st["sent"] = False
    return _finish(sid, st, is_new, render_template("index.html", st=st, scheme=st["scheme"]))


@app.get("/admin")
def admin():
    return render_template("admin.html",
                           rows=list(reversed(store.list_submissions())),
                           plans=list(reversed(store.list_plans())))


@app.post("/admin/delete/<sub_id>")
def admin_delete(sub_id):
    store.delete_submission(sub_id)
    return ""


@app.post("/admin/plan/delete/<plan_id>")
def admin_plan_delete(plan_id):
    store.delete_plan(plan_id)
    return ""


@app.get("/healthz")
def healthz():
    return {"ok": True}


# --------------------------------------------------------------- token edits

def _apply_color(st, theme, key, value):
    if theme not in ("light", "dark") or key not in presets.TOKEN_KEYS:
        return False
    rgb = color.parse_any(value or "")
    if not rgb:
        return False
    st["scheme"][theme][key] = color.rgb_to_hex(rgb)
    return True


@app.post("/color")
def set_color():
    sid, st, is_new = _get_state()
    ok = _apply_color(st, request.form.get("theme"), request.form.get("key"),
                      request.form.get("value"))
    if ok:
        store.record_history(st)
    return _finish(sid, st, is_new, workspace(st))


@app.post("/nudge")
def nudge():
    sid, st, is_new = _get_state()
    theme, key, direction = (request.form.get("theme"), request.form.get("key"),
                             request.form.get("dir"))
    if theme in ("light", "dark") and key in presets.TOKEN_KEYS:
        amount = 0.05 if direction == "up" else -0.05
        st["scheme"][theme][key] = color.adjust_lightness(st["scheme"][theme][key], amount)
        store.record_history(st)
    return _finish(sid, st, is_new, workspace(st))


@app.post("/hsl")
def set_hsl():
    sid, st, is_new = _get_state()
    theme, key = request.form.get("theme"), request.form.get("key")
    if theme in ("light", "dark") and key in presets.TOKEN_KEYS:
        try:
            h = float(request.form.get("h", 0))
            s = float(request.form.get("s", 0))
            lightness = float(request.form.get("l", 0))
            st["scheme"][theme][key] = color.rgb_to_hex(color.hsl_to_rgb((h, s, lightness)))
            store.record_history(st)
        except ValueError:
            pass
    return _finish(sid, st, is_new, workspace(st))


@app.post("/oklch")
def set_oklch():
    sid, st, is_new = _get_state()
    theme, key = request.form.get("theme"), request.form.get("key")
    if theme in ("light", "dark") and key in presets.TOKEN_KEYS:
        try:
            L = float(request.form.get("l", 0))
            c = float(request.form.get("c", 0))
            h = float(request.form.get("h", 0))
            st["scheme"][theme][key] = color.rgb_to_hex(color.oklch_to_rgb((L, c, h)))
            store.record_history(st)
        except ValueError:
            pass
    return _finish(sid, st, is_new, workspace(st))


@app.post("/expand")
def expand():
    sid, st, is_new = _get_state()
    key = request.form.get("key")
    exp = set(st.get("expanded", []))
    exp.symmetric_difference_update({key})
    st["expanded"] = sorted(exp)
    return _finish(sid, st, is_new, workspace(st))


# --------------------------------------------------------------- scheme-level

@app.post("/name")
def set_name():
    sid, st, is_new = _get_state()
    st["scheme"]["meta"]["name"] = (request.form.get("value") or "").strip()[:120]
    store.record_history(st)
    return _finish(sid, st, is_new, workspace(st))


@app.post("/options")
def set_options():
    sid, st, is_new = _get_state()
    opts = st["scheme"]["options"]
    try:
        if "radius" in request.form:
            opts["radius"] = max(0, min(28, int(float(request.form["radius"]))))
        if "font_scale" in request.form:
            opts["font_scale"] = max(0.85, min(1.2, float(request.form["font_scale"])))
    except ValueError:
        pass
    store.record_history(st)
    return _finish(sid, st, is_new, workspace(st))


@app.post("/preset")
def load_preset():
    sid, st, is_new = _get_state()
    p = presets.get_preset(request.form.get("id", ""))
    if p:
        keep = st["scheme"]["meta"].get("name")
        if keep and keep != "Untitled scheme":
            p["meta"]["name"] = keep
        store.replace_scheme(st, p)
    return _finish(sid, st, is_new, workspace(st))


@app.post("/harmony")
def harmony():
    sid, st, is_new = _get_state()
    base = color.normalize_hex(request.form.get("base", "#3b6fe0"))
    htype = request.form.get("type", "analogous")
    theme = st["theme"]
    hset = color.harmonies(base).get(htype, [base])
    st["scheme"][theme]["primary"] = color.normalize_hex(hset[0])
    if len(hset) > 1:
        st["scheme"][theme]["secondary"] = color.normalize_hex(hset[1])
    if len(hset) > 2:
        st["scheme"][theme]["accent"] = color.normalize_hex(hset[2])
    store.record_history(st)
    return _finish(sid, st, is_new, workspace(st))


@app.post("/randomize")
def randomize():
    sid, st, is_new = _get_state()
    theme = st["theme"]
    dark = theme == "dark"
    base_h = random.uniform(0, 360)

    def lch(L, c, h):
        return color.rgb_to_hex(color.oklch_to_rgb((L, c, h % 360)))

    s = st["scheme"][theme]
    s["primary"] = lch(0.72 if dark else 0.58, random.uniform(0.13, 0.2), base_h)
    s["secondary"] = lch(0.7 if dark else 0.55, random.uniform(0.08, 0.16), base_h + random.uniform(20, 60))
    s["accent"] = lch(0.78 if dark else 0.72, random.uniform(0.14, 0.2), base_h + random.uniform(150, 210))
    s["background"] = lch(0.17 if dark else 0.99, 0.01 if dark else 0.004, base_h)
    s["surface"] = lch(0.22 if dark else 0.975, 0.015 if dark else 0.005, base_h)
    s["surfaceAlt"] = lch(0.27 if dark else 0.95, 0.02 if dark else 0.006, base_h)
    s["text"] = lch(0.93 if dark else 0.25, 0.01, base_h)
    s["muted"] = lch(0.72 if dark else 0.5, 0.01, base_h)
    s["border"] = lch(0.32 if dark else 0.9, 0.008, base_h)
    store.record_history(st)
    return _finish(sid, st, is_new, workspace(st))


@app.post("/reset")
def reset():
    sid, st, is_new = _get_state()
    store.replace_scheme(st, presets.default_scheme())
    return _finish(sid, st, is_new, workspace(st))


@app.post("/undo")
def undo():
    sid, st, is_new = _get_state()
    store.undo(st)
    return _finish(sid, st, is_new, workspace(st))


@app.post("/redo")
def redo():
    sid, st, is_new = _get_state()
    store.redo(st)
    return _finish(sid, st, is_new, workspace(st))


# --------------------------------------------------------------- view / toggles

@app.post("/view")
def set_view():
    sid, st, is_new = _get_state()
    v = request.form.get("name")
    if v in ("preview", "contrast", "ramps", "export"):
        st["view"] = v
    return _finish(sid, st, is_new, live(st))


@app.post("/toggle")
def toggle():
    sid, st, is_new = _get_state()
    what, value = request.form.get("what"), request.form.get("value")
    if what == "theme" and value in ("light", "dark"):
        st["theme"] = value
    elif what == "device" and value in ("desktop", "tablet", "phone"):
        st["device"] = value
    return _finish(sid, st, is_new, workspace(st))


@app.post("/export-opts")
def export_opts():
    sid, st, is_new = _get_state()
    if "fmt" in request.form and request.form["fmt"] in exporters.FORMATS:
        st["fmt"] = request.form["fmt"]
    st["ramp_scale"] = request.form.get("ramp_scale") in ("1", "true", "on")
    return _finish(sid, st, is_new, live(st))


@app.get("/download")
def download():
    sid, st, is_new = _get_state()
    fmt = request.args.get("fmt", st["fmt"])
    spec = exporters.FORMATS.get(fmt, exporters.FORMATS["css"])
    body = exporters.render(fmt, st["scheme"], st.get("ramp_scale", True))
    slug = (st["scheme"]["meta"].get("name") or "scheme").lower()
    slug = "".join(c if c.isalnum() else "-" for c in slug).strip("-") or "scheme"
    resp = make_response(body)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="{slug}.{spec["ext"]}"'
    return resp


# --------------------------------------------------------------- share / submit

@app.post("/share")
def share():
    sid, st, is_new = _get_state()
    token = store.encode_scheme(st["scheme"])
    url = request.host_url.rstrip("/") + "/?s=" + token
    return _finish(sid, st, is_new, render_template("_share.html", url=url))


@app.post("/submit")
def submit():
    sid, st, is_new = _get_state()
    row = store.add_submission(
        client=request.form.get("client", ""),
        notes=request.form.get("notes", ""),
        user_agent=request.headers.get("User-Agent", ""),
        scheme=st["scheme"],
    )
    st["sent"] = True
    return _finish(sid, st, is_new, render_template("_sent.html", row=row))


# =============================================================== site planner
#
# A second tool on the same session cookie: the client outlines the pages, top
# nav and per-page content blocks of a site that hasn't been built yet, and
# previews it as a wireframe painted with a palette borrowed from the color
# picker. Every control is one POST that returns the #planspace fragment.

def _get_plan():
    """Return (sid, plan_state, is_new)."""
    sid = request.cookies.get(SID_COOKIE)
    is_new = not sid
    if is_new:
        sid = store.new_sid()
    return sid, store.load_plan_state(sid), is_new


def _plan_ref(plan: dict) -> tuple[dict, str]:
    """Resolve the plan's reference palette to (scheme, label)."""
    ref = plan.get("ref") or ""
    if ref:
        for row in store.list_submissions():
            if row["id"] == ref:
                label = row["scheme"]["meta"].get("name") or "scheme"
                if row.get("client"):
                    label += f" — {row['client']}"
                return row["scheme"], label
    return presets.default_scheme(), ""


def plan_space(st: dict) -> str:
    scheme, ref_label = _plan_ref(st["plan"])
    return render_template("_plan.html", st=st, plan=st["plan"],
                           refs=store.list_submissions(),
                           ref_scheme=scheme, ref_label=ref_label)


def _finish_plan(sid: str, st: dict, is_new: bool, html: str) -> Response:
    store.save_plan_state(sid, st)
    resp = make_response(html)
    if is_new:
        resp.set_cookie(SID_COOKIE, sid, max_age=60 * 60 * 24 * 30,
                        samesite="Lax", httponly=True)
    return resp


@app.get("/plan")
def plan_page():
    sid, st, is_new = _get_plan()
    scheme, ref_label = _plan_ref(st["plan"])
    return _finish_plan(sid, st, is_new,
                        render_template("plan.html", st=st, plan=st["plan"],
                                        refs=store.list_submissions(),
                                        ref_scheme=scheme, ref_label=ref_label))


@app.post("/plan/meta")
def plan_meta():
    sid, st, is_new = _get_plan()
    plan = st["plan"]
    if "name" in request.form:
        plan["meta"]["name"] = (request.form["name"] or "").strip()[:siteplan.MAX_TITLE] or "Site outline"
    if "ref" in request.form:
        plan["ref"] = (request.form["ref"] or "")[:64]
    st["plan"] = siteplan.normalize_plan(plan)
    return _finish_plan(sid, st, is_new, plan_space(st))


@app.post("/plan/pages")
def plan_pages():
    sid, st, is_new = _get_plan()
    plan = st["plan"]
    op = request.form.get("op")
    pid = request.form.get("id", "")
    if op == "add" and len(plan["pages"]) < siteplan.MAX_PAGES:
        plan["pages"].append(siteplan.new_page(request.form.get("title", "New page")))
    elif op == "remove" and len(plan["pages"]) > 1:
        plan["pages"] = [p for p in plan["pages"] if p["id"] != pid]
    elif op == "rename":
        p = siteplan.find_page(plan, pid)
        if p:
            p["title"] = (request.form.get("value") or "").strip()[:siteplan.MAX_TITLE] or p["title"]
    elif op == "nav":
        p = siteplan.find_page(plan, pid)
        if p:
            p["in_nav"] = not p["in_nav"]
    elif op == "move":
        siteplan.move_item(plan["pages"], pid, request.form.get("dir", "up"))
    st["plan"] = siteplan.normalize_plan(plan)
    return _finish_plan(sid, st, is_new, plan_space(st))


@app.post("/plan/blocks")
def plan_blocks():
    sid, st, is_new = _get_plan()
    plan = st["plan"]
    op = request.form.get("op")
    page = siteplan.find_page(plan, request.form.get("page", ""))
    bid = request.form.get("id", "")
    if page is not None:
        if op == "add" and len(page["blocks"]) < siteplan.MAX_BLOCKS:
            page["blocks"].append(siteplan.new_block(request.form.get("type", "custom")))
        elif op == "remove":
            page["blocks"] = [b for b in page["blocks"] if b["id"] != bid]
        elif op == "note":
            b = siteplan.find_block(page, bid)
            if b:
                b["note"] = (request.form.get("value") or "").strip()[:siteplan.MAX_NOTE]
        elif op == "move":
            siteplan.move_item(page["blocks"], bid, request.form.get("dir", "up"))
    st["plan"] = siteplan.normalize_plan(plan)
    return _finish_plan(sid, st, is_new, plan_space(st))


@app.post("/plan/nav")
def plan_nav():
    sid, st, is_new = _get_plan()
    plan = st["plan"]
    op = request.form.get("op")
    lid = request.form.get("id", "")
    if op == "add" and len(plan["nav_links"]) < siteplan.MAX_NAV_LINKS:
        plan["nav_links"].append({
            "id": siteplan.new_id(),
            "label": (request.form.get("label") or "").strip()[:siteplan.MAX_LABEL] or "New button",
            "note": "",
        })
    elif op == "remove":
        plan["nav_links"] = [l for l in plan["nav_links"] if l["id"] != lid]
    elif op == "rename":
        l = next((l for l in plan["nav_links"] if l["id"] == lid), None)
        if l:
            l["label"] = (request.form.get("value") or "").strip()[:siteplan.MAX_LABEL] or l["label"]
    st["plan"] = siteplan.normalize_plan(plan)
    return _finish_plan(sid, st, is_new, plan_space(st))


@app.post("/plan/reset")
def plan_reset():
    sid, st, is_new = _get_plan()
    st["plan"] = siteplan.normalize_plan(siteplan.default_plan())
    return _finish_plan(sid, st, is_new, plan_space(st))


@app.post("/plan/submit")
def plan_submit():
    sid, st, is_new = _get_plan()
    scheme, ref_label = _plan_ref(st["plan"])
    row = store.add_plan(
        client=request.form.get("client", ""),
        notes=request.form.get("notes", ""),
        user_agent=request.headers.get("User-Agent", ""),
        plan=st["plan"],
        ref_name=ref_label,
        ref_scheme=scheme,
    )
    st["sent"] = True
    return _finish_plan(sid, st, is_new, render_template("_plan_sent.html", row=row))


# --------------------------------------------------------------------- boot

def _lan_ips():
    ips = []
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4173))
    print("\n  Palette Picker\n")
    print(f"  Local:    http://localhost:{port}")
    for ip in _lan_ips():
        print(f"  Network:  http://{ip}:{port}   (share this with the client)")
    print(f"\n  Admin:    http://localhost:{port}/admin\n")
    app.run(host="0.0.0.0", port=port, debug=bool(os.environ.get("DEBUG")))
