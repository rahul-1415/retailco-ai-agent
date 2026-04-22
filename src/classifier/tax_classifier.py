import csv
import os


class TaxClassifier:
    def __init__(self, csv_path: str | None = None):
        if csv_path is None:
            csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "tax_rate_by_category.csv")
        self.categories = self._load_categories(csv_path)

    def _load_categories(self, path: str) -> dict[str, float]:
        categories = {}
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                categories[row["Category"].strip()] = float(row["Tax Rate (%)"].strip())
        return categories

    def get_categories_text(self) -> str:
        return "\n".join(f"- {cat}: {rate}%" for cat, rate in self.categories.items())

    def get_rate(self, category: str) -> float:
        return self.categories.get(category, 0.0)
