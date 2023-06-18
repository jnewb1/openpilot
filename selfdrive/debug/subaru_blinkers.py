from enum import IntEnum
import sys
import argparse
from subprocess import check_output, CalledProcessError
from panda import Panda
from panda.python.uds import ACCESS_TYPE, DATA_IDENTIFIER_TYPE, UdsClient, SESSION_TYPE
from Crypto.Cipher import AES
import time


GEN2_BODY_SECRET_KEY = 0x00F17B760F53C30CBFFB54AD808F497A
                      #0x76E19EDB3027B6C51C8E90CED15E59BA

class ACCESS_TYPE_LEVEL_1(IntEnum):
  REQUEST_SEED = ACCESS_TYPE.REQUEST_SEED + 2
  SEND_KEY = ACCESS_TYPE.SEND_KEY + 2

def gen2_security_access(seed):
    cipher = AES.new(GEN2_BODY_SECRET_KEY, AES.MODE_ECB)
    key = cipher.encrypt(seed)
    return key

try:
  check_output(["pidof", "boardd"])
  print("boardd is running, please kill openpilot before running this script! (aborted)")
  sys.exit(1)
except CalledProcessError as e:
  if e.returncode != 1: # 1 == no process found (boardd not running)
    raise e

addr = 0x752

left_signal_input = 0x10A5
right_signal_unput = 0x10A6

left_signal_output = 0x10A7
right_signal_output = 0x10A8

panda = Panda()
panda.set_safety_mode(Panda.SAFETY_ELM327)
uds_client = UdsClient(panda, addr, bus=2, debug=True)

print("extended diagnostic session ...")
uds_client.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)

print("unlock body")
seed = uds_client.security_access(ACCESS_TYPE_LEVEL_1.REQUEST_SEED)
key = gen2_security_access(seed)
resp = uds_client.security_access(ACCESS_TYPE_LEVEL_1.SEND_KEY, key)

print(resp)

while True:
    resp = uds_client.read_data_by_identifier(left_signal_input)

    print(resp)

    time.sleep(1)

# resp = uds_client.write_data_by_identifier(left_signal_output, '\x01')

# print(resp)