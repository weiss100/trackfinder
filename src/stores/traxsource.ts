import fetch from 'node-fetch';
import * as cheerio from 'cheerio';
import { TrackResult, StoreAdapter } from '../types';

export const STORE_NAME = 'Traxsource';
const STORE_URL = 'https://www.traxsource.com';

function parsePrice(str: string): number | null {
  const match = str.match(/[\d.]+/);
  return match ? parseFloat(match[0]) : null;
}

export async function search(query: string): Promise<TrackResult[]> {
  try {
    const url = `${STORE_URL}/search?term=${encodeURIComponent(query)}`;
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
    const results: TrackResult[] = [];

    $('.trk-row, .search-trk-row').each((_, el) => {
      const $el = $(el);
      const title = $el.find('.title a, .trk-name a').first().text().trim();
      const artist = $el.find('.artists a, .trk-artists a').map((_, a) => $(a).text().trim()).get().join(', ');
      const label = $el.find('.label a, .trk-label a').first().text().trim();
      const genre = $el.find('.genre a, .trk-genre a').first().text().trim();
      const priceText = $el.find('.add-cart .price, .buy-btn, .trk-price').first().text().trim();
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
          price: priceText || '$1.49',
          priceValue: parsePrice(priceText || '$1.49'),
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
    console.error(`Traxsource search error: ${(err as Error).message}`);
    return [];
  }
}

export default { search, STORE_NAME } satisfies StoreAdapter;
