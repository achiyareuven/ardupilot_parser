from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, Union

from src.business_logic.bin_parser import BinParser
from src.business_logic.chunking import split_file_for_processes
from src.utils.constants import CHUNK_SIZE_BYTES
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)


class ParallelParser:
    """Parallel wrapper around BinParser using processes or threads."""

    def __init__(
        self,
        file_path: str,
        *,
        mode: Literal["process", "thread"] = "process",
        num_workers: Optional[int] = None,
        wanted_types: Optional[Union[str, Iterable[str]]] = None,
    ):
        """
        Initialize a ParallelParser for the given .BIN file.
        mode selects between process-based and thread-based execution.
        """
        if mode not in ("process", "thread"):
            raise ValueError("mode must be 'process' or 'thread'")
        self.file_path = file_path
        self.mode = mode
        self.num_workers = num_workers
        self._wanted_raw = wanted_types

    @staticmethod
    def worker_chunk(
        file_path: str,
        start_offset: int,
        end_offset: int,
        schema_by_type: Dict[int, Dict[str, Any]],
        wanted_names: Optional[Union[str, Iterable[str]]] = None,
        name_to_id: Optional[Dict[str, int]] = None,
        timebase: Optional[float] = None,
        first_us_stamp: Optional[int] = None,
        have_timebase: bool = False,
        last_timestamp: Optional[float] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse a single byte range [start_offset, end_offset) in a worker.
        Rebuilds a BinParser, injects schemas and timebase data, and returns
        messages grouped by name.
        """


        with BinParser(file_path) as reader:
            reader.schemas_dict_by_type = schema_by_type
            reader.name_to_type_id = name_to_id or {}

            if  have_timebase and (timebase is not None):
                reader.timestamp_builder.timebase = timebase
                reader.timestamp_builder.first_us_stamp = first_us_stamp
                reader.timestamp_builder.have_timebase = True

                if last_timestamp is not None:
                    reader.timestamp_builder.timestamp = last_timestamp
                else:
                    reader.timestamp_builder.timestamp = timebase

            return reader.parse_messages(
                start=start_offset,
                end=end_offset,
                wanted_names=wanted_names,
            )

    def parse(self) -> Dict[str, List[Dict[str, Any]]]:
        logger.info(
            "Parse started | path=%s | mode=%s ",
            self.file_path,
            self.mode,
        )
        """
        Parse the log in parallel and merge results from all chunks.
        Splits the file into aligned chunks, dispatches them to workers and
        returns a dict of messages grouped by name.
        """

        with BinParser(self.file_path) as reader:
            reader.parse_fmt_messages()
            schemas_by_type = reader.schemas_dict_by_type
            schemas_by_name = reader.name_to_type_id

            reader.scan_timebase_from_log()
            ts_builder = reader.timestamp_builder

            have_timebase = ts_builder.have_timebase
            timebase = ts_builder.timebase if have_timebase else None
            first_us_stamp = ts_builder.first_us_stamp
            last_timestamp = ts_builder.timestamp if have_timebase else None

        logger.info(
            "FMT scan completed | schemas=%d | have_timebase=%s",
            len(schemas_by_type),
            have_timebase,
        )

        num_workers = self.num_workers or (os.cpu_count() or 1)

        try:
            chunks: List[Tuple[int, int]] = split_file_for_processes(
                file_path=self.file_path,
                schemas_by_type=schemas_by_type,
                num_procs=num_workers,
                chunk_bytes=CHUNK_SIZE_BYTES,
            )
        except Exception:
            logger.exception("ParallelParser.parse: failed to split file into chunks")
            raise

        if not chunks:
            logger.warning("ParallelParser.parse: no chunks produced (empty file or no valid messages?)")
            raise RuntimeError("No chunks produced")

        max_workers = min(len(chunks), num_workers)
        logger.info("File split | chunks=%d | workers=%d", len(chunks), max_workers)

        submit_function = ParallelParser.worker_chunk if self.mode == "process" else self.worker_chunk
        Executor = ProcessPoolExecutor if self.mode == "process" else ThreadPoolExecutor

        results_by_index: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
        try:
            with Executor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        submit_function,
                        self.file_path,
                        start,
                        end,
                        schemas_by_type,
                        self._wanted_raw,
                        schemas_by_name,
                        timebase,
                        first_us_stamp,
                        have_timebase,
                        last_timestamp,
                    ): idx
                    for idx, (start, end) in enumerate(chunks)
                }
                logger.info("Parallel execution started | futures=%d", len(futures))

                for fut in as_completed(futures):
                    idx = futures[fut]
                    try:
                        results_by_index[idx] = fut.result()
                    except Exception:
                        logger.exception("ParallelParser.parse: worker failed (chunk idx=%d)", idx)
                        results_by_index[idx] = {}
        except Exception:
            logger.exception("ParallelParser.parse: executor-level failure")
            raise

        merged: Dict[str, List[Dict[str, Any]]] = {}
        for i in range(len(chunks)):
            chunk_msgs_by_type = results_by_index.get(i, {})
            if not chunk_msgs_by_type:
                continue

            for msg_name, msg_list in chunk_msgs_by_type.items():
                msgs = merged.get(msg_name)
                if msgs is None:
                    msgs = []
                    merged[msg_name] = msgs
                msgs.extend(msg_list)

        total_msgs = sum(len(lst) for lst in merged.values())
        logger.info("ParallelParser.parse: done, total messages=%d", total_msgs)
        return merged
