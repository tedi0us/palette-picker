"""Token model + preset scheme library.

A "scheme" is: {meta, light: {token: hex}, dark: {token: hex}, options}
"""

from __future__ import annotations

import copy

TOKEN_GROUPS = [
    {
        "id": "brand",
        "label": "Brand",
        "tokens": [
            {"key": "primary", "label": "Primary", "hint": "Main brand color — primary buttons, links, focus"},
            {"key": "secondary", "label": "Secondary", "hint": "Supporting brand color"},
            {"key": "accent", "label": "Accent", "hint": "Highlights, badges, calls to attention"},
        ],
    },
    {
        "id": "surfaces",
        "label": "Surfaces & Text",
        "tokens": [
            {"key": "background", "label": "Background", "hint": "Page background"},
            {"key": "surface", "label": "Surface", "hint": "Cards, panels, raised elements"},
            {"key": "surfaceAlt", "label": "Surface alt", "hint": "Secondary panels, table stripes, wells"},
            {"key": "text", "label": "Text", "hint": "Primary body text"},
            {"key": "muted", "label": "Muted text", "hint": "Secondary text, captions, placeholders"},
            {"key": "border", "label": "Border", "hint": "Dividers, input outlines, card edges"},
        ],
    },
    {
        "id": "status",
        "label": "Status",
        "tokens": [
            {"key": "success", "label": "Success", "hint": "Confirmations, positive state"},
            {"key": "warning", "label": "Warning", "hint": "Cautions, pending state"},
            {"key": "danger", "label": "Danger", "hint": "Errors, destructive actions"},
            {"key": "info", "label": "Info", "hint": "Neutral notices"},
        ],
    },
]

TOKEN_KEYS = [t["key"] for g in TOKEN_GROUPS for t in g["tokens"]]
TOKEN_META = {t["key"]: {**t, "group": g["id"], "group_label": g["label"]}
              for g in TOKEN_GROUPS for t in g["tokens"]}

RAMPED_TOKENS = ["primary", "secondary", "accent", "success", "warning", "danger", "info"]

DEFAULT_OPTIONS = {"radius": 10, "font_scale": 1.0}

# Foreground / background axes for the contrast matrix view.
MATRIX_FG = ["text", "muted", "primary", "secondary", "accent",
             "success", "warning", "danger", "info"]
MATRIX_BG = ["background", "surface", "surfaceAlt", "primary", "secondary", "accent"]

HARMONY_TYPES = [
    ("analogous", "Analogous"),
    ("complementary", "Complementary"),
    ("triadic", "Triadic"),
    ("split_complementary", "Split complementary"),
    ("tetradic", "Tetradic"),
]


def _scheme(name, description, tags, light, dark):
    return {
        "meta": {"name": name, "description": description, "tags": tags},
        "light": light,
        "dark": dark,
        "options": dict(DEFAULT_OPTIONS),
    }


PRESETS = {
    "clean-slate": _scheme(
        "Clean Slate",
        "Neutral, professional, safe default. Blue primary on white.",
        ["neutral", "corporate", "light"],
        {
            "primary": "#3b6fe0", "secondary": "#6b7280", "accent": "#f0a020",
            "background": "#ffffff", "surface": "#f7f8fa", "surfaceAlt": "#eef0f4",
            "text": "#1f2933", "muted": "#66707c", "border": "#dfe3e9",
            "success": "#1f9d55", "warning": "#d98a04", "danger": "#dc2626", "info": "#2563eb",
        },
        {
            "primary": "#5b8def", "secondary": "#9aa1ac", "accent": "#f5b942",
            "background": "#0f1115", "surface": "#171a21", "surfaceAlt": "#1f232c",
            "text": "#e6e8ec", "muted": "#9aa1ac", "border": "#2b303b",
            "success": "#3ecf7e", "warning": "#f0b429", "danger": "#f87171", "info": "#60a5fa",
        },
    ),
    "catppuccin-mocha": _scheme(
        "Catppuccin Mocha",
        "The warm dark pastel palette. Dark-first, with a Latte-ish light mode.",
        ["pastel", "dark", "developer"],
        {
            "primary": "#8839ef", "secondary": "#1e66f5", "accent": "#ea76cb",
            "background": "#eff1f5", "surface": "#e6e9ef", "surfaceAlt": "#dce0e8",
            "text": "#4c4f69", "muted": "#6c6f85", "border": "#bcc0cc",
            "success": "#40a02b", "warning": "#df8e1d", "danger": "#d20f39", "info": "#209fb5",
        },
        {
            "primary": "#cba6f7", "secondary": "#89b4fa", "accent": "#f5c2e7",
            "background": "#1e1e2e", "surface": "#181825", "surfaceAlt": "#313244",
            "text": "#cdd6f4", "muted": "#a6adc8", "border": "#45475a",
            "success": "#a6e3a1", "warning": "#f9e2af", "danger": "#f38ba8", "info": "#94e2d5",
        },
    ),
    "soft-pastel": _scheme(
        "Soft Pastel",
        "Gentle, low-chroma pastels. Friendly consumer / lifestyle brands.",
        ["pastel", "light", "playful"],
        {
            "primary": "#7c9ef0", "secondary": "#b58cd6", "accent": "#f6a5b8",
            "background": "#fdfcff", "surface": "#f4f2fb", "surfaceAlt": "#eceaf6",
            "text": "#3b3a4a", "muted": "#7d7b90", "border": "#e3dff1",
            "success": "#79c9a4", "warning": "#f2c580", "danger": "#ec9296", "info": "#8fc7e8",
        },
        {
            "primary": "#9db8f5", "secondary": "#c6a7e2", "accent": "#f7b9c6",
            "background": "#1b1a24", "surface": "#232230", "surfaceAlt": "#2c2b3b",
            "text": "#e9e7f2", "muted": "#a8a5b8", "border": "#38364a",
            "success": "#8fd6b6", "warning": "#f4d19a", "danger": "#f0a6aa", "info": "#a6d5ef",
        },
    ),
    "forest": _scheme(
        "Forest",
        "Grounded greens and warm stone. Outdoors, sustainability, food.",
        ["earthy", "green", "light"],
        {
            "primary": "#2f7d4f", "secondary": "#7a6a52", "accent": "#d98f3d",
            "background": "#fbfaf6", "surface": "#f2efe6", "surfaceAlt": "#e8e3d6",
            "text": "#23291f", "muted": "#5f6656", "border": "#dcd7c6",
            "success": "#2f7d4f", "warning": "#c9861f", "danger": "#b5442f", "info": "#3b7a86",
        },
        {
            "primary": "#5fb87e", "secondary": "#b6a488", "accent": "#e8ab63",
            "background": "#12160f", "surface": "#1a2015", "surfaceAlt": "#232a1c",
            "text": "#e7e9df", "muted": "#a2a892", "border": "#33392a",
            "success": "#5fb87e", "warning": "#e0ac4c", "danger": "#e0765f", "info": "#6cb6c2",
        },
    ),
    "sunset": _scheme(
        "Sunset",
        "High-energy warm gradient feel. Media, events, creative.",
        ["warm", "vibrant", "light"],
        {
            "primary": "#e0533b", "secondary": "#7b3f8f", "accent": "#f2a516",
            "background": "#fffaf6", "surface": "#fdefe6", "surfaceAlt": "#f8e2d4",
            "text": "#331e18", "muted": "#7a5c50", "border": "#f0d8c8",
            "success": "#2f9d6a", "warning": "#e08a1e", "danger": "#cc2f2f", "info": "#3f7fbf",
        },
        {
            "primary": "#ff7a5c", "secondary": "#b06bc4", "accent": "#f7bd4a",
            "background": "#1a1210", "surface": "#241a16", "surfaceAlt": "#2e211c",
            "text": "#f2e7e2", "muted": "#b39a90", "border": "#3c2c25",
            "success": "#4cc98d", "warning": "#f0a942", "danger": "#f26d6d", "info": "#66a6e0",
        },
    ),
    "midnight": _scheme(
        "Midnight",
        "Dark-first, deep indigo and cyan. SaaS, fintech, dashboards.",
        ["dark", "cool", "tech"],
        {
            "primary": "#4f46e5", "secondary": "#0ea5b7", "accent": "#f43f8e",
            "background": "#ffffff", "surface": "#f5f6fb", "surfaceAlt": "#eceef7",
            "text": "#1a1c2b", "muted": "#5b6072", "border": "#dcdff0",
            "success": "#0f9d63", "warning": "#d98a04", "danger": "#e11d48", "info": "#4f46e5",
        },
        {
            "primary": "#8b83ff", "secondary": "#3fd0e0", "accent": "#ff6fa5",
            "background": "#0b0d17", "surface": "#121524", "surfaceAlt": "#1b2036",
            "text": "#e7e9f5", "muted": "#9297b0", "border": "#262c47",
            "success": "#3ddc97", "warning": "#f0b429", "danger": "#fb7185", "info": "#8b83ff",
        },
    ),
    "mono-ink": _scheme(
        "Mono Ink",
        "Near-monochrome. Editorial, portfolio, luxury. One restrained accent.",
        ["minimal", "monochrome", "light"],
        {
            "primary": "#111111", "secondary": "#555555", "accent": "#b8895a",
            "background": "#ffffff", "surface": "#f4f4f4", "surfaceAlt": "#ebebeb",
            "text": "#141414", "muted": "#6b6b6b", "border": "#dcdcdc",
            "success": "#2f7d4f", "warning": "#b07d1f", "danger": "#b23b3b", "info": "#3a6ea5",
        },
        {
            "primary": "#f2f2f2", "secondary": "#a8a8a8", "accent": "#d0a273",
            "background": "#0d0d0d", "surface": "#161616", "surfaceAlt": "#1f1f1f",
            "text": "#ededed", "muted": "#9a9a9a", "border": "#2c2c2c",
            "success": "#5fb87e", "warning": "#d8a94c", "danger": "#e07a7a", "info": "#7ba7d4",
        },
    ),
    "ocean": _scheme(
        "Ocean",
        "Cool teals and sand. Travel, wellness, hospitality.",
        ["cool", "calm", "light"],
        {
            "primary": "#0d7d8f", "secondary": "#2a6f97", "accent": "#e9b949",
            "background": "#fbfdfd", "surface": "#eef5f5", "surfaceAlt": "#e0eded",
            "text": "#173038", "muted": "#527079", "border": "#d0e2e2",
            "success": "#1f9d76", "warning": "#d59120", "danger": "#cf4444", "info": "#2a6f97",
        },
        {
            "primary": "#3fc0d0", "secondary": "#5aa0c8", "accent": "#f2cd6b",
            "background": "#0a1518", "surface": "#0f1e22", "surfaceAlt": "#16292e",
            "text": "#e2eef0", "muted": "#94adb2", "border": "#25393e",
            "success": "#4dcfa2", "warning": "#e6b64c", "danger": "#eb6b6b", "info": "#6db3d8",
        },
    ),
}


def default_scheme() -> dict:
    s = copy.deepcopy(PRESETS["clean-slate"])
    s["meta"]["name"] = "Untitled scheme"
    return s


def get_preset(pid: str) -> dict | None:
    p = PRESETS.get(pid)
    return copy.deepcopy(p) if p else None
