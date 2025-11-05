from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Union ,Iterable
from src.business_logic.reader_process import ReaderProcess
from src.business_logic.chunking import split_file_for_processes
from src.utils.helpers import resolve_wanted_type_ids
import os


class MultiThread:
    def __init__(
        self,
        file_path: str,
        round_like_pymav: bool = False,
        num_threads: Optional[int] = None,
        wanted_types: Optional[Union[str, Iterable[str]]] = None,
    ):
        self.file_path = file_path
        self.round_like_pymav = round_like_pymav
        self.num_threads = num_threads
        self._wanted_raw = wanted_types

    @staticmethod
    def _worker_thread_chunk(
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

    def parse_bin_multithread(self) -> List[Dict[str, Any]]:
        with ReaderProcess(self.file_path, round_like_pymav=self.round_like_pymav) as reader:
            reader.parse_fmt_messages()
            schemas_by_type = reader._schemas_dict_by_type
            schemas_by_name = reader._name_to_type_id

        wanted_ids = resolve_wanted_type_ids(self._wanted_raw, schemas_by_name)

        nthreads = self.num_threads or (os.cpu_count() or 4)
        chunks = split_file_for_processes(self.file_path, schemas_by_type, nthreads)
        if not chunks:
            return []

        results_by_index: Dict[int, List[Dict[str, Any]]] = {}
        with ThreadPoolExecutor(max_workers=min(len(chunks), nthreads)) as pool:
            futures = {
                pool.submit(
                    self._worker_thread_chunk,
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
                results_by_index[idx] = fut.result()

        all_msgs: List[Dict[str, Any]] = []
        for i in range(len(chunks)):
            all_msgs.extend(results_by_index.get(i, []))
        return all_msgs



