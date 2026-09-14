"""Render assets/activity-dark.svg and assets/activity-light.svg.

Contributions for the last 31 days, fetched from GitHub's GraphQL API and drawn
in the README's palette. Standard library only. On any fetch failure the script
exits non-zero without touching the existing SVGs, so a bad run never publishes
a broken card.

Env: GITHUB_TOKEN (Actions' default token is enough for public contributions),
     USERNAME (defaults to ijshd7).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = os.environ.get("USERNAME", "ijshd7")
DAYS = 31
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

TOKENS = {
    "dark":  dict(canvas="#0d1117", ink="#e6edf3", muted="#8b949e", moss="#86c06c", clay="#e8a26a", rule="#30363d"),
    "light": dict(canvas="#ffffff", ink="#1f2328", muted="#57606a", moss="#3f7a2f", clay="#b3561f", rule="#d0d7de"),
}
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"  # same stack the stats cards use

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_days():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set")
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=DAYS + 7)  # a little slack; trimmed below
    body = json.dumps({
        "query": QUERY,
        "variables": {"login": USERNAME, "from": start.isoformat(), "to": now.isoformat()},
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": f"{USERNAME}-readme-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors") or not data.get("data", {}).get("user"):
        sys.exit(f"GraphQL error: {data.get('errors')}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    return days[-DAYS:]


def render(days, theme):
    t = TOKENS[theme]
    W, H = 900, 220
    left, right, top, bottom = 52, 876, 62, 178
    counts = [d["contributionCount"] for d in days]
    total, peak = sum(counts), max(counts) if counts else 0
    ymax = max(peak, 1)
    n = len(days)
    step = (right - left) / max(n - 1, 1)

    def x(i):
        return left + i * step

    def y(v):
        return bottom - (v / ymax) * (bottom - top)

    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    line = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts)
    area = f"M{pts[0][0]:.1f} {bottom} L" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts) + f" L{pts[-1][0]:.1f} {bottom} Z"

    grid = ""
    for frac in (0, 0.5, 1):
        gy = y(ymax * frac)
        label = int(round(ymax * frac))
        grid += (f'<line x1="{left}" y1="{gy:.1f}" x2="{right}" y2="{gy:.1f}" stroke="{t["rule"]}" stroke-width="1"/>'
                 f'<text x="{left - 10}" y="{gy + 4:.1f}" text-anchor="end" font-size="11" fill="{t["muted"]}">{label}</text>')

    xlabels = ""
    for i in range(0, n, 6):
        d = datetime.strptime(days[i]["date"], "%Y-%m-%d")
        xlabels += f'<text x="{x(i):.1f}" y="{bottom + 22}" text-anchor="middle" font-size="11" fill="{t["muted"]}">{d.strftime("%b")} {d.day}</text>'

    dots = "".join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.5" fill="{t["moss"]}"/>'
                   for (px, py), c in zip(pts, counts) if c > 0)
    peak_mark = ""
    if peak > 0:
        i = counts.index(peak)
        px, py = pts[i]
        peak_mark = (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{t["clay"]}"/>'
                     f'<text x="{px:.1f}" y="{py - 10:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="{t["clay"]}">{peak}</text>')

    first = datetime.strptime(days[0]["date"], "%Y-%m-%d").strftime("%b %d")
    last = datetime.strptime(days[-1]["date"], "%Y-%m-%d").strftime("%b %d")
    peak_day = datetime.strptime(days[counts.index(peak)]["date"], "%Y-%m-%d").strftime("%B %d") if peak else None
    desc = f"{total} contributions from {first} to {last}" + (f", peaking at {peak} on {peak_day}." if peak else ".")

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-labelledby="t d" font-family="{FONT}">'
        f'<title id="t">Contributions over the last month</title><desc id="d">{desc}</desc>'
        f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>'
        f'<text x="24" y="34" font-size="18" font-weight="600" fill="{t["clay"]}">Contributions over the last month</text>'
        f'<text x="{right}" y="34" text-anchor="end" font-size="13" fill="{t["muted"]}">{total} in {n} days</text>'
        f'{grid}'
        f'<path d="{area}" fill="{t["moss"]}" fill-opacity="0.14"/>'
        f'<path d="{line}" fill="none" stroke="{t["moss"]}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'{dots}{peak_mark}{xlabels}'
        f'</svg>'
    )


def main():
    days = fetch_days()
    if not days:
        sys.exit("no contribution data returned")
    for theme in TOKENS:
        path = os.path.join(OUT_DIR, f"activity-{theme}.svg")
        with open(path, "w") as f:
            f.write(render(days, theme))
        print("wrote", path)


if __name__ == "__main__":
    main()
