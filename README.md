# TrackFinder

A DJ track search engine that searches multiple online music stores simultaneously and lets you compare prices, BPM, key, and other track metadata side by side.

## Supported Stores

- **Beatport** – Electronic music
- **Traxsource** – House, disco, and urban music
- **Bandcamp** – Independent artists
- **Amazon Music** – Mainstream music

## Features

- Search by track name, artist, or label
- Filter results by store
- Results sorted by price (lowest first)
- Track metadata: BPM, key, genre, duration, artwork, release date
- Direct links to purchase on each store

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# or
.venv/bin/pip install -r requirements.txt       # Linux/macOS
```

The Bandcamp scraper drives a headless browser (Playwright) to clear Bandcamp's
bot challenge. Install a browser once after the pip install:

```bash
.venv/Scripts/python -m playwright install chromium   # Windows
# or
.venv/bin/python -m playwright install chromium       # Linux/macOS
```

A system Chrome is used automatically if present; otherwise this bundled
Chromium is the fallback. Without a browser, Bandcamp simply returns no results
and the other stores work as usual.

## Usage

**Windows:**
```
start.bat
```

**Manual:**
```bash
.venv/Scripts/python server.py   # Windows
.venv/bin/python server.py       # Linux/macOS
```

Open http://localhost:3000 in your browser.

## Tech Stack

- **Backend:** Python, Flask, BeautifulSoup, Requests
- **Frontend:** Vanilla HTML/CSS/JavaScript
- **Data sources:** Web scraping (Beatport, Traxsource, Bandcamp, Amazon Music)
