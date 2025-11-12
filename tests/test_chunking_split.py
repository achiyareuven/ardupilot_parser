from __future__ import annotations

import os
import mmap
import tempfile
from typing import Any, Dict, List, Tuple

import pytest

from src.utils.constants import HEADER
from src.utils.logger import Logger
from src.business_logic.chunking import (
    find_next_message_start_offset,
    split_file_for_processes,
)

logger = Logger.get_logger(__name__)


def make_msg(total_len: int, type_id: int) -> bytes:
    return HEADER + bytes([type_id]) + b"x" * (total_len - 3)


@pytest.fixture
def fake_schemas() -> Dict[int, Dict[str, Any]]:
    return {
        0: {"total_length": 13},
        1: {"total_length": 23},
        2: {"total_length": 33},
        3: {"total_length": 43},
    }


@pytest.fixture
def build_file(tmp_path):
    def _build(chunks: List[bytes]) -> str:
        p = tmp_path / "test_file.bin"
        p.write_bytes(b"".join(chunks))
        return str(p)
    return _build


def test_find_next_message_at_exact_position(fake_schemas, build_file):
    data_bytes = make_msg(23, 1) + make_msg(33, 2)
    path = build_file([data_bytes])

    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            pos = find_next_message_start_offset(mm, 0, fake_schemas)
            assert pos == 0

            start_mid = 10
            pos2 = find_next_message_start_offset(mm, start_mid, fake_schemas)
            assert pos2 == len(make_msg(23, 1))
        finally:
            mm.close()


def test_find_next_message_skips_unknown_types(fake_schemas, build_file):
    data_bytes = make_msg(13, 0) + make_msg(13, 9) + make_msg(33, 2)
    path = build_file([data_bytes])

    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            start_at_unknown = len(make_msg(13, 0))
            pos = find_next_message_start_offset(mm, start_at_unknown, fake_schemas)
            assert pos == len(make_msg(13, 0)) + len(make_msg(13, 9))
        finally:
            mm.close()


def test_find_next_message_none_when_truncated_at_end(fake_schemas, build_file):
    known = make_msg(23, 1)
    truncated_header = HEADER + bytes([9])  # total_length של type=2 אמור להיות 33, אבל אין מספיק נתונים
    path = build_file([known + truncated_header])

    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            pos = find_next_message_start_offset(
                mm, len(known), fake_schemas
            )
            assert pos is None
        finally:
            mm.close()


def test_split_by_num_procs_basic(fake_schemas, build_file):
    msgs = [
        make_msg(13, 0),
        make_msg(23, 1),
        make_msg(33, 2),
        make_msg(43, 3),
        make_msg(33, 2),
        make_msg(23, 1),
    ]
    path = build_file(msgs)
    data_len = sum(len(m) for m in msgs)

    chunks = split_file_for_processes(path, fake_schemas, num_procs=3)
    assert len(chunks) == 3

    assert chunks[0][0] == 0
    assert chunks[-1][1] == data_len
    for (s1, e1), (s2, e2) in zip(chunks, chunks[1:]):
        assert e1 == s2

    raw = b"".join(msgs)
    for start, _ in chunks:
        assert raw[start : start + 2] == HEADER
        msg_type = raw[start + 2]
        assert msg_type in fake_schemas


def test_split_by_chunk_bytes_alignment(fake_schemas, build_file):
    msgs = [make_msg(13, 0)] * 10 + [make_msg(23, 1)] * 5 + [make_msg(33, 2)] * 3
    path = build_file(msgs)
    raw = b"".join(msgs)

    chunks = split_file_for_processes(
        path, fake_schemas, num_procs=1, chunk_bytes=20
    )
    assert len(chunks) >= 2

    for start, end in chunks:
        assert raw[start : start + 2] == HEADER
        assert raw[end - 1 : end]


def test_split_empty_file_returns_empty_list(tmp_path, fake_schemas):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    assert split_file_for_processes(str(path), fake_schemas, num_procs=4) == []


def test_split_raises_on_missing_file(fake_schemas):
    missing = os.path.join(tempfile.gettempdir(), "definitely_missing_123456.bin")
    with pytest.raises(FileNotFoundError):
        _ = split_file_for_processes(missing, fake_schemas, num_procs=2)
