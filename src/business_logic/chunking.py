from __future__ import annotations

import mmap
from typing import Any, Dict, List, Optional, Tuple

from src.utils.constants import HEADER
from src.utils.constants import CHUNK_SIZE_BYTES
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)


def find_next_message_start_offset(
    data: mmap.mmap,
    start_offset: int,
    schema_by_type: Dict[int, Dict[str, Any]],
) -> Optional[int]:
    """
    Find the next valid message start (HEADER + known type) at or after start_offset.
    Returns the byte offset of the message start, or None if no valid message is found.
    """

    data_len = len(data)
    search_offset = start_offset
    find = data.find

    while True:
        position = find(HEADER, search_offset)
        if position == -1 or position + 3 > data_len:
            return None

        msg_type = data[position + 2]
        schema_dict = schema_by_type.get(msg_type)
        if schema_dict is None:
            search_offset = position + 1
            continue

        msg_end = position + schema_dict["total_length"]
        if msg_end <= data_len:
            return position
        return None


def split_file_for_processes(
    file_path: str,
    schemas_by_type: Dict[int, Dict[str, Any]],
) -> List[Tuple[int, int]]:
    """
    Split a .BIN file into aligned byte ranges for parallel parsing.
    Chunks are aligned to valid message boundaries based on schemas, and returned
    as (start, end) offsets suitable for use with mmap slices.
    """

    chunk_bytes = CHUNK_SIZE_BYTES

    with open(file_path, "rb") as file_handle:
        data = mmap.mmap(file_handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            data_len = len(data)

            check_positions = [i * chunk_bytes for i in range(1, (data_len // chunk_bytes) + 1)]
            check_positions = [p for p in check_positions if p < data_len]

            chunk_start_positions: List[int] = [0]

            for check_position in check_positions:
                valid_position = find_next_message_start_offset(data, check_position, schemas_by_type)
                if valid_position is None:
                    break
                # Avoid duplicates if alignment finds the same header twice
                # (e.g., when no valid next message is found and the scan re-checks the same position).
                if valid_position > chunk_start_positions[-1]:
                    chunk_start_positions.append(valid_position)

            if chunk_start_positions[-1] != data_len:
                chunk_start_positions.append(data_len)

            chunks: List[Tuple[int, int]] = [
                (chunk_start_positions[i], chunk_start_positions[i + 1])
                for i in range(len(chunk_start_positions) - 1)
                if chunk_start_positions[i] < chunk_start_positions[i + 1]
            ]
            return chunks

        except FileNotFoundError:
            logger.exception("split_file_for_processes: file not found %s", file_path)
            raise
        except PermissionError:
            logger.exception("split_file_for_processes: permission denied %s", file_path)
            raise
        except Exception:
            logger.exception("split_file_for_processes: unexpected error for %s", file_path)
            raise

        finally:
            data.close()
