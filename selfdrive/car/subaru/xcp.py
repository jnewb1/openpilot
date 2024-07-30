import time
from cereal import messaging
from openpilot.selfdrive.pandad import can_list_to_can_capnp


XCP_MASTER = 0x7fa
XCP_SLAVE = 0x7fb


class CANClient:
  def __init__(self, logcan, sendcan):
    self.logcan = logcan
    self.sendcan = sendcan

  def send_can(self, addr, dat, bus):
    self.sendcan.send(can_list_to_can_capnp([(addr, 0, dat, bus)], msgtype='sendcan'))

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
    if resp is None:
      raise Exception("xcp no response")
    if resp[0] != 0xFF:
      raise Exception(f"xcp bad response: {resp}")
    return resp

  def req(self, dat):
    self.send_can(self.master_addr, dat, self.bus)

  def connect(self):
    self.req(b'\xff' + b'\x00' * 7)
    return self.get()

  def disconnect(self):
    self.req(b'\xfe' + b'\x00' * 7)

  def set_mta(self, addr):
    self.req(b'\xf6' + b'\x00' * 3 + int.to_bytes(addr, 4, "big"))
    return self.get()

  def upload(self, size):
    self.req(b'\xf5' + int.to_bytes(size) + b'\x00' * 6)
    return self.get()

  def download(self, size, value):
    self.req(b'\xf0' + int.to_bytes(size) + value.to_bytes(size, "big") + b'\x00' * (6-size))
    return self.get()

  def set_value(self, offset, value, length):
    self.set_mta(offset)
    self.download(length, value)

    self.set_mta(offset)
    assert int.from_bytes(self.upload(length)[1:1+length], "big") == value


"""
Row 1: 16 values, 2 bytes each, of speed breakpoints
Row 2: 16 values, 2 bytes each, of values

XCP allows for temporarily increasing these limits
"""


# this is the start of the values part of the table
SPEED_BREAKPOINTS = [0, 10, 20, 30, 40, 50, 60, 80, 100, 120, 140, 160, 180, 200, 220, 260]

# Max angle allowed for the LKAS messages at specific speeds
MAX_ANGLE_TABLE = 0x4002b68c + 2 * 16

# Max torque allowed for the LKAS messages at specific speeds
MAX_TORQUE_TABLE = 0x4002b64c + 2 * 16


def configure_eps(logcan, sendcan):
  xcp = XCP(logcan, sendcan, XCP_MASTER, XCP_SLAVE, 0)
  xcp.connect()

  xcp.set_value(MAX_ANGLE_TABLE, 30000, 2)
  xcp.set_value(MAX_ANGLE_TABLE + 2, 30000, 2)
  xcp.set_value(MAX_ANGLE_TABLE + 4, 30000, 2)
  xcp.set_value(MAX_ANGLE_TABLE + 6, 30000, 2)
  xcp.set_value(MAX_ANGLE_TABLE + 8, 30000, 2)

  xcp.set_value(MAX_TORQUE_TABLE,     3000, 2)
  xcp.set_value(MAX_TORQUE_TABLE + 2, 3000, 2)
  xcp.set_value(MAX_TORQUE_TABLE + 4, 3000, 2)
  xcp.set_value(MAX_TORQUE_TABLE + 6, 3000, 2)
  xcp.set_value(MAX_TORQUE_TABLE + 8, 3000, 2)

  xcp.disconnect()
