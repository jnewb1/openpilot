import time

import cereal.messaging as messaging
from openpilot.selfdrive.pandad import can_list_to_can_capnp

sm = messaging.SubMaster(['can'])



XCP_MASTER = 0x7fa
XCP_SLAVE = 0x7fb

UDS_TOOL = 0x746
UDS_ECU = UDS_TOOL + 0x8

sendcan = messaging.pub_sock('sendcan')
recvcan = sm.sock["can"]

EPS_BUS = 1



def can_send(id, dat, bus):
  sendcan.send(can_list_to_can_capnp([(id, 0, dat, bus)], msgtype='sendcan'))


def can_recv():
  dat = recvcan.receive()
  dat = messaging.log_from_bytes(dat).can
  return dat

def wait_for_resp(target_addr, timeout):
  start = time.time()

  while (time.time() - start) < timeout:
    for msg in can_recv():
      addr = msg.address
      dat = msg.dat
      bus = msg.src
      if addr == target_addr:
        return dat

  return None


def connect():
  can_send(XCP_MASTER, b'\xff' + b'\x00' * 7, EPS_BUS)
  resp = wait_for_resp(XCP_SLAVE, .2)
  assert resp


def set_mta(addr):
  can_send(XCP_MASTER, b'\xf6' + b'\x00' * 3 + addr, EPS_BUS)
  resp = wait_for_resp(XCP_SLAVE, .2)
  assert resp


def upload(size):
  can_send(XCP_MASTER, b'\xf5' + int.to_bytes(size) + b'\x00' * 6, EPS_BUS)
  resp = wait_for_resp(XCP_SLAVE, .2)
  return resp




can_send(UDS_TOOL, b'\x03\x22\xf1\x00\x00\x00\x00\x00', EPS_BUS)
resp = wait_for_resp(UDS_ECU, .2)
print(resp)


def memory_dump():
  connect()

  START = 0x40000000

  with open("data.bin", "wb") as f:
    i = 0
    while True:
      addr = int.to_bytes(START + i, 4)
      set_mta(addr)
      print(addr.hex())

      attempts = 0
      while True:
        resp = upload(7)

        if resp is None:
          print(f"failed -- {attempts}/5")
          if attempts > 5:
            exit(1)
        else:
          i += 7
          f.write(resp[1:])
          break

        attempts += 1


memory_dump()