from __future__ import annotations

import struct
from struct import Struct
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type, Union

from src.business_logic.schema import build_dict_schema
from src.utils.constants import FMT_PAYLOAD_LEN, FMT_TYPE, HEADER, MIN_MAGIC_ADVANCE
from src.utils.helpers import cstr_to_text, is_valid_name, open_file_and_mmap, resolve_wanted_type_ids
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)


class BinParser:
    def __init__(self, file_path: str, round_like_pymav: bool = False):
        self.file_path = file_path
        self._file_handle, self._mmap = open_file_and_mmap(file_path)
        self.schemas_dict_by_type: Dict[int, Dict[str, Any]] = {}
        self.name_to_type_id: Dict[str, int] = {}
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

    def __enter__(self) -> "BinParser":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[Any],
    ) -> None:
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
                type_id, total_len, name_b, fmt_b, labels_b = struct.unpack_from("<BB4s16s64s", data, fmt_payload_start)
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
                logger.info(
                    "parse_fmt_messages: build_dict_schema ValueError (name=%r, fmt=%r) pos=%d", name, fmt_str, position
                )
                offset = position + MIN_MAGIC_ADVANCE
                continue
            except Exception:
                logger.exception(
                    "parse_fmt_messages: unexpected error building schema (name=%r, fmt=%r) pos=%d",
                    name,
                    fmt_str,
                    position,
                )
                offset = position + MIN_MAGIC_ADVANCE
                continue

            self.schemas_dict_by_type[type_id] = schema
            self.name_to_type_id = {s["name"]: tid for tid, s in self.schemas_dict_by_type.items()}

            offset = position + MIN_MAGIC_ADVANCE

        logger.debug("parse_fmt_messages: collected %d schemas", len(self.schemas_dict_by_type))

    def _get_struct(self, type_id: int) -> Struct:
        st = self._struct_cache.get(type_id)
        if st is None:
            sch = self.schemas_dict_by_type[type_id]
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
        wanted_names: Optional[Union[str, Iterable[str]]] = None,
    ) -> List[Dict[str, Any]]:

        if not self.name_to_type_id and self.schemas_dict_by_type:
            self.name_to_type_id = {s["name"]: tid for tid, s in self.schemas_dict_by_type.items()}

        data_len = len(self._mmap)
        start = 0 if start is None else max(0, int(start))
        end = data_len if end is None else min(int(end), data_len)

        if wanted_names is None:
            try:
                return self._parse_multi_types_ranged(start=start, end=end, wanted_set=None)
            except Exception:
                logger.exception("parse_messages: unexpected failure in _parse_multi_types_ranged (no filter)")
                return []

        try:
            wanted_types = resolve_wanted_type_ids(wanted_names, self.name_to_type_id)
        except Exception:
            logger.exception("parse_messages: failed to resolve wanted names %r", wanted_names)
            return []

        wanted_set = None if wanted_types is None else set(wanted_types)
        if not wanted_set:
            logger.warning("parse_messages: no matching types for %s", wanted_names)
            return []

        if len(wanted_set) == 1:
            only_type = next(iter(wanted_set))
            try:
                return self._parse_one_type_ranged(start=start, end=end, type_id=only_type)
            except Exception:
                logger.exception("parse_messages: unexpected failure in _parse_one_type_ranged (type_id=%s)", only_type)
                return []

        try:
            return self._parse_multi_types_ranged(start=start, end=end, wanted_set=wanted_set)
        except Exception:
            logger.exception("parse_messages: unexpected failure in _parse_multi_types_ranged (with filter)")
            return []

    def _parse_one_type_ranged(
        self,
        *,
        start: int,
        end: int,
        type_id: int,
    ) -> List[Dict[str, Any]]:

        all_msgs: List[Dict[str, Any]] = []
        data = self._mmap
        find = data.find
        get_schema = self.schemas_dict_by_type.get
        get_struct = self._get_struct
        build_msg = self.build_message_dict

        schema = get_schema(type_id)
        if schema is None:
            return all_msgs

        total_len = schema["total_length"]
        if total_len < 4:
            return all_msgs

        type_header = HEADER + bytes([type_id])
        unpack_from = get_struct(type_id).unpack_from

        position = start
        while True:
            position = find(type_header, position, end)
            if position == -1:
                break

            end_msg = position + total_len
            if end_msg > end:
                break

            if (end_msg + 2) <= end and data[end_msg : end_msg + 2] != HEADER:
                position += 1
                continue

            payload_start = position + 3
            try:
                values = unpack_from(data, payload_start)
            except struct.error:
                position += 1
                continue
            except Exception:
                logger.debug("_parse_one_type_ranged: unexpected unpack error at pos=%d type_id=%d", position, type_id)
                position += 1
                continue

            all_msgs.append(build_msg(schema, values))
            position = end_msg

        return all_msgs

    def _parse_multi_types_ranged(
        self,
        *,
        start: int,
        end: int,
        wanted_set: Optional[Set[int]],
    ) -> List[Dict[str, Any]]:
        all_msgs: List[Dict[str, Any]] = []
        data = self._mmap
        find = data.find
        get_schema = self.schemas_dict_by_type.get
        get_struct = self._get_struct
        build_msg = self.build_message_dict

        position = start
        while True:
            position = find(HEADER, position, end)
            if position == -1:
                break

            msg_type = data[position + 2]
            schema = get_schema(msg_type)
            if schema is None:
                position += 1
                continue

            end_msg = position + schema["total_length"]
            if end_msg > end:
                break

            if (wanted_set is not None) and (msg_type not in wanted_set):
                position = end_msg
                continue

            payload_start = position + 3
            try:
                values = get_struct(msg_type).unpack_from(data, payload_start)
            except struct.error:
                position = end_msg
                continue
            except Exception:
                logger.debug("_parse_multi_types_ranged: unexpected unpack error at pos=%d type=%d", position, msg_type)
                position = end_msg
                continue

            all_msgs.append(build_msg(schema, values))
            position = end_msg

        return all_msgs


if __name__ == "__main__":
    from datetime import datetime

    star = datetime.now()
    path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
    with BinParser(path, round_like_pymav=True) as reader:
        reader.parse_fmt_messages()
        messages = reader.parse_messages(wanted_names="ATT")
        en = datetime.now()
    print(f"Parsed {len(messages)} messages in {en - star}")
