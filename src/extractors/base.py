from abc import ABC, abstractmethod
from src.models import Invoice


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, pdf_bytes: bytes) -> Invoice:
        pass
