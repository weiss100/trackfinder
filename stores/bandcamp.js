const fetch = require('node-fetch');
const cheerio = require('cheerio');

const STORE_NAME = 'Bandcamp';
const STORE_URL = 'https://bandcamp.com';

async function search(query) {
  try {
    const url = `https://bandcamp.com/search?q=${encodeURIComponent(query)}&item_type=t`;
    const res = await fetch(url, {
      timeout: 10000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
      },
    });

    if (!res.ok) return [];

    const html = await res.text();
    const $ = cheerio.load(html);
    const results = [];

    $('.searchresult.track, .result-items .searchresult').each((_, el) => {
      const $el = $(el);
      const heading = $el.find('.heading a').first();
      const title = heading.text().trim();
      const link = heading.attr('href');
      const subhead = $el.find('.subhead').first().text().trim();
      const img = $el.find('img.art, .art img').first().attr('src');

      // Subhead format: "from <album> by <artist>"
      let artist = '';
      let album = '';
      const byMatch = subhead.match(/by\s+(.+)/i);
      const fromMatch = subhead.match(/from\s+(.+?)(?:\s+by\s+|$)/i);
      if (byMatch) artist = byMatch[1].trim();
      if (fromMatch) album = fromMatch[1].trim();

      const genre = $el.find('.genre').first().text().replace('genre:', '').trim();
      const priceText = $el.find('.price, .buy-now').first().text().trim();

      if (title) {
        results.push({
          title,
          artist,
          label: album,
          genre,
          bpm: null,
          key: null,
          duration: '',
          price: priceText || 'Name Your Price',
          priceValue: parsePrice(priceText),
          currency: 'USD',
          artwork: img || null,
          url: link || `${STORE_URL}/search?q=${encodeURIComponent(query)}&item_type=t`,
          store: STORE_NAME,
          storeIcon: 'bandcamp',
          releaseDate: '',
        });
      }
    });

    return results.slice(0, 25);
  } catch (err) {
    console.error(`Bandcamp search error: ${err.message}`);
    return [];
  }
}

function parsePrice(str) {
  if (!str) return null;
  const match = str.match(/[\d.]+/);
  return match ? parseFloat(match[0]) : null;
}

module.exports = { search, STORE_NAME };
