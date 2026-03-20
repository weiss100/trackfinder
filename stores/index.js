const beatport = require('./beatport');
const traxsource = require('./traxsource');
const juno = require('./juno');
const bandcamp = require('./bandcamp');
const itunes = require('./itunes');

const stores = {
  beatport,
  traxsource,
  juno,
  bandcamp,
  itunes,
};

/**
 * Search all stores in parallel
 */
async function searchAll(query, selectedStores = null) {
  const storeKeys = selectedStores || Object.keys(stores);
  const searches = storeKeys
    .filter(key => stores[key])
    .map(async key => {
      try {
        const results = await stores[key].search(query);
        return results;
      } catch (err) {
        console.error(`Error searching ${key}: ${err.message}`);
        return [];
      }
    });

  const allResults = await Promise.all(searches);
  return allResults.flat();
}

module.exports = { stores, searchAll };
