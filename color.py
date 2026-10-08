"""Color math: HEX <-> RGB <-> HSL <-> OKLab <-> OKLCH, WCAG contrast,
perceptual tint/shade ramps, harmony helpers.

All pure functions. RGB tuples are (r, g, b) floats in 0..255.
"""

from __future__ import annotations

import math
import re

RAMP_STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
_RAMP_L = {
    50: 0.971, 100: 0.936, 200: 0.885, 300: 0.808, 400: 0.704,
    500: 0.606, 600: 0.524, 700: 0.451, 800: 0.386, 900: 0.327, 950: 0.235,
}


def _clamp(n: float, lo: float, hi: float) -> float:
    return lo if n < lo else hi if n > hi else n


def _cbrt(n: float) -> float:
    return math.copysign(abs(n) ** (1 / 3), n)


# --------------------------------------------------------------- HEX / RGB

def parse_hex(value: str):
    if not isinstance(value, str):
        return None
    s = value.strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", s):
        s = "".join(c * 2 for c in s)
    if re.fullmatch(r"[0-9a-fA-F]{4}", s):
        s = "".join(c * 2 for c in s)
    if re.fullmatch(r"[0-9a-fA-F]{8}", s):
        s = s[:6]
    if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        return None
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def rgb_to_hex(rgb) -> str:
    r, g, b = (int(round(_clamp(c, 0, 255))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------- RGB / HSL

def rgb_to_hsl(rgb):
    r, g, b = (c / 255 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    h = 0.0
    if d:
        if mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h *= 60
    lightness = (mx + mn) / 2
    s = 0.0 if d == 0 else d / (1 - abs(2 * lightness - 1))
    return (round(h % 360, 1), round(s * 100, 1), round(lightness * 100, 1))


def hsl_to_rgb(hsl):
    h, s, lightness = hsl
    h = h % 360
    s = _clamp(s, 0, 100) / 100
    lightness = _clamp(lightness, 0, 100) / 100
    c = (1 - abs(2 * lightness - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = lightness - c / 2
    if h < 60:
        rp, gp, bp = c, x, 0
    elif h < 120:
        rp, gp, bp = x, c, 0
    elif h < 180:
        rp, gp, bp = 0, c, x
    elif h < 240:
        rp, gp, bp = 0, x, c
    elif h < 300:
        rp, gp, bp = x, 0, c
    else:
        rp, gp, bp = c, 0, x
    return ((rp + m) * 255, (gp + m) * 255, (bp + m) * 255)


# --------------------------------------------------------- sRGB <-> OKLab

def _srgb_to_linear(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    c = max(c, 0.0)
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return _clamp(v * 255, 0, 255)


def rgb_to_oklab(rgb):
    lr, lg, lb = (_srgb_to_linear(c) for c in rgb)
    l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb
    m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb
    s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb
    l_, m_, s_ = _cbrt(l), _cbrt(m), _cbrt(s)
    return (
        0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
    )


def oklab_to_rgb(lab):
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.291485548 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        _linear_to_srgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
        _linear_to_srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
        _linear_to_srgb(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
    )


def oklab_to_oklch(lab):
    L, a, b = lab
    c = math.hypot(a, b)
    h = math.degrees(math.atan2(b, a)) % 360
    return (L, c, h)


def oklch_to_oklab(lch):
    L, c, h = lch
    rad = math.radians(h)
    return (L, math.cos(rad) * c, math.sin(rad) * c)


def rgb_to_oklch(rgb):
    return oklab_to_oklch(rgb_to_oklab(rgb))


def oklch_to_rgb(lch):
    return oklab_to_rgb(oklch_to_oklab(lch))


# --------------------------------------------------------------- parsing

def parse_any(value: str):
    """Parse hex / rgb() / hsl() / oklch() strings. Returns an (r,g,b) tuple or None."""
    if not isinstance(value, str):
        return None
    s = value.strip().lower()
    if s.startswith("#"):
        return parse_hex(s)
    m = re.fullmatch(r"rgba?\(([^)]+)\)", s)
    if m:
        p = [float(x) for x in re.split(r"[ ,/]+", m.group(1).strip()) if x]
        if len(p) >= 3:
            return (p[0], p[1], p[2])
    m = re.fullmatch(r"hsla?\(([^)]+)\)", s)
    if m:
        p = [float(x) for x in re.split(r"[ ,/]+", m.group(1).replace("%", "").strip()) if x]
        if len(p) >= 3:
            return hsl_to_rgb((p[0], p[1], p[2]))
    m = re.fullmatch(r"oklch\(([^)]+)\)", s)
    if m:
        p = [float(x) for x in re.split(r"[ ,/]+", m.group(1).replace("%", "").strip()) if x]
        if len(p) >= 3:
            L = p[0] / 100 if p[0] > 1 else p[0]
            return oklch_to_rgb((L, p[1], p[2]))
    return None


def normalize_hex(value: str, fallback: str = "#888888") -> str:
    rgb = parse_any(value)
    return rgb_to_hex(rgb) if rgb else fallback


# --------------------------------------------------------------- formatting

def fmt_rgb(rgb) -> str:
    r, g, b = (int(round(c)) for c in rgb)
    return f"rgb({r} {g} {b})"


def fmt_hsl(hsl) -> str:
    h, s, lightness = hsl
    return f"hsl({h:.1f} {s:.1f}% {lightness:.1f}%)"


def fmt_oklch(lch) -> str:
    L, c, h = lch
    return f"oklch({L * 100:.1f}% {c:.4f} {h:.1f})"


def model(hex_value: str) -> dict:
    rgb = parse_hex(hex_value) or (136, 136, 136)
    return {
        "hex": rgb_to_hex(rgb),
        "rgb": tuple(int(round(c)) for c in rgb),
        "hsl": rgb_to_hsl(rgb),
        "oklch": rgb_to_oklch(rgb),
        "rgb_str": fmt_rgb(rgb),
        "hsl_str": fmt_hsl(rgb_to_hsl(rgb)),
        "oklch_str": fmt_oklch(rgb_to_oklch(rgb)),
    }


# --------------------------------------------------------------- contrast

def relative_luminance(rgb) -> float:
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b) -> float:
    ra = parse_hex(a) if isinstance(a, str) else a
    rb = parse_hex(b) if isinstance(b, str) else b
    if not ra or not rb:
        return 0.0
    la, lb = relative_luminance(ra), relative_luminance(rb)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def wcag_grade(fg, bg) -> dict:
    ratio = contrast_ratio(fg, bg)
    if ratio >= 7:
        tag, cls = "AAA", "pass"
    elif ratio >= 4.5:
        tag, cls = "AA", "pass"
    elif ratio >= 3:
        tag, cls = "AA large", "warn"
    else:
        tag, cls = "fail", "fail"
    return {"ratio": round(ratio, 2), "tag": tag, "cls": cls,
            "normal_aa": ratio >= 4.5, "large_aa": ratio >= 3}


def readable_on(bg: str) -> str:
    return "#000000" if contrast_ratio("#000000", bg) >= contrast_ratio("#ffffff", bg) else "#ffffff"


# --------------------------------------------------------------- transforms

def adjust_lightness(hex_value: str, amount: float) -> str:
    L, a, b = rgb_to_oklab(parse_hex(hex_value) or (136, 136, 136))
    return rgb_to_hex(oklab_to_rgb((_clamp(L + amount, 0, 1), a, b)))


def rotate_hue(hex_value: str, deg: float) -> str:
    L, c, h = rgb_to_oklch(parse_hex(hex_value) or (136, 136, 136))
    return rgb_to_hex(oklch_to_rgb((L, c, (h + deg) % 360)))


def scale_chroma(hex_value: str, k: float) -> str:
    L, c, h = rgb_to_oklch(parse_hex(hex_value) or (136, 136, 136))
    return rgb_to_hex(oklch_to_rgb((L, _clamp(c * k, 0, 0.5), h)))


def build_ramp(base_hex: str) -> dict:
    base_L, base_c, base_h = rgb_to_oklch(parse_hex(base_hex) or (136, 136, 136))
    out = {}
    for step in RAMP_STEPS:
        L = _RAMP_L[step]
        edge = min(L, 1 - L) / 0.5
        chroma = base_c * (0.35 + 0.65 * _clamp(edge, 0, 1))
        out[step] = rgb_to_hex(oklch_to_rgb((L, chroma, base_h)))
    nearest, best = 500, math.inf
    for step in RAMP_STEPS:
        d = abs(rgb_to_oklab(parse_hex(out[step]))[0] - base_L)
        if d < best:
            best, nearest = d, step
    out[nearest] = rgb_to_hex(parse_hex(base_hex) or (136, 136, 136))
    out["base"] = nearest
    return out


def harmonies(hex_value: str) -> dict:
    return {
        "complementary": [hex_value, rotate_hue(hex_value, 180)],
        "analogous": [rotate_hue(hex_value, -30), hex_value, rotate_hue(hex_value, 30)],
        "triadic": [hex_value, rotate_hue(hex_value, 120), rotate_hue(hex_value, 240)],
        "tetradic": [hex_value, rotate_hue(hex_value, 90),
                     rotate_hue(hex_value, 180), rotate_hue(hex_value, 270)],
        "split_complementary": [hex_value, rotate_hue(hex_value, 150), rotate_hue(hex_value, 210)],
    }
