#!/usr/bin/env python3
"""Generate a compact SVG card from public AniList user statistics."""
import json
import os
import sys
import urllib.request
import urllib.error
from xml.sax.saxutils import escape

USERNAME = os.environ.get("ANILIST_USERNAME", "BocchiChord")
API_URL = "https://graphql.anilist.co"

QUERY = """
query ($name: String) {
  User(name: $name) {
    name
    statistics {
      anime {
        count
        episodesWatched
        minutesWatched
        meanScore
        genres(limit: 5, sort: COUNT_DESC) {
          genre
          count
        }
      }
      manga {
        count
        chaptersRead
        volumesRead
        meanScore
        genres(limit: 5, sort: COUNT_DESC) {
          genre
          count
        }
      }
    }
  }
}
"""

def fetch_stats():
    payload = json.dumps({
        "query": QUERY,
        "variables": {"name": USERNAME}
    }).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "BocchiChord-AniList-Stats/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not reach AniList API: {exc}") from exc

    if data.get("errors"):
        messages = "; ".join(error.get("message", "Unknown GraphQL error")
                             for error in data["errors"])
        raise RuntimeError(f"AniList API returned an error: {messages}")

    user = (data.get("data") or {}).get("User")
    if not user:
        raise RuntimeError(
            f"Could not find public AniList user '{USERNAME}'. "
            "Check ANILIST_USERNAME in the workflow."
        )
    return user

def fmt_number(value):
    return f"{int(value or 0):,}"

def fmt_score(value):
    return f"{float(value or 0):.1f}/100"

def fmt_days(minutes):
    return f"{(minutes or 0) / 1440:.1f} days"

def genre_line(genres):
    names = [item.get("genre", "") for item in (genres or []) if item.get("genre")]
    return "  ·  ".join(names) if names else "No genre data yet"

def text(x, y, content, size=14, fill="#eeeaf7", weight="400", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="Inter,Segoe UI,Arial,sans-serif" '
            f'font-size="{size}" fill="{fill}" font-weight="{weight}" {extra}>'
            f'{escape(str(content))}</text>')

def generate_svg(user):
    anime = user["statistics"]["anime"]
    manga = user["statistics"]["manga"]
    width, height = 660, 260
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="AniList statistics for {escape(user["name"])}">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#171323"/><stop offset="55%" stop-color="#211a35"/><stop offset="100%" stop-color="#152538"/></linearGradient>',
        '<linearGradient id="pink" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#ff79bd"/><stop offset="100%" stop-color="#bda0ff"/></linearGradient></defs>',
        '<rect width="660" height="260" rx="18" fill="url(#bg)"/>',
        '<rect x="0" y="0" width="660" height="5" rx="2" fill="url(#pink)"/>',
        '<circle cx="622" cy="34" r="54" fill="#9e7bff" opacity=".08"/>',
        '<circle cx="605" cy="31" r="28" fill="#ff79bd" opacity=".08"/>',
        text(24, 34, "BocchiChord", 19, "#fff2fb", "700"),
        text(24, 54, "ANILIST STATS", 10, "#c9b8e8", "600", 'letter-spacing="2"'),
        '<line x1="24" y1="68" x2="636" y2="68" stroke="#ffffff" stroke-opacity=".13"/>',
        '<rect x="24" y="82" width="296" height="112" rx="12" fill="#ffffff" fill-opacity=".055" stroke="#ff91c8" stroke-opacity=".32"/>',
        '<rect x="340" y="82" width="296" height="112" rx="12" fill="#ffffff" fill-opacity=".055" stroke="#a997ff" stroke-opacity=".32"/>',
        text(40, 105, "ANIME", 12, "#ff9dcc", "700", 'letter-spacing="1.5"'),
        text(356, 105, "MANGA", 12, "#bdaaff", "700", 'letter-spacing="1.5"'),
        text(40, 133, fmt_number(anime.get("count")), 24, "#ffffff", "700"),
        text(40, 149, "titles", 10, "#c9c2d8"),
        text(164, 133, fmt_number(anime.get("episodesWatched")), 20, "#ffffff", "700"),
        text(164, 149, "episodes", 10, "#c9c2d8"),
        text(40, 177, fmt_days(anime.get("minutesWatched")), 12, "#ffd1e8", "600"),
        text(164, 177, f'Mean score {fmt_score(anime.get("meanScore"))}', 11, "#e7dfff", "600"),
        text(356, 133, fmt_number(manga.get("count")), 24, "#ffffff", "700"),
        text(356, 149, "titles", 10, "#c9c2d8"),
        text(480, 133, fmt_number(manga.get("chaptersRead")), 20, "#ffffff", "700"),
        text(480, 149, "chapters", 10, "#c9c2d8"),
        text(356, 177, f'Volumes read: {fmt_number(manga.get("volumesRead"))}', 11, "#e4dcff", "600"),
        text(480, 177, f'Mean score {fmt_score(manga.get("meanScore"))}', 11, "#e4dcff", "600"),
        text(24, 217, "TOP ANIME GENRES", 9, "#ff9dcc", "700", 'letter-spacing="1.2"'),
        text(24, 236, genre_line(anime.get("genres")), 11, "#f0eaf9"),
        text(24, 253, f'@{user["name"]}  ·  refreshed automatically', 9, "#a99dbd"),
        '</svg>',
    ]
    return "\n".join(elements)

def main():
    os.makedirs("site", exist_ok=True)
    user = fetch_stats()
    svg = generate_svg(user)
    with open("site/stats.svg", "w", encoding="utf-8") as file:
        file.write(svg)
    with open("site/index.html", "w", encoding="utf-8") as file:
        file.write("""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BocchiChord — AniList Stats</title>
  <style>
    :root { color-scheme: dark; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center;
      background: #100e18; color: #eeeaf7; font: 16px system-ui, sans-serif; }
    main { width: min(660px, calc(100% - 32px)); text-align: center; }
    img { display: block; width: 100%; height: auto; }
    a { color: #ff9dcc; }
    p { color: #b9adc9; font-size: 13px; }
  </style>
</head>
<body><main>
  <img src="./stats.svg" alt="Automatically updated AniList statistics for BocchiChord">
  <p>Generated from public AniList data. <a href="https://anilist.co/user/BocchiChord/">View AniList profile</a></p>
</main></body></html>
""")
    print("Generated site/stats.svg and site/index.html successfully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
