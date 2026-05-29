from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):
    name: str = "base"

    @abstractmethod
    async def analyze(self, pr) -> list:
        ...
