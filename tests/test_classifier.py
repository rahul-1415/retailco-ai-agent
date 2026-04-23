import pytest
from src.classifier.tax_classifier import TaxClassifier


@pytest.fixture
def classifier():
    return TaxClassifier()


def test_loads_categories(classifier):
    assert len(classifier.categories) == 50


def test_known_category_rate(classifier):
    # Spot-check known categories from the CSV
    assert classifier.get_rate("Small Kitchen Appliances") == 8.5
    assert classifier.get_rate("Fresh Produce") == 0.0
    assert classifier.get_rate("Alcoholic Beverages") == 10.0


def test_unknown_category_returns_zero(classifier):
    assert classifier.get_rate("Nonexistent Category XYZ") == 0.0


def test_get_categories_text(classifier):
    text = classifier.get_categories_text()
    assert "Fresh Produce" in text
    assert "%" in text


def test_all_rates_are_floats(classifier):
    for category, rate in classifier.categories.items():
        assert isinstance(rate, float), f"{category} rate is not a float"


def test_all_rates_non_negative(classifier):
    for category, rate in classifier.categories.items():
        assert rate >= 0, f"{category} has negative rate: {rate}"
