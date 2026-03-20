export interface TrackResult {
  title: string;
  artist: string;
  label: string;
  genre: string;
  bpm: string | null;
  key: string | null;
  duration: string;
  price: string;
  priceValue: number | null;
  currency: string;
  artwork: string | null;
  url: string;
  store: string;
  storeIcon: string;
  releaseDate: string;
}

export interface SearchResponse {
  results: TrackResult[];
  query: string;
  total: number;
}

export interface StoreAdapter {
  search(query: string): Promise<TrackResult[]>;
  STORE_NAME: string;
}
