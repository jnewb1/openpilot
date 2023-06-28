from enum import IntEnum
import sys
import argparse
from subprocess import check_output, CalledProcessError
from panda import Panda
from panda.python.uds import ACCESS_TYPE, CONTROL_PARAMETER_TYPE, DATA_IDENTIFIER_TYPE, DYNAMIC_DEFINITION_TYPE, RESET_TYPE, ROUTINE_CONTROL_TYPE, DynamicSourceDefinition, UdsClient, SESSION_TYPE
from Crypto.Cipher import AES
import time

GEN2_ES_SECRET_KEY = {
  1: b'\x33\xe6\x3c\xa0\x43\x11\x53\x46\x0c\x18\xf1\x06\x4c\x70\xfe\x41',
  16: b'\xA8\x08\x35\x0D\x2B\xAF\x20\x84\xF0\xA5\xC1\x07\x90\xA5\xD5\x06',
  32: b'\x29\x5A\x6E\xBA\xEC\x78\xD7\x74\xD8\xAA\xC1\xE0\xB3\xB5\x75\x0C'
}

GEN2_BODY_SECRET_KEY = b'\x00\xF1\x7B\x76\x0F\x53\xC3\x0C\xBF\xFB\x54\xAD\x80\x8F\x49\x7A' # level 1
                      #0x76E19EDB3027B6C51C8E90CED15E59BA # level 3

class ACCESS_TYPE_LEVEL_1(IntEnum):
  REQUEST_SEED = ACCESS_TYPE.REQUEST_SEED + 2
  SEND_KEY = ACCESS_TYPE.SEND_KEY + 2

def gen2_security_access(seed, version=1):
    cipher = AES.new(GEN2_ES_SECRET_KEY[version], AES.MODE_ECB)
    return cipher.encrypt(seed)

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

red_panda = Panda()
red_panda.set_safety_mode(Panda.SAFETY_OPENPORT)

# uds_client = UdsClient(red_panda, addr, bus=2)

# print("extended diagnostic session ...")
# uds_client.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)

# print("unlock es lvl 1")
# seed = uds_client.security_access(ACCESS_TYPE_LEVEL_1.REQUEST_SEED)
# key = gen2_security_access(seed, 16)
# resp = uds_client.security_access(ACCESS_TYPE_LEVEL_1.SEND_KEY, key)
# print(resp)

# GEN2_ES_BUTTONS_1_DID = 0x4136 # from ssm4
# GEN2_ES_BUTTONS_2_DID = 0x4137 # from ssm4

# GEN2_ES_EYESIGHT_FUNCTION_CUSTOMIZE = 0x3513

red_panda.set_can_speed_kbps(0, 500)
red_panda.set_can_speed_kbps(1, 250)
red_panda.set_can_speed_kbps(2, 500)

while True:
  # button_1 = uds_client.read_data_by_identifier(GEN2_ES_BUTTONS_1_DID)
  # button_2 = uds_client.read_data_by_identifier(GEN2_ES_BUTTONS_2_DID)

  # print(f"{button_1} {button_2}")

  # uds_client.write_data_by_identifier(GEN2_ES_BUTTONS_2_DID, b'\x01')

  # red_panda.can_clear(0)
  # red_panda.can_clear(1)
  # red_panda.can_clear(2)

  # time.sleep(0.01)

  for msg in red_panda.can_recv():
    addr, _, dat, bus = msg

    if bus != 2:
      print(addr, bus)