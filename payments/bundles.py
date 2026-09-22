"""Token bundles. The 2022 prices, defined once (they were duplicated in a template and a view)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Bundle:
    key: str
    tokens: int
    price_cents: int

    @property
    def cents_per_token(self) -> int:
        return self.price_cents // self.tokens


BUNDLES = (
    Bundle("single", 1, 20_00),
    Bundle("five", 5, 80_00),
    Bundle("ten", 10, 120_00),
    Bundle("twenty", 20, 180_00),
)
CURRENCY = "USD"


def get_bundle(key: str) -> Bundle | None:
    return next((b for b in BUNDLES if b.key == key), None)
