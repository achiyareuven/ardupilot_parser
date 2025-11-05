from __future__ import annotations
import mmap
import struct
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.utils.constants import HEADER, FMT_TYPE, FMT_PAYLOAD_LEN,MIN_MAGIC_ADVANCE
from src.models.schema import MessageSchema, build_message_schema
from src.utils.helpers import cstr_to_text, is_valid_name



class BinReader:
    def __init__(self, file_path: str, round_like_pymav: bool = False):
        self.file_path = file_path
        self._file_handle = open(self.file_path, "rb")
        self._mmap = mmap.mmap(self._file_handle.fileno(), 0, access=mmap.ACCESS_READ)
        self._schemas_by_type: Dict[int, MessageSchema] = {}
        self._pos_all: int = 0
        self._round_like_pymav: bool = round_like_pymav

    def close(self) -> None:
        try:
            self._mmap.close()
        finally:
            self._file_handle.close()

    def __enter__(self) -> "BinReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def load_fmt_schemas(self) -> None:
        data = self._mmap
        data_len = len(data)
        fmt_header = HEADER + bytes([FMT_TYPE])
        find = data.find
        offset = 0

        while True:
            position = find(fmt_header, offset)
            if position == -1 or position + 3 + FMT_PAYLOAD_LEN > data_len:
                break


            fmt_payload_start = position + 3
            try:
                type_id, total_len, name_b, fmt_b, labels_b = struct.unpack_from(
                    "<BB4s16s64s", data, fmt_payload_start
                )
            except struct.error:
                offset = position + MIN_MAGIC_ADVANCE
                continue

            name = cstr_to_text(name_b)
            fmt_str = cstr_to_text(fmt_b)
            labels_str = cstr_to_text(labels_b)

            if not is_valid_name(name):
                offset = position + MIN_MAGIC_ADVANCE
                continue

            try:
                schema = build_message_schema(
                    type_id=type_id,
                    name=name,
                    ardupilot_format=fmt_str,
                    total_length=total_len,
                    labels_str=labels_str,
                )
            except ValueError:
                offset = position + MIN_MAGIC_ADVANCE
                continue

            self._schemas_by_type[type_id] = schema
            offset = position + MIN_MAGIC_ADVANCE

    def _build_message_dict(self, schema: MessageSchema, values) -> dict:
        msg_dict = {"mavpackettype": schema.name}

        columns = schema.columns
        is_byte_field = schema.is_byte_field
        scale_factors = schema.scale_factors
        round_decimals = schema.round_decimals
        round_mask = schema.round_mask
        like_pymavlink = self._round_like_pymav
        field_count = schema.field_count

        for idx in range(field_count):
            field_name = columns[idx]
            value = values[idx]

            if field_name == "Data":
                msg_dict[field_name] = bytes(value)
                continue

            if is_byte_field[idx]:
                nul_index = value.find(b"\0")
                if nul_index != -1:
                    value = value[:nul_index]
                value = value.decode("ascii", "ignore")

            scale = scale_factors[idx]
            if scale is not None:
                value = value * scale

            if like_pymavlink and round_mask[idx]:
                value = round(value, round_decimals[idx])


            msg_dict[field_name] = value

        return msg_dict

    def parse_messages(self, msg_name: Optional[str] = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        if msg_name is not None:
            out = self.parse_msg_by_type(msg_name)
            return out

        data = self._mmap
        data_len = len(data)
        offset = 0
        find = data.find
        get_schema = self._schemas_by_type.get

        while True:
            position = find(HEADER, offset)
            if position == -1 or position + 3 > data_len:
                break

            msg_type = data[position + 2]

            schema = get_schema(msg_type)
            if schema is None:
                offset = position + MIN_MAGIC_ADVANCE
                continue

            end = position + schema.total_length
            if end > data_len:
                break

            payload_start = position + 3
            try:
                values = schema.struct_obj.unpack_from(data, payload_start)
            except struct.error:
                offset = end
                continue

            out.append(self._build_message_dict(schema, values))
            offset = end

        return out

    def parse_msg_by_type(self, msg_name: str) -> List[Dict[str, Any]]:
        data = self._mmap
        data_len = len(data)
        schema = next((s for s in self._schemas_by_type.values() if s.name == msg_name), None)
        if schema is None:
            return []

        type_id = schema.type_id
        total_len = schema.total_length
        if total_len < 4:
            return []

        type_header = HEADER + bytes([type_id])
        find = data.find
        unpack_from = schema.struct_obj.unpack_from

        out: List[Dict[str, Any]] = []
        offset = 0

        while True:
            position = find(type_header, offset)
            if position == -1:
                break

            end = position + total_len
            if end > data_len:
                break

            if end < data_len and data[end:end + 2] != HEADER:
                offset = position + 1
                continue

            payload_start = position + 3
            try:
                values = unpack_from(data, payload_start)
            except struct.error:
                offset = position + 1
                continue

            out.append(self._build_message_dict(schema, values))

            offset = end

        return out

    def next_message(self) -> Optional[Dict[str, Any]]:
        data = self._mmap
        data_len = len(data)
        find = data.find
        get_schema = self._schemas_by_type.get

        offset = self._pos_all
        while True:
            position = find(HEADER, offset)
            if position == -1 or position + 3 > data_len:
                return None

            msg_type = data[position + 2]

            schema = get_schema(msg_type)
            if schema is None:
                offset = position + MIN_MAGIC_ADVANCE
                continue

            end = position + schema.total_length
            if end > data_len:
                return None

            payload_start = position + 3
            try:
                values = schema.struct_obj.unpack_from(data, payload_start)
            except struct.error:
                offset = end
                continue


            self._pos_all = end
            return self._build_message_dict(schema, values)

    def next_msg_by_type(self, msg_name: str=None) -> Optional[Dict[str, Any]]:

        if msg_name is None:
            return self.next_message()

        data = self._mmap
        data_len = len(data)
        schema = next((s for s in self._schemas_by_type.values() if s.name == msg_name), None)
        if schema is None:
            return None

        type_id = schema.type_id
        total_len = schema.total_length
        if total_len < 4:
            return None

        type_header = HEADER + bytes([type_id])
        find = data.find
        unpack_from = schema.struct_obj.unpack_from

        offset = self._pos_all
        while True:
            position = find(type_header, offset)
            if position == -1 or position + 3 > data_len:
                return None

            end = position + total_len
            if end > data_len:
                return None

            if end < data_len and data[end:end + 2] != HEADER:
                offset = position + 1
                continue

            payload_start = position + 3
            try:
                values = unpack_from(data, payload_start)
            except struct.error:
                offset = position + 1
                continue

            self._pos_all = end
            return self._build_message_dict(schema, values)




