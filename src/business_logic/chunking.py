from __future__ import annotations
import mmap
from typing import Any, Dict, List, Optional, Tuple, Set
from src.utils.constants import HEADER
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)


def find_next_message_start_offset(
    data: mmap.mmap,
    start_offset: int,
    schema_by_type: Dict[int, Dict[str, Any]],
) -> Optional[int]:
    data_len = len(data)
    search_offset = start_offset
    find = data.find

    logger.debug("find_next_message_start_offset: start_offset=%d, data_len=%d", start_offset, data_len)

    while True:
        position = find(HEADER, search_offset)
        if position == -1 or position + 3 > data_len:
            logger.debug("find_next_message_start_offset: no more headers (pos=%d)", position)
            return None

        msg_type = data[position + 2]
        schema_dict = schema_by_type.get(msg_type)
        if schema_dict is None:
            search_offset = position + 1
            continue

        msg_end = position + schema_dict["total_length"]
        if msg_end <= data_len:
            logger.debug("find_next_message_start_offset: found start at %d (type=%d)", position, msg_type)
            return position

        logger.debug("find_next_message_start_offset: truncated message at %d (type=%d)", position, msg_type)
        return None


def split_file_for_processes(
    file_path: str,
    schemas_by_type: Dict[int, Dict[str, Any]],
    num_procs: int,
) -> List[Tuple[int, int]]:
    if num_procs < 1:
        num_procs = 1

    logger.debug("split_file_for_processes: path=%s num_procs=%d", file_path, num_procs)

    try:
        with open(file_path, "rb") as file_handle:
            try:
                data = mmap.mmap(file_handle.fileno(), 0, access=mmap.ACCESS_READ)
            except Exception:
                logger.exception("split_file_for_processes: failed to mmap file %s", file_path)
                raise

            try:
                data_len = len(data)
                if data_len == 0:
                    logger.warning("split_file_for_processes: empty file %s", file_path)
                    return []

                approx_chunk_size_bytes = max(1, data_len // num_procs)
                chunk_start_positions: List[int] = [0]

                for i in range(1, num_procs):
                    check_position = i * approx_chunk_size_bytes
                    if check_position >= data_len:
                        break

                    valid_position = find_next_message_start_offset(data, check_position, schemas_by_type)
                    if valid_position is None:
                        break
                    if valid_position > chunk_start_positions[-1]:
                        chunk_start_positions.append(valid_position)

                if chunk_start_positions[-1] != data_len:
                    chunk_start_positions.append(data_len)

                chunks: List[Tuple[int, int]] = []
                for i in range(len(chunk_start_positions) - 1):
                    start_pos, end_pos = chunk_start_positions[i], chunk_start_positions[i + 1]
                    if start_pos < end_pos:
                        chunks.append((start_pos, end_pos))

                logger.debug(
                    "split_file_for_processes: data_len=%d chunk_size≈%d chunks=%d",
                    data_len, approx_chunk_size_bytes, len(chunks)
                )
                return chunks

            finally:
                try:
                    data.close()
                except Exception:
                    logger.exception("split_file_for_processes: failed to close mmap for %s", file_path)

    except FileNotFoundError:
        logger.exception("split_file_for_processes: file not found %s", file_path)
        raise
    except PermissionError:
        logger.exception("split_file_for_processes: permission denied %s", file_path)
        raise
    except Exception:
        logger.exception("split_file_for_processes: unexpected error for %s", file_path)
        raise
