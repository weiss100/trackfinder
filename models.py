from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TrackResult:
    title: str
    artist: str
    label: str
    genre: str
    bpm: Optional[str]
    key: Optional[str]
    duration: str
    price: str
    price_value: Optional[float]
    currency: str
    artwork: Optional[str]
    url: str
    store: str
    store_icon: str
    release_date: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["priceValue"] = d.pop("price_value")
        d["storeIcon"] = d.pop("store_icon")
        d["releaseDate"] = d.pop("release_date")
        return d
