from __future__ import annotations
from typing import Any, Dict, List
from src.utils.logger import Logger
from src.utils.constants import FORMAT_MAPPING

logger = Logger.get_logger(__name__)


def build_struct_and_formats(ardupilot_format: str) -> tuple[str, List[str]]:
    """
    Convert an ArduPilot format string (e.g., 'QfB') into a Python struct format.
    Returns:
        struct_fmt: A full struct format string with '<' prefix.
        fmts:       A list of the original ArduPilot format characters in order.
    Raises:
        ValueError: If an unsupported format character is encountered.
    """

    parts: List[str] = []
    fmts: List[str] = []

    for char in ardupilot_format:
        mapped = FORMAT_MAPPING.get(char)
        if mapped is None:
            logger.error("Unsupported format char: %r", char)
            raise ValueError(f"Unsupported format char: {char!r}")
        parts.append(mapped)
        fmts.append(char)

    struct_fmt = "<" + "".join(parts)
    return struct_fmt, fmts

def build_dict_schema(
    type_id: int,
    name: str,
    ardupilot_format: str,
    total_length: int,
    labels_str: str,
) -> Dict[str, Any]:
    """
    Build a full schema dictionary for a message type based on FMT metadata.
    The schema includes:
        - struct format string
        - list of column names
        - ArduPilot format chars
        - total message length
        - field count used for unpacking
    Returns:
        A dictionary describing how to unpack and map message fields.
    """

    logger.debug(
        "build_dict_schema: type_id=%s name=%s format=%s total_len=%s",
        type_id, name, ardupilot_format, total_length
    )

    struct_fmt, formats = build_struct_and_formats(ardupilot_format)

    columns: List[str] = labels_str.split(",") if labels_str else []
    field_count = min(len(columns), len(formats))

    columns = columns[:field_count]
    formats = formats[:field_count]

    schema_dict: Dict[str, Any] = {
        "type_id": type_id,
        "name": name,
        "format_str": ardupilot_format,
        "struct_fmt": struct_fmt,
        "total_length": total_length,
        "columns": tuple(columns),
        "formats": tuple(formats),
        "field_count": field_count,
    }
    logger.debug("build_dict_schema: built dict schema for %s with %d fields", name, field_count)
    return schema_dict
