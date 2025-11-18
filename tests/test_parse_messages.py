import pytest
from struct import Struct

from src.business_logic.bin_parser import BinParser
from src.utils.constants import HEADER


def make_msg(type_id: int, struct_fmt: str, values: tuple[object, ...]) -> bytes:
    structfmt = Struct(struct_fmt)
    return HEADER + bytes([type_id]) + structfmt.pack(*values)


def _write_dummy_file(tmp_path, data=b"\x00" * 32):
    path = tmp_path / "dummy.bin"
    path.write_bytes(data)
    return path


def test_no_filter_calls_multi_with_none_and_clamps_bounds(tmp_path, monkeypatch):
    file_path = _write_dummy_file(tmp_path, b"\x00" * 10)

    calls = []

    def fake_multi(self, *, start, end, wanted_set):
        calls.append({"start": start, "end": end, "wanted_set": wanted_set})
        # מחזירים dict כמו המימוש האמיתי
        return {"X": [{"ok": True}]}

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(mod.BinParser, "_parse_multi_types_ranged", fake_multi)

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {}
        out = parser.parse_messages(start=-5, end=9999, wanted_names=None)

    assert out == {"X": [{"ok": True}]}
    assert calls == [{"start": 0, "end": 10, "wanted_set": None}]


def test_builds_name_map_when_missing(tmp_path, monkeypatch):
    file_path = _write_dummy_file(tmp_path)

    monkeypatch.setattr(
        BinParser,
        "_parse_multi_types_ranged",
        lambda self, **kw: {"dummy": [{"dummy": 1}]},
    )

    with BinParser(str(file_path)) as parser:
        parser.name_to_type_id = {}  # ריק
        parser.schemas_dict_by_type = {
            10: {"name": "GPS", "struct_fmt": "<I", "total_length": 7},
            11: {"name": "ATT", "struct_fmt": "<I", "total_length": 7},
        }
        _ = parser.parse_messages()

        assert parser.name_to_type_id == {"GPS": 10, "ATT": 11}


def test_resolve_failure_returns_empty(tmp_path, monkeypatch):
    file_path = _write_dummy_file(tmp_path)

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(
        mod,
        "resolve_wanted_type_ids",
        lambda wanted, mapping: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            10: {"name": "X", "struct_fmt": "<I", "total_length": 7}
        }
        parser.name_to_type_id = {"X": 10}
        out = parser.parse_messages(wanted_names="X")

    assert out == {}


@pytest.mark.parametrize("resolved", [None, [], set(), tuple()])
def test_resolved_empty_returns_empty(tmp_path, monkeypatch, resolved):
    file_path = _write_dummy_file(tmp_path)

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(mod, "resolve_wanted_type_ids", lambda wanted, mapping: resolved)

    with BinParser(str(file_path)) as parser:
        parser.name_to_type_id = {"X": 10}
        parser.schemas_dict_by_type = {
            10: {"name": "X", "struct_fmt": "<I", "total_length": 7}
        }
        out = parser.parse_messages(wanted_names="X")

    assert out == {}  # no matching types → dict ריק


def test_single_type_route_calls_one_type(tmp_path, monkeypatch):
    file_path = _write_dummy_file(tmp_path)

    calls = []

    def fake_one(self, *, start, end, type_id):
        calls.append({"start": start, "end": end, "type_id": type_id})
        # מחזיר רשימה כמו המימוש האמיתי של _parse_one_type_ranged
        return [{"one": type_id}]

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(mod, "resolve_wanted_type_ids", lambda wanted, mapping: [7])
    monkeypatch.setattr(mod.BinParser, "_parse_one_type_ranged", fake_one)

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            7: {"name": "A", "struct_fmt": "<I", "total_length": 7}
        }
        parser.name_to_type_id = {"A": 7}
        out = parser.parse_messages(start=2, end=20, wanted_names="A")

    # parse_messages מחזיר dict לפי שם הטייפ
    assert out == {"A": [{"one": 7}]}
    assert calls == [{"start": 2, "end": 20, "type_id": 7}]


def test_internal_exception_no_filter_returns_empty(tmp_path, monkeypatch):
    file_path = _write_dummy_file(tmp_path)

    from src.business_logic import bin_parser as mod

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(mod.BinParser, "_parse_multi_types_ranged", boom)

    with BinParser(str(file_path)) as parser:
        out = parser.parse_messages(wanted_names=None)

    assert out == {}


def test_internal_exception_single_type_returns_empty(tmp_path, monkeypatch):
    file_path = _write_dummy_file(tmp_path)

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(mod, "resolve_wanted_type_ids", lambda wanted, mapping: [42])
    monkeypatch.setattr(
        mod.BinParser,
        "_parse_one_type_ranged",
        lambda self, **kw: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            42: {"name": "ONLY", "struct_fmt": "<I", "total_length": 7}
        }
        parser.name_to_type_id = {"ONLY": 42}
        out = parser.parse_messages(wanted_names="ONLY")

    assert out == {}


@pytest.mark.parametrize("wanted_arg", ["GPS", ["GPS"], ("GPS",)])
def test_wanted_names_accepts_str_and_iterable(tmp_path, monkeypatch, wanted_arg):
    file_path = _write_dummy_file(tmp_path)

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(mod, "resolve_wanted_type_ids", lambda wanted, mapping: [10])
    monkeypatch.setattr(
        mod.BinParser,
        "_parse_one_type_ranged",
        lambda self, **kw: [{"ok": "one"}],
    )

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            10: {"name": "GPS", "struct_fmt": "<I", "total_length": 7}
        }
        parser.name_to_type_id = {"GPS": 10}
        out = parser.parse_messages(wanted_names=wanted_arg)

    assert out == {"GPS": [{"ok": "one"}]}


def test_defaults_full_range(tmp_path, monkeypatch):
    data = b"\x00" * 123
    file_path = _write_dummy_file(tmp_path, data)

    calls = []

    def fake_multi(self, *, start, end, wanted_set):
        calls.append((start, end, wanted_set))
        return {"X": [{"ok": True}]}

    monkeypatch.setattr(BinParser, "_parse_multi_types_ranged", fake_multi)

    with BinParser(str(file_path)) as parser:
        out = parser.parse_messages()

    assert out == {"X": [{"ok": True}]}
    assert calls == [(0, len(data), None)]
