import os
import pytest

import src.business_logic.parallel_parser as pp


class FakeBinParserThread:
    wanted_log = []

    def __init__(self, file_path):
        self.file_path = file_path
        self.schemas_dict_by_type = {}
        self.name_to_type_id = {}

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

    def parse_fmt_messages(self):
        self.schemas_dict_by_type = {1: {"total_length": 10}, 2: {"total_length": 20}}
        self.name_to_type_id = {"A": 1, "B": 2}

    def parse_messages(self, *, start=None, end=None, wanted_names=None):
        FakeBinParserThread.wanted_log.append(wanted_names)
        s = 0 if start is None else start
        e = -1 if end is None else end
        return [{"chunk": (s, e), "data": f"wanted={wanted_names}"}]


def test_init_invalid_mode_raises():
    with pytest.raises(ValueError):
        pp.ParallelParser(file_path="dummy.bin", mode="gpu")

def test_init_thread_and_process_modes():
    t = pp.ParallelParser("dummy.bin", mode="thread", num_workers=16)
    assert t.mode == "thread" and t.num_workers == 16

    p = pp.ParallelParser("dummy.bin", mode="process", num_workers=2)
    assert p.mode == "process" and p.num_workers == 2


def _patch_thread_env(monkeypatch, *, chunks):
    monkeypatch.setattr(pp, "BinParser", FakeBinParserThread, raising=True)
    monkeypatch.setattr(pp, "split_file_for_processes", lambda **kw: chunks, raising=True)

def test_parse_thread_happy_path(monkeypatch):
    _patch_thread_env(monkeypatch, chunks=[(0, 10), (10, 20)])
    FakeBinParserThread.wanted_log.clear()

    parser = pp.ParallelParser(
        file_path="dummy.bin",
        mode="thread",
        num_workers=4,
        wanted_types=["A", "B"],
    )
    out = parser.parse()

    assert len(out) == 2
    assert out[0]["chunk"] == (0, 10)
    assert out[1]["chunk"] == (10, 20)
    assert FakeBinParserThread.wanted_log == [["A", "B"], ["A", "B"]]

def test_parse_thread_no_chunks_raises(monkeypatch):
    _patch_thread_env(monkeypatch, chunks=[])
    parser = pp.ParallelParser(file_path="dummy.bin", mode="thread", num_workers=2)
    with pytest.raises(RuntimeError, match="No chunks"):
        parser.parse()

def test_parse_thread_worker_exception_is_caught(monkeypatch):
    _patch_thread_env(monkeypatch, chunks=[(0, 10), (10, 20), (20, 30)])
    FakeBinParserThread.wanted_log.clear()

    orig_worker = pp.ParallelParser.worker_chunk

    def boom_worker(file_path, start_offset, end_offset, schema_by_type, wanted_names=None, name_to_id=None):
        if (start_offset, end_offset) == (10, 20):
            raise RuntimeError("boom")
        return orig_worker(file_path, start_offset, end_offset, schema_by_type, wanted_names, name_to_id)

    monkeypatch.setattr(pp.ParallelParser, "worker_chunk", staticmethod(boom_worker), raising=True)

    parser = pp.ParallelParser(file_path="dummy.bin", mode="thread", num_workers=3)
    out = parser.parse()


    assert len(out) == 2
    assert out[0]["chunk"] == (0, 10)
    assert out[1]["chunk"] == (20, 30)

