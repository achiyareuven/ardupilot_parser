import io
import mmap
import tempfile
import pytest

from src.utils.constants import HEADER
from src.business_logic.chunking import split_file_for_processes, find_next_message_start_offset


# ---------- עזר לבניית קובץ בינארי מזויף ----------
def make_fake_bin(sizes: list[int]) -> bytes:

    out = bytearray()
    for i, sz in enumerate(sizes):
        out += HEADER
        out += bytes([i % 255])
        out += bytes(sz)
    return bytes(out)


@pytest.fixture
def fake_schemas():
    return {
        0: {"total_length": 10},
        1: {"total_length": 20},
        2: {"total_length": 30},
    }


# ---------------------- find_next_message_start_offset ----------------------

def test_find_next_message_start_offset_valid(fake_schemas):
    data = make_fake_bin([10, 20, 30])
    mm = mmap.mmap(-1, len(data))
    mm.write(data)
    mm.seek(0)

    pos = find_next_message_start_offset(mm, 5, fake_schemas)
    assert pos == (len(HEADER) + 1 + 10)

    pos2 = find_next_message_start_offset(mm, 15, fake_schemas)
    assert pos2 is not None and pos2 > 0

    mm.close()


def test_find_next_message_start_offset_no_valid_header(fake_schemas):
    mm = mmap.mmap(-1, 10)
    mm.write(b"XXXXXXXXXX")  # בלי HEADER בכלל
    mm.seek(0)
    result = find_next_message_start_offset(mm, 0, fake_schemas)
    assert result is None
    mm.close()


# --------------------------- split_file_for_processes ---------------------------

def test_split_file_for_processes_basic(fake_schemas):
    fake_data = make_fake_bin([10, 20, 30, 40, 50])
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(fake_data)
        tmp_path = tmp.name

    chunks = split_file_for_processes(tmp_path, fake_schemas, num_procs=3)


    assert isinstance(chunks, list)
    assert all(isinstance(t, tuple) and len(t) == 2 for t in chunks)

    for (s, e) in chunks:
        assert s < e
    for i in range(len(chunks) - 1):
        assert chunks[i][1] == chunks[i + 1][0]


def test_split_file_for_processes_empty_file(fake_schemas):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"")
        tmp_path = tmp.name

    chunks = split_file_for_processes(tmp_path, fake_schemas, num_procs=4)
    assert chunks == []


def test_split_file_for_processes_one_proc(fake_schemas):
    fake_data = make_fake_bin([10, 20, 30])
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(fake_data)
        tmp_path = tmp.name

    chunks = split_file_for_processes(tmp_path, fake_schemas, num_procs=1)
    assert len(chunks) == 1
    assert chunks[0][0] == 0
    with open(tmp_path, "rb") as f:
        f.seek(0, io.SEEK_END)
        assert chunks[0][1] == f.tell()


def test_split_file_for_processes_invalid_path(fake_schemas):
    with pytest.raises(FileNotFoundError):
        split_file_for_processes("non_existing_file.bin", fake_schemas, num_procs=2)


def test_find_next_message_start_is_forward_only(fake_schemas):
    data = make_fake_bin([10, 20])
    mm = mmap.mmap(-1, len(data)); mm.write(data); mm.seek(0)
    expected = len(HEADER) + 1 + 10
    assert find_next_message_start_offset(mm, 5, fake_schemas) == expected
    mm.close()
