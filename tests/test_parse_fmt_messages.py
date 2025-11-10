import struct
from src.business_logic.bin_parsr import BinParser
from src.utils.constants import HEADER, FMT_TYPE, FMT_PAYLOAD_LEN


def _cstr_fixed(s: bytes, size: int) -> bytes:
    s = s.split(b"\x00", 1)[0]
    return (s + b"\x00").ljust(size, b"\x00")

def make_fmt_record(*, type_id: int, total_len: int, name: bytes, fmt: bytes, labels: bytes) -> bytes:
    payload = struct.pack(
        "<BB4s16s64s",
        type_id,
        total_len,
        _cstr_fixed(name, 4),
        _cstr_fixed(fmt, 16),
        _cstr_fixed(labels, 64),
    )
    assert len(payload) == FMT_PAYLOAD_LEN
    return HEADER + bytes([FMT_TYPE]) + payload



def test_parse_single_valid_fmt(tmp_path, monkeypatch):

    buf = make_fmt_record(
        type_id=42,
        total_len=20,
        name=b"GPS",
        fmt=b"fI",
        labels=b"Lat,TimeUS",
    )
    path = tmp_path / "one_fmt.bin"
    path.write_bytes(buf)


    from src.business_logic import bin_parsr as mod
    def fake_build_dict_schema(type_id, name, ardupilot_format, total_length, labels_str):
        return {
            "type_id": type_id,
            "name": name,
            "format_str": ardupilot_format,
            "total_length": total_length,
            "columns_raw": labels_str,
        }
    monkeypatch.setattr(mod, "build_dict_schema", fake_build_dict_schema)

    with BinParser(str(p)) as reader:
        reader.parse_fmt_messages()

        assert reader.schemas_dict_by_type == {
            42: {
                "type_id": 42,
                "name": "GPS",
                "format_str": "fI",
                "total_length": 20,
                "columns_raw": "Lat,TimeUS",
            }
        }
        assert reader.name_to_type_id == {"GPS": 42}


def test_invalid_name_is_skipped(tmp_path, monkeypatch):
    buf = make_fmt_record(
        type_id=7,
        total_len=10,
        name=b"BAD!",
        fmt=b"f",
        labels=b"X",
    )
    path = tmp_path / "bad_name.bin"
    path.write_bytes(buf)

    with BinParser(str(path)) as reader:
        reader.parse_fmt_messages()
        assert reader.schemas_dict_by_type == {}
        assert reader.name_to_type_id == {}


def test_truncated_fmt_payload_is_ignored(tmp_path):
    head = HEADER + bytes([FMT_TYPE])
    truncated_payload = b"\x00" * (FMT_PAYLOAD_LEN - 5)
    path = tmp_path / "trunc.bin"
    path.write_bytes(head + truncated_payload)

    with BinParser(str(path)) as reader:
        reader.parse_fmt_messages()
        assert reader.schemas_dict_by_type == {}
        assert reader.name_to_type_id == {}


def test_build_dict_schema_value_error_is_skipped(tmp_path, monkeypatch):
    buf = make_fmt_record(
        type_id=9,
        total_len=12,
        name=b"ATT",
        fmt=b"ZZZZ",
        labels=b"A,B,C,D",
    )
    path = tmp_path / "schema_fail.bin"
    path.write_bytes(buf)

    from src.business_logic import bin_parsr as mod
    def raise_value_error(*a, **k):
        raise ValueError("bad format")
    monkeypatch.setattr(mod, "build_dict_schema", raise_value_error)

    with BinParser(str(p)) as reader:
        reader.parse_fmt_messages()
        assert reader.schemas_dict_by_type == {}
        assert reader.name_to_type_id == {}


def test_multiple_fmt_records_build_and_map_names(tmp_path, monkeypatch):
    buf = b"".join([
        make_fmt_record(type_id=1, total_len=10, name=b"GPS", fmt=b"fI", labels=b"Lat,TimeUS"),
        make_fmt_record(type_id=2, total_len=8,  name=b"ATT", fmt=b"fff", labels=b"Roll,Pitch,Yaw"),
    ])
    path = tmp_path / "multi.bin"
    path.write_bytes(buf)

    from src.business_logic import bin_parsr as mod
    def fake_build_dict_schema(type_id, name, ardupilot_format, total_length, labels_str):
        return {"type_id": type_id, "name": name, "format_str": ardupilot_format, "total_length": total_length, "columns_raw": labels_str}
    monkeypatch.setattr(mod, "build_dict_schema", fake_build_dict_schema)

    with BinParser(str(path)) as reader:
        reader.parse_fmt_messages()
        assert set(reader.schemas_dict_by_type.keys()) == {1, 2}
        assert reader.schemas_dict_by_type[1]["name"] == "GPS"
        assert reader.schemas_dict_by_type[2]["name"] == "ATT"
        assert reader.name_to_type_id == {"GPS": 1, "ATT": 2}
