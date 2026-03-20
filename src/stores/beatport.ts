import fetch from 'node-fetch';
import * as cheerio from 'cheerio';
import { TrackResult, StoreAdapter } from '../types';

export const STORE_NAME = 'Beatport';
const STORE_URL = 'https://www.beatport.com';

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function parsePrice(str: string): number | null {
  const match = str.match(/[\d.]+/);
  return match ? parseFloat(match[0]) : null;
}

function extractTracks(data: unknown, results: TrackResult[] = []): TrackResult[] {
  if (!data || typeof data !== 'object') return results;
  if (Array.isArray(data)) {
    for (const item of data) extractTracks(item, results);
    return results;
  }

  const obj = data as Record<string, unknown>;

  if (obj.name && (obj.artists || obj.artist) && (obj.slug || obj.id)) {
    const artists = obj.artists as Array<{ name?: string }> | undefined;
    const artist = obj.artist as { name?: string } | string | undefined;
    const artistNames = artists
      ? artists.map(a => a.name || String(a)).join(', ')
      : typeof artist === 'object' ? artist?.name || '' : String(artist || '');

    const label = obj.label as { name?: string } | undefined;
    const release = obj.release as { label?: { name?: string }; image?: { uri?: string } } | undefined;
    const genre = obj.genre as { name?: string } | undefined;
    const genres = obj.genres as Array<{ name?: string }> | undefined;
    const keyObj = obj.key as { name?: string } | string | undefined;
    const price = obj.price as { value?: number; currency?: string } | undefined;
    const image = obj.image as { uri?: string } | undefined;
    const dateObj = obj.date as { published?: string } | undefined;

    results.push({
      title: String(obj.name || obj.title || ''),
      artist: artistNames,
      label: label?.name || release?.label?.name || '',
      genre: genre?.name || (genres ? genres[0]?.name || '' : ''),
      bpm: obj.bpm ? String(obj.bpm) : null,
      key: typeof keyObj === 'object' ? keyObj?.name || null : keyObj || null,
      duration: typeof obj.length === 'number' ? formatDuration(obj.length) : '',
      price: price ? `$${(price.value! / 100).toFixed(2)}` : '$1.29',
      priceValue: price ? price.value! / 100 : 1.29,
      currency: price?.currency || 'USD',
      artwork: image?.uri || release?.image?.uri || null,
      url: obj.slug ? `${STORE_URL}/track/${obj.slug}/${obj.id}` : STORE_URL,
      store: STORE_NAME,
      storeIcon: 'beatport',
      releaseDate: dateObj?.published || String(obj.publish_date || ''),
    });
  } else {
    for (const val of Object.values(obj)) {
      if (typeof val === 'object' && val !== null && results.length < 25) {
        extractTracks(val, results);
      }
    }
  }

  return results;
}

export async function search(query: string): Promise<TrackResult[]> {
  try {
    const url = `${STORE_URL}/search?q=${encodeURIComponent(query)}`;
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

    // Try __NEXT_DATA__ first
    let pageData: unknown = null;
    $('script#__NEXT_DATA__').each((_, el) => {
      try {
        const parsed = JSON.parse($(el).html() || '');
        if (parsed?.props?.pageProps) {
          pageData = parsed.props.pageProps;
        }
      } catch { /* ignore */ }
    });

    // Try other JSON scripts
    if (!pageData) {
      $('script[type="application/json"]').each((_, el) => {
        try {
          const text = $(el).html();
          if (text && text.includes('tracks')) {
            pageData = JSON.parse(text);
          }
        } catch { /* ignore */ }
      });
    }

    if (pageData) {
      return extractTracks(pageData).slice(0, 25);
    }

    // Fallback: parse HTML
    $('[data-testid="track-row"], .track-row, .bucket-item').each((_, el) => {
      const $el = $(el);
      const title = $el.find('.track-title, [data-testid="track-title"]').first().text().trim();
      const artist = $el.find('.track-artists, [data-testid="track-artists"]').first().text().trim();
      const priceText = $el.find('.add-to-cart-btn, .price, [data-testid="price"]').first().text().trim();
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
          price: priceText || '$1.29',
          priceValue: parsePrice(priceText || '$1.29'),
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
    console.error(`Beatport search error: ${(err as Error).message}`);
    return [];
  }
}

export default { search, STORE_NAME } satisfies StoreAdapter;
