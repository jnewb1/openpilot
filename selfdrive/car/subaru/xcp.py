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

  def send(self, id, dat, bus):
    self.sendcan.send(can_list_to_can_capnp([(id, 0, dat, bus)], msgtype='sendcan'))

  def recv(self):
    dat = self.logcan.receive()
    dat = messaging.log_from_bytes(dat).can
    return dat

  def wait_for_addr(self, target_addr, timeout):
    start = time.time()

    while (time.time() - start) < timeout:
      for msg in self.recv():
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

  def wait(self):
    return self.wait_for_addr(self.slave_addr, .2)

  def connect(self):
    self.send(self.master_addr, b'\xff' + b'\x00' * 7, self.bus)
    resp = self.wait()
    assert resp

  def set_mta(self, addr):
    self.send(self.master_addr, b'\xf6' + b'\x00' * 3 + addr, self.bus)
    resp = self.wait()
    assert resp

  def upload(self, size):
    self.send(self.master_addr, b'\xf5' + int.to_bytes(size) + b'\x00' * 6, self.bus)
    resp = self.wait()
    return resp


def configure_eps(logcan, sendcan):
  xcp = XCP(logcan, sendcan, XCP_MASTER, XCP_SLAVE, 0)

  xcp.connect()
