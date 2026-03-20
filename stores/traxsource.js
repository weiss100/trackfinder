const fetch = require('node-fetch');
const cheerio = require('cheerio');

const STORE_NAME = 'Traxsource';
const STORE_URL = 'https://www.traxsource.com';

async function search(query) {
  try {
    const url = `https://www.traxsource.com/search?term=${encodeURIComponent(query)}`;
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

    $('.trk-row, .search-trk-row').each((_, el) => {
      const $el = $(el);
      const title = $el.find('.title a, .trk-name a').first().text().trim();
      const artist = $el.find('.artists a, .trk-artists a').map((_, a) => $(a).text().trim()).get().join(', ');
      const label = $el.find('.label a, .trk-label a').first().text().trim();
      const genre = $el.find('.genre a, .trk-genre a').first().text().trim();
      const price = $el.find('.add-cart .price, .buy-btn, .trk-price').first().text().trim();
      const link = $el.find('.title a, .trk-name a').first().attr('href');
      const img = $el.find('img.lazy, img.trk-art').first().attr('data-src') || $el.find('img').first().attr('src');

      if (title) {
        results.push({
          title,
          artist,
          label,
          genre,
          bpm: $el.find('.bpm, .trk-bpm').first().text().trim() || null,
          key: $el.find('.key, .trk-key').first().text().trim() || null,
          duration: $el.find('.duration, .trk-duration').first().text().trim(),
          price: price || '$1.49',
          priceValue: parsePrice(price || '$1.49'),
          currency: 'USD',
          artwork: img || null,
          url: link ? (link.startsWith('http') ? link : `${STORE_URL}${link}`) : `${STORE_URL}/search?term=${encodeURIComponent(query)}`,
          store: STORE_NAME,
          storeIcon: 'traxsource',
          releaseDate: '',
        });
      }
    });

    return results.slice(0, 25);
  } catch (err) {
    console.error(`Traxsource search error: ${err.message}`);
    return [];
  }
}

function parsePrice(str) {
  const match = str.match(/[\d.]+/);
  return match ? parseFloat(match[0]) : null;
}

module.exports = { search, STORE_NAME };
