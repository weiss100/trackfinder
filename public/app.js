const searchForm = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const resultsEl = document.getElementById('results');
const statusEl = document.getElementById('status');
const emptyState = document.getElementById('emptyState');
const storeFilters = document.getElementById('storeFilters');

let activeStores = ['all'];

// Store filter handling
storeFilters.addEventListener('click', (e) => {
  const chip = e.target.closest('.store-chip');
  if (!chip) return;

  const store = chip.dataset.store;

  if (store === 'all') {
    activeStores = ['all'];
    storeFilters.querySelectorAll('.store-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
  } else {
    // Remove 'all' if selecting specific store
    const allChip = storeFilters.querySelector('[data-store="all"]');
    allChip.classList.remove('active');
    activeStores = activeStores.filter(s => s !== 'all');

    chip.classList.toggle('active');
    if (chip.classList.contains('active')) {
      activeStores.push(store);
    } else {
      activeStores = activeStores.filter(s => s !== store);
    }

    // If none selected, select all
    if (activeStores.length === 0) {
      activeStores = ['all'];
      allChip.classList.add('active');
    }
  }
});

// Search
searchForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = searchInput.value.trim();
  if (!query) return;

  await performSearch(query);
});

async function performSearch(query) {
  searchBtn.disabled = true;
  emptyState.classList.add('hidden');
  resultsEl.innerHTML = '';
  statusEl.classList.remove('hidden');
  statusEl.innerHTML = '<span class="spinner"></span>Suche in allen Stores...';

  try {
    const storeParam = activeStores.includes('all') ? '' : `&stores=${activeStores.join(',')}`;
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}${storeParam}`);
    const data = await res.json();

    statusEl.classList.add('hidden');

    if (data.results && data.results.length > 0) {
      renderResults(data.results, query);
    } else {
      resultsEl.innerHTML = `
        <div class="no-results">
          <p>Keine Ergebnisse für "<strong>${escapeHtml(query)}</strong>"</p>
          <p style="font-size:13px;margin-top:8px;">Versuche einen anderen Suchbegriff</p>
        </div>
      `;
    }
  } catch (err) {
    statusEl.classList.remove('hidden');
    statusEl.innerHTML = 'Fehler bei der Suche. Bitte nochmal versuchen.';
    console.error('Search error:', err);
  } finally {
    searchBtn.disabled = false;
  }
}

function renderResults(results, query) {
  const header = document.createElement('div');
  header.className = 'results-header';
  header.innerHTML = `
    <span>${results.length} Ergebnis${results.length !== 1 ? 'se' : ''} für "${escapeHtml(query)}"</span>
    <span>Sortiert nach Preis</span>
  `;
  resultsEl.appendChild(header);

  results.forEach(track => {
    const card = document.createElement('a');
    card.className = 'result-card';
    card.href = track.url;
    card.target = '_blank';
    card.rel = 'noopener noreferrer';

    const storeClass = `store-${track.storeIcon || track.store.toLowerCase().replace(/\s+/g, '')}`;

    const metaTags = [];
    if (track.genre) metaTags.push(track.genre);
    if (track.bpm) metaTags.push(`${track.bpm} BPM`);
    if (track.key) metaTags.push(track.key);
    if (track.duration) metaTags.push(track.duration);
    if (track.label) metaTags.push(track.label);

    card.innerHTML = `
      <div class="result-artwork">
        ${track.artwork
          ? `<img src="${escapeHtml(track.artwork)}" alt="" loading="lazy" onerror="this.parentNode.innerHTML='<span class=no-art>♪</span>'">`
          : '<span class="no-art">♪</span>'
        }
      </div>
      <div class="result-info">
        <div class="result-title">${escapeHtml(track.title)}</div>
        <div class="result-artist">${escapeHtml(track.artist)}</div>
        <div class="result-meta">
          ${metaTags.map(t => `<span class="result-tag">${escapeHtml(t)}</span>`).join('')}
        </div>
      </div>
      <div class="result-right">
        <div class="result-price">${escapeHtml(track.price)}</div>
        <span class="result-store ${storeClass}">${escapeHtml(track.store)}</span>
      </div>
    `;

    resultsEl.appendChild(card);
  });
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
