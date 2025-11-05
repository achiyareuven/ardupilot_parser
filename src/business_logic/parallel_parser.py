from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union ,Literal
import os
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor,as_completed
from src.business_logic.reader_process import ReaderProcess
from src.business_logic.chunking import split_file_for_processes
from src.utils.helpers import resolve_wanted_type_ids


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
    def _worker_chunk(
        file_path: str,
        start_offset: int,
        end_offset: int,
        schema_by_type: Dict[int, Dict[str, Any]],
        like_pymav: bool = False,
        wanted_ids: Optional[Iterable[int]] = None,
    ) -> List[Dict[str, Any]]:
        with ReaderProcess(file_path, round_like_pymav=like_pymav) as reader:
            reader._schemas_dict_by_type = schema_by_type
            return reader.parse_messages(
                start=start_offset,
                end=end_offset,
                wanted_types=wanted_ids,
            )

    def parse(self) -> List[Dict[str, Any]]:
        logger.debug("ParallelParser.parse: start (mode=%s, path=%s)", self.mode, self.file_path)

        with ReaderProcess(self.file_path, round_like_pymav=self.round_like_pymav) as r:
            r.parse_fmt_messages()
            schemas_by_type = r._schemas_dict_by_type
            schemas_by_name = r._name_to_type_id

        wanted_ids = resolve_wanted_type_ids(self._wanted_raw, schemas_by_name)

        num_workers = self.num_workers or (os.cpu_count() or 1)
        try:
            chunks: List[Tuple[int, int]] = split_file_for_processes(
                file_path=self.file_path,
                schemas_by_type=schemas_by_type,
                num_procs=num_workers,
            )
        except Exception:
            logger.exception("ParallelParser.parse: failed to split file into chunks")
            raise

        if not chunks:
            logger.warning("ParallelParser.parse: no chunks produced (empty file or no valid messages?)")
            return []

        max_workers = min(len(chunks), num_workers)
        logger.debug("ParallelParser.parse: %d chunks, using %d workers", len(chunks), max_workers)

        submit_fn = _worker_chunk if self.mode == "process" else self._worker_chunk
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
                        wanted_ids,
                    ): idx
                    for idx, (start, end) in enumerate(chunks)
                }

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

        logger.debug("ParallelParser.parse: done, total messages=%d", len(all_msgs))
        return all_msgs


_worker_chunk = ParallelParser._worker_chunk



