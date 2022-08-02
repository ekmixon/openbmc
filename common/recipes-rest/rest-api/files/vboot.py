#!/usr/bin/env python3
#
# Copyright 2014-present Facebook. All Rights Reserved.
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
import os
import re
import subprocess

from common_utils import async_exec


interested_keys = {
    "Certificates fallback": "cert_fallback_time",
    "Certificates time": "cert_time",
    "U-Boot fallback": "uboot_fallback_time",
    "U-Boot time": "uboot_time",
    "Flags force_recovery": "force_recovery",
    "Flags hardware_enforce": "hardware_enforce",
    "Flags software_enforce": "software_enforce",
    "Flags recovery_boot": "recovery_boot",
    "Flags recovery_retried": "recovery_retried",
}


async def get_vboot_status():
    info = {"status": "-1", "status_text": "Unsupported"}
    vboot_util = "/usr/local/bin/vboot-util"
    if not os.path.isfile(vboot_util):
        return info
    try:
        retcode, stdout, _ = await async_exec(["/usr/local/bin/vboot-util"])
        data = stdout.splitlines()

        info["status_text"] = data[-1].strip()
        if "Verified boot is not supported" in info["status_text"]:
            return info
        if m := re.match("Status CRC: (0[xX][0-9a-fA-F]+)", data[-4].strip()):
            info["status_crc"] = m[1]
        if m := re.match(
            "Status type \((\d+)\) code \((\d+)\)", data[-2].strip()
        ):
            info["status"] = f"{m[1]}.{m[2]}"
        if m := re.match("TPM.? status  \((\d+)\)", data[-3].strip()):
            info["tpm_status"] = m[1]
        for l in data:
            a = l.split(": ")
            if len(a) == 2:
                key = a[0].strip()
                value = a[1].strip()
                if key in interested_keys:
                    info[interested_keys[key]] = value
    except (OSError, subprocess.CalledProcessError) as e:
        pass
    return info
