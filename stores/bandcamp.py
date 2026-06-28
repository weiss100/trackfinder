# bandcamp.com/search sits behind a Fastly "Client Challenge" that runs a JS
# proof-of-work and only redirects to the real results once it is solved. A
# plain HTTP GET only ever sees the ~3 KB challenge shell (zero listings), so
# we drive headless Chrome via Playwright, which executes the challenge JS and
# lands on the results in ~3 s.
#
# Requires the `playwright` package plus a browser. We prefer a system Chrome
# (channel="chrome") because it clears the challenge most reliably, and fall
# back to the bundled Chromium (`playwright install chromium`). If neither
# Playwright nor a browser is available, search() degrades to [] like any other
# store failure.
from __future__ import annotations

import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from models import TrackResult

STORE_NAME = "Bandcamp"
_STORE_URL = "https://bandcamp.com"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# Time allowed for the Fastly challenge to solve itself and reveal results.
_CHALLENGE_TIMEOUT_MS = 25000


def _split_subhead(text: str) -> tuple[str, str]:
    """Pull (artist, album) out of a search subhead.

    Bandcamp formats it two ways:
        "by <artist>"                         -> standalone track
        "from <album> by <artist>"            -> track on a release
    """
    artist = album = ""
    by_match = re.search(r"\bby\s+(.+)", text, re.IGNORECASE)
    from_match = re.search(r"\bfrom\s+(.+?)(?:\s+by\s+|$)", text, re.IGNORECASE)
    if by_match:
        artist = by_match.group(1).strip()
    if from_match:
        album = from_match.group(1).strip()
    return artist, album


def fetch(query: str) -> str | None:
    """Render the search page through a real browser engine and return its HTML
    once the bot challenge has cleared, or None if that isn't possible."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Bandcamp disabled: playwright not installed (pip install playwright)")
        return None

    url = f"{_STORE_URL}/search?q={quote(query)}&item_type=t"
    with sync_playwright() as p:
        browser = None
        try:
            launch_args = ["--disable-blink-features=AutomationControlled"]
            try:
                browser = p.chromium.launch(headless=True, channel="chrome", args=launch_args)
            except Exception:
                # No system Chrome installed — fall back to bundled Chromium.
                browser = p.chromium.launch(headless=True, args=launch_args)

            ctx = browser.new_context(
                user_agent=_UA, locale="en-US",
                viewport={"width": 1280, "height": 900},
            )
            # Hide the headless automation flag the challenge scripts look for.
            ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # The challenge auto-navigates to the results; wait for a listing.
            page.wait_for_selector(".searchresult", timeout=_CHALLENGE_TIMEOUT_MS)
            return page.content()
        except Exception as e:
            print(f"Bandcamp fetch error: {e}")
            return None
        finally:
            if browser:
                browser.close()


def parse(html: str) -> list[TrackResult]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[TrackResult] = []

    for el in soup.select(".searchresult"):
        heading = el.select_one(".heading a")
        title = heading.get_text(strip=True) if heading else ""
        if not title:
            continue
        link = (heading.get("href") or "").split("?")[0] or None

        subhead = el.select_one(".subhead")
        subhead_text = " ".join(subhead.get_text(" ", strip=True).split()) if subhead else ""
        artist, album = _split_subhead(subhead_text)

        img_el = el.select_one(".art img")
        img = (img_el.get("src") or img_el.get("data-original")) if img_el else None

        results.append(TrackResult(
            title=title,
            artist=artist,
            label=album,
            genre="",
            bpm=None,
            key=None,
            duration="",
            # Search results don't carry a price; it lives on the track page.
            price="Name Your Price",
            price_value=None,
            currency="USD",
            artwork=img,
            url=link or _STORE_URL,
            store=STORE_NAME,
            store_icon="bandcamp",
            release_date="",
        ))

    return results[:25]


def search(query: str) -> list[TrackResult]:
    html = fetch(query)
    if not html:
        return []
    try:
        return parse(html)
    except Exception as e:
        print(f"Bandcamp parse error: {e}")
        return []
