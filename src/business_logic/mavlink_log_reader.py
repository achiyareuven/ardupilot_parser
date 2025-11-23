
import os
from pathlib import Path
from typing import  Dict, List, Any
from src.business_logic.bin_parser import BinParser
from src.business_logic.parallel_parser import ParallelParser

def is_valid_bin(bin_path:str)-> bool:
    try:
        with open(bin_path,"rb") as file:
            first_bytes = file.read(10)

        hex_view = " ".join(f"{byte:02x}" for byte in first_bytes)

        if first_bytes[:2] == b"\x00\x00":
            return False

        if b"\xa3" not in first_bytes and b"\x95" not in first_bytes:
            return False

        return True
    except Exception as e:
        return False


class MavlinkLogReader:
    def __init__(self,logs_dir_:str):
        self.logs__dir = logs_dir_

    @staticmethod
    def read_log_file_process(file_path:str , types:List[str])-> Dict[str, List[Dict[str, Any]]]:
        parser = ParallelParser(
            file_path=file_path,
            mode="process",
            wanted_types=types,
        )
        return parser.parse()

    @staticmethod
    def read_log_file_single(file_path:str , types:List[str])-> Dict[str, List[Dict[str, Any]]]:
        with BinParser(file_path) as reader:
            reader.parse_fmt_messages()
            return reader.parse_messages(wanted_names=types)

    def grab_data_from_log(self,messages_to_read:List[str] = None) -> Dict[str, List[Dict[str, Any]]]:

        logs_dict: Dict[str, List[Dict[str, Any]]] = {}
        try:
            logs__dir = str(Path(self.logs__dir).resolve())
            files = [file for file in os.listdir(logs__dir)if file.endswith(".bin")]

            if len(files) == 0 :
                raise Exception

            files.sort()

            for file in  files:

                bin_path = os.path.join(logs__dir,file)

                if not is_valid_bin(bin_path):
                    raise Exception("Error! bin file not valid")

                log_data = self.read_log_file_process(file_path=bin_path,types=messages_to_read)

                for msg_name, messages in log_data.items():

                    saved_log_key =  "GPS" if msg_name in ("GPS", "GPS2") else msg_name

                    target_list = logs_dict.setdefault(saved_log_key, [])
                    target_list.extend(messages)

            for key in logs_dict:
                logs_dict[key] = sorted(logs_dict[key],key=lambda x:x["timestamp"])


            if "TRIG" in logs_dict:
                logs_dict["TRIG"] = [
                    {**d,"gimbal_roll": d.pop("gr"), "gimbal_pitch": d.pop("gp"), "gimbal_yaw":d.pop("gy")}
                    for d in logs_dict["TRIG"]
                ]
                [d.pop(key) for d in logs_dict["TRIG"] for key in ["gr","gp","gy"]]

            return logs_dict

        except Exception as e:

            raise Exception



if __name__ == "__main__":
    from datetime import datetime
    e = datetime.now()
    a = MavlinkLogReader(r"C:\Users\achiy\logs")
    b= a.grab_data_from_log()
    s = datetime.now()
    print(f"time:{s-e}")
    total = sum(len(lst) for lst in b.values())
    print(total)
    for msg_type, messages in b.items():
        example = messages[0] if messages else None
        print(f"\n--- {msg_type} ---")
        print(example)