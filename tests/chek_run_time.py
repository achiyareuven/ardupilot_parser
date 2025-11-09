# from src.business_logic.parallel_parser import ParallelParser
# from src.business_logic.bin_parsr import BinParser
# from pymavlink import mavutil
# from datetime import datetime
#
# def check_time_pyma():
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#
#     # Read messages using pymavlink
#     pyma = []
#     start_time = datetime.now()
#     log = mavutil.mavlink_connection(path, dialect="ardupilotmega")
#     while True:
#         msg = log.recv_match()  # Blocking call
#         if msg is None:
#             break
#         pyma.append(msg.to_dict())
#     end_time = datetime.now()
#     print(f"pymavlink read {len(pyma)} messages in {end_time - start_time}")
#
#
# def check_time_binparser():
#     # Read messages using BinParser
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     with BinParser(path, round_like_pymav=True) as reader:
#         reader.parse_fmt_messages()
#         start_time = datetime.now()
#         single_process = reader.parse_messages()
#         end_time = datetime.now()
#         print(f"BinParser read {len(single_process)} messages in {end_time - start_time}")
# def check_time_parallelparser():
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     # Read messages using ParallelParser
#     processor = ParallelParser(path, num_workers=20,mode="process", round_like_pymav=True)
#     start_time = datetime.now()
#     multi_process = processor.parse()
#     end_time = datetime.now()
#     print(f"ParallelParser read with mood  {len(multi_process)} messages in {end_time - start_time}")
#
#
# if __name__  == "__main__":
#     check_time_parallelparser()
#     check_time_binparser()
#     check_time_pyma()

#
# import matplotlib.pyplot as plt
# from datetime import datetime
# from src.business_logic.parallel_parser import ParallelParser
# from src.business_logic.bin_parsr import BinParser
# from pymavlink import mavutil
#
# def check_time_pyma(msg_name: str = None):
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     start = datetime.now()
#     pyma = []
#     log = mavutil.mavlink_connection(path, dialect="ardupilotmega")
#     while True:
#         msg = log.recv_match(type=msg_name)
#         if msg is None:
#
#             break
#         pyma.append(msg.to_dict())
#     return (datetime.now() - start).total_seconds() , len(pyma)
#
# def check_time_binparser(msg_name: str = None):
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     with BinParser(path, round_like_pymav=True) as reader:
#         reader.parse_fmt_messages()
#         start = datetime.now()
#         single_process = reader.parse_messages(wanted_names=msg_name)
#         return (datetime.now() - start).total_seconds() , len(single_process)
#
# def check_time_multi_process(msg_name: str = None):
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     parser = ParallelParser(path, num_workers=None, mode="process", round_like_pymav=True,wanted_types=)
#     start = datetime.now()
#     multi_process = parser.parse()
#     return (datetime.now() - start).total_seconds(), len(multi_process)
#
#
# def ckeck_time_multi_thread(msg_name: str = None):
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     # Read messages using ParallelParser
#     processor = ParallelParser(path, num_workers=None,mode="thread", round_like_pymav=True,wanted_types = msg_name)
#     start_time = datetime.now()
#     multi_thread = processor.parse()
#     return (datetime.now() - start_time).total_seconds() , len(multi_thread)
#
# if __name__ == "__main__":
#     results = {
#         "pymavlink": check_time_pyma(),
#         "BinParser": check_time_binparser(),
#         "ParallelParser": check_time_parallelparser(),
#     }
#
#     plt.bar(results.keys(), results.values(), color=["gray", "orange", "green"])
#     plt.ylabel("Time (seconds)")
#     plt.title("Parsing performance comparison")
#     plt.show()

#
#
# import matplotlib.pyplot as plt
# from datetime import datetime
# from src.business_logic.parallel_parser import ParallelParser
# from src.business_logic.bin_parsr import BinParser
# from pymavlink import mavutil
#
#
# # ---------- פונקציות מדידה ----------
#
# def check_time_pyma(msg_name: str = None):
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     start = datetime.now()
#     pyma = []
#     log = mavutil.mavlink_connection(path, dialect="ardupilotmega")
#     while True:
#         msg = log.recv_match(type=msg_name)
#         if msg is None:
#             break
#         pyma.append(msg.to_dict())
#     elapsed = (datetime.now() - start).total_seconds()
#     print(elapsed)
#     return elapsed, len(pyma)
#
#
# def check_time_binparser(msg_name: str = None):
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     with BinParser(path, round_like_pymav=True) as reader:
#         reader.parse_fmt_messages()
#         start = datetime.now()
#         items = reader.parse_messages(wanted_names=msg_name)
#         elapsed = (datetime.now() - start).total_seconds()
#         print(elapsed)
#     return elapsed, len(items)
#
#
# def check_time_multi_process(msg_name: str = None):
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     parser = ParallelParser(
#         path,
#         num_workers=None,
#         mode="process",
#         round_like_pymav=True,
#         wanted_types=msg_name,
#     )
#     start = datetime.now()
#     items = parser.parse()
#     elapsed = (datetime.now() - start).total_seconds()
#     print(elapsed)
#     return elapsed, len(items)
#
#
# def check_time_multi_thread(msg_name: str = None):
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#     parser = ParallelParser(
#         path,
#         num_workers=None,
#         mode="thread",
#         round_like_pymav=True,
#         wanted_types=msg_name,
#     )
#     start = datetime.now()
#     items = parser.parse()
#     elapsed = (datetime.now() - start).total_seconds()
#     print(elapsed)
#     return elapsed, len(items)
#
#
# # ---------- הרצה והשוואה ----------
#
# def compare_all():
#     tests = {
#         "pymavlink": check_time_pyma,
#         "BinParser": check_time_binparser,
#         "ParallelProcess": check_time_multi_process,
#         "ParallelThread": check_time_multi_thread,
#     }
#
#     # נריץ פעמיים: בלי GPS ועם GPS בלבד
#     results_all = {}
#     results_gps = {}
#
#     for name, func in tests.items():
#         t_all, n_all = func()
#         t_gps, n_gps = func("GPS")
#         results_all[name] = {"time": t_all, "count": n_all}
#         results_gps[name] = {"time": t_gps, "count": n_gps}
#
#     # ---------- גרף ראשון: כל ההודעות ----------
#     base = results_all["pymavlink"]["time"]
#     names = list(results_all.keys())
#     times = [results_all[n]["time"] for n in names]
#     diffs = [(base / t) * 100 for t in times]  # כמה אחוזים מהריצה של pymavlink
#
#     plt.figure(figsize=(8, 5))
#     bars = plt.bar(names, diffs, color=["gray", "orange", "green", "blue"])
#     plt.title("Parsing Speed (All messages) – % vs pymavlink")
#     plt.ylabel("Relative Speed [% of pymavlink]")
#     for i, (n, d) in enumerate(zip(names, diffs)):
#         plt.text(i, d + 1, f"{d:.1f}%\n({results_all[n]['count']} msgs)", ha="center", va="bottom")
#     plt.ylim(0, max(diffs) * 1.2)
#     plt.tight_layout()
#     plt.show()
#
#     # ---------- גרף שני: רק GPS ----------
#     base_gps = results_gps["pymavlink"]["time"]
#     names_gps = list(results_gps.keys())
#     times_gps = [results_gps[n]["time"] for n in names_gps]
#     diffs_gps = [(base_gps / t) * 100 for t in times_gps]
#
#     plt.figure(figsize=(8, 5))
#     bars = plt.bar(names_gps, diffs_gps, color=["gray", "orange", "green", "blue"])
#     plt.title("Parsing Speed (GPS only) – % vs pymavlink")
#     plt.ylabel("Relative Speed [% of pymavlink]")
#     for i, (n, d) in enumerate(zip(names_gps, diffs_gps)):
#         plt.text(i, d + 1, f"{d:.1f}%\n({results_gps[n]['count']} msgs)", ha="center", va="bottom")
#     plt.ylim(0, max(diffs_gps) * 1.2)
#     plt.tight_layout()
#     plt.show()
#
#
# if __name__ == "__main__":
#     compare_all()
#







import matplotlib.pyplot as plt
from time import perf_counter
from src.business_logic.parallel_parser import ParallelParser
from src.business_logic.bin_parsr import BinParser
from pymavlink import mavutil

BIN_PATH = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
WORKERS = None  # אותו מספר כמו בבדיקות שלך

def check_time_pyma(msg_name: str | None = None):
    start = perf_counter()
    pyma = []
    log = mavutil.mavlink_connection(BIN_PATH, dialect="ardupilotmega")
    while True:
        # כשmsg_name=None זה קורא הכל; כש"GPS" — רק GPS
        msg = log.recv_match(type=msg_name)
        if msg is None:
            break
        pyma.append(msg.to_dict())  # חשוב: המרה ל-dict כמו אצלך
    elapsed = perf_counter() - start
    n = len(pyma)
    del pyma  # שחרור זיכרון
    return elapsed, n

def check_time_binparser(msg_name: str | None = None):
    with BinParser(BIN_PATH, round_like_pymav=True) as reader:
        reader.parse_fmt_messages()
        start = perf_counter()
        items = reader.parse_messages(wanted_names=msg_name)
        elapsed = perf_counter() - start
    n = len(items)
    del items
    return elapsed, n

def check_time_multi_process(msg_name: str | None = None):
    parser = ParallelParser(
        BIN_PATH,
        num_workers=WORKERS,
        mode="process",
        round_like_pymav=True,
        wanted_types=msg_name,  # אם אצלך נדרש Iterable — העבר [msg_name] כשmsg_name לא None
    )
    start = perf_counter()
    items = parser.parse()
    elapsed = perf_counter() - start
    n = len(items)
    del items
    return elapsed, n

def check_time_multi_thread(msg_name: str | None = None):
    parser = ParallelParser(
        BIN_PATH,
        num_workers=WORKERS,
        mode="thread",
        round_like_pymav=True,
        wanted_types=msg_name,
    )
    start = perf_counter()
    items = parser.parse()
    elapsed = perf_counter() - start
    n = len(items)
    del items
    return elapsed, n

def _plot_relative(title: str, base_time: float, results_dict: dict):
    names = list(results_dict.keys())
    rel = [(base_time / results_dict[n]["time"]) * 100 for n in names]
    times = [results_dict[n]["time"] for n in names]

    plt.figure(figsize=(8, 5))
    plt.bar(names, rel)
    plt.title(title)
    plt.ylabel("Relative Speed [% of pymavlink]")

    for i, n in enumerate(names):
        rel_text = f"{rel[i]:.1f}%"
        time_text = f"{times[i]:.2f}s"
        count_text = f"{results_dict[n]['count']:,} msgs"
        plt.text(
            i, rel[i] + 2,
            f"{rel_text}\n{time_text}\n{count_text}",
            ha="center", va="bottom", fontsize=9
        )

    plt.ylim(0, max(rel) * 1.3)
    plt.tight_layout()
    plt.show()

def compare_all():
    tests = {
        "pymavlink": check_time_pyma,
        "BinParser": check_time_binparser,
        "ParallelProcess": check_time_multi_process,
        "ParallelThread": check_time_multi_thread,
    }

    # כל ההודעות
    results_all = {}
    for name, func in tests.items():
        t, n = func(None)
        results_all[name] = {"time": t, "count": n}
        print(f"[ALL] {name}: {t:.3f}s, {n} msgs")

    _plot_relative(
        "Parsing Speed (All messages) – % vs pymavlink",
        results_all["pymavlink"]["time"],
        results_all,
    )

    # רק GPS
    results_gps = {}
    for name, func in tests.items():
        t, n = func("GPS")
        results_gps[name] = {"time": t, "count": n}
        print(f"[GPS] {name}: {t:.3f}s, {n} msgs")

    _plot_relative(
        "Parsing Speed (GPS only) – % vs pymavlink",
        results_gps["pymavlink"]["time"],
        results_gps,
    )

if __name__ == "__main__":
    compare_all()



















