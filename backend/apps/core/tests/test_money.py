from decimal import Decimal

from apps.core.money import indian_format


def test_indian_grouping():
    assert indian_format(Decimal("0")) == "0.00"
    assert indian_format(Decimal("999.5")) == "999.50"
    assert indian_format(Decimal("1234.5")) == "1,234.50"
    assert indian_format(Decimal("1234567.891")) == "12,34,567.89"
    assert indian_format(Decimal("-123456.7")) == "-1,23,456.70"
