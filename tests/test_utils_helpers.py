import os
import mmap
import tempfile
import pytest

from src.utils.helpers import cstr_to_text, is_valid_name, resolve_wanted_type_ids, open_file_and_mmap
from src.utils.constants import NAME_PATTERN

# ---------------- cstr_to_text ----------------

@pytest.mark.parametrize(
    "buf,expected",
    [
        (b"HELLO\x00WORLD", "HELLO"),
        (b"NO_NULL", "NO_NULL"),
        (b"\xff\xfeABC\x00", "ABC"),
        (b"", ""),
    ],
)
def test_cstr_to_text_ok(buf, expected):
    assert cstr_to_text(buf) == expected

# ---------------- is_valid_name ----------------

@pytest.mark.parametrize(
    "name,valid",
    [
        ("GPS", True),
        ("POS", True),
        ("FMT", True),
        ("A",   True),
        ("TOO_LONG", False),
        ("lower", False),
        ("", False),
        ("AB_1", False),
    ],
)
def test_is_valid_name(name, valid):
    assert is_valid_name(name) == valid
    assert bool(NAME_PATTERN.match(name)) == valid

# ------------- resolve_wanted_type_ids -------------

def test_resolve_wanted_none_returns_none():
    assert resolve_wanted_type_ids(None, {"GPS": 1}) is None

def test_resolve_wanted_str_and_bytes(caplog):
    schemas = {"GPS": 1, "ATT": 2}
    caplog.set_level("DEBUG")
    assert resolve_wanted_type_ids("GPS", schemas) == {1}
    assert resolve_wanted_type_ids(b"ATT", schemas) == {2}
    got = resolve_wanted_type_ids("NOPE", schemas)
    assert got == set()


def test_resolve_wanted_iterable_mixed_types():
    schemas = {"GPS": 1, "ATT": 2, "MODE": 3}
    wanted = ["GPS", b"MODE", "NOPE"]
    assert resolve_wanted_type_ids(wanted, schemas) == {1, 3}

# ------------- open_file_and_mmap -------------

def test_open_file_and_mmap_happy_path():
    data = b"1234567890"
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(data)
        path = tmp.name

    f, mm = open_file_and_mmap(path)
    try:
        assert isinstance(mm, mmap.mmap)
        assert mm.size() == len(data)
        assert mm[:5] == b"12345"
    finally:
        mm.close()
        f.close()
        os.remove(path)

def test_open_file_and_mmap_file_not_found():
    with pytest.raises(FileNotFoundError):
        open_file_and_mmap("this_file_should_not_exist.bin")
