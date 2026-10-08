# Palette Picker

A LAN-hosted tool for letting a client choose a website color scheme from their
own phone or computer. **Flask + HTMX, minimal JavaScript.**

You (the designer) run it on your machine, seed it with a few starting palettes,
and send the client a link on your local network. They tweak colors, watch a full
website preview repaint, check contrast, and hit **Send to designer** — their
pick lands in `data/submissions.json` and shows up on `/admin`.

---

## Running it

```bash
cd palette-picker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

```
Local:    http://localhost:4173
Network:  http://192.168.1.90:4173     <- give this to the client
Admin:    http://localhost:4173/admin
```

`PORT=8080 .venv/bin/python app.py` to change the port. `DEBUG=1` for the Flask
reloader.

Tests:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

---

## Architecture

The server renders HTML; **HTMX** swaps fragments in response to every control.
There is no client-side state and no SPA framework.

```
palette-picker/
├── app.py            Flask routes — one per user action, each returns a fragment
├── color.py          hex/rgb/hsl/oklab/oklch, WCAG contrast, OKLab ramps, harmony
├── presets.py        token model + 8 preset schemes
├── siteplan.py       site-planner model — block vocabulary, normalize, default outline
├── exporters.py      CSS / SCSS / Tailwind / JSON / W3C tokens / Markdown
├── store.py          per-session working state + submissions (palette) + plans (planner)
├── requirements.txt  Flask only
├── templates/
│   ├── base.html         html shell, loads htmx + app.js
│   ├── index.html        page frame
│   ├── _workspace.html   subbar + sidebar + live area + submit modal  (id="workspace")
│   ├── _sidebar.html     presets, harmony, token editors, options
│   ├── _token_row.html   one token: swatch, hex/rgb/hsl/oklch fields, HSL+OKLCH sliders
│   ├── _live.html        the right pane: view tabs + active panel  (id="live")
│   ├── _preview.html     the token-driven marketing-site mockup
│   ├── _macros.html      mk_vars() — turns a palette into inline CSS custom properties
│   ├── _share.html / _sent.html   small fragments
│   ├── plan.html         site-planner page frame
│   ├── _plan.html        planner workspace  (id="planspace")
│   ├── _plan_editor.html sidebar — pages, blocks, extra nav buttons
│   ├── _plan_preview.html the wireframe, painted with a borrowed palette
│   ├── _plan_sent.html   confirmation fragment
│   └── admin.html        submissions + site plans review
└── static/
    ├── css/app.css       application chrome (fixed dark theme)
    ├── css/mockup.css     the preview site — 100% var(--mk-*) driven
    └── js/
        ├── htmx.min.js    vendored (v2.0.4)
        └── app.js         ~60 lines: clipboard, modal toggle, Ctrl+Z/Ctrl+Shift+Z, toasts
```

### Request → fragment map

| Action | Route | Returns |
|---|---|---|
| Edit a color (picker / hex / rgb / hsl / oklch field) | `POST /color` | `#workspace` |
| Lighten / darken | `POST /nudge` | `#workspace` |
| HSL / OKLCH sliders (fire on release) | `POST /hsl`, `POST /oklch` | `#workspace` |
| Show/hide a token's sliders | `POST /expand` | `#workspace` |
| Load a preset | `POST /preset` | `#workspace` |
| Auto-fill from a base color + harmony | `POST /harmony` | `#workspace` |
| Randomize / reset | `POST /randomize`, `POST /reset` | `#workspace` |
| Undo / redo | `POST /undo`, `POST /redo` | `#workspace` |
| Rename, radius, font scale | `POST /name`, `POST /options` | `#workspace` |
| Switch tab (Preview / Contrast / Ramps / Export) | `POST /view` | `#live` |
| Light/dark, device frame | `POST /toggle` | `#workspace` |
| Change export format / toggle ramps | `POST /export-opts` | `#live` |
| Download export file | `GET /download` | file attachment |
| Copy shareable link | `POST /share` | link fragment |
| Send scheme to designer | `POST /submit` | confirmation fragment |
| Admin delete | `POST /admin/delete/<id>` | empty (row removed) |

State lives in `data/state/<session-id>.json`, keyed by the `pp_sid` cookie, and
survives a server restart. A shareable link (`/?s=<base64>`) fully restores a
scheme.

---

## Front-end feature set

- **8 preset schemes**, each with matched light **and** dark palettes
- **13 tokens** in 3 groups (Brand / Surfaces & Text / Status)
- Per token: native picker, editable **hex / rgb / hsl / oklch**, HSL sliders,
  perceptual **OKLCH** sliders, one-click lighten / darken, live WCAG ratio
- **Contrast matrix** — foreground × background grid with AA / AAA / large verdicts
- **Tints & shades** — OKLab 50–950 ramps for every brand/status color
- **Live preview** — nav, hero, cards, form, alerts, table, buttons, footer,
  painted from the tokens; light/dark + desktop/tablet/phone frames
- **Auto-fill** from one base color (complementary / analogous / triadic / split /
  tetradic)
- Border-radius + font-scale controls
- **Undo / redo** (`Ctrl+Z` / `Ctrl+Shift+Z`), shareable link
- **Export** to CSS custom properties, SCSS, Tailwind, JSON, W3C tokens, Markdown

---

## Back end

Flask, one dependency. No authentication — **run on a trusted LAN only.**
Submissions and per-session state are plain JSON files under `data/` (git-ignored,
created on first run).

## Site planner (`/plan`)

A second tool on the same server and session cookie. The client outlines the
site *structure* before any design work: which **pages** exist, which show in the
**top nav** (★), and an ordered list of **content blocks** per page (Hero, Feature
grid, Pricing, Contact form, …, each with a one-line note). A live **wireframe**
preview repaints as they edit, painted with a palette borrowed from the color
picker — they pick which submitted scheme to preview against from a dropdown.

**Send to designer** appends the outline to `data/plans.json` (with a snapshot of
the palette used) and it shows up on `/admin` under **Site plans** as a text
outline plus the mini wireframe.

| Action | Route | Returns |
|---|---|---|
| Rename outline / pick preview palette | `POST /plan/meta` | `#planspace` |
| Add / rename / remove / move / nav-toggle a page | `POST /plan/pages` (`op=`) | `#planspace` |
| Add / edit-note / remove / move a block | `POST /plan/blocks` (`op=`) | `#planspace` |
| Add / rename / remove an extra nav button | `POST /plan/nav` (`op=`) | `#planspace` |
| Reset outline | `POST /plan/reset` | `#planspace` |
| Send outline to designer | `POST /plan/submit` | confirmation fragment |
| Admin delete a plan | `POST /admin/plan/delete/<id>` | empty |

Block vocabulary and the starter outline live in `siteplan.py`.

## Customizing for a client

- **Presets / tokens** → `presets.py`
- **Preview markup** → `templates/_preview.html` (swap "Northwind" for the client's
  brand, match their real page structure)
- **Export shapes** → `exporters.py`
