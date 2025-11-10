import json, re
try:
    with open(r"C:\Users\achiy\PycharmProjects\ardupilot_parser\constants.json", "r", encoding="utf-8") as f:
        data = json.load(f)

except FileNotFoundError:
    raise RuntimeError("constants.json file not found.")
except json.JSONDecodeError as e:
    raise RuntimeError(f"Error decoding constants.json: {e}")
except Exception as e:
    raise RuntimeError(f"Failed to load constants.json: {e}")


HEADER = bytes.fromhex(data["HEADER_hex"])
FMT_TYPE = data["FMT_TYPE"]
FMT_PAYLOAD_LEN = data["FMT_PAYLOAD_LEN"]
NAME_PATTERN = re.compile(data["NAME_PATTERN"])
MIN_MAGIC_ADVANCE = data["MIN_MAGIC_ADVANCE"]
CHUNK_SIZE_BYTES = data["CHUNK_SIZE_BYTES"]
FORMAT_MAPPING = data["FORMAT_MAPPING"]
SCALE_FACTOR_FIELDS = set(data["SCALE_FACTOR_FIELDS"])
LATITUDE_LONGITUDE_FORMAT = data["LATITUDE_LONGITUDE_FORMAT"]
BYTES_FIELDS = set(data["BYTES_FIELDS"])
