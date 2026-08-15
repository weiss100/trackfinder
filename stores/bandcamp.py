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

import html as _htmllib
import json
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
# The search page carries no price; we render each track page to read it, but
# only for the first few hits so a search doesn't fan out into 25 renders.
_PRICE_RESOLVE_LIMIT = 3


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


def _launch(p):
    """Prefer a system Chrome (clears the challenge most reliably); fall back to
    the bundled Chromium."""
    launch_args = ["--disable-blink-features=AutomationControlled"]
    try:
        return p.chromium.launch(headless=True, channel="chrome", args=launch_args)
    except Exception:
        return p.chromium.launch(headless=True, args=launch_args)


def _new_page(browser):
    ctx = browser.new_context(
        user_agent=_UA, locale="en-US",
        viewport={"width": 1280, "height": 900},
    )
    # Hide the headless automation flag the challenge scripts look for.
    ctx.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    )
    return ctx.new_page()


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
            browser = _launch(p)
            page = _new_page(browser)
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
            price="",
            price_value=None,
            currency="USD",
            artwork=img,
            url=link or _STORE_URL,
            store=STORE_NAME,
            store_icon="bandcamp",
            release_date="",
        ))

    return results[:25]


def _parse_track_price(page_html: str) -> tuple[str, float | None, str] | None:
    """Pull (display, value, currency) out of a rendered track page.

    Bandcamp stores the price in a ``data-tralbum`` JSON blob and the band's
    currency in a separate ``data-band-currency`` attribute. A track is either a
    fixed price (``is_set_price``) or name-your-price with an optional minimum.
    Returns None if the blob is absent (markup changed / not a track page).
    """
    m = re.search(r'data-tralbum="([^"]*)"', page_html)
    if not m:
        return None
    try:
        blob = json.loads(_htmllib.unescape(m.group(1)))
    except (ValueError, TypeError):
        return None

    current = blob.get("current") or {}
    cur_match = re.search(r'data-band-currency="([A-Z]{3})"', page_html)
    currency = cur_match.group(1) if cur_match else "USD"

    set_price = current.get("set_price")
    minimum = current.get("minimum_price")
    if current.get("is_set_price") and isinstance(set_price, (int, float)) and set_price > 0:
        return f"{set_price:.2f} {currency}", float(set_price), currency
    if isinstance(minimum, (int, float)) and minimum > 0:
        # Name-your-price with a floor — show the minimum as the comparable price.
        return f"ab {minimum:.2f} {currency}", float(minimum), currency
    return "Name Your Price", None, currency


def fetch_prices(urls: list[str]) -> dict[str, tuple[str, float | None, str]]:
    """Render each track page and read its real price, returned as
    {url: (display, value, currency)}.

    The search page carries no price, so callers look these up out-of-band (see
    the /api/bandcamp-prices endpoint) to keep the search itself fast. Bounded to
    _PRICE_RESOLVE_LIMIT so a request can't fan out into many renders.
    """
    targets = [u for u in urls if u and u != _STORE_URL][:_PRICE_RESOLVE_LIMIT]
    if not targets:
        return {}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {}

    prices: dict[str, tuple[str, float | None, str]] = {}
    with sync_playwright() as p:
        browser = None
        try:
            browser = _launch(p)
            page = _new_page(browser)
            for url in targets:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_selector("script[data-tralbum]", state="attached", timeout=15000)
                    parsed = _parse_track_price(page.content())
                except Exception as e:
                    print(f"Bandcamp price lookup failed for {url}: {e}")
                    continue
                if parsed:
                    prices[url] = parsed
        finally:
            if browser:
                browser.close()
    return prices


def search(query: str) -> list[TrackResult]:
    # Prices are resolved separately (fetch_prices) so the search stays fast.
    html = fetch(query)
    if not html:
        return []
    try:
        return parse(html)
    except Exception as e:
        print(f"Bandcamp parse error: {e}")
        return []
