import beatport from './beatport';
import traxsource from './traxsource';
import juno from './juno';
import bandcamp from './bandcamp';
import itunes from './itunes';
import { TrackResult, StoreAdapter } from '../types';

export const stores: Record<string, StoreAdapter> = {
  beatport,
  traxsource,
  juno,
  bandcamp,
  itunes,
};

export async function searchAll(query: string, selectedStores: string[] | null = null): Promise<TrackResult[]> {
  const storeKeys = selectedStores || Object.keys(stores);
  const searches = storeKeys
    .filter(key => stores[key])
    .map(async key => {
      try {
        return await stores[key].search(query);
      } catch (err) {
        console.error(`Error searching ${key}: ${(err as Error).message}`);
        return [];
      }
    });

  const allResults = await Promise.all(searches);
  return allResults.flat();
}
