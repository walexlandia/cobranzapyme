import pytest

from app.utils.rut import normalize_rut


def test_normalizes_valid_rut() -> None:
    assert normalize_rut("76.086.428-5") == "76086428-5"


@pytest.mark.parametrize("value", ["", "123", "76.086.428-4", "abcdefgh"])
def test_rejects_invalid_rut(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_rut(value)

