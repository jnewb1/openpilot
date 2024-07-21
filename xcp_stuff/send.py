import time
import cereal.messaging as messaging
from openpilot.selfdrive.pandad import can_list_to_can_capnp
from cereal import car
from openpilot.common.params import Params

from opendbc.can.packer import CANPacker

sendcan = messaging.pub_sock('sendcan')


def can_send(id, dat, bus):
  sendcan.send(can_list_to_can_capnp([(id, 0, dat, bus)], msgtype='sendcan'))


cp = car.CarParams.new_message()

safety_config = car.CarParams.SafetyConfig.new_message()
safety_config.safetyModel = car.CarParams.SafetyModel.allOutput
cp.safetyConfigs = [safety_config]*1

params = Params()
params.put_bool("IsOnroad", True)
params.put_bool("FirmwareQueryDone", True)
params.put_bool("ControlsReady", True)
params.put("CarParams", cp.to_bytes())


packer = CANPacker("subaru_global_2017_generated")


while True:
  addr, _, dat, bus = packer.make_can_msg("ES_LKAS", 2, {"LKAS_Output": 40, "LKAS_Request": 1, "SET_1": 1})

  print(addr, dat, bus)

  can_send(addr, dat, bus)
  time.sleep(1/50)
