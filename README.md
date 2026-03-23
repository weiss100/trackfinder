# TrackFinder

A DJ track search engine that searches multiple online music stores simultaneously and lets you compare prices, BPM, key, and other track metadata side by side.

## Supported Stores

- **Beatport** – Electronic music
- **Traxsource** – House, disco, and urban music
- **Juno Download** – UK-based electronic music
- **Bandcamp** – Independent artists
- **iTunes** – Mainstream music (via Apple API)

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
- **Data sources:** Web scraping (Beatport, Traxsource, Juno, Bandcamp) + iTunes Search API
