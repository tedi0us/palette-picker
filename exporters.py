"""Turn a scheme into copy-pasteable code in several formats."""

from __future__ import annotations

import json
import re

import color
from presets import RAMPED_TOKENS, TOKEN_KEYS, TOKEN_META


def _kebab(s: str) -> str:
    return re.sub(r"([a-z])([A-Z])", r"\1-\2", s).lower()


def _resolve(theme_colors: dict) -> tuple[dict, dict]:
    ramps = {k: color.build_ramp(theme_colors[k]) for k in RAMPED_TOKENS if theme_colors.get(k)}
    return theme_colors, ramps


# --------------------------------------------------------------------- CSS

def to_css(scheme: dict, ramp_scale: bool = True) -> str:
    def block(theme_colors, indent=""):
        colors, ramps = _resolve(theme_colors)
        out = []
        for key in TOKEN_KEYS:
            if not colors.get(key):
                continue
            out.append(f"{indent}  --color-{_kebab(key)}: {colors[key]};")
            out.append(f"{indent}  --color-{_kebab(key)}-contrast: {color.readable_on(colors[key])};")
        if ramp_scale:
            out.append("")
            for key in RAMPED_TOKENS:
                if key not in ramps:
                    continue
                for step in color.RAMP_STEPS:
                    out.append(f"{indent}  --color-{_kebab(key)}-{step}: {ramps[key][step]};")
        return "\n".join(out)

    radius = scheme.get("options", {}).get("radius", 10)
    return (
        f":root {{\n  color-scheme: light dark;\n  --radius: {radius}px;\n\n"
        f"{block(scheme['light'])}\n}}\n\n"
        f"@media (prefers-color-scheme: dark) {{\n  :root {{\n"
        f"{block(scheme['dark'], indent='  ')}\n  }}\n}}\n\n"
        f'[data-theme="light"] {{\n{block(scheme["light"])}\n}}\n'
        f'[data-theme="dark"] {{\n{block(scheme["dark"])}\n}}\n'
    )


# -------------------------------------------------------------------- SCSS

def to_scss(scheme: dict, ramp_scale: bool = True) -> str:
    def emit(theme_colors, suffix):
        colors, ramps = _resolve(theme_colors)
        out = [f"// {suffix} theme"]
        for key in TOKEN_KEYS:
            if colors.get(key):
                out.append(f"$color-{_kebab(key)}-{suffix}: {colors[key]};")
        if ramp_scale:
            for key in RAMPED_TOKENS:
                if key not in ramps:
                    continue
                pairs = ",\n".join(f'  "{s}": {ramps[key][s]}' for s in color.RAMP_STEPS)
                out.append(f"${_kebab(key)}-{suffix}: (\n{pairs}\n);")
        return "\n".join(out)

    return f"{emit(scheme['light'], 'light')}\n\n{emit(scheme['dark'], 'dark')}\n"


# ---------------------------------------------------------------- Tailwind

def to_tailwind(scheme: dict, ramp_scale: bool = True) -> str:
    colors, ramps = _resolve(scheme["light"])
    obj = {}
    for key in TOKEN_KEYS:
        if not colors.get(key):
            continue
        if ramp_scale and key in ramps:
            obj[_kebab(key)] = {"DEFAULT": colors[key],
                                **{str(s): ramps[key][s] for s in color.RAMP_STEPS}}
        else:
            obj[_kebab(key)] = colors[key]
    cfg = {"theme": {"extend": {
        "colors": obj,
        "borderRadius": {"DEFAULT": f"{scheme.get('options', {}).get('radius', 10)}px"},
    }}}
    return ("/** Tailwind config fragment — light theme.\n"
            " *  For dark mode, wire these via CSS vars or the CSS export. */\n"
            f"module.exports = {json.dumps(cfg, indent=2)};\n")


# ------------------------------------------------------------------- JSON

def to_json(scheme: dict, ramp_scale: bool = True) -> str:
    return json.dumps(scheme, indent=2) + "\n"


def to_design_tokens(scheme: dict, ramp_scale: bool = True) -> str:
    def group(theme_colors):
        colors, ramps = _resolve(theme_colors)
        g = {}
        for key in TOKEN_KEYS:
            if not colors.get(key):
                continue
            node = {"$type": "color", "$value": colors[key]}
            if key in TOKEN_META:
                node["$description"] = TOKEN_META[key]["hint"]
            if ramp_scale and key in ramps:
                node["scale"] = {str(s): {"$type": "color", "$value": ramps[key][s]}
                                 for s in color.RAMP_STEPS}
            g[key] = node
        return g

    return json.dumps({
        "$description": scheme.get("meta", {}).get("name", "Color scheme"),
        "color": {"light": group(scheme["light"]), "dark": group(scheme["dark"])},
    }, indent=2) + "\n"


# --------------------------------------------------------------- Markdown

def to_markdown(scheme: dict, ramp_scale: bool = True) -> str:
    def rows(theme_colors, title):
        md = (f"### {title}\n\n| Token | Hex | On-color | Contrast vs bg |\n"
              "|---|---|---|---|\n")
        for key in TOKEN_KEYS:
            v = theme_colors.get(key)
            if not v:
                continue
            cr = color.contrast_ratio(v, theme_colors["background"])
            label = TOKEN_META.get(key, {}).get("label", key)
            md += f"| {label} | `{v}` | `{color.readable_on(v)}` | {cr:.2f}:1 |\n"
        return md

    meta = scheme.get("meta", {})
    head = f"# {meta.get('name', 'Color scheme')}\n\n"
    if meta.get("description"):
        head += meta["description"] + "\n\n"
    return head + rows(scheme["light"], "Light") + "\n" + rows(scheme["dark"], "Dark") + "\n"


FORMATS = {
    "css": {"label": "CSS variables", "ext": "css", "fn": to_css},
    "scss": {"label": "SCSS", "ext": "scss", "fn": to_scss},
    "tailwind": {"label": "Tailwind config", "ext": "js", "fn": to_tailwind},
    "json": {"label": "JSON (scheme)", "ext": "json", "fn": to_json},
    "tokens": {"label": "Design Tokens (W3C)", "ext": "tokens.json", "fn": to_design_tokens},
    "markdown": {"label": "Markdown sheet", "ext": "md", "fn": to_markdown},
}


def render(fmt: str, scheme: dict, ramp_scale: bool = True) -> str:
    spec = FORMATS.get(fmt, FORMATS["css"])
    return spec["fn"](scheme, ramp_scale)
