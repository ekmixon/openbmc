#!/usr/bin/env python

from subprocess import *

from common_utils import async_exec
from kv import FPERSIST, kv_get
from node import node
from rest_pal_legacy import *

identify_name = {"FBTTN": "identify_slot1", "Grand Canyon": "system_identify_server"}


class identifyNode(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        # Get Platform Name
        plat_name = pal_get_platform_name()

        if plat_name in identify_name:
            identify_status = kv_get(identify_name[plat_name], FPERSIST)
        else:
            identify_status = kv_get("identify_slot1", FPERSIST)
        return {"Status of identify LED": identify_status}

    async def doAction(self, data, param={}):
        if data["action"] == "on":
            cmd = "/usr/bin/fpc-util --identify on"
            _, stdout, _ = await async_exec(cmd, shell=True)
            res = "failure" if stdout.startswith("Usage") else "success"
        elif data["action"] == "off":
            cmd = "/usr/bin/fpc-util --identify off"
            _, stdout, _ = await async_exec(cmd, shell=True)
            res = "failure" if stdout.startswith("Usage") else "success"
        else:
            res = "not support this action"

        return {"result": res}


def get_node_identify(name):
    actions = ["on", "off"]
    return identifyNode(name=name, actions=actions)
