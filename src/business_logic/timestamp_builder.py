from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence


@dataclass
class TimestampBuilder:
    timebase: float = 0.0
    timestamp: float = 0.0
    first_us_stamp: Optional[int] = None
    have_timebase: bool = False

    def _gpsTimeToTime(self, week: int, msec: int) -> float:
        epoch = 86400 * (10 * 365 + int((1980 - 1969) / 4) + 1 + 6 - 2)
        return epoch + 86400 * 7 * week + msec * 0.001 - 18.0

    @staticmethod
    def _type_has_good_TimeMS(msg_name: str) -> bool:
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

    def update_and_get(
        self,
        msg_dict: Dict[str, Any],
        *,
        msg_name: str,
        columns: Sequence[str],
    ) -> Optional[float]:

        if columns and columns[0] == "TimeUS" and "TimeUS" in msg_dict:
            us_val = int(msg_dict["TimeUS"])
            if self.first_us_stamp is None:
                self.first_us_stamp = us_val

        if not self.have_timebase:
            gwk = msg_dict.get("GWk")
            gms = msg_dict.get("GMS")
            timeus = msg_dict.get("TimeUS")

            if (
                isinstance(gwk, (int, float))
                and isinstance(gms, (int, float))
                and isinstance(timeus, (int, float))
            ):
                gps_time = self._gpsTimeToTime(int(gwk), int(gms))

                self.timebase = gps_time - timeus * 1.0e-6

                first_us = timeus if self.first_us_stamp is None else self.first_us_stamp
                self.timestamp = self.timebase + first_us * 1.0e-6

                self.first_us_stamp = int(first_us)
                self.have_timebase = True

        if not self.have_timebase:
            return None

        if columns and columns[0] == "TimeUS" and "TimeUS" in msg_dict:
            timeus = msg_dict["TimeUS"]
            timestamp = self.timebase + timeus * 1.0e-6
            self.timestamp = timestamp
            return timestamp

        if self._should_use_msec_field0(msg_name, columns, msg_dict):
            time_ms = msg_dict["TimeMS"]
            timestamp = self.timebase + time_ms * 1.0e-3
            self.timestamp = timestamp
            return timestamp

        return self.timestamp
