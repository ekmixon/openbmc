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

import json
import os
import re
import subprocess
from asyncio import TimeoutError

from common_utils import async_exec
from node import node


async def sensor_util_history_clear(fru="all", sensor_id="", sensor_name=""):
    cmd = ["/usr/local/bin/sensor-util", fru, "--history-clear"]
    if sensor_id != "":
        cmd += [sensor_id]
    if sensor_name != "":
        cmd_util = ["/usr/local/bin/sensor-util", fru]
        sensors = []
        try:
            retcode, stdout, stderr = await async_exec(cmd_util, shell=False)
            out = stdout.decode().splitlines()
            rx = re.compile(
                r"(\S+[\S\s]*\S+)\s+\(0x([a-fA-F\d]+)\)\s+:\s+(-?\d+\.\d+)\s+(\S+)\s+\|\s+\((\S+)\)(.*)$"
            )
            rx_na = re.compile(
                r"(\S+[\S\s]*\S+)\s+\(0x([a-fA-F\d]+)\)\s+:\s+(\S+)\s+\|\s+\((\S+)\)"
            )
            for line in out:
                m_val = rx.match(line)
                m_na = rx_na.match(line)
                if m_val:
                    s_name = m_val[1]
                    s_id = m_val[2]
                    s_val = m_val[3]
                    s_unit = m_val[4]
                    s_status = m_val[5]
                elif m_na:
                    s_name = m_na[1]
                    s_id = m_na[2]
                    s_val = m_na[3]
                    s_unit = "na"
                    s_status = m_na[4]
                else:
                    continue

                if sensor_name != "" and sensor_name.lower() == s_name.lower():
                    snr_num = f"0x{str(s_id)}"
                    cmd += [snr_num]
        except TimeoutError:
            print("TimeoutException received")
        except Exception:
            print("Exception  received")
    try:
        retcode, stdout, stderr = await async_exec(cmd, shell=True)
        return {"result": "success"} if retcode == 0 else {"result": "failure"}
    except Exception:
        return {"result": "failure"}


async def sensor_util(fru="all", sensor_name="", sensor_id="", period="60", display=[]):
    cmd = ["/usr/local/bin/sensor-util", fru]
    if sensor_id != "":
        cmd += [sensor_id]
    if "thresholds" in display:
        cmd += ["--threshold"]
        if "history" in display:
            return {}
    elif "history" in display:
        cmd += ["--history", period]
    sensors = []
    sensor_id_val = int(sensor_id, base=16) if sensor_id != "" else 0
    try:
        retcode, stdout, stderr = await async_exec(cmd, shell=False)
        out = stdout.splitlines()
        sensors = {}
        if "history" in display:
            # MB_CONN_P12V_INA230_PWR (0x9B) min = NA, average = NA, max = NA
            # SYSTEM_AIRFLOW     (0x0) min = 15.48, average = 15.77, max = 15.86
            rx = re.compile(
                r"(\S+[\S\s]*\S+)\s+\(0x([a-fA-F\d]+)\)\s+min = ([^,]+), average = ([^,]+), max = (\S+)"
            )
        else:
            # SYSTEM_AIRFLOW               (0x0) :   15.78 CFM   | (ok)
            # SYSTEM_AIRFLOW               (0x0) :   15.62 CFM   | (ok) | UCR: NA | UNC: NA | UNR: NA | LCR: NA | LNC: NA | LNR: NA
            rx = re.compile(
                r"(\S+[\S\s]*\S+)\s+\(0x([a-fA-F\d]+)\)\s+:\s+(-?\d+\.\d+)\s+(\S+)\s+\|\s+\((\S+)\)(.*)$"
            )
            # MB_CONN_P12V_INA230_PWR      (0x9B) : NA | (na)
            # MB_CONN_P12V_INA230_PWR      (0x9B) : NA | (na)
            rx_na = re.compile(
                r"(\S+[\S\s]*\S+)\s+\(0x([a-fA-F\d]+)\)\s+:\s+(\S+)\s+\|\s+\((\S+)\)"
            )

        for line in out:
            if "history" in display:
                if not (m := rx.match(line)):
                    continue
                s_name = m[1]
                s_id = m[2]
                s_min = m[3]
                s_avg = m[4]
                s_max = m[5]
                snr = {"min": s_min, "avg": s_avg, "max": s_max}
                if "id" in display:
                    snr["id"] = s_id
            else:
                m_val = rx.match(line)
                m_na = rx_na.match(line)
                s_thresholds = {}
                if m_val:
                    s_name = m_val[1]
                    s_id = m_val[2]
                    s_val = m_val[3]
                    s_unit = m_val[4]
                    s_status = m_val[5]
                    if "thresholds" in display:
                        thres_str = m_val[6].strip()
                        threshold_arr = thres_str.split("|")
                        for t in threshold_arr:
                            a = t.split(": ")
                            if len(a) != 2:
                                continue
                            key = a[0].strip()
                            val = a[1].strip()
                            if val.lower() != "na":
                                s_thresholds[key] = val
                elif m_na:
                    s_name = m_na.group(1)
                    s_id = m_na.group(2)
                    s_val = m_na.group(3)
                    s_unit = "na"
                    s_status = m_na.group(4)
                else:
                    continue
                snr = {"value": s_val}
                if "units" in display:
                    snr["units"] = s_unit
                if "id" in display:
                    snr["id"] = s_id
                if "status" in display:
                    snr["status"] = s_status
                if "thresholds" in display and s_thresholds:
                    snr["thresholds"] = s_thresholds

            processing_id = int(s_id, 16)

            if (
                (sensor_id == "" and sensor_name == "")
                or (sensor_name != "" and sensor_name.lower() == s_name.lower())
                or (sensor_id != "" and sensor_id_val == processing_id)
            ):
                if s_name in sensors:
                    if isinstance(sensors[s_name], list):
                        sensors[s_name].append(snr)
                    else:
                        sensors[s_name] = [sensors[s_name], snr]
                else:
                    sensors[s_name] = snr
    except TimeoutError:
        print("TimeoutException received")
    except Exception as e:
        print("Exception  received")
        print(e)
    return sensors


class sensorsNode(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name
        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        display = param["display"].split(",") if "display" in param else []
        snr_name = param["name"] if "name" in param else ""
        snr_id = param["id"] if "id" in param else ""
        period = param["history-period"] if "history-period" in param else "60"
        return await sensor_util(self.name, snr_name, snr_id, period, display)

    async def doAction(self, info, param={}):
        snr_name = param["name"] if "name" in param else ""
        snr = param["id"] if "id" in param else ""
        return (
            await sensor_util_history_clear(self.name, snr, snr_name)
            if self.actions
            else {"result": "failure"}
        )


def get_node_sensors(name):
    actions = ["history-clear"]
    return sensorsNode(name, actions=actions)
