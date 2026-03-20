const fetch = require('node-fetch');
const cheerio = require('cheerio');

const STORE_NAME = 'Juno Download';
const STORE_URL = 'https://www.junodownload.com';

async function search(query) {
  try {
    const url = `https://www.junodownload.com/search/?q%5Ball%5D%5B%5D=${encodeURIComponent(query)}&solrorder=relevancy`;
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

    $('.product-tracklist .product-tracklist-track, .jd-listing-item, .product').each((_, el) => {
      const $el = $(el);
      const title = $el.find('.product-tracklist-track-title a, .juno-title a, .product-title a').first().text().trim();
      const artist = $el.find('.product-tracklist-track-artists a, .juno-artist a, .product-artist a').map((_, a) => $(a).text().trim()).get().join(', ');
      const label = $el.find('.product-label a, .juno-label a').first().text().trim();
      const genre = $el.find('.product-genre a, .juno-genre a').first().text().trim();
      const price = $el.find('.product-buy .price, .buy-btn-price, .product-price').first().text().trim();
      const link = $el.find('.product-tracklist-track-title a, .juno-title a, .product-title a').first().attr('href');
      const img = $el.find('img').first().attr('data-src') || $el.find('img').first().attr('src');

      if (title) {
        results.push({
          title,
          artist,
          label,
          genre,
          bpm: null,
          key: null,
          duration: '',
          price: price || '£1.49',
          priceValue: parsePrice(price || '£1.49'),
          currency: 'GBP',
          artwork: img || null,
          url: link ? (link.startsWith('http') ? link : `${STORE_URL}${link}`) : `${STORE_URL}/search/?q%5Ball%5D%5B%5D=${encodeURIComponent(query)}`,
          store: STORE_NAME,
          storeIcon: 'juno',
          releaseDate: '',
        });
      }
    });

    return results.slice(0, 25);
  } catch (err) {
    console.error(`Juno Download search error: ${err.message}`);
    return [];
  }
}

function parsePrice(str) {
  const match = str.match(/[\d.]+/);
  return match ? parseFloat(match[0]) : null;
}

module.exports = { search, STORE_NAME };
