from openpilot.common.numpy_fast import clip, interp
from opendbc.can.packer import CANPacker
from openpilot.selfdrive.car import apply_driver_steer_torque_limits, common_fault_avoidance
from openpilot.selfdrive.car.subaru import subarucan
from openpilot.selfdrive.car.subaru.values import DBC, GLOBAL_ES_ADDR, GLOBAL_GEN2, PREGLOBAL_CARS, HYBRID_CARS, STEER_RATE_LIMITED, \
                                                  CanBus, CarControllerParams, SubaruFlags

# FIXME: These limits aren't exact. The real limit is more than likely over a larger time period and
# involves the total steering angle change rather than rate, but these limits work well for now
MAX_STEER_RATE = 25  # deg/s
MAX_STEER_RATE_FRAMES = 7  # tx control frames needed before torque can be cut


class CarController:
  def __init__(self, dbc_name, CP, VM):
    self.CP = CP
    self.apply_steer_last = 0
    self.frame = 0

    self.cruise_button_prev = 0
    self.steer_rate_counter = 0

    self.p = CarControllerParams(CP)
    self.packer = CANPacker(DBC[CP.carFingerprint]['pt'])

  def update(self, CC, CS, now_nanos):
    actuators = CC.actuators
    hud_control = CC.hudControl
    pcm_cancel_cmd = CC.cruiseControl.cancel

    can_sends = []

    # *** steering ***
    if (self.frame % self.p.STEER_STEP) == 0:
      apply_steer = int(round(actuators.steer * self.p.STEER_MAX))

      # limits due to driver torque

      new_steer = int(round(apply_steer))
      apply_steer = apply_driver_steer_torque_limits(new_steer, self.apply_steer_last, CS.out.steeringTorque, self.p)

      if not CC.latActive:
        apply_steer = 0

      if self.CP.carFingerprint in PREGLOBAL_CARS:
        can_sends.append(subarucan.create_preglobal_steering_control(self.packer, self.frame // self.p.STEER_STEP, apply_steer, CC.latActive))
      else:
        apply_steer_req = CC.latActive

        if self.CP.carFingerprint in STEER_RATE_LIMITED:
          # Steering rate fault prevention
          self.steer_rate_counter, apply_steer_req = \
            common_fault_avoidance(abs(CS.out.steeringRateDeg) > MAX_STEER_RATE, apply_steer_req,
                                  self.steer_rate_counter, MAX_STEER_RATE_FRAMES)

        can_sends.append(subarucan.create_steering_control(self.packer, apply_steer, apply_steer_req))

      self.apply_steer_last = apply_steer

    # *** longitudinal ***

    if CC.longActive:
      apply_throttle = int(round(interp(actuators.accel, CarControllerParams.THROTTLE_LOOKUP_BP, CarControllerParams.THROTTLE_LOOKUP_V)))
      apply_rpm = int(round(interp(actuators.accel, CarControllerParams.RPM_LOOKUP_BP, CarControllerParams.RPM_LOOKUP_V)))
      apply_brake = int(round(interp(actuators.accel, CarControllerParams.BRAKE_LOOKUP_BP, CarControllerParams.BRAKE_LOOKUP_V)))

      if actuators.accel < 0:
        apply_throttle = CarControllerParams.THROTTLE_ENGINE_BRAKE

      # limit min and max values
      cruise_throttle = clip(apply_throttle, CarControllerParams.THROTTLE_MIN, CarControllerParams.THROTTLE_MAX)
      cruise_rpm = clip(apply_rpm, CarControllerParams.RPM_MIN, CarControllerParams.RPM_MAX)
      cruise_brake = clip(apply_brake, CarControllerParams.BRAKE_MIN, CarControllerParams.BRAKE_MAX)
    else:
      cruise_throttle = CarControllerParams.THROTTLE_INACTIVE
      cruise_rpm = CarControllerParams.RPM_MIN
      cruise_brake = CarControllerParams.BRAKE_MIN

    # *** alerts and pcm cancel ***
    if self.frame % 10 == 0:
      if self.CP.carFingerprint not in PREGLOBAL_CARS:
        can_sends.append(subarucan.create_es_dashstatus(self.packer, self.frame // 10, CS.es_dashstatus_msg, CC.enabled, self.CP.openpilotLongitudinalControl,
                                                        CC.longActive, hud_control.leadVisible))

        can_sends.append(subarucan.create_es_lkas_state(self.packer, self.frame // 10, CS.es_lkas_state_msg, CC.enabled, hud_control.visualAlert,
                                                        hud_control.leftLaneVisible, hud_control.rightLaneVisible,
                                                        hud_control.leftLaneDepart, hud_control.rightLaneDepart))

        if self.CP.flags & SubaruFlags.SEND_INFOTAINMENT:
          can_sends.append(subarucan.create_es_infotainment(self.packer, self.frame // 10, CS.es_infotainment_msg, hud_control.visualAlert))
      else:
        can_sends.append(subarucan.create_preglobal_es_dashstatus(self.packer, CS.es_dashstatus_msg, self.CP.openpilotLongitudinalControl))

    if self.CP.openpilotLongitudinalControl:
      if self.frame % 5 == 0:
        if self.CP.carFingerprint not in PREGLOBAL_CARS:
          can_sends.append(subarucan.create_es_status(self.packer, self.frame // 5, CS.es_status_msg,
                                                      self.CP.openpilotLongitudinalControl, CC.longActive, cruise_rpm))

          can_sends.append(subarucan.create_es_brake(self.packer, self.frame // 5, CS.es_brake_msg, CC.enabled, cruise_brake))

          can_sends.append(subarucan.create_es_distance(self.packer, self.frame // 5, CS.es_distance_msg, 0, pcm_cancel_cmd,
                                                        self.CP.openpilotLongitudinalControl, cruise_brake > 0, cruise_throttle))
        else:
          can_sends.append(subarucan.create_preglobal_es_status(self.packer, self.frame // 5, CS.es_status_msg,
                                                                self.CP.openpilotLongitudinalControl, CC.longActive, cruise_rpm))

          can_sends.append(subarucan.create_preglobal_es_brake(self.packer, self.frame // 5, CS.es_brake_msg, CC.enabled, cruise_brake))

          can_sends.append(subarucan.create_preglobal_es_distance(self.packer, self.frame // 5, CS.es_distance_msg, pcm_cancel_cmd,
                                                                  self.CP.openpilotLongitudinalControl, cruise_brake > 0, cruise_throttle))
      if self.frame % 2 == 0:
        if self.CP.carFingerprint in PREGLOBAL_CARS:
          stock_brake_value = CS.es_brake_msg["Brake_Pressure"]
          can_sends.append(subarucan.create_preglobal_brake_status(self.packer, CS.brake_status_msg, stock_brake_value))

    if pcm_cancel_cmd:
      if self.CP.carFingerprint not in HYBRID_CARS:
        bus = CanBus.alt if self.CP.carFingerprint in GLOBAL_GEN2 else CanBus.main
        if self.CP.carFingerprint not in PREGLOBAL_CARS:
          can_sends.append(subarucan.create_es_distance(self.packer, CS.es_distance_msg["COUNTER"] + 1, CS.es_distance_msg, bus, pcm_cancel_cmd))
        else:
          can_sends.append(subarucan.create_preglobal_es_distance(self.packer, CS.es_distance_msg["COUNTER"] + 1, CS.es_distance_msg, pcm_cancel_cmd))

      if self.CP.flags & SubaruFlags.DISABLE_EYESIGHT:
        # Tester present (keeps eyesight disabled)
        if self.frame % 100 == 0:
          can_sends.append([GLOBAL_ES_ADDR, 0, b"\x02\x3E\x80\x00\x00\x00\x00\x00", CanBus.camera])

        # Create all of the other eyesight messages to keep the rest of the car happy when eyesight is disabled
        if self.frame % 5 == 0:
          can_sends.append(subarucan.create_es_highbeamassist(self.packer))

        if self.frame % 10 == 0:
          can_sends.append(subarucan.create_es_static_1(self.packer))

        if self.frame % 2 == 0:
          can_sends.append(subarucan.create_es_static_2(self.packer))

    new_actuators = actuators.copy()
    new_actuators.steer = self.apply_steer_last / self.p.STEER_MAX
    new_actuators.steerOutputCan = self.apply_steer_last

    self.frame += 1
    return new_actuators, can_sends
