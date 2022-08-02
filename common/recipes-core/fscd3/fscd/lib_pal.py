import subprocess
from ctypes import CDLL, c_uint, pointer


lpal_hndl = CDLL("libpal.so.0")


def pal_fan_dead_handle(fan):
    return None if (ret := lpal_hndl.pal_fan_dead_handle(fan)) else ret


def pal_fan_recovered_handle(fan):
    return None if (ret := lpal_hndl.pal_fan_recovered_handle(fan)) else ret


def pal_fan_chassis_intrusion_handle():
    self_tray_pull_out = c_uint(1)
    self_tray_pull_out_point = pointer(self_tray_pull_out)
    if ret := lpal_hndl.pal_self_tray_location(self_tray_pull_out_point):
        return None
    else:
        return self_tray_pull_out.value
