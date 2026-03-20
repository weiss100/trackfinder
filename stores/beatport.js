const fetch = require('node-fetch');
const cheerio = require('cheerio');

const STORE_NAME = 'Beatport';
const STORE_URL = 'https://www.beatport.com';

async function search(query) {
  try {
    const url = `https://www.beatport.com/search?q=${encodeURIComponent(query)}`;
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

    // Beatport embeds data in JSON-LD or in Next.js data scripts
    // Try to extract from the page structure
    const scriptTags = $('script[type="application/json"]');
    let pageData = null;

    scriptTags.each((_, el) => {
      try {
        const text = $(el).html();
        if (text && text.includes('tracks')) {
          const parsed = JSON.parse(text);
          if (parsed && typeof parsed === 'object') {
            pageData = parsed;
          }
        }
      } catch (e) { /* ignore parse errors */ }
    });

    // Also try __NEXT_DATA__
    $('script#__NEXT_DATA__').each((_, el) => {
      try {
        const parsed = JSON.parse($(el).html());
        if (parsed?.props?.pageProps) {
          pageData = parsed.props.pageProps;
        }
      } catch (e) { /* ignore */ }
    });

    if (pageData) {
      const tracks = extractTracks(pageData);
      return tracks.slice(0, 25);
    }

    // Fallback: parse HTML structure
    $('[data-testid="track-row"], .track-row, .bucket-item').each((_, el) => {
      const $el = $(el);
      const title = $el.find('.track-title, [data-testid="track-title"]').first().text().trim();
      const artist = $el.find('.track-artists, [data-testid="track-artists"]').first().text().trim();
      const price = $el.find('.add-to-cart-btn, .price, [data-testid="price"]').first().text().trim();
      const link = $el.find('a[href*="/track/"]').first().attr('href');

      if (title) {
        results.push({
          title,
          artist,
          label: $el.find('.track-label, [data-testid="track-label"]').first().text().trim(),
          genre: $el.find('.track-genre, [data-testid="track-genre"]').first().text().trim(),
          bpm: $el.find('.track-bpm, [data-testid="track-bpm"]').first().text().trim() || null,
          key: $el.find('.track-key, [data-testid="track-key"]').first().text().trim() || null,
          duration: $el.find('.track-duration, [data-testid="track-duration"]').first().text().trim(),
          price: price || '$1.29',
          priceValue: parsePrice(price || '$1.29'),
          currency: 'USD',
          artwork: $el.find('img').first().attr('src') || null,
          url: link ? `${STORE_URL}${link}` : `${STORE_URL}/search?q=${encodeURIComponent(query)}`,
          store: STORE_NAME,
          storeIcon: 'beatport',
          releaseDate: '',
        });
      }
    });

    return results;
  } catch (err) {
    console.error(`Beatport search error: ${err.message}`);
    return [];
  }
}

function extractTracks(data, results = []) {
  if (!data || typeof data !== 'object') return results;
  if (Array.isArray(data)) {
    for (const item of data) extractTracks(item, results);
    return results;
  }

  // Look for track-like objects
  if (data.name && (data.artists || data.artist) && (data.slug || data.id)) {
    const artistNames = data.artists
      ? data.artists.map(a => a.name || a).join(', ')
      : data.artist?.name || data.artist || '';

    results.push({
      title: data.name || data.title || '',
      artist: artistNames,
      label: data.label?.name || data.release?.label?.name || '',
      genre: data.genre?.name || (data.genres ? data.genres[0]?.name : '') || '',
      bpm: data.bpm || null,
      key: data.key?.name || data.key || null,
      duration: data.length ? formatDuration(data.length) : '',
      price: data.price ? `$${(data.price.value / 100).toFixed(2)}` : '$1.29',
      priceValue: data.price ? data.price.value / 100 : 1.29,
      currency: data.price?.currency || 'USD',
      artwork: data.image?.uri || data.release?.image?.uri || null,
      url: data.slug ? `${STORE_URL}/track/${data.slug}/${data.id}` : STORE_URL,
      store: STORE_NAME,
      storeIcon: 'beatport',
      releaseDate: data.date?.published || data.publish_date || '',
    });
  } else {
    // Recurse into object values
    for (const val of Object.values(data)) {
      if (typeof val === 'object' && val !== null && results.length < 25) {
        extractTracks(val, results);
      }
    }
  }

  return results;
}

function formatDuration(seconds) {
  if (!seconds) return '';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function parsePrice(str) {
  const match = str.match(/[\d.]+/);
  return match ? parseFloat(match[0]) : null;
}

module.exports = { search, STORE_NAME };
