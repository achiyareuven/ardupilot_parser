from __future__ import annotations
from src.business_logic.reader_process import ReaderProcess
from datetime import datetime
import os
from typing import Any, Dict, List, Optional, Iterable, Tuple, Union
from concurrent.futures import ProcessPoolExecutor, as_completed
from src.business_logic.chunking import split_file_for_processes
from src.utils.helpers import resolve_wanted_type_ids


class MultiProcess:
    def __init__(self, file_path: str, round_like_pymav: bool = False,
                 num_procs: Optional[int] = None,
                 wanted_types: Optional[Union[str, Iterable[str]]] = None):
        self.file_path = file_path
        self.round_like_pymav = round_like_pymav
        self.num_procs = num_procs
        self._wanted_raw = wanted_types

    @staticmethod
    def _worker_process_chunk(
        file_path: str,
        start_offset: int,
        end_offset: int,
        schema_by_type: Dict[int, Dict[str, Any]],
        like_pymav: bool = False,
        wanted_ids: Optional[Iterable[int]] = None,   # ← שם עקבי
    ) -> List[Dict[str, Any]]:
        with ReaderProcess(file_path, round_like_pymav=like_pymav) as reader:
            reader._schemas_dict_by_type = schema_by_type  # portable schemas
            return reader.parse_messages(
                start=start_offset,
                end=end_offset,
                wanted_types=wanted_ids,
            )

    def parse_bin_multiprocess(self) -> List[Dict[str, Any]]:
        with ReaderProcess(file_path=self.file_path,
                           round_like_pymav=self.round_like_pymav) as reader:
            reader.parse_fmt_messages()
            schemas_by_type = reader._schemas_dict_by_type
            schemas_by_name = reader._name_to_type_id

        wanted_ids = resolve_wanted_type_ids(self._wanted_raw, schemas_by_name)

        num_procs = self.num_procs or (os.cpu_count() or 1)
        chunks: List[Tuple[int, int]] = split_file_for_processes(
            file_path=self.file_path,
            schemas_by_type=schemas_by_type,
            num_procs=num_procs,
        )
        if not chunks:
            return []

        results_by_index: Dict[int, List[Dict[str, Any]]] = {}
        with ProcessPoolExecutor(max_workers=min(len(chunks), num_procs)) as pool:
            futures = {
                pool.submit(
                    _worker_process_chunk,
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
                    results_by_index[idx] = []

        all_messages: List[Dict[str, Any]] = []
        for idx in range(len(chunks)):
            all_messages.extend(results_by_index.get(idx, []))
        return all_messages


_worker_process_chunk = MultiProcess._worker_process_chunk


if __name__ == "__main__":
    path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
    start = datetime.now()
    decoder = MultiProcess(file_path=path,round_like_pymav=True, num_procs=8,wanted_types="GPS")
    messages = decoder.parse_bin_multiprocess()
    end = datetime.now()
    print(f"Parsed {len(messages)} messages in {end - start}")

