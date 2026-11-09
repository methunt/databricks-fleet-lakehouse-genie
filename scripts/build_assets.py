"""Build this README's SVG assets, one dark and one light variant each.

Why a generator rather than hand-written files: the light and dark variants
differ only by palette, and the figures on them come from the project's own
verified numbers. One spec plus two palettes produces every variant, and the
numbers are read from `readme-facts.json`, so a banner cannot disagree with the
README prose or the dashboard.

Animation notes, learned the hard way about GitHub:

  * GitHub strips <style> and <script> from markdown, so CSS cannot live in the
    README. It DOES run CSS inside an .svg referenced as <img>, which is why the
    animation lives in the asset rather than the page.
  * No external fonts can load - a proxied SVG has no network access - so every
    text element uses a generic system stack.
  * GitHub cannot be forced into dark mode. Both variants are emitted and the
    README picks between them with <picture> and prefers-color-scheme.
  * Entrances animate transform only, never opacity. A renderer that ignores CSS
    must still show a fully legible banner.

Rendered size: the canvas is 1200 wide and GitHub's content column is ~900, so
everything here is seen at 0.75x. A 22px source size arrives as 16.5px. Judge
sizes on the rendered result, not the source.

Usage:
    python scripts/build_assets.py
    python scripts/build_assets.py --spec scripts/readme-assets.json --out assets

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import string
import sys
from pathlib import Path

FONT = "system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Consolas,'Liberation Mono',monospace"

# Light is tuned to read as one piece with the dashboard: white cards, the same
# Okabe-Ito accents the report uses. Dark is tuned to GitHub's dark surface
# rather than being light inverted.
LIGHT = {
    "name": "light",
    "bg": "#FFFFFF", "card": "#F6F8FA", "card2": "#EEF1F5", "border": "#D0D7DE",
    "text": "#1F2328", "muted": "#656D76", "faint": "#8C959F",
    "primary": "#2563EB", "good": "#059669", "warn": "#D97706",
    "bad": "#DC2626", "violet": "#7C3AED", "cyan": "#0891B2",
    "glowopacity": "0.07", "glowhalf": "0.03", "ctashadow": "0.34", "wash": "0.10",
}
DARK = {
    "name": "dark",
    "bg": "#0D1117", "card": "#161B22", "card2": "#1C2128", "border": "#30363D",
    "text": "#E6EDF3", "muted": "#8B949E", "faint": "#484F58",
    "primary": "#3B82F6", "good": "#10B981", "warn": "#F59E0B",
    "bad": "#EF4444", "violet": "#8B5CF6", "cyan": "#22D3EE",
    "glowopacity": "0.16", "glowhalf": "0.06", "ctashadow": "0.55", "wash": "0.22",
}

ACCENTS = {"primary", "good", "warn", "bad", "violet", "cyan"}

MOTION = """
    .rise  { animation: rise .55s cubic-bezier(.2,.7,.3,1) both; }
    @keyframes rise { from { transform: translateY(9px) } to { transform: translateY(0) } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important } }"""


def esc(s: str) -> str:
    """Escape XML text. One raw & from a project name breaks the whole file."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_attr(s: str) -> str:
    """Escape for an attribute value, not text content.

    esc() is not enough here: a double quote inside an attribute closes it
    early, the SVG stops being well-formed, and GitHub renders a malformed SVG
    as blank space with no error.
    """
    return esc(s).replace('"', "&quot;")


def fill(text: str, facts: dict) -> str:
    """Substitute {key} from the facts dict. A missing key raises rather than
    rendering a blank, so a renamed field fails the build instead of shipping a
    gap in the banner."""
    if not isinstance(text, str) or "{" not in text:
        return text
    try:
        return string.Formatter().vformat(text, (), facts)
    except KeyError as e:
        sys.exit(f"error: spec references unknown fact {e} in: {text!r}")


def paint(template: str, p: dict) -> str:
    out = template
    for k, v in p.items():
        out = out.replace(f"__{k.upper()}__", str(v))
    return out.replace("__FONT__", FONT).replace("__MONO__", MONO)


def wrap(text: str, width: int) -> list[str]:
    """Greedy character-budget wrap. Approximate by design - exact metrics need
    a font, and banner copy is short enough for a character budget."""
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if len(candidate) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def accent(name: str, where: str) -> str:
    if name not in ACCENTS:
        sys.exit(f"error: {where} has unknown accent {name!r}; "
                 f"expected one of {', '.join(sorted(ACCENTS))}")
    return f"__{name.upper()}__"


# --------------------------------------------------------------------------- #
# Hero - eyebrow + subtitle only
# --------------------------------------------------------------------------- #

def hero(spec: dict, facts: dict) -> str:
    """The hero banner: eyebrow and subtitle, no title.

    The project name lives as a real `<h1>` in the README, wrapped in the same
    link as this image, so a search engine and a screen reader both get the name
    as text rather than pixels inside an `<img>`. `spec["title"]` is required
    anyway, but only to drive aria-label and the paste-this-heading note main()
    prints - it is never drawn.
    """
    if "title" not in spec:
        sys.exit("error: hero needs a title even though it isn't drawn - it "
                 "drives aria-label and the <h1> the README carries above it")
    eyebrow = esc(fill(spec.get("eyebrow", ""), facts))
    subtitle = fill(spec.get("subtitle", ""), facts)
    note = esc(fill(spec.get("note", ""), facts))
    col = accent(spec.get("accent", "primary"), "hero")

    eyebrow_y = 74
    rule_y = (eyebrow_y + 34) if eyebrow else 50
    sub_lines = wrap(subtitle, 104) if subtitle else []
    sub_step = 34
    y = rule_y
    sub_svg = ""
    for i, line in enumerate(sub_lines):
        y = rule_y + 38 + i * sub_step
        sub_svg += f"""
  <text class="rise" style="animation-delay:{0.2 + i * 0.05:.2f}s" x="40" y="{y}"
        font-family="__FONT__" font-size="25" fill="__MUTED__">{esc(line)}</text>"""
    note_svg = ""
    if note:
        y += sub_step if sub_lines else 38
        note_svg = f"""
  <text class="rise" style="animation-delay:.25s" x="40" y="{y}"
        font-family="__MONO__" font-size="18" fill="__MUTED__">{note}</text>"""

    height = y + 40

    eyebrow_svg = ""
    if eyebrow:
        eyebrow_svg = f"""
  <text class="rise" x="40" y="{eyebrow_y}" font-family="__FONT__" font-size="22" font-weight="700"
        letter-spacing="3" fill="{col}">{eyebrow.upper()}</text>"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}"
     width="1200" height="{height}" role="img" aria-label="{esc_attr(fill(spec["title"], facts))}">
  <style>
    /* Entrance animations move things but never fade them. A renderer that does
       not run CSS would otherwise show an empty banner, because the from-state
       of a fade is invisible and fill-mode both holds it for the whole delay. */{MOTION}
    .sweep {{ animation: sweep .9s cubic-bezier(.2,.7,.3,1) .15s; }}
    .blob  {{ animation: drift 14s ease-in-out infinite alternate; }}
    @keyframes sweep {{ from {{ width: 0 }} to {{ width: 1120px }} }}
    @keyframes drift {{ from {{ transform: translate(0,0) }}
                        to   {{ transform: translate(64px,-22px) }} }}
  </style>
  <defs>
    <radialGradient id="g" cx="50%" cy="50%" r="50%">
      <!-- Three stops: a two-stop fade keeps its outer third visible as a hard
           circular edge on dark surfaces. Fading to zero by ~70% removes the edge. -->
      <stop offset="0%" stop-color="__PRIMARY__" stop-opacity="__GLOWOPACITY__"/>
      <stop offset="55%" stop-color="__PRIMARY__" stop-opacity="__GLOWHALF__"/>
      <stop offset="100%" stop-color="__PRIMARY__" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <!-- The panel paints the theme's own card colour rather than staying
       transparent, so the hero reads as a deliberate surface on all four
       GitHub backgrounds. -->
  <rect width="1200" height="{height}" rx="16" fill="__CARD__"/>
  <rect x="0.5" y="0.5" width="1199" height="{height - 1}" rx="15.5" fill="none" stroke="__BORDER__"/>
  <rect width="8" height="{height}" rx="4" fill="{col}"/>
  <g class="blob"><circle cx="1010" cy="70" r="240" fill="url(#g)"/></g>{eyebrow_svg}
  <rect class="sweep" x="40" y="{rule_y}" width="1120" height="2"
        rx="1" fill="__BORDER__"/>{sub_svg}{note_svg}
</svg>
"""


# --------------------------------------------------------------------------- #
# Caption - renders under a real <h2>
# --------------------------------------------------------------------------- #

def caption(spec: dict, facts: dict) -> str:
    """A caption strip for the sentence under a section's real `<h2>`.

    The heading itself stays in the markdown, so it is searchable and readable
    by a screen reader. `spec["eyebrow"]` and `spec["title"]` are required but
    only compose the aria-label and the exact `<h2>` text main() prints.
    Everything drawn here is `spec["body"]`.
    """
    if "eyebrow" not in spec or "title" not in spec:
        sys.exit(f"error: caption {spec.get('name')!r} needs eyebrow and title, "
                 f"even though neither is drawn")
    body = fill(spec.get("body", ""), facts)
    col = accent(spec.get("accent", "primary"), f"caption {spec.get('name')}")
    lines = wrap(body, 104)
    first_y, step = 46, 32
    height = first_y + max(0, len(lines) - 1) * step + 34

    body_svg = "".join(f"""
  <text x="40" y="{first_y + i * step}" font-family="__FONT__" font-size="22"
        fill="__MUTED__">{esc(line)}</text>""" for i, line in enumerate(lines))

    label = esc_attr(f"{fill(spec['eyebrow'], facts)} - {fill(spec['title'], facts)}")

    # A tint of the accent, not a solid band: a solid band fights the page.
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}"
     width="1200" height="{height}" role="img" aria-label="{label}">
  <style>{MOTION}</style>
  <defs>
    <linearGradient id="w" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{col}" stop-opacity="__WASH__"/>
      <stop offset="100%" stop-color="{col}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="{height}" rx="12" fill="__CARD__"/>
  <rect width="1200" height="{height}" rx="12" fill="url(#w)"/>
  <rect width="6" height="{height}" rx="3" fill="{col}"/>
  <g class="rise">{body_svg}
  </g>
</svg>
"""


# --------------------------------------------------------------------------- #
# Card strip - 2 or 3 stat cards
# --------------------------------------------------------------------------- #

def cards(spec: dict, facts: dict) -> str:
    """A row of 2-3 stat cards - the business-case banner, not a heading, so it
    keeps its own title baked into the SVG. Each stat comes from `facts` so it
    cannot drift from what the project's data shows."""
    items = spec.get("cards", [])
    if not (2 <= len(items) <= 3):
        sys.exit(f"error: card strip {spec.get('name')!r} holds 2 or 3 cards")

    gap = 20
    w = (1200 - gap * (len(items) - 1)) // len(items)
    # 386px card minus 56px of padding leaves ~330px; at 21px a character is
    # roughly 10px, so 31 characters is the safe budget. 36 overflowed the card.
    wrapped = [wrap(fill(c.get("body", ""), facts), 30) for c in items]
    body_y0, body_step = 158, 31
    height = body_y0 + max(len(b) for b in wrapped) * body_step + 56

    out = []
    for i, (c, body) in enumerate(zip(items, wrapped)):
        col = accent(c.get("colour", "primary"), f"card {i + 1}")
        x = i * (w + gap)
        lines = "".join(f"""
    <text x="{x + 28}" y="{body_y0 + j * body_step}" font-family="__FONT__" font-size="21"
          fill="__MUTED__">{esc(line)}</text>""" for j, line in enumerate(body))
        foot_y = height - 32
        out.append(f"""
  <g class="rise" style="animation-delay:{0.15 + i * 0.12:.2f}s">
    <rect x="{x}" y="0" width="{w}" height="{height}" rx="14" fill="__CARD__" stroke="__BORDER__"/>
    <rect x="{x}" y="0" width="{w}" height="5" rx="2.5" fill="{col}"/>
    <circle cx="{x + 52}" cy="64" r="28" fill="{col}" fill-opacity="0.14"/>
    <text x="{x + 52}" y="75" text-anchor="middle" font-family="__FONT__"
          font-size="29">{esc(c.get("icon", ""))}</text>
    <text x="{x + 28}" y="124" font-family="__FONT__" font-size="26" font-weight="700"
          fill="__TEXT__" letter-spacing="-0.4">{esc(fill(c.get("title", ""), facts))}</text>{lines}
    <rect x="{x + 28}" y="{foot_y - 23}" width="{w - 56}" height="1" fill="__BORDER__"/>
    <text x="{x + 28}" y="{foot_y}" font-family="__FONT__" font-size="19.5" font-weight="700"
          fill="{col}" letter-spacing="0.3">{esc(fill(c.get("stat", ""), facts))}</text>
  </g>""")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}"
     width="1200" height="{height}" role="img" aria-label="{esc_attr(spec.get('label', 'Feature strip'))}">
  <style>{MOTION}</style>
{''.join(out)}
</svg>
"""


# --------------------------------------------------------------------------- #
# Call-to-action button
# --------------------------------------------------------------------------- #

def cta(spec: dict, facts: dict) -> str:
    label = esc(fill(spec["label"], facts))
    sublabel = esc(fill(spec.get("sublabel", ""), facts))
    col = accent(spec.get("accent", "primary"), "cta")

    # Drawn at 1320 and displayed at width="660" for 2x effective resolution.
    # Paints no page background, so it sits on all four GitHub surfaces.
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1320 152"
     width="1320" height="152" role="img" aria-label="{esc_attr(fill(spec["label"], facts))}">
  <style>{MOTION}
    .sheen {{ animation: sheen 4.5s ease-in-out infinite 1.4s; }}
    @keyframes sheen {{ from {{ transform: translateX(-200px) }}
                        to   {{ transform: translateX(1320px) }} }}
  </style>
  <defs>
    <linearGradient id="btn" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{col}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{col}" stop-opacity="0.86"/>
    </linearGradient>
    <filter id="sh" x="-20%" y="-40%" width="140%" height="200%">
      <feDropShadow dx="0" dy="6" stdDeviation="9" flood-color="{col}"
                    flood-opacity="__CTASHADOW__"/>
    </filter>
    <clipPath id="clip"><rect x="210" y="18" width="900" height="92" rx="46"/></clipPath>
    <linearGradient id="sheenfade" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="50%" stop-color="#FFFFFF" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <g class="rise">
    <rect x="210" y="18" width="900" height="92" rx="46" fill="url(#btn)" filter="url(#sh)"/>
    <g clip-path="url(#clip)">
      <rect class="sheen" x="210" y="18" width="150" height="92" fill="url(#sheenfade)"/>
    </g>
    <!-- Sizes look oversized because the asset is drawn at 1320 and shown at
         width="660" - halve them to judge the result. -->
    <text x="660" y="{60 if sublabel else 74}" text-anchor="middle" font-family="__FONT__"
          font-size="36" font-weight="700" fill="#FFFFFF">{label}</text>
    <text x="660" y="90" text-anchor="middle" font-family="__FONT__" font-size="24"
          fill="#FFFFFF" opacity="0.86">{sublabel}</text>
  </g>
</svg>
"""


# --------------------------------------------------------------------------- #
# Architecture - five stages, left to right
# --------------------------------------------------------------------------- #

def architecture(spec: dict, facts: dict) -> str:
    """The dataflow. Carries no figures by design: its subject is the shape of
    the pipeline, and changing a number should not produce a diff in it."""
    stages = spec.get("stages", [])
    n = len(stages)
    if not 3 <= n <= 6:
        sys.exit("error: architecture needs 3-6 stages")

    W = 1200
    margin, gap = 40, 16
    w = (W - margin * 2 - gap * (n - 1)) // n
    card_y, card_h = 54, 236
    height = card_y + card_h + 92

    body = []
    for i, st in enumerate(stages):
        col = accent(st.get("colour", "primary"), f"stage {i + 1}")
        x = margin + i * (w + gap)
        body.append(f"""
  <g class="rise" style="animation-delay:{0.1 + i * 0.09:.2f}s">
    <rect x="{x}" y="{card_y}" width="{w}" height="{card_h}" rx="14" fill="__CARD__" stroke="__BORDER__"/>
    <rect x="{x}" y="{card_y}" width="{w}" height="5" rx="2.5" fill="{col}"/>
    <text x="{x + 18}" y="{card_y + 44}" font-family="__FONT__" font-size="20" font-weight="700"
          fill="__TEXT__" letter-spacing="-0.2">{esc(st["title"])}</text>""")
        yy = card_y + 76
        for line in st.get("lines", []):
            body.append(f"""
    <text x="{x + 18}" y="{yy}" font-family="__FONT__" font-size="15.5"
          fill="__MUTED__">{esc(line)}</text>""")
            yy += 26
        body.append("""
  </g>""")
        if i < n - 1:
            ax1, ax2 = x + w + 2, x + w + gap - 2
            body.append(f"""
  <line x1="{ax1}" y1="{card_y + card_h // 2}" x2="{ax2}" y2="{card_y + card_h // 2}"
        stroke="__MUTED__" stroke-width="2" stroke-linecap="round" marker-end="url(#a)"/>""")

    note = esc(fill(spec.get("note", ""), facts))
    note_svg = ""
    if note:
        note_svg = f"""
  <text x="{margin}" y="{height - 34}" font-family="__FONT__" font-size="19"
        fill="__FAINT__">{note}</text>"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}"
     width="{W}" height="{height}" role="img" aria-label="{esc_attr(spec.get('label', 'Architecture'))}">
  <style>{MOTION}</style>
  <defs>
    <marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6"
            orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="__MUTED__"/>
    </marker>
  </defs>
{''.join(body)}{note_svg}
</svg>
"""


# --------------------------------------------------------------------------- #
# Lineage - one graph, volume to consumers, edges are the real reads
# --------------------------------------------------------------------------- #

def lineage(spec: dict, facts: dict) -> str:
    """Left-to-right lineage. Column widths come from the longest label, and
    every edge endpoint is checked against the node ids so a renamed table
    fails the build instead of drawing a dangling line."""
    FS, pad, gap, margin, step = 15, 14, 52, 30, 44
    cols, nodes = spec["columns"], {}
    x = margin
    top = 96
    H = max(len(c["nodes"]) for c in cols) * step
    for c in cols:
        c["w"] = int(max(len(n["label"]) for n in c["nodes"]) * 0.6 * FS + 2 * pad)
        c["x"] = x
        x += c["w"] + gap
        k = len(c["nodes"])
        for i, n in enumerate(c["nodes"]):
            n.update(col=c, cy=top + (i + 0.5) * H / k)
            nodes[n["id"]] = n
    W = x - gap + margin
    height = top + H + 24

    edges = []
    for src, dst in spec["edges"]:
        if src not in nodes or dst not in nodes:
            sys.exit(f"error: lineage edge {src!r} -> {dst!r} names an unknown node")
        a, b = nodes[src], nodes[dst]
        x1, x2 = a["col"]["x"] + a["col"]["w"], b["col"]["x"]
        mx = (x2 - x1) / 2
        edges.append(f'''
  <path d="M {x1} {a['cy']:.1f} C {x1 + mx:.1f} {a['cy']:.1f} {x2 - mx:.1f} {b['cy']:.1f} {x2 - 3} {b['cy']:.1f}"
        fill="none" stroke="{accent(a['col'].get('colour', 'primary'), 'column')}" stroke-opacity="0.8"
        stroke-width="1.8" stroke-dasharray="6 5" stroke-linecap="round" class="flow"
        marker-end="url(#a)"/>''')

    body = []
    for c in cols:
        col = accent(c.get("colour", "primary"), c["title"])
        body.append(f'''
  <text x="{c['x']}" y="40" font-family="__FONT__" font-size="19" font-weight="700" fill="__TEXT__">{esc(c['title'])}</text>
  <text x="{c['x']}" y="62" font-family="__FONT__" font-size="14" fill="{col}">{esc(c['sub'])}</text>''')
        for n in c["nodes"]:
            dim = n.get("dim", False)
            y = n["cy"] - 17
            body.append(f'''
  <rect x="{c['x']}" y="{y:.1f}" width="{c['w']}" height="34" rx="8" fill="__CARD__" stroke="__BORDER__"
        {'stroke-dasharray="5 4"' if dim else ''}/>
  <rect x="{c['x']}" y="{y:.1f}" width="4" height="34" rx="2" fill="{'__FAINT__' if dim else col}"/>
  <text x="{c['x'] + pad}" y="{n['cy'] + 5:.1f}" font-family="__MONO__" font-size="{FS}"
        fill="{'__MUTED__' if dim else '__TEXT__'}">{esc(n['label'])}</text>''')

    note = spec.get("note", "")
    note_svg = f'''
  <text x="{margin}" y="{height - 4}" font-family="__FONT__" font-size="14" fill="__FAINT__">{esc(note)}</text>''' if note else ""
    height += 18 if note else 0
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}"
     width="{W}" height="{height}" role="img" aria-label="{esc_attr(spec['label'])}">
  <style>
    /* Dashes travel along each path, and every path is drawn source to
       target, so the motion always reads left to right. Reduced-motion users
       get static dashes. */
    .flow {{ animation: flow 1.1s linear infinite; }}
    @keyframes flow {{ to {{ stroke-dashoffset: -11 }} }}
    @media (prefers-reduced-motion: reduce) {{ .flow {{ animation: none }} }}
  </style>
  <defs>
    <marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="__MUTED__"/>
    </marker>
  </defs>{''.join(edges)}{''.join(body)}{note_svg}
</svg>
"""


BUILDERS = {"hero": hero, "caption": caption, "cards": cards, "cta": cta,
            "architecture": architecture, "lineage": lineage}


def main() -> None:
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--spec", default=str(here / "readme-assets.json"))
    ap.add_argument("--out", default=str(here.parent / "assets"))
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    facts = json.loads((here / spec.get("facts_from", "readme-facts.json")).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    headings: list[str] = []
    count = 0
    for kind in ("hero", "architecture", "lineage", "cards", "cta", "captions"):
        v = spec.get(kind, [])
        entries = v if isinstance(v, list) else [v]
        for entry in entries:
            builder = BUILDERS["caption" if kind == "captions" else kind]
            # Captions are light-only by convention: they sit under a real
            # heading and a light strip reads correctly on all four surfaces.
            variants = ["light"] if kind == "captions" else ["light", "dark"]
            for variant in variants:
                theme = LIGHT if variant == "light" else DARK
                svg = paint(builder(entry, facts), theme)
                path = out / f"{entry['name']}-{variant}.svg"
                path.write_text(svg, encoding="utf-8")
                count += 1
            if kind == "captions":
                headings.append(f"## {entry['eyebrow']} — {fill(entry['title'], facts)}")

    print(f"wrote {count} files to {out}\n")
    if headings:
        print("Paste these as the real headings above each caption image:")
        for h in headings:
            print(f"  {h}")


if __name__ == "__main__":
    main()
