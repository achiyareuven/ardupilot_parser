from __future__ import annotations
from struct import Struct
from typing import Dict, List, Optional
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)

AP_FORMAT_TO_STRUCT_FMT: Dict[str, str] = {
    "a": "32h",
    "b": "b",   # int8
    "B": "B",   # uint8
    "h": "h",   # int16
    "H": "H",   # uint16
    "i": "i",   # int32
    "I": "I",   # uint32
    "f": "f",   # float32
    "d": "d",   # float64
    "q": "q",   # int64
    "Q": "Q",   # uint64
    "n": "4s",  # char[4]
    "N": "16s", # char[16]
    "Z": "64s", # char[64]
    "c": "h",   # int16  (scaled 1/100)
    "C": "H",   # uint16 (scaled 1/100)
    "e": "i",   # int32  (scaled 1/100)
    "E": "I",   # uint32 (scaled 1/100)
    "L": "i",   # int32  (lat/lon * 1e-7)
    "M": "B",   # uint8  (flight mode code)
}

POST_SCALE_FACTORS: Dict[str, float] = {
    "c": 1 / 100.0,
    "C": 1 / 100.0,
    "e": 1 / 100.0,
    "E": 1 / 100.0,
    "L": 1 / 1e7,  # lat/lon מעלות
}


def build_struct_and_metadata(ardupilot_format: str) -> tuple[Struct, List[Optional[float]], List[bool]]:

    struct_format_parts: List[str] = []
    scale_factors: List[Optional[float]] = []
    is_bytes: List[bool] = []

    try:


        for fmt_char in ardupilot_format:
            struct_format_char = AP_FORMAT_TO_STRUCT_FMT.get(fmt_char)
            if struct_format_char is None:
                logger.error(f"Unsupported format character encountered: '{fmt_char}'")
                raise ValueError(f"Unsupported format char: {fmt_char!r}")

            struct_format_parts.append(struct_format_char)
            is_bytes.append(struct_format_char.endswith("s"))
            scale_factors.append(POST_SCALE_FACTORS.get(fmt_char))

        struct_obj = Struct("<" + "".join(struct_format_parts))
        return struct_obj, scale_factors, is_bytes

    except Exception as e:
        logger.exception(f"Error while building struct for format '{ardupilot_format}': {e}")
        raise
