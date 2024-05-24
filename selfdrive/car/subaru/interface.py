from cereal import car
from panda import Panda
from openpilot.selfdrive.car import get_safety_config
from openpilot.selfdrive.car.disable_ecu import disable_ecu
from openpilot.selfdrive.car.interfaces import CarInterfaceBase
from openpilot.selfdrive.car.subaru.values import CAR, GLOBAL_ES_ADDR, SubaruFlags


class CarInterface(CarInterfaceBase):

  @staticmethod
  def _get_params(ret, candidate: CAR, fingerprint, car_fw, experimental_long, docs):
    ret.carName = "subaru"
    ret.radarUnavailable = True
    # for HYBRID CARS to be upstreamed, we need:
    # - replacement for ES_Distance so we can cancel the cruise control
    # - to find the Cruise_Activated bit from the car
    # - proper panda safety setup (use the correct cruise_activated bit, throttle from Throttle_Hybrid, etc)
    ret.dashcamOnly = bool(ret.flags & (SubaruFlags.PREGLOBAL | SubaruFlags.LKAS_ANGLE | SubaruFlags.HYBRID))
    ret.autoResumeSng = False

    # Detect infotainment message sent from the camera
    if not (ret.flags & SubaruFlags.PREGLOBAL) and 0x323 in fingerprint[2]:
      ret.flags |= SubaruFlags.SEND_INFOTAINMENT.value

    if ret.flags & SubaruFlags.PREGLOBAL:
      ret.enableBsm = 0x25c in fingerprint[0]
      ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.subaruPreglobal)]
    else:
      ret.enableBsm = 0x228 in fingerprint[0]
      ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.subaru)]
      if ret.flags & SubaruFlags.GLOBAL_GEN2:
        ret.safetyConfigs[0].safetyParam |= Panda.FLAG_SUBARU_GEN2

    ret.steerLimitTimer = 0.4
    ret.steerActuatorDelay = 0.1

    if ret.flags & SubaruFlags.LKAS_ANGLE:
      ret.steerControlType = car.CarParams.SteerControlType.angle
    else:
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    if candidate in (CAR.SUBARU_FORESTER_PREGLOBAL, CAR.SUBARU_OUTBACK_PREGLOBAL_2018):
      ret.safetyConfigs[0].safetyParam = Panda.FLAG_SUBARU_PREGLOBAL_REVERSED_DRIVER_TORQUE  # Outback 2018-2019 and Forester have reversed driver torque signal

    ret.experimentalLongitudinalAvailable = not (ret.flags & (SubaruFlags.GLOBAL_GEN2 | SubaruFlags.PREGLOBAL |
                                                              SubaruFlags.LKAS_ANGLE | SubaruFlags.HYBRID))
    ret.openpilotLongitudinalControl = experimental_long and ret.experimentalLongitudinalAvailable

    if ret.flags & SubaruFlags.GLOBAL_GEN2 and ret.openpilotLongitudinalControl:
      ret.flags |= SubaruFlags.DISABLE_EYESIGHT.value

    if ret.openpilotLongitudinalControl:
      ret.longitudinalTuning.kpBP = [0., 5., 35.]
      ret.longitudinalTuning.kpV = [0.8, 1.0, 1.5]
      ret.longitudinalTuning.kiBP = [0., 35.]
      ret.longitudinalTuning.kiV = [0.54, 0.36]

      ret.stoppingControl = True
      ret.safetyConfigs[0].safetyParam |= Panda.FLAG_SUBARU_LONG

    return ret

  # returns a car.CarState
  def _update(self, c):

    ret = self.CS.update(self.cp, self.cp_cam, self.cp_body)

    ret.events = self.create_common_events(ret).to_msg()

    return ret

  @staticmethod
  def init(CP, logcan, sendcan):
    if CP.flags & SubaruFlags.DISABLE_EYESIGHT:
      disable_ecu(logcan, sendcan, bus=2, addr=GLOBAL_ES_ADDR, com_cont_req=b'\x28\x03\x01')
