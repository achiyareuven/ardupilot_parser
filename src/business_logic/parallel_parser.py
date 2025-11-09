from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, Union

from src.business_logic.bin_parsr import BinParser
from src.business_logic.chunking import split_file_for_processes
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)


class ParallelParser:

    def __init__(
        self,
        file_path: str,
        *,
        mode: Literal["process", "thread"] = "process",
        num_workers: Optional[int] = None,
        round_like_pymav: bool = False,
        wanted_types: Optional[Union[str, Iterable[str]]] = None,
    ):
        if mode not in ("process", "thread"):
            raise ValueError("mode must be 'process' or 'thread'")
        self.file_path = file_path
        self.mode = mode
        self.num_workers = num_workers
        self.round_like_pymav = round_like_pymav
        self._wanted_raw = wanted_types

    @staticmethod
    def worker_chunk(
        file_path: str,
        start_offset: int,
        end_offset: int,
        schema_by_type: Dict[int, Dict[str, Any]],
        like_pymav: bool = False,
        wanted_names: Optional[Union[str, Iterable[str]]] = None,
        name_to_id: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        with BinParser(file_path, round_like_pymav=like_pymav) as reader:
            reader.schemas_dict_by_type = schema_by_type
            reader.name_to_type_id = name_to_id or {}
            return reader.parse_messages(
                start=start_offset,
                end=end_offset,
                wanted_names=wanted_names,
            )

    def parse(self) -> List[Dict[str, Any]]:
        logger.info(
            "Parse started | path=%s | mode=%s | like_pymav=%s",
            self.file_path, self.mode, self.round_like_pymav
        )

        with BinParser(self.file_path, round_like_pymav=self.round_like_pymav) as r:
            r.parse_fmt_messages()
            schemas_by_type = r.schemas_dict_by_type
            schemas_by_name = r.name_to_type_id

        logger.info("FMT scan completed | schemas=%d", len(schemas_by_type))

        num_workers = self.num_workers or (os.cpu_count() or 1)
        CHUNK_SIZE_BYTES = 5 * 1024 * 1024

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

        submit_fn = ParallelParser.worker_chunk if self.mode == "process" else self.worker_chunk
        Executor = ProcessPoolExecutor if self.mode == "process" else ThreadPoolExecutor

        results_by_index: Dict[int, List[Dict[str, Any]]] = {}
        try:
            with Executor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        submit_fn,
                        self.file_path,
                        start,
                        end,
                        schemas_by_type,
                        self.round_like_pymav,
                        self._wanted_raw,
                        schemas_by_name,
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
                        results_by_index[idx] = []
        except Exception:
            logger.exception("ParallelParser.parse: executor-level failure")
            raise

        all_msgs: List[Dict[str, Any]] = []
        for i in range(len(chunks)):
            all_msgs.extend(results_by_index.get(i, []))

        logger.info("ParallelParser.parse: done, total messages=%d", len(all_msgs))
        return all_msgs



