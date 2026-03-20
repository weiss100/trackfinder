const express = require('express');
const path = require('path');
const { searchAll, stores } = require('./stores');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Search API endpoint
app.get('/api/search', async (req, res) => {
  const { q, stores: storeFilter } = req.query;

  if (!q || !q.trim()) {
    return res.json({ results: [], query: '' });
  }

  const query = q.trim();
  const selectedStores = storeFilter ? storeFilter.split(',') : null;

  try {
    const results = await searchAll(query, selectedStores);

    // Sort: results with prices first, then by store
    results.sort((a, b) => {
      if (a.priceValue && !b.priceValue) return -1;
      if (!a.priceValue && b.priceValue) return 1;
      if (a.priceValue && b.priceValue) return a.priceValue - b.priceValue;
      return 0;
    });

    res.json({ results, query, total: results.length });
  } catch (err) {
    console.error('Search error:', err);
    res.status(500).json({ error: 'Search failed', message: err.message });
  }
});

// Available stores
app.get('/api/stores', (req, res) => {
  const storeList = Object.entries(stores).map(([key, store]) => ({
    key,
    name: store.STORE_NAME,
  }));
  res.json(storeList);
});

app.listen(PORT, () => {
  console.log(`TrackFinder running at http://localhost:${PORT}`);
});
