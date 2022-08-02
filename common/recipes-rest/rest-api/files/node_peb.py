#!/usr/bin/env python

from common_utils import async_exec
from kv import kv_get
from node import node
from rest_pal_legacy import pal_get_platform_name


class pebNode(node):
    def __init__(self, name=None, info=None, actions=None):
        self.name = pal_get_platform_name()
        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        name = pal_get_platform_name()
        location = kv_get("tray_location")
        cmd = "cat /sys/class/gpio/gpio108/value"
        _, stdout, _ = await async_exec(cmd, shell=True)
        data = stdout.strip("\n")
        if data == "0":
            status = "In"
        elif data == "1":
            status = "Out"
        else:
            status = "Unknown"

        data = kv_get("system_identify", 1)
        identify_status = data.strip("\n")

        return {
            "Description": f"{name} PCIe Expansion Board",
            "Tray Location": location,
            "Tray Status": status,
            "Status of identify LED": identify_status,
        }

    async def doAction(self, data, param={}):
        if data["action"] == "identify-on":
            cmd = "/usr/bin/fpc-util --identify on"
            _, data, _ = await async_exec(cmd, shell=True)
            res = "failure" if data.startswith("Usage") else "success"
        elif data["action"] == "identify-off":
            cmd = "/usr/bin/fpc-util --identify off"
            _, data, _ = await async_exec(cmd, shell=True)
            res = "failure" if data.startswith("Usage") else "success"
        else:
            res = "not support this action"

        return {"result": res}


def get_node_peb():
    actions = ["identify-on", "identify-off"]

    return pebNode(actions=actions)
