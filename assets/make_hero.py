"""Build hero-dark.svg / hero-light.svg for the ijshd7 profile README.

Usage: pip install fonttools && python3 make_hero.py   (then commit the SVGs to assets/)

Design tokens (shared with the README card URLs):
  dark : ink e6edf3  muted 8b949e  moss 86c06c  clay e8a26a  rule 30363d
  light: ink 1f2328  muted 57606a  moss 3f7a2f  clay b3561f  rule d0d7de

Type is converted to outlines so the header renders identically on every
OS/browser: SVGs loaded through <img> cannot fetch web fonts.
"""
import os
import urllib.request

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONT = "BricolageGrotesque.ttf"
FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/"
            "BricolageGrotesque%5Bopsz,wdth,wght%5D.ttf")  # OFL 1.1

TOKENS = {
    "dark":  dict(ink="#e6edf3", muted="#8b949e", moss="#86c06c", clay="#e8a26a", rule="#30363d"),
    "light": dict(ink="#1f2328", muted="#57606a", moss="#3f7a2f", clay="#b3561f", rule="#d0d7de"),
}

W, H = 1200, 280


def instance(axes):
    return instancer.instantiateVariableFont(TTFont(FONT), axes)


def kern_table(font):
    """Flat pair-kerning lookup from GPOS PairPos (format 1 and 2)."""
    kern = {}
    if "GPOS" not in font:
        return kern
    gpos = font["GPOS"].table
    for lookup in gpos.LookupList.Lookup:
        for sub in lookup.SubTable:
            if getattr(sub, "LookupType", lookup.LookupType) == 9:  # extension
                sub = sub.ExtSubTable
            if sub.LookupType != 2:
                continue
            if sub.Format == 1:
                for first, ps in zip(sub.Coverage.glyphs, sub.PairSet):
                    for pvr in ps.PairValueRecord:
                        v = pvr.Value1.XAdvance if pvr.Value1 and hasattr(pvr.Value1, "XAdvance") else 0
                        if v:
                            kern.setdefault((first, pvr.SecondGlyph), v)
            elif sub.Format == 2:
                cd1, cd2 = sub.ClassDef1.classDefs, sub.ClassDef2.classDefs
                for first in sub.Coverage.glyphs:
                    c1 = cd1.get(first, 0)
                    for second, c2 in list(cd2.items()) + [(None, 0)]:
                        rec = sub.Class1Record[c1].Class2Record[c2]
                        v = rec.Value1.XAdvance if rec.Value1 and hasattr(rec.Value1, "XAdvance") else 0
                        if v and second is not None:
                            kern.setdefault((first, second), v)
    return kern


def text_path(font, kern, text, size, x, y):
    """Return (path d, advance) for `text` set at `size` px with baseline at (x, y)."""
    upem = font["head"].unitsPerEm
    s = size / upem
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    hmtx = font["hmtx"]
    names = [cmap.get(ord(c), ".notdef") for c in text]
    parts, cx = [], x
    for i, g in enumerate(names):
        pen = SVGPathPen(gs, ntos=lambda v: ('%.1f' % v).rstrip('0').rstrip('.'))
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
        d = pen.getCommands()
        if d:
            parts.append(d)
        cx += hmtx[g][0] * s
        if i + 1 < len(names):
            cx += kern.get((g, names[i + 1]), 0) * s
    return " ".join(parts), cx


def surface(kind, cx, t):
    """One of the five 'surfaces' as an SVG group centred on cx. 88x66 box, top y=98."""
    x, y, w, h = cx - 44, 92, 88, 66
    ink, muted, moss, clay = t["ink"], t["muted"], t["moss"], t["clay"]
    frame = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="none" stroke="{muted}" stroke-width="3"/>'
    if kind == "terminal":
        body = (frame +
                f'<path d="M{x+16} {y+22} l10 8 -10 8" fill="none" stroke="{moss}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<rect x="{x+34}" y="{y+22}" width="10" height="16" fill="{moss}"/>'
                f'<rect x="{x+16}" y="{y+46}" width="34" height="3" rx="1.5" fill="{muted}"/>')
    elif kind == "web":
        body = (frame +
                f'<line x1="{x}" y1="{y+18}" x2="{x+w}" y2="{y+18}" stroke="{muted}" stroke-width="3"/>'
                f'<rect x="{x+10}" y="{y+6}" width="46" height="7" rx="3.5" fill="{muted}" opacity=".55"/>'
                f'<rect x="{x+14}" y="{y+30}" width="60" height="3" rx="1.5" fill="{muted}"/>'
                f'<rect x="{x+14}" y="{y+40}" width="42" height="3" rx="1.5" fill="{muted}"/>'
                f'<rect x="{x+14}" y="{y+50}" width="24" height="8" rx="4" fill="{moss}"/>')
    elif kind == "desktop":
        body = (frame +
                f'<line x1="{x}" y1="{y+14}" x2="{x+w}" y2="{y+14}" stroke="{muted}" stroke-width="3"/>'
                f'<line x1="{x+26}" y1="{y+14}" x2="{x+26}" y2="{y+h}" stroke="{muted}" stroke-width="3"/>'
                f'<rect x="{x+6}" y="{y+22}" width="14" height="3" rx="1.5" fill="{muted}"/>'
                f'<rect x="{x+6}" y="{y+31}" width="14" height="3" rx="1.5" fill="{moss}"/>'
                f'<rect x="{x+6}" y="{y+40}" width="14" height="3" rx="1.5" fill="{muted}"/>'
                f'<circle cx="{x+57}" cy="{y+37}" r="8" fill="{clay}"/>'
                f'<path d="M{x+42} {y+58} q15 -16 30 0" fill="{clay}"/>')
    elif kind == "extension":
        body = (frame +
                f'<line x1="{x}" y1="{y+18}" x2="{x+w}" y2="{y+18}" stroke="{muted}" stroke-width="3"/>'
                f'<rect x="{x+10}" y="{y+6}" width="30" height="7" rx="3.5" fill="{muted}" opacity=".55"/>'
                f'<rect x="{x+14}" y="{y+30}" width="26" height="3" rx="1.5" fill="{muted}"/>'
                f'<rect x="{x+14}" y="{y+40}" width="20" height="3" rx="1.5" fill="{muted}"/>'
                # popup card hanging from the toolbar, with a toggle switched on
                f'<rect x="{x+46}" y="{y+22}" width="46" height="36" rx="6" fill="none" stroke="{ink}" stroke-width="3"/>'
                f'<rect x="{x+56}" y="{y+34}" width="26" height="12" rx="6" fill="{moss}"/>'
                f'<circle cx="{x+76}" cy="{y+40}" r="4" fill="{ink}"/>')
    elif kind == "game":
        # a hand of three cards, the front one face-up
        body = (f'<rect x="{x+8}" y="{y+10}" width="40" height="56" rx="6" fill="none" stroke="{muted}" stroke-width="3" transform="rotate(-8 {x+28} {y+38})"/>'
                f'<rect x="{x+26}" y="{y+6}" width="40" height="56" rx="6" fill="none" stroke="{muted}" stroke-width="3" transform="rotate(4 {x+46} {y+34})"/>'
                f'<rect x="{x+44}" y="{y+4}" width="40" height="58" rx="6" fill="none" stroke="{ink}" stroke-width="3" transform="rotate(12 {x+64} {y+33})"/>'
                f'<path d="M{x+66} {y+22} l7 10 -7 10 -7 -10z" fill="{clay}" transform="rotate(12 {x+64} {y+33})"/>')
    return body


def build(theme):
    t = TOKENS[theme]
    display = instance({"wght": 800, "wdth": 92, "opsz": 96})
    body = instance({"wght": 500, "wdth": 100, "opsz": 14})
    kd, kb = kern_table(display), kern_table(body)

    name_d, _ = text_path(display, kd, "Isaiah", 132, 40, 160)
    tag1, _ = text_path(body, kb, "Senior full-stack engineer in Missouri.", 26, 44, 208)
    tag2, _ = text_path(body, kb, "I build whole products and finish them.", 26, 44, 242)

    kinds = [("terminal", "Terminal"), ("web", "Web"), ("desktop", "Desktop"),
             ("extension", "Extensions"), ("game", "Games")]
    centers = [714, 816, 918, 1020, 1122]
    groups = []
    for i, ((kind, label), cx) in enumerate(zip(kinds, centers)):
        lab_d, adv = text_path(body, kb, label, 17, 0, 0)
        # centre the caption under the glyph
        lab_d, _ = text_path(body, kb, label, 17, cx - adv / 2, 199)
        groups.append(
            f'<g class="s" style="animation-delay:{0.12 + i*0.14:.2f}s">'
            f'{surface(kind, cx, t)}'
            f'<path d="{lab_d}" fill="{t["muted"]}"/>'
            f'</g>'
        )

    css = (
        ".s{opacity:0;transform:translateY(8px);animation:in .55s cubic-bezier(.2,.7,.2,1) forwards}"
        "@keyframes in{to{opacity:1;transform:none}}"
        "@media (prefers-reduced-motion:reduce){.s{animation:none;opacity:1;transform:none}}"
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-labelledby="t d">'
        f'<title id="t">Isaiah</title>'
        f'<desc id="d">Senior full-stack engineer in Missouri. I build whole products and finish them. '
        f'Ships to the terminal, the web, the desktop, browser extensions, and games.</desc>'
        f'<style>{css}</style>'
        f'<path d="{name_d}" fill="{t["clay"]}"/>'
        f'<path d="{tag1}" fill="{t["ink"]}"/>'
        f'<path d="{tag2}" fill="{t["ink"]}"/>'
        f'<line x1="640" y1="84" x2="640" y2="208" stroke="{t["rule"]}" stroke-width="2"/>'
        + "".join(groups) +
        "</svg>"
    )
    with open(f"hero-{theme}.svg", "w") as f:
        f.write(svg)
    print(theme, len(svg), "bytes")


if __name__ == "__main__":
    if not os.path.exists(FONT):
        urllib.request.urlretrieve(FONT_URL, FONT)
    build("dark")
    build("light")
