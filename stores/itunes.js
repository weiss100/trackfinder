const fetch = require('node-fetch');

const STORE_NAME = 'iTunes / Apple Music';
const STORE_URL = 'https://music.apple.com';

async function search(query) {
  try {
    const url = `https://itunes.apple.com/search?term=${encodeURIComponent(query)}&media=music&entity=song&limit=25`;
    const res = await fetch(url, { timeout: 10000 });
    if (!res.ok) return [];

    const data = await res.json();
    return (data.results || []).map(track => ({
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
    console.error(`iTunes search error: ${err.message}`);
    return [];
  }
}

function formatDuration(ms) {
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

module.exports = { search, STORE_NAME };
