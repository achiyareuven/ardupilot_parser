# from  src.business_logic.parallel_parser import ParallelParser
# from src.business_logic.bin_parser import BinParser
# from pymavlink import mavutil
# from datetime import datetime
#
# def test_compare_binreader_pymavlink():
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#
#     # Read messages using pymavlink
#     pyma = []
#     log = mavutil.mavlink_connection(path, dialect="ardupilotmega")
#     while True:
#         msg = log.recv_match()  # Blocking call
#         if msg is None:
#             break
#         pyma.append(msg.to_dict())
#
#     # Read messages using BinParser
#
#     with BinParser(path) as reader:
#         reader.parse_fmt_messages()
#         single_process = reader.parse_messages()
#
#     # Compare lengths
#     assert len(pyma) == len(single_process), f"Message count mismatch: pymavlink={len(pyma)}, BinParser={len(single_process)}"
#
#     # Compare individual messages
#     differences = 0
#     for i in range(len(pyma)):
#         if pyma[i] != single_process[i]:
#             differences += 1
#             print(f"Difference at message {i}:")
#             print("pymavlink:", pyma[i])
#             print("BinParser:", single_process[i])
#
#     print(f"Total differences found: {differences}")
#
#
# def test_parallel_parser():
#     path = r"C:\Users\achiy\Downloads\log_file_test_01.bin"
#
#     # Read messages using pymavlink
#     pyma = []
#     log = mavutil.mavlink_connection(path, dialect="ardupilotmega")
#     while True:
#         msg = log.recv_match()  # Blocking call
#         if msg is None:
#             break
#         pyma.append(msg.to_dict())
#
#     # Read messages using ParallelParser
#     processor = ParallelParser(path, num_workers=20,mode="process")
#     multi_process = processor.parse()
#
#     # Compare lengths
#     assert len(pyma) == len(multi_process), f"Message count mismatch: pymavlink={len(pyma)}, ParallelParser={len(multi_process)}"
#
#     # Compare individual messages
#     differences = 0
#     for i in range(len(pyma)):
#         if pyma[i] != multi_process[i]:
#             differences += 1
#             print(f"Difference at message {i}:")
#             print("pymavlink:", pyma[i])
#             print("ParallelParser:", multi_process[i])
#
#     print(f"Total differences found: {differences}")
#
