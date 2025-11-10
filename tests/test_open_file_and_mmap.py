import mmap
import pytest
from src.utils.helpers import open_file_and_mmap



def test_open_file_and_mmap_success(tmp_path):
    path = tmp_path / "ok.bin"
    path.write_bytes(b"ABCDEF")

    fh = mm = None
    try:
        fh, mm = open_file_and_mmap(str(path))
        assert not fh.closed
        assert isinstance(mm, mmap.mmap)
        assert len(mm) == path.stat().st_size

        assert mm[:3] == b"ABC"
    finally:
        if mm is not None:
            mm.close()
        if fh is not None and not fh.closed:
            fh.close()


def test_rejects_non_bin_extension_raises_value_error(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_bytes(b"x")

    with pytest.raises(ValueError, match=r"Path must end with \.bin"):
        open_file_and_mmap(str(path))


def test_file_not_found_raises_file_not_found_error(tmp_path):
    missing = tmp_path / "missing.bin"
    with pytest.raises(FileNotFoundError):
        open_file_and_mmap(str(missing))

def test_empty_file_raises_value_error(tmp_path):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")

    with pytest.raises(ValueError, match="empty file"):
        open_file_and_mmap(str(path))
