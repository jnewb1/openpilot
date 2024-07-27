import time
from cereal import messaging
from openpilot.selfdrive.pandad import can_list_to_can_capnp
from openpilot.common.swaglog import cloudlog


XCP_MASTER = 0x7fa
XCP_SLAVE = 0x7fb


class CANClient:
  def __init__(self, logcan, sendcan):
    self.logcan = logcan
    self.sendcan = sendcan

  def send_can(self, id, dat, bus):
    self.sendcan.send(can_list_to_can_capnp([(id, 0, dat, bus)], msgtype='sendcan'))

  def recv_can(self):
    dat = self.logcan.receive()
    dat = messaging.log_from_bytes(dat).can
    return dat

  def wait_for_addr(self, target_addr, timeout):
    start = time.time()

    while (time.time() - start) < timeout:
      for msg in self.recv_can():
        addr = msg.address
        dat = msg.dat
        bus = msg.src
        if addr == target_addr and bus == self.bus:
          return dat

    return None


class XCP(CANClient):
  def __init__(self, logcan, sendcan, master_addr, slave_addr, bus):
    super().__init__(logcan, sendcan)
    self.logcan = logcan
    self.sendcan = sendcan
    self.master_addr = master_addr
    self.slave_addr = slave_addr
    self.bus = bus

  def get(self):
    resp = self.wait_for_addr(self.slave_addr, .2)
    cloudlog.error(f"xcp query response: {self.slave_addr} - {resp}")
    return resp

  def req(self, dat):
    cloudlog.error(f"xcp query request: {self.master_addr} - {dat}")
    self.send_can(self.master_addr, dat, self.bus)

  def connect(self):
    self.req(b'\xff' + b'\x00' * 7)
    return self.get()

  def set_mta(self, addr):
    self.req(b'\xf6' + b'\x00' * 3 + addr)
    return self.get()

  def upload(self, size):
    self.req(b'\xf5' + int.to_bytes(size) + b'\x00' * 6)
    return self.get()


def memory_dump(logcan, sendcan):
  xcp = XCP(logcan, sendcan, XCP_MASTER, XCP_SLAVE, 0)

  xcp.connect()

  START = 0x40000000

  with open("data.bin", "wb") as f:
    i = 0
    while True:
      addr = int.to_bytes(START + i, 4)
      xcp.set_mta(addr)
      print(addr.hex())

      attempts = 0
      while True:
        resp = xcp.upload(7)

        if resp is None:
          print(f"failed -- {attempts}/5")
          if attempts > 5:
            exit(1)
        else:
          i += 7
          f.write(resp[1:])
          break

        attempts += 1


def configure_eps(logcan, sendcan):
  xcp = XCP(logcan, sendcan, XCP_MASTER, XCP_SLAVE, 0)
  xcp.connect()
