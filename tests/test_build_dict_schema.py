
import math
import pytest
from importlib import import_module
from src.utils.formats import AP_FORMAT_TO_STRUCT_FMT, POST_SCALE_FACTORS, build_struct_and_metadata
from src.business_logic.schema import _derive_decimal_places, build_dict_schema



@pytest.mark.parametrize(
    "scale,expected",
    [
        (0.1,   1),
        (0.01,  2),
        (0.001, 3),
        (1.0,   0),
        (0.0,   None),
        (-0.1,  None),
        (0.333, None),
    ],
)
def test_derive_decimal_places(scale, expected):
    assert _derive_decimal_places(scale) == expected



def test_build_struct_and_metadata_basic():
    fmt = "LNeZcE"
    struct_obj, scales, is_bytes = build_struct_and_metadata(fmt)

    assert struct_obj.format.startswith("<")
    assert len(scales) == len(is_bytes) == len(fmt)


    idx_N = fmt.index("N")
    idx_Z = fmt.index("Z")
    assert is_bytes[idx_N] is True
    assert is_bytes[idx_Z] is True
    for i, ch in enumerate(fmt):
        if ch not in ("N", "Z", "n"):
            assert is_bytes[i] is False

    by_ch = {ch: i for i, ch in enumerate(fmt)}
    assert math.isclose(scales[by_ch["L"]], POST_SCALE_FACTORS["L"])
    assert math.isclose(scales[by_ch["e"]], POST_SCALE_FACTORS["e"])
    assert math.isclose(scales[by_ch["c"]], POST_SCALE_FACTORS["c"])
    assert math.isclose(scales[by_ch["E"]], POST_SCALE_FACTORS["E"])
    assert scales[by_ch["N"]] is None
    assert scales[by_ch["Z"]] is None


def test_build_struct_and_metadata_unsupported_char():
    with pytest.raises(ValueError):
        build_struct_and_metadata("X")


# -------------------------- build_dict_schema --------------------------

def test_build_dict_schema_rounding_mask_and_counts():
    fmt = "LLfN"
    labels = "Lat,Lng,Alt,Name"

    schema = build_dict_schema(
        type_id=42,
        name="GPS",
        ardupilot_format=fmt,
        total_length=0,
        labels_str=labels,
    )


    assert schema["type_id"] == 42
    assert schema["name"] == "GPS"
    assert schema["field_count"] == 4
    assert tuple(schema["columns"]) == ("Lat", "Lng", "Alt", "Name")


    sf = schema["scale_factors"]
    assert sf[0] and math.isclose(sf[0], POST_SCALE_FACTORS["L"])
    assert sf[1] and math.isclose(sf[1], POST_SCALE_FACTORS["L"])
    assert sf[2] is None
    assert sf[3] is None

    rd = schema["round_decimals"]
    assert rd[0] == 7
    assert rd[1] == 7

    rm = schema["round_mask"]
    assert rm[0] is True
    assert rm[1] is True

    assert isinstance(rm[2], bool)
    assert isinstance(rm[3], bool)


def test_build_dict_schema_truncates_to_min_length():
    fmt = "LI"
    labels = "TimeUS,Lat,Lng,Extra"

    schema = build_dict_schema(
        type_id=7,
        name="TEST",
        ardupilot_format=fmt,
        total_length=0,
        labels_str=labels,
    )

    assert schema["field_count"] == 2
    assert tuple(schema["columns"]) == ("TimeUS", "Lat")


def test_build_dict_schema_scales_of_one_are_none():

    fmt = "If"
    labels = "Count,Value"

    schema = build_dict_schema(
        type_id=8,
        name="NOSCALE",
        ardupilot_format=fmt,
        total_length=0,
        labels_str=labels,
    )

    sf = schema["scale_factors"]
    assert all((s is None) or (isinstance(s, float) and s != 1.0) for s in sf)
