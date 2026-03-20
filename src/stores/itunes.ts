import fetch from 'node-fetch';
import { TrackResult, StoreAdapter } from '../types';

export const STORE_NAME = 'iTunes / Apple Music';

interface ITunesTrack {
  trackName: string;
  artistName: string;
  collectionName?: string;
  primaryGenreName?: string;
  trackTimeMillis?: number;
  trackPrice?: number;
  currency?: string;
  artworkUrl100?: string;
  trackViewUrl: string;
  releaseDate?: string;
}

interface ITunesResponse {
  results: ITunesTrack[];
}

function formatDuration(ms: number): string {
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export async function search(query: string): Promise<TrackResult[]> {
  try {
    const url = `https://itunes.apple.com/search?term=${encodeURIComponent(query)}&media=music&entity=song&limit=25`;
    const res = await fetch(url, { timeout: 10000 });
    if (!res.ok) return [];

    const data = (await res.json()) as ITunesResponse;
    return (data.results || []).map((track): TrackResult => ({
      title: track.trackName,
      artist: track.artistName,
      label: track.collectionName || '',
      genre: track.primaryGenreName || '',
      bpm: null,
      key: null,
      duration: track.trackTimeMillis ? formatDuration(track.trackTimeMillis) : '',
      price: track.trackPrice ? `${track.trackPrice} ${track.currency}` : 'N/A',
      priceValue: track.trackPrice || null,
      currency: track.currency || 'USD',
      artwork: track.artworkUrl100 ? track.artworkUrl100.replace('100x100', '200x200') : null,
      url: track.trackViewUrl,
      store: STORE_NAME,
      storeIcon: 'apple',
      releaseDate: track.releaseDate ? track.releaseDate.split('T')[0] : '',
    }));
  } catch (err) {
    console.error(`iTunes search error: ${(err as Error).message}`);
    return [];
  }
}

export default { search, STORE_NAME } satisfies StoreAdapter;
