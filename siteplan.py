"""Site planner — page / nav / content-outline model.

A "plan" is: {meta, pages: [...], nav_links: [...], ref}

    page      = {id, title, in_nav, blocks: [{id, type, note}]}
    nav_link  = {id, label, note}       top-nav buttons that aren't full pages
    ref       = id of the palette submission whose colors paint the preview
                ("" -> the default palette)

This mirrors presets.py: a small fixed vocabulary plus normalize / default
helpers. No colors here — the planner borrows a scheme from the palette tool.
"""

from __future__ import annotations

import uuid

BLOCK_TYPES = [
    {"id": "hero", "label": "Hero", "hint": "Headline, subhead, primary call-to-action"},
    {"id": "richtext", "label": "Rich text", "hint": "Prose — headings, paragraphs, lists"},
    {"id": "image_text", "label": "Image + text", "hint": "A picture beside a block of copy"},
    {"id": "features", "label": "Feature grid", "hint": "3–6 short items: icon, title, blurb"},
    {"id": "gallery", "label": "Gallery", "hint": "Grid or carousel of images"},
    {"id": "testimonials", "label": "Testimonials", "hint": "Customer or client quotes"},
    {"id": "logos", "label": "Logo strip", "hint": '"As seen in" / client logos'},
    {"id": "pricing", "label": "Pricing", "hint": "Plan comparison — table or cards"},
    {"id": "faq", "label": "FAQ", "hint": "Expandable question / answer list"},
    {"id": "cta", "label": "Call to action", "hint": "Banner nudging one action"},
    {"id": "contact", "label": "Contact form", "hint": "Name / email / message fields"},
    {"id": "embed", "label": "Embed / map", "hint": "Map, video, calendar or other iframe"},
    {"id": "custom", "label": "Custom", "hint": "Anything else — describe it in the note"},
]
BLOCK_TYPE_IDS = [b["id"] for b in BLOCK_TYPES]
BLOCK_META = {b["id"]: b for b in BLOCK_TYPES}

MAX_PAGES = 24
MAX_BLOCKS = 40
MAX_NAV_LINKS = 12
MAX_NOTE = 240
MAX_TITLE = 80
MAX_LABEL = 40


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def new_block(type_id: str, note: str = "") -> dict:
    return {
        "id": new_id(),
        "type": type_id if type_id in BLOCK_TYPE_IDS else "custom",
        "note": (note or "").strip()[:MAX_NOTE],
    }


def new_page(title: str = "New page", in_nav: bool = True) -> dict:
    return {
        "id": new_id(),
        "title": (title or "").strip()[:MAX_TITLE] or "New page",
        "in_nav": bool(in_nav),
        "blocks": [],
    }


def default_plan() -> dict:
    home = new_page("Home")
    home["blocks"] = [new_block("hero"), new_block("features"),
                      new_block("testimonials"), new_block("cta")]
    about = new_page("About")
    about["blocks"] = [new_block("richtext"), new_block("image_text")]
    contact = new_page("Contact")
    contact["blocks"] = [new_block("contact"),
                         new_block("embed", "Map to the office")]
    return {
        "meta": {"name": "Site outline"},
        "pages": [home, about, contact],
        "nav_links": [],
        "ref": "",
    }


def normalize_plan(plan: dict) -> dict:
    plan = dict(plan or {})

    meta = dict(plan.get("meta") or {})
    meta["name"] = (str(meta.get("name") or "").strip() or "Site outline")[:MAX_TITLE]
    plan["meta"] = meta

    pages = []
    for p in (plan.get("pages") or [])[:MAX_PAGES]:
        if not isinstance(p, dict):
            continue
        blocks = []
        for b in (p.get("blocks") or [])[:MAX_BLOCKS]:
            if not isinstance(b, dict):
                continue
            blocks.append({
                "id": str(b.get("id") or new_id())[:16],
                "type": b.get("type") if b.get("type") in BLOCK_TYPE_IDS else "custom",
                "note": str(b.get("note") or "").strip()[:MAX_NOTE],
            })
        pages.append({
            "id": str(p.get("id") or new_id())[:16],
            "title": (str(p.get("title") or "").strip() or "Untitled")[:MAX_TITLE],
            "in_nav": bool(p.get("in_nav", True)),
            "blocks": blocks,
        })
    plan["pages"] = pages or default_plan()["pages"]

    links = []
    for l in (plan.get("nav_links") or [])[:MAX_NAV_LINKS]:
        if not isinstance(l, dict):
            continue
        label = str(l.get("label") or "").strip()[:MAX_LABEL]
        if not label:
            continue
        links.append({
            "id": str(l.get("id") or new_id())[:16],
            "label": label,
            "note": str(l.get("note") or "").strip()[:MAX_NOTE],
        })
    plan["nav_links"] = links

    plan["ref"] = str(plan.get("ref") or "")[:64]
    return plan


# --------------------------------------------------------------- mutation helpers

def find_page(plan: dict, page_id: str) -> dict | None:
    return next((p for p in plan["pages"] if p["id"] == page_id), None)


def find_block(page: dict, block_id: str) -> dict | None:
    return next((b for b in page["blocks"] if b["id"] == block_id), None)


def move_item(items: list, item_id: str, direction: str) -> None:
    idx = next((i for i, x in enumerate(items) if x["id"] == item_id), None)
    if idx is None:
        return
    j = idx - 1 if direction == "up" else idx + 1
    if 0 <= j < len(items):
        items[idx], items[j] = items[j], items[idx]
