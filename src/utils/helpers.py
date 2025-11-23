from __future__ import annotations

import os
import mmap
from typing import IO, Dict, Iterable, Optional, Set, Tuple, Union

from src.utils.logger import Logger

from .constants import NAME_PATTERN

logger = Logger.get_logger(__name__)




def cstr_to_text(buf: bytes) -> str:
    """
    Decode a null-terminated ASCII C-string.
    Splits at the first NULL byte, decodes to ASCII, and ignores invalid characters.
    """
    try:
        return buf.split(b"\0", 1)[0].decode("ascii", "ignore")
    except Exception as e:
        logger.exception(
            "cstr_to_text: failed to decode buffer (len=%s): %s", len(buf) if buf is not None else "None", e
        )
        raise


def is_valid_name(name: str) -> bool:
    """
    Validate that a message name matches the ArduPilot NAME_PATTERN.
    Returns True for valid names like: 'GPS', 'ATT', 'BARO', etc.
    """
    try:
        return bool(name) and bool(NAME_PATTERN.match(name))
    except Exception as e:
        logger.exception("is_valid_name: validation failed for %r: %s", name, e)
        raise


def resolve_wanted_type_ids(
    wanted: Optional[Union[str, bytes, Iterable[Union[str, bytes]]]],
    schemas_by_name: Dict[str, int],
) -> Optional[Set[int]]:
    """
    Convert requested message names into a set of type IDs.
    - Accepts a single name or a list of names.
    - Returns a set of matching type_ids (possibly empty).
    - Returns None if no filtering is requested.
    """
    try:
        if wanted is None:
            return None

        if isinstance(wanted, (str, bytes)):
            names = [wanted]
        else:
            names = list(wanted)

        ids: set[int] = set()

        for name in names:
            type_id = schemas_by_name.get(name)
            if type_id is not None:
                ids.add(type_id)
            else:
                logger.info("resolve_wanted_type_ids: name not found in schemas: %r", name)

        result = ids if ids else set()
        logger.debug("resolve_wanted_type_ids: matched %d id(s)", len(result))
        return result

    except Exception as e:
        logger.exception("resolve_wanted_type_ids: unexpected error (wanted=%r): %s", wanted, e)
        raise


def open_file_and_mmap(path: str) -> Tuple[IO[bytes], mmap.mmap]:
    """
    Open a .BIN file in read-only mode and return (file_handle, mmap).
    Validates:
    - Path ends with .bin
    - File exists
    - File is not empty
    Raises exceptions on any failure and logs details.
    """

    if not path.lower().endswith(".bin"):
        logger.warning("open_file_and_mmap: file does not have .bin extension: %s", path)
        raise ValueError("Path must end with .bin")

    if os.path.getsize(path) == 0:
        logger.warning("open_file_and_mmap: file is empty: %s", path)
        raise ValueError("Cannot mmap empty file")

    try:
        file_handler = open(path, "rb")
    except FileNotFoundError:
        logger.exception("File not found: %s", path)
        raise
    except PermissionError:
        logger.exception("Permission denied: %s", path)
        raise
    except Exception:
        logger.exception("Unexpected error opening %s", path)
        raise

    try:
        memory_map = mmap.mmap(file_handler.fileno(), 0, access=mmap.ACCESS_READ)
    except Exception:
        logger.exception("Failed to mmap file %s", path)
        try:
            file_handler.close()
        except Exception:
            logger.exception("Also failed closing file after mmap error")
        raise

    return file_handler, memory_map


import os
import psutil
from typing import Optional


def choose_num_workers_for_log(file_size_bytes: int,) -> int:

    num_cpu = os.cpu_count() or 1

    available_gb = psutil.virtual_memory().available / (1024 ** 3)
    file_size_gb = max(0.01, file_size_bytes / (1024 ** 3))

    # Base memory ~0.25GB per worker + small growth by file size
    process_memory_gb = 0.25 + 0.20 * file_size_gb

    # Clamp values to avoid insane numbers:
    # at least 0.25GB per worker, at most 1.5GB
    process_memory_gb = min(max(process_memory_gb, 0.25), 1.5)

    # How many workers can RAM support
    max_by_memory = max(1, int(available_gb // process_memory_gb))

    # Combine RAM + CPU limits
    workers = min(num_cpu, max_by_memory)

    return max(1, workers)
