from __future__ import annotations
from typing import Any, Dict, List, Optional
import math
from src.utils.formats import build_struct_and_metadata
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)

ROUNDING_FIELD_NAMES = {
    "Lat", "Lng", "TLat", "TLng", "Pitch", "IPE", "Yaw", "IPN", "IYAW",
    "DesPitch", "NavPitch", "Temp", "AltE", "VDop", "VAcc", "Roll", "HAGL",
    "SM", "VWN", "VWE", "IVT", "SAcc", "TAW", "IPD", "ErrRP", "SVT", "SP", "TAT",
    "GZ", "HDop", "NavRoll", "NavBrg", "TAsp", "HAcc", "DesRoll", "SH", "TBrg", "AX", "Alt"
}


def _derive_decimal_places(scale_factor: Optional[float]) -> Optional[int]:
    if scale_factor is None or scale_factor <= 0:
        return None
    log_value = -math.log10(scale_factor)
    rounded = round(log_value)
    return rounded if abs(log_value - rounded) < 1e-12 and rounded >= 0 else None



def build_dict_schema(
    type_id: int,
    name: str,
    ardupilot_format: str,
    total_length: int,
    labels_str: str,
) -> Dict[str, Any]:
    logger.debug(
        "build_dict_schema: type_id=%s name=%s format=%s total_len=%s",
        type_id, name, ardupilot_format, total_length
    )
    try:
        struct_obj, scale_factors, is_byte_field = build_struct_and_metadata(ardupilot_format)

        columns: List[str] = labels_str.split(",") if labels_str else []
        field_count = min(len(columns), len(scale_factors), len(is_byte_field))

        columns = columns[:field_count]
        scale_factors = scale_factors[:field_count]
        is_byte_field = is_byte_field[:field_count]

        scale_factors = [None if s == 1.0 else s for s in scale_factors]

        round_decimals: List[Optional[int]] = [_derive_decimal_places(s) for s in scale_factors]

        round_mask = tuple(
            (col in ROUNDING_FIELD_NAMES) and (nd is not None)
            for col, nd in zip(columns, round_decimals)
        )

        schema_dict = {
            "type_id": type_id,
            "name": name,
            "format_str": ardupilot_format,
            "struct_fmt": struct_obj.format,
            "total_length": total_length,
            "columns_raw": labels_str,
            "columns": tuple(columns),
            "is_byte_field": tuple(is_byte_field),
            "scale_factors": tuple(scale_factors),
            "field_count": field_count,
            "round_decimals": tuple(round_decimals),
            "round_mask": round_mask,
        }
        logger.debug("build_dict_schema: built dict schema for %s with %d fields", name, field_count)
        return schema_dict

    except Exception as e:
        logger.exception("build_dict_schema: failed for name=%r format=%r: %s", name, ardupilot_format, e)
        raise
