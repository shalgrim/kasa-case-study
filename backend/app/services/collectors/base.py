from abc import ABC, abstractmethod

from ...models import Hotel


class BaseCollector(ABC):
    @abstractmethod
    def collect(self, hotel: Hotel) -> tuple[float | None, int | None]:
        """Returns (score, review_count) or (None, None) if unavailable."""
        ...
