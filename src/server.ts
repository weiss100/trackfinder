import express, { Request, Response } from 'express';
import path from 'path';
import { searchAll, stores } from './stores';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, '..', 'public')));
app.use(express.json());

app.get('/api/search', async (req: Request, res: Response) => {
  const q = req.query.q as string | undefined;
  const storeFilter = req.query.stores as string | undefined;

  if (!q || !q.trim()) {
    res.json({ results: [], query: '' });
    return;
  }

  const query = q.trim();
  const selectedStores = storeFilter ? storeFilter.split(',') : null;

  try {
    const results = await searchAll(query, selectedStores);

    results.sort((a, b) => {
      if (a.priceValue && !b.priceValue) return -1;
      if (!a.priceValue && b.priceValue) return 1;
      if (a.priceValue && b.priceValue) return a.priceValue - b.priceValue;
      return 0;
    });

    res.json({ results, query, total: results.length });
  } catch (err) {
    console.error('Search error:', err);
    res.status(500).json({ error: 'Search failed', message: (err as Error).message });
  }
});

app.get('/api/stores', (_req: Request, res: Response) => {
  const storeList = Object.entries(stores).map(([key, store]) => ({
    key,
    name: store.STORE_NAME,
  }));
  res.json(storeList);
});

app.listen(PORT, () => {
  console.log(`TrackFinder running at http://localhost:${PORT}`);
});
