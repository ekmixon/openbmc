#!/usr/bin/env python
#
# Copyright 2015-present Facebook. All Rights Reserved.
#
# This program file is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program in a file named COPYING; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301 USA
#

PAL_STATUS_UNSUPPORTED = 2

# Does the FRU have a FRUID EEPROM
FRU_CAPABILITY_FRUID_WRITE = 1 << 0
FRU_CAPABILITY_FRUID_READ = 1 << 1
FRU_CAPABILITY_FRUID_ALL = FRU_CAPABILITY_FRUID_WRITE | FRU_CAPABILITY_FRUID_READ

# Sensors on this FRU
FRU_CAPABILITY_SENSOR_READ = 1 << 2
FRU_CAPABILITY_SENSOR_THRESHOLD_UPDATE = 1 << 3
FRU_CAPABILITY_SENSOR_HISTORY = 1 << 4
FRU_CAPABILITY_SENSOR_ALL = (
    FRU_CAPABILITY_SENSOR_READ
    | FRU_CAPABILITY_SENSOR_THRESHOLD_UPDATE
    | FRU_CAPABILITY_SENSOR_HISTORY
)

import binascii
import os
import uuid
from ctypes import CDLL, c_char_p, c_ubyte, c_uint32, create_string_buffer, pointer
from subprocess import PIPE, CalledProcessError, Popen, check_output

from common_utils import async_exec

try:
    lpal_hndl = CDLL("libpal.so.0")
except OSError:
    lpal_hndl = None


def pal_get_platform_name():
    if lpal_hndl is None:
        machine = "OpenBMC"
        with open("/etc/issue") as f:
            line = f.read().strip()
            if line.startswith("OpenBMC Release "):
                tmp = line.split(" ")
                vers = tmp[2]
                tmp2 = vers.split("-")
                machine = tmp2[0]
        return machine
    name = create_string_buffer(16)
    if ret := lpal_hndl.pal_get_platform_name(name):
        return None
    else:
        return name.value.decode()


def pal_get_num_slots():
    if lpal_hndl is None:
        return 1
    num = c_ubyte()
    p_num = pointer(num)
    return None if (ret := lpal_hndl.pal_get_num_slots(p_num)) else num.value


def pal_is_fru_prsnt(slot_id):
    if lpal_hndl is None:
        return None
    status = c_ubyte()
    p_status = pointer(status)
    if ret := lpal_hndl.pal_is_fru_prsnt(slot_id, p_status):
        return None
    else:
        return status.value


def pal_get_server_power(slot_id):
    # TODO Use wedge_power.sh?
    if lpal_hndl is None:
        return None
    status = c_ubyte()
    p_status = pointer(status)
    if ret := lpal_hndl.pal_get_server_power(slot_id, p_status):
        return None
    else:
        return status.value


def pal_get_fru_name(slot_id):
    if lpal_hndl is None:
        return None
    name = create_string_buffer(16)
    if ret := lpal_hndl.pal_get_fru_name(slot_id, name):
        return None
    else:
        return name.value.decode()


# return value
#  1 - bic okay
#  0 - bic error
#  2 - not present
def pal_get_bic_status(slot_id):
    if lpal_hndl is None:
        return 0

    fru_name = pal_get_fru_name(slot_id)

    if fru_name is None:
        return PAL_STATUS_UNSUPPORTED
    else:
        fru = fru_name

    cmd = ["/usr/bin/bic-util", fru, "--get_dev_id"]

    try:
        ret = check_output(cmd).decode()
        return 0 if "Usage:" in ret or "fail " in ret else 1
    except (OSError, IOError):
        return PAL_STATUS_UNSUPPORTED  # No bic on this platform
    except (CalledProcessError):
        return 0  # bic-util returns error


def pal_server_action(slot_id, command, fru_name=None):
    # TODO use wedge_power.sh?
    if lpal_hndl is None:
        return -1
    if (
        command
        in [
            "power-off",
            "power-on",
            "power-reset",
            "power-cycle",
            "graceful-shutdown",
        ]
        and lpal_hndl.pal_is_slot_server(slot_id) == 0
    ):
        return -2

    fru_name = pal_get_fru_name(slot_id)

    if "server" in fru_name and "identify" in command:
        fru = ""
    elif fru_name is None:
        fru = f"slot{str(slot_id)}"
    else:
        fru = fru_name

    if command == "12V-cycle":
        cmd = f"/usr/local/bin/power-util {fru} 12V-cycle"
    elif command == "12V-off":
        cmd = f"/usr/local/bin/power-util {fru} 12V-off"
    elif command == "12V-on":
        cmd = f"/usr/local/bin/power-util {fru} 12V-on"
    elif command == "graceful-shutdown":
        cmd = f"/usr/local/bin/power-util {fru} graceful-shutdown"
    elif command == "identify-off":
        cmd = f"/usr/bin/fpc-util {fru} --identify off"
    elif command == "identify-on":
        cmd = f"/usr/bin/fpc-util {fru} --identify on"
    elif command == "power-cycle":
        cmd = f"/usr/local/bin/power-util {fru} cycle"
    elif command == "power-off":
        cmd = f"/usr/local/bin/power-util {fru} off"
    elif command == "power-on":
        cmd = f"/usr/local/bin/power-util {fru} on"
    elif command == "power-reset":
        cmd = f"/usr/local/bin/power-util {fru} reset"
    else:
        return -1
    ret = Popen(cmd, shell=True, stdout=PIPE).stdout.read().decode()
    return -1 if ret.find("Usage:") != -1 or ret.find("fail ") != -1 else 0


def pal_sled_action(command):
    if command == "sled-cycle":
        cmd = ["/usr/local/bin/power-util", "sled-cycle"]
    elif command == "sled-identify-off":
        cmd = ["/usr/bin/fpc-util", "sled", "--identify", "off"]
    elif command == "sled-identify-on":
        cmd = ["/usr/bin/fpc-util", "sled", "--identify", "on"]
    else:
        return -1
    try:
        ret = check_output(cmd).decode()
        return -1 if ret.startswith("Usage") else 0
    except (OSError, IOError, CalledProcessError):
        return -1


async def pal_set_key_value(key, value):
    cmd = ["/usr/local/bin/cfg-util", key, value]
    if os.path.exists(cmd[0]):
        retcode, output, stderr = await async_exec(cmd, shell=False)
        if "Usage:" in output or "Usage:" in stderr or retcode != 0:
            raise ValueError("failure")
    else:
        pkey = c_char_p(key.encode())
        pvalue = c_char_p(value.encode())
        ret = lpal_hndl.pal_set_key_value(pkey, pvalue)
        if ret != 0:
            raise ValueError("failure")


def pal_get_eth_intf_name():
    name = create_string_buffer(8)
    lpal_hndl.pal_get_eth_intf_name(name)
    return name.value.decode()


def pal_get_uuid():
    uuid_str = create_string_buffer(16)
    lpal_hndl.pal_get_dev_guid(0, uuid_str)
    uuid_str = binascii.hexlify(uuid_str)
    uuid_str = str(uuid_str, "ascii")
    uuid_str = uuid.UUID(uuid_str)
    return str(uuid_str)


def pal_get_fru_capability(fru):
    if lpal_hndl is None:
        return None
    cap = c_uint32()
    p_cap = pointer(cap)
    if ret := lpal_hndl.pal_get_fru_capability(fru, p_cap):
        return None
    else:
        return cap.value
