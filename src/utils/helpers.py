from __future__ import annotations

import mmap
from struct import Struct
from typing import IO, Dict, Iterable, Optional, Set, Tuple, Union

from src.utils.logger import Logger

from .constants import NAME_PATTERN

logger = Logger.get_logger(__name__)

_F32 = Struct("<f")


def cstr_to_text(buf: bytes) -> str:
    try:
        return buf.split(b"\0", 1)[0].decode("ascii", "ignore")
    except Exception as e:
        logger.exception(
            "cstr_to_text: failed to decode buffer (len=%s): %s", len(buf) if buf is not None else "None", e
        )
        raise


def is_valid_name(name: str) -> bool:
    try:
        return bool(name) and bool(NAME_PATTERN.match(name))
    except Exception as e:
        logger.exception("is_valid_name: validation failed for %r: %s", name, e)
        raise


def resolve_wanted_type_ids(
    wanted: Optional[Union[str, bytes, Iterable[Union[str, bytes]]]],
    schemas_by_name: Dict[str, int],
) -> Optional[Set[int]]:
    try:
        if wanted is None:
            return None

        if isinstance(wanted, (str, bytes)):
            names = [wanted]
        else:
            names = list(wanted)

        ids: set[int] = set()

        for name in names:
            if isinstance(name, bytes):
                try:
                    name = name.decode("ascii", "ignore")
                except Exception as e:
                    logger.exception("resolve_wanted_type_ids: failed to decode bytes name: %s", e)
                    continue
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

    if path[-4:] != ".bin":
        logger.warning("open_file_and_mmap: file does not have .bin extension: %s", path)
        raise
    try:
        f = open(path, "rb")
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
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    except Exception:
        logger.exception("Failed to mmap file %s", path)
        try:
            f.close()
        except Exception:
            logger.exception("Also failed closing file after mmap error")
        raise

    return f, mm
