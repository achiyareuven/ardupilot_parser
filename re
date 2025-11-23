"# ardupilot_parser"

#  Constants Overview

This section explains the core constants used by the ArduPilot BIN parser.
These values ensure correct message detection, schema decoding, chunking, and type-safe parsing of all log records.

---

## Magic Header & FMT Settings

### `HEADER_hex: "a395"`
The binary log signature used by ArduPilot.
All messages begin with **2 bytes**: `0xA3 0x95`.
This is how the parser locates message boundaries efficiently with `mmap.find()`.

### `FMT_TYPE: 128`
The message type ID for **FMT** (Format) messages.
FMT records describe the structure of all other messages in the log — field names, types, and total size.

### `FMT_PAYLOAD_LEN: 86`
The length (in bytes) of the FMT payload.
Used to perform safe range checks during schema extraction.

---

## Message Name Validation

### `NAME_PATTERN: "^[A-Z0-9]{1,4}$"`
A strict regex ensuring message names are valid ArduPilot identifiers
(e.g., `GPS`, `ATT`, `IMU`, `RCOU`, etc.).

---

## Resync Step After Bad FMT

### `SAFE_FMT_SKIP: 3`
Number of bytes to skip forward after encountering an invalid FMT entry.

**Why 3?**

- Every FMT scan starts by searching for:
  `HEADER (2 bytes) + TYPE (1 byte)` → total **3 bytes**
- Advancing by 3 ensures:
  - No rescan of the same invalid location
  - No risk of skipping past the next real header
  - Faster recovery from corrupted/truncated logs

---

## Chunking Configuration

### `CHUNK_SIZE_BYTES: 5242880`
File splitting size for multiprocess parsing (≈ 5 MB per chunk).
Each worker receives its own slice of the file, keeping:

- Memory predictable
- CPU usage efficient
- Low overhead
- Minimal inter-process contention

### Why split the log into small chunks (even with few processes)?
Using small, fixed-size chunks ensures that no single worker becomes a bottleneck.
Even if the number of processes is low, large logs often contain sections that are heavier to parse
(e.g., dense GPS blocks or high-rate IMU bursts).

With smaller chunks:

- A slow region in the log affects only one chunk, not an entire worker
- Other workers can continue processing additional chunks instead of waiting
- Workload stays balanced, preventing “one slow worker” from stalling the whole job
- Parallel scheduling remains efficient, even on machines with few cores

Chunking keeps the system responsive and avoids situations where one heavy part of the file
forces all workers to sit idle.


---

## ArduPilot Format Mapping

### `FORMAT_MAPPING`
Mapping between ArduPilot's single-character FMT codes and Python `struct` formats.

| ArduPilot Code | Python Struct | Meaning               |
|----------------|---------------|------------------------|
| `a`            | `32h`         | 32 signed shorts      |
| `b`            | `b`           | int8                  |
| `B`            | `B`           | uint8                 |
| `h`            | `h`           | int16                 |
| `H`            | `H`           | uint16                |
| `i`            | `i`           | int32                 |
| `I`            | `I`           | uint32                |
| `f`            | `f`           | float                 |
| `d`            | `d`           | double                |
| `n`            | `4s`          | 4-char string         |
| `N`            | `16s`         | 16-char string        |
| `Z`            | `64s`         | 64-char string        |
| `c`            | `h`           | scaled short (÷100)   |
| `C`            | `H`           | scaled ushort (÷100)  |
| `e`            | `i`           | scaled int32 (÷100)   |
| `E`            | `I`           | scaled uint32 (÷100)  |
| `L`            | `i`           | latitude/longitude (÷1e7) |
| `M`            | `B`           | mode byte             |
| `q`            | `q`           | int64                 |
| `Q`            | `Q`           | uint64                |

---

## Field Scaling Rules

### `SCALE_FACTOR_FIELDS: ["c", "C", "e", "E"]`
Format codes that must be scaled by **1/100**.

### `LATITUDE_LONGITUDE_FORMAT: "L"`
Latitude/longitude fields stored as integers scaled by **1e-7**.

---

## Binary Payload Fields

### `BYTES_FIELDS: ["Data"]`
Fields that should remain raw bytes instead of ASCII-decoded strings.
Used for structured binary payload messages like `DATA`, custom telemetry blocks, etc.

---


