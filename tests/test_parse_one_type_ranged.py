import struct
import pytest
from struct import Struct

from src.business_logic.bin_parser import BinParser
from src.utils.constants import HEADER



def make_msg(type_id: int, struct_fmt: str, values: tuple[object, ...]) -> bytes:
    st = Struct(struct_fmt)
    payload = st.pack(*values)
    return HEADER + bytes([type_id]) + payload


def test_basic_two_messages_in_range(tmp_path, monkeypatch):
    struct_fmt = "<fI"
    payload_size = Struct(struct_fmt).size
    total_len = 3 + payload_size

    msg_x1 = make_msg(10, struct_fmt, (1.5, 100))
    msg_y  = make_msg(11, struct_fmt, (2.5, 200))
    msg_x2 = make_msg(10, struct_fmt, (3.5, 300))

    buf = msg_x1 + msg_y + msg_x2
    path = tmp_path / "data.bin"
    path.write_bytes(buf)


    from src.business_logic import bin_parser as mod
    def fake_build_msg(schema, values):
        return {"mavpackettype": schema["name"], "vals": values}
    monkeypatch.setattr(mod.BinParser, "build_message_dict", lambda self, schema, values: fake_build_msg(schema, values))

    with BinParser(str(path)) as reader:

        reader.schemas_dict_by_type = {
            10: {"name": "X", "struct_fmt": struct_fmt, "total_length": total_len},
            11: {"name": "Y", "struct_fmt": struct_fmt, "total_length": total_len},
        }
        reader._struct_cache.clear()

        out = reader._parse_one_type_ranged(start=0, end=len(buf), type_id=10)

    assert len(out) == 2
    assert out[0]["mavpackettype"] == "X"
    assert out[1]["mavpackettype"] == "X"
    assert out[0]["vals"][1] == 100
    assert out[1]["vals"][1] == 300


def test_missing_schema_returns_empty(tmp_path):
    struct_fmt = "<I"
    msg = make_msg(7, struct_fmt, (123,))
    path = tmp_path / "no_schema.bin"
    path.write_bytes(msg)

    with BinParser(str(path)) as reader:
        reader.schemas_dict_by_type = {}
        out = reader._parse_one_type_ranged(start=0, end=len(msg), type_id=7)

    assert out == []


def test_total_length_too_small_returns_empty(tmp_path):
    path = tmp_path / "small.bin"
    path.write_bytes(b"\x01")

    with BinParser(str(path)) as reader:
        reader.schemas_dict_by_type = {5: {"name": "Z", "struct_fmt": "<B", "total_length": 3}}
        out = reader._parse_one_type_ranged(start=0, end=1, type_id=5)

    assert out == []


def test_truncated_message_at_range_end_is_ignored(tmp_path, monkeypatch):
    struct_fmt = "<I"
    payload_size = Struct(struct_fmt).size
    total_len = 3 + payload_size

    full = make_msg(9, struct_fmt, (111,))
    half = HEADER + bytes([9]) + b"\x01"

    buf = full + half
    path = tmp_path / "trunc.bin"
    path.write_bytes(buf)

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(mod.BinParser, "build_message_dict", lambda self, schema, values: {"ok": True, "vals": values})

    with BinParser(str(path)) as reader:
        reader.schemas_dict_by_type = {9: {"name": "T", "struct_fmt": struct_fmt, "total_length": total_len}}
        out = reader._parse_one_type_ranged(start=0, end=len(buf), type_id=9)

    assert len(out) == 1
    assert out[0]["ok"] is True


def test_false_positive_header_inside_payload_is_filtered(tmp_path, monkeypatch):
    target_type = 5
    struct_fmt = "<I"
    payload_size = Struct(struct_fmt).size
    total_len = 3 + payload_size

    carrier_type = 99
    carrier_payload = (0x050595A3,)
    msg_carrier = HEADER + bytes([carrier_type]) + Struct("<I").pack(*carrier_payload)

    msg_ok = HEADER + bytes([target_type]) + Struct(struct_fmt).pack(123)

    buf = msg_carrier + msg_ok
    path = tmp_path / "falsepos.bin"
    path.write_bytes(buf)

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(mod.BinParser, "build_message_dict",
                        lambda self, schema, values: {"x": values[0]})

    with BinParser(str(path)) as reader:
        reader.schemas_dict_by_type = {
            target_type: {"name": "T", "struct_fmt": struct_fmt, "total_length": total_len}
        }
        reader._struct_cache.clear()

        out = reader._parse_one_type_ranged(start=0, end=len(buf), type_id=target_type)

    assert [msg["x"] for msg in out] == [123]



def test_accept_last_msg_when_no_lookahead_space(tmp_path, monkeypatch):
    struct_fmt = "<I"
    payload_size = Struct(struct_fmt).size
    total_len = 3 + payload_size

    last = HEADER + bytes([4]) + Struct(struct_fmt).pack(999)
    buf = last
    path = tmp_path / "last_no_lookahead.bin"
    path.write_bytes(buf)

    from src.business_logic import bin_parser as mod
    monkeypatch.setattr(mod.BinParser, "build_message_dict",
                        lambda self, schema, values: {"v": values[0]})

    monkeypatch.setattr(mod.BinParser, "_get_struct", lambda self, t: Struct(struct_fmt))

    with BinParser(str(path)) as reader:
        reader.schemas_dict_by_type = {4: {"name": "L", "struct_fmt": struct_fmt, "total_length": total_len}}
        reader._struct_cache.clear()
        out = reader._parse_one_type_ranged(start=0, end=len(buf), type_id=4)

    assert [msg["v"] for msg in out] == [999]


