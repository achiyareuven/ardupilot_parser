from __future__ import annotations

import re

HEADER: bytes = b"\xa3\x95"

FMT_TYPE: int = 0x80

FMT_PAYLOAD_LEN: int = 86

NAME_PATTERN = re.compile(r"^[A-Z0-9]{1,4}$")

MIN_MAGIC_ADVANCE: int = 2
