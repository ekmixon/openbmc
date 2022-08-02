#!/usr/bin/env python

from asyncio import TimeoutError

from common_utils import async_exec
from node import node


def get_node_enclosure():
    info = {"Description": "Enclosure-util Information"}
    return node(info)


class enclosure_error_Node(node):
    def __init__(self, name=None, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        result = {}

        cmd = "/usr/bin/enclosure-util --error"
        _, data, _ = await async_exec(cmd, shell=True)
        data = data.strip()
        sdata = data.split("\n")
        for line in sdata:
            kv = line.split(":")
            result[kv[0].strip()] = kv[1].strip()

        return result


def get_node_enclosure_error():
    return enclosure_error_Node()


class enclosure_flash_health_Node(node):
    def __init__(self, name=None, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        result = {}

        cmd = "/usr/bin/enclosure-util --flash-health"
        _, data, _ = await async_exec(cmd, shell=True)
        data = data.strip()
        sdata = data.split("\n")
        for line in sdata:
            kv = line.split(":")
            result[kv[0].strip()] = kv[1].strip()

        return result


def get_node_enclosure_flash_health():
    return enclosure_flash_health_Node()


class enclosure_flash_status_Node(node):
    def __init__(self, name=None, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        info = {}

        cmd = "/usr/bin/enclosure-util --flash-status"
        _, data, _ = await async_exec(cmd, shell=True)
        data = data.split("flash-2")
        data_flash_1 = data[0].strip().split("\n")
        data_flash_2 = data[1].strip().split("\n")
        info = {"flash-1": data_flash_1[1:], "flash-2": data_flash_2[1:]}

        return info


def get_node_enclosure_flash_status():
    return enclosure_flash_status_Node()


class enclosure_hdd_status_Node(node):
    def __init__(self, name=None, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        result = {}

        cmd = "/usr/bin/enclosure-util --hdd-status"
        _, data, _ = await async_exec(cmd, shell=True)
        data = data.strip()
        sdata = data.split("\n")
        for line in sdata:
            kv = line.split(":")
            result[kv[0].strip()] = kv[1].strip()

        return result

    async def doAction(self, data, param={}):
        result = {}

        if (
            (data["action"].isdigit())
            and (int(data["action"]) >= 0)
            and (int(data["action"]) < 36)
        ):
            cmd = "/usr/bin/enclosure-util --hdd-status " + data["action"]
            _, data, _ = await async_exec(cmd, shell=True)
            sdata = data.strip().split(":")

            result[sdata[0].strip()] = sdata[1].strip()
        else:
            result = {"result": "failure"}

        return result


def get_node_enclosure_hdd_status():
    actions = ["0~35"]
    return enclosure_hdd_status_Node(actions=actions)
