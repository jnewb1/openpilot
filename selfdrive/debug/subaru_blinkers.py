from enum import IntEnum
import sys
import argparse
from subprocess import check_output, CalledProcessError
from panda import Panda
from panda.python.uds import ACCESS_TYPE, DATA_IDENTIFIER_TYPE, UdsClient, SESSION_TYPE
from Crypto.Cipher import AES
import time


GEN2_ES_SECRET_KEY = b'\x33\xe6\x3c\xa0\x43\x11\x53\x46\x0c\x18\xf1\x06\x4c\x70\xfe\x41' # level 1
GEN2_ES_SECRET_KEY = b'\x33\xe6\x3c\xa0\x43\x11\x53\x46\x0c\x18\xf1\x06\x4c\x70\xfe\x41' # level 3


GEN2_BODY_SECRET_KEY = b'\x00\xF1\x7B\x76\x0F\x53\xC3\x0C\xBF\xFB\x54\xAD\x80\x8F\x49\x7A' # level 1
                      #0x76E19EDB3027B6C51C8E90CED15E59BA # level 3

class ACCESS_TYPE_LEVEL_1(IntEnum):
  REQUEST_SEED = ACCESS_TYPE.REQUEST_SEED
  SEND_KEY = ACCESS_TYPE.SEND_KEY

def gen2_security_access(seed):
    cipher = AES.new(GEN2_ES_SECRET_KEY, AES.MODE_ECB)
    key = cipher.encrypt(seed)
    return key

try:
  check_output(["pidof", "boardd"])
  print("boardd is running, please kill openpilot before running this script! (aborted)")
  sys.exit(1)
except CalledProcessError as e:
  if e.returncode != 1: # 1 == no process found (boardd not running)
    raise e

addr = 0x787

left_signal_input = 0x10A5
right_signal_unput = 0x10A6

left_signal_output = 0x10A7
right_signal_output = 0x10A8

panda = Panda()
panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

uds_client = UdsClient(panda, addr, bus=2, debug=True)

print("extended diagnostic session ...")
uds_client.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)

print("unlock body")
seed = uds_client.security_access(ACCESS_TYPE_LEVEL_1.REQUEST_SEED)
key = gen2_security_access(seed)
resp = uds_client.security_access(ACCESS_TYPE_LEVEL_1.SEND_KEY, key)

print(resp)

data = uds_client.request_upload(0, 100)

print(data)