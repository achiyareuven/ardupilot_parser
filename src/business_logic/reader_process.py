from __future__ import annotations
import struct
from typing import Any, Dict, List, Optional, Iterable, Tuple
from src.utils.constants import HEADER, FMT_TYPE, FMT_PAYLOAD_LEN, MIN_MAGIC_ADVANCE
from src.models.schema import build_dict_schema
from src.utils.helpers import cstr_to_text, is_valid_name , open_file_and_mmap
from struct import Struct
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)


class ReaderProcess:
    def __init__(self, file_path: str, round_like_pymav: bool = False):
        self.file_path = file_path
        self._file_handle, self._mmap = open_file_and_mmap(file_path)
        self._schemas_dict_by_type = {}
        self._name_to_type_id = {}
        self._struct_cache: Dict[int, Struct] = {}
        self.round_like_pymav: bool = round_like_pymav



    def close(self) -> None:
        try:
            if self._mmap is not None:
                self._mmap.close()
        finally:
            try:
                if self._file_handle is not None:
                    self._file_handle.close()
            except Exception:
                logger.exception("ReaderProcess.close: failed closing file %s", self.file_path)

    def __enter__(self) -> "ReaderProcess":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def parse_fmt_messages(self) -> None:
        data = self._mmap
        data_len = len(data)
        pattern = HEADER + bytes([FMT_TYPE])
        find = data.find
        offset = 0

        logger.debug("parse_fmt_messages: start scanning FMTs in %s (len=%d)", self.file_path, data_len)

        while True:
            position = find(pattern, offset)
            if position == -1 or position + 3 + FMT_PAYLOAD_LEN > data_len:
                break

            fmt_payload_start = position + 3
            try:
                type_id, total_len, name_b, fmt_b, labels_b = struct.unpack_from(
                    "<BB4s16s64s", data, fmt_payload_start
                )
            except struct.error:
                logger.debug("parse_fmt_messages: struct.error at pos=%d, skipping", position)
                offset = position + MIN_MAGIC_ADVANCE
                continue

            name = cstr_to_text(name_b)
            fmt_str = cstr_to_text(fmt_b)
            labels_str = cstr_to_text(labels_b)

            if not is_valid_name(name):
                logger.debug("parse_fmt_messages: invalid FMT name %r at pos=%d", name, position)
                offset = position + MIN_MAGIC_ADVANCE
                continue

            try:
                schema = build_dict_schema(
                    type_id=type_id,
                    name=name,
                    ardupilot_format=fmt_str,
                    total_length=total_len,
                    labels_str=labels_str,
                )
            except ValueError:
                logger.debug("parse_fmt_messages: build_dict_schema ValueError (name=%r, fmt=%r) pos=%d",
                             name, fmt_str, position)
                offset = position + MIN_MAGIC_ADVANCE
                continue
            except Exception:
                logger.exception("parse_fmt_messages: unexpected error building schema (name=%r, fmt=%r) pos=%d",
                                 name, fmt_str, position)
                offset = position + MIN_MAGIC_ADVANCE
                continue

            self._schemas_dict_by_type[type_id] = schema
            self._name_to_type_id = {s["name"]: tid for tid, s in self._schemas_dict_by_type.items()}

            offset = position + MIN_MAGIC_ADVANCE

        logger.debug("parse_fmt_messages: collected %d schemas", len(self._schemas_dict_by_type))

    def _get_struct(self, type_id: int) -> Struct:
        st = self._struct_cache.get(type_id)
        if st is None:
            sch = self._schemas_dict_by_type[type_id]
            st = Struct(sch["struct_fmt"])
            self._struct_cache[type_id] = st
        return st

    def build_message_dict(self, schema: Dict[str, Any], values: Tuple[Any, ...]) -> Dict[str, Any]:
        record: Dict[str, Any] = {"mavpackettype": schema["name"]}

        columns = schema["columns"]
        is_byte_field = schema["is_byte_field"]
        scale_factors = schema["scale_factors"]
        round_decimals = schema["round_decimals"]
        round_mask = schema["round_mask"]
        like_pymavlink = self.round_like_pymav
        field_count = schema["field_count"]

        for idx in range(field_count):
            field_name = columns[idx]
            value = values[idx]

            if field_name == "Data":
                record[field_name] = bytes(value)
                continue

            if is_byte_field[idx]:
                value = value.partition(b"\0")[0].decode("ascii", "ignore")

            scale = scale_factors[idx]
            if scale is not None:
                value = value * scale

            if like_pymavlink and round_mask[idx]:
                value = round(value, round_decimals[idx])

            record[field_name] = value

        return record

    def parse_messages(
        self,
        *,
        start: Optional[int] = None,
        end: Optional[int] = None,
        wanted_types: Optional[Iterable[int]] = None,
    ) -> List[Dict[str, Any]]:

        out: List[Dict[str, Any]] = []

        data = self._mmap
        data_len = len(data)
        offset = 0 if start is None else max(0, int(start))
        stop_at = data_len if end is None else min(int(end), data_len)

        if offset >= stop_at:
            return out

        logger.debug("parse_messages: range=[%d,%d) len=%d", offset, stop_at, data_len)

        find = data.find
        get_schema = self._schemas_dict_by_type.get
        wanted_set = None if wanted_types is None else set(wanted_types)

        while True:
            position = find(HEADER, offset)
            if position == -1 or position + 3 > stop_at:
                break

            msg_type = data[position + 2]
            sch = get_schema(msg_type)
            if sch is None:
                offset = position + MIN_MAGIC_ADVANCE
                continue

            end_msg = position + sch["total_length"]
            if end_msg > stop_at:
                break

            payload_start = position + 3
            try:
                struct_obj = self._get_struct(msg_type)
                values = struct_obj.unpack_from(data, payload_start)
            except struct.error:
                logger.debug("parse_messages: struct.error at pos=%d type=%d, skipping to %d",
                             position, msg_type, end_msg)
                offset = end_msg
                continue
            except Exception:
                logger.exception("parse_messages: unexpected unpack error at pos=%d type=%d", position, msg_type)
                offset = end_msg
                continue

            if (wanted_set is None) or (msg_type in wanted_set):
                rec = self.build_message_dict(sch, values)
                out.append(rec)

            offset = end_msg

        logger.debug("parse_messages: produced %d messages", len(out))
        return out
