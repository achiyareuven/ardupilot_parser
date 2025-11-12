import struct
from struct import Struct
import pytest

from src.business_logic.bin_parser import BinParser
from src.utils.constants import HEADER


def make_msg(type_id: int, struct_fmt: str, values: tuple[object, ...]) -> bytes:
    st = Struct(struct_fmt)
    payload = st.pack(*values)
    return HEADER + bytes([type_id]) + payload


def _patch_parser(monkeypatch, struct_fmt):
    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(
        mod.BinParser,
        "build_message_dict",
        lambda self, schema, values: {"name": schema["name"], "values": values},
    )
    monkeypatch.setattr(mod.BinParser, "_get_struct", lambda self, t: Struct(struct_fmt))




def test_reads_multiple_types_in_order(tmp_path, monkeypatch):
    struct_fmt = "<I"
    total_len = 3 + Struct(struct_fmt).size

    msg_x1 = make_msg(10, struct_fmt, (100,))
    msg_y = make_msg(11, struct_fmt, (200,))
    msg_x2 = make_msg(10, struct_fmt, (300,))
    data = msg_x1 + msg_y + msg_x2

    file_path = tmp_path / "multi_types.bin"
    file_path.write_bytes(data)

    _patch_parser(monkeypatch, struct_fmt)

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            10: {"name": "X", "struct_fmt": struct_fmt, "total_length": total_len},
            11: {"name": "Y", "struct_fmt": struct_fmt, "total_length": total_len},
        }
        parser._struct_cache.clear()

        result = parser._parse_multi_types_ranged(start=0, end=len(data), wanted_set=None)

    assert [msg["name"] for msg in result] == ["X", "Y", "X"]
    assert [msg["values"][0] for msg in result] == [100, 200, 300]


def test_filters_and_collects_multiple_types(tmp_path, monkeypatch):
    struct_fmt = "<I"
    total_len = 3 + Struct(struct_fmt).size

    msg_type7_1 = make_msg(7, struct_fmt, (100,))
    msg_type8_1 = make_msg(8, struct_fmt, (200,))
    msg_type9_1 = make_msg(9, struct_fmt, (300,))
    msg_type7_2 = make_msg(7, struct_fmt, (400,))
    msg_type8_2 = make_msg(8, struct_fmt, (500,))
    msg_type9_2 = make_msg(9, struct_fmt, (600,))

    data = msg_type7_1 + msg_type8_1 + msg_type9_1 + msg_type7_2 + msg_type8_2 + msg_type9_2

    file_path = tmp_path / "multi_types_filter.bin"
    file_path.write_bytes(data)

    _patch_parser(monkeypatch, struct_fmt)

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            7: {"name": "Type7", "struct_fmt": struct_fmt, "total_length": total_len},
            8: {"name": "Type8", "struct_fmt": struct_fmt, "total_length": total_len},
            9: {"name": "Type9", "struct_fmt": struct_fmt, "total_length": total_len},
        }
        parser._struct_cache.clear()

        result = parser._parse_multi_types_ranged(start=0, end=len(data), wanted_set={7, 9})

    names = [msg["name"] for msg in result]
    values = [msg["values"][0] for msg in result]

    assert names == ["Type7", "Type9", "Type7", "Type9"]
    assert values == [100, 300, 400, 600]



def test_skips_unknown_schema(tmp_path, monkeypatch):
    struct_fmt = "<I"
    total_len = 3 + Struct(struct_fmt).size

    msg_unknown = HEADER + bytes([99]) + Struct(struct_fmt).pack(999)
    msg_known = HEADER + bytes([5]) + Struct(struct_fmt).pack(42)
    data = msg_unknown + msg_known

    file_path = tmp_path / "unknown_schema.bin"
    file_path.write_bytes(data)

    _patch_parser(monkeypatch, struct_fmt)

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            5: {"name": "Known", "struct_fmt": struct_fmt, "total_length": total_len}
        }
        parser._struct_cache.clear()

        result = parser._parse_multi_types_ranged(start=0, end=len(data), wanted_set=None)

    assert [msg["name"] for msg in result] == ["Known"]
    assert [msg["values"][0] for msg in result] == [42]


def test_ignores_truncated_message_at_end(tmp_path, monkeypatch):
    struct_fmt = "<I"
    total_len = 3 + Struct(struct_fmt).size

    msg_full = make_msg(9, struct_fmt, (111,))
    msg_truncated = HEADER + bytes([9]) + b"\x01"
    data = msg_full + msg_truncated

    file_path = tmp_path / "truncated_message.bin"
    file_path.write_bytes(data)

    _patch_parser(monkeypatch, struct_fmt)

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            9: {"name": "T", "struct_fmt": struct_fmt, "total_length": total_len}
        }
        parser._struct_cache.clear()

        result = parser._parse_multi_types_ranged(start=0, end=len(data), wanted_set=None)

    assert [msg["values"][0] for msg in result] == [111]



def test_empty_wanted_set_returns_empty(tmp_path, monkeypatch):
    struct_fmt = "<I"
    total_len = 3 + Struct(struct_fmt).size

    msg_1 = make_msg(1, struct_fmt, (7,))
    msg_2 = make_msg(2, struct_fmt, (8,))
    data = msg_1 + msg_2

    file_path = tmp_path / "empty_wanted.bin"
    file_path.write_bytes(data)

    _patch_parser(monkeypatch, struct_fmt)

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            1: {"name": "A", "struct_fmt": struct_fmt, "total_length": total_len},
            2: {"name": "B", "struct_fmt": struct_fmt, "total_length": total_len},
        }
        parser._struct_cache.clear()

        result = parser._parse_multi_types_ranged(start=0, end=len(data), wanted_set=set())

    assert result == []


def test_unpack_error_skips_message_and_continues(tmp_path, monkeypatch):
    struct_fmt = "<I"
    total_len = 3 + Struct(struct_fmt).size  # 7

    first_msg  = HEADER + bytes([4]) + Struct(struct_fmt).pack(123)
    second_msg = HEADER + bytes([4]) + Struct(struct_fmt).pack(456)
    data = first_msg + second_msg

    file_path = tmp_path / "unpack_error_once.bin"
    file_path.write_bytes(data)

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(
        mod.BinParser,
        "build_message_dict",
        lambda self, schema, values: {"name": schema["name"], "values": values},
    )

    class FailingOnceStruct:
        def __init__(self, inner):
            self.inner = inner
            self.failed_once = False
        def unpack_from(self, buf, offset=0):
            if not self.failed_once:
                self.failed_once = True
                raise struct.error("forced fail for test")
            return self.inner.unpack_from(buf, offset)

    failing_struct = FailingOnceStruct(Struct(struct_fmt))

    monkeypatch.setattr(
        mod.BinParser,
        "_get_struct",
        lambda self, t: failing_struct
    )

    with BinParser(str(file_path)) as parser:
        parser.schemas_dict_by_type = {
            4: {"name": "L", "struct_fmt": struct_fmt, "total_length": total_len}
        }
        parser._struct_cache.clear()

        result = parser._parse_multi_types_ranged(
            start=0, end=len(data), wanted_set=None
        )

    assert [msg["values"][0] for msg in result] == [456]

