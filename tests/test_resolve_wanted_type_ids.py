import pytest

from src.utils.helpers import resolve_wanted_type_ids


@pytest.fixture
def schemas_by_name():
    return {
        "GPS": 1,
        "ATT": 2,
        "AHR2": 3,
        "FMT": 128,
    }


def test_none_returns_none(schemas_by_name):
    assert resolve_wanted_type_ids(None, schemas_by_name) is None


def test_single_str_matches(schemas_by_name):
    out = resolve_wanted_type_ids("GPS", schemas_by_name)
    assert out == {1}


def test_single_bytes_without_bytes_key_returns_empty_set(schemas_by_name):
    out = resolve_wanted_type_ids(b"GPS", schemas_by_name)
    assert out == set()


def test_iterable_multiple_some_missing(schemas_by_name):
    out = resolve_wanted_type_ids(["GPS", "NOPE", "ATT"], schemas_by_name)
    assert out == {1, 2}


def test_duplicates_are_deduped(schemas_by_name):
    out = resolve_wanted_type_ids(["GPS", "GPS", "ATT", "ATT"], schemas_by_name)
    assert out == {1, 2}




def test_all_missing_returns_empty_set(schemas_by_name):
    out = resolve_wanted_type_ids(["NOPE", "MISSING"], schemas_by_name)
    assert out == set()


def test_empty_iterable_returns_empty_set(schemas_by_name):
    out = resolve_wanted_type_ids([], schemas_by_name)
    assert out == set()
