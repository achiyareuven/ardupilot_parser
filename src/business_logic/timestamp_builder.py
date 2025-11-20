from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence


@dataclass
class TimestampBuilder:
    """
    Build and maintain real timestamps for ArduPilot messages.
    Tracks GPS-based timebase, first TimeUS value, and produces
    absolute timestamps for each message during parsing.
    """

    timebase: float = 0.0
    timestamp: float = 0.0
    first_us_stamp: Optional[int] = None
    have_timebase: bool = False

    def _gpsTimeToTime(self, week: int, msec: int) -> float:
        """
        Convert GPS (week, msec-of-week) into a Unix timestamp (seconds).
        Applies GPS epoch offset and GPS–UTC leap second correction.
        """
        epoch = 86400 * (10 * 365 + int((1980 - 1969) / 4) + 1 + 6 - 2)
        return epoch + 86400 * 7 * week + msec * 0.001 - 18.0

    @staticmethod
    def _type_has_good_TimeMS(msg_name: str) -> bool:
        """
        Return True if the message type has a reliable TimeMS field.
        ACC* and GYR* messages often contain invalid or unstable TimeMS values.
        """
        if msg_name.startswith("ACC"):
            return False
        if msg_name.startswith("GYR"):
            return False
        return True

    def _should_use_msec_field0(
        self,
        msg_name: str,
        columns: Sequence[str],
        msg: Dict[str, Any],
    ) -> bool:
        """
        Determine whether to use TimeMS (field 0) as a fallback timestamp.
        Only used when:
        - Message has a good TimeMS field.
        - `columns[0] == "TimeMS"`.
        - Time is monotonic (no backward jumps).
        """
        if not self._type_has_good_TimeMS(msg_name):
            return False

        if not columns or columns[0] != "TimeMS":
            return False

        time_ms = msg.get("TimeMS")
        if time_ms is None:
            return False

        if self.timebase + time_ms * 0.001 < self.timestamp:
            return False

        return True

    def update_timebase_from_msg(
            self,
            msg_dict: Dict[str, Any],
            *,
            columns: Sequence[str],
    ) -> None:
        """
        Update internal timebase state during the initial scan.
        Tracks first TimeUS and initializes timebase if GPS+TimeUS are available.
        Does not return a timestamp.
        """

        if columns and columns[0] == "TimeUS" and "TimeUS" in msg_dict:
            us_val = int(msg_dict["TimeUS"])
            if self.first_us_stamp is None:
                self.first_us_stamp = us_val

        if self.have_timebase:
            return

        gwk = msg_dict.get("GWk")
        gms = msg_dict.get("GMS")
        timeus = msg_dict.get("TimeUS")

        if (
                isinstance(gwk, (int, float))
                and isinstance(gms, (int, float))
                and isinstance(timeus, (int, float))
        ):
            gps_time = self._gpsTimeToTime(int(gwk), int(gms))
            self.timebase = gps_time - timeus * 1e-6

            first_us = timeus if self.first_us_stamp is None else self.first_us_stamp
            self.timestamp = self.timebase + first_us * 1e-6

            self.first_us_stamp = int(first_us)
            self.have_timebase = True

    def compute_timestamp_for_msg(
            self,
            msg_dict: Dict[str, Any],
            *,
            msg_name: str,
            columns: Sequence[str],
    ) -> Optional[float]:
        """
        Compute message timestamp using an existing timebase.
        Uses TimeUS when available, otherwise falls back to TimeMS or last timestamp.
        Returns None if timebase is not ready.
        """

        if not self.have_timebase:
            return None

        if columns and columns[0] == "TimeUS" and "TimeUS" in msg_dict:
            timeus = msg_dict["TimeUS"]
            ts = self.timebase + timeus * 1e-6
            self.timestamp = ts
            return ts

        if self._should_use_msec_field0(msg_name, columns, msg_dict):
            time_ms = msg_dict["TimeMS"]
            ts = self.timebase + time_ms * 1e-3
            self.timestamp = ts
            return ts

        return self.timestamp
