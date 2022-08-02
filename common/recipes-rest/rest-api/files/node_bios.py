#!/usr/bin/env python
import os.path

from common_utils import async_exec
from node import node
from rest_pal_legacy import *


IOM_M2 = 1  # IOM type: M.2
IOM_IOC = 2  # IOM type: IOC
PLATFORM_FILE = "/tmp/system.bin"


def get_iom_type():
    pal_sku_file = open(PLATFORM_FILE, "r")
    pal_sku = pal_sku_file.read()
    iom_type = int(pal_sku) & 0x3  # The IOM type is the last 2 bits

    if iom_type in [IOM_M2, IOM_IOC]:
        return iom_type
    print("Rest-API: System type is unknown! Please confirm the system type.")
    return -1


"""""" """""" """""" """""" """""" """''
          Main Node
""" """""" """""" """""" """""" """""" ""


class biosNode(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        return {"Description": "BIOS Information"}


def get_node_bios(name):
    return biosNode(name)


"""""" """""" """""" """""" """""" """''
      Boot Order Information
""" """""" """""" """""" """""" """""" ""


class bios_boot_order_trunk_node(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        return {"Description": "BIOS Boot Order Information"}


"""""" """""" """""" """""" """''
         Boot Mode
""" """""" """""" """""" """""" ""


class bios_boot_mode_node(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        cmd = f"/usr/local/bin/bios-util {self.name} --boot_order get --boot_mode"
        _, boot_order, _ = await async_exec(cmd, shell=True)
        boot_order = boot_order.split("\n")[0].split(": ")

        return {
            boot_order[0]: boot_order[1],
            "Note #1: Actions Format:": "{ 'action': 'set', 'mode': {0,1} }",
            "Note #2: Boot Mode No.": "{ 0: 'Legacy', 1: 'UEFI' }",
        }

    async def doAction(self, data, param={}):
        if data["action"] == "set" and len(data) == 2:
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --boot_order set --boot_mode "
                + data["mode"]
            )
            _, _, err = await async_exec(cmd, shell=True)

            res = "failure" if err.startswith("usage") else "success"
        else:
            res = "failure"

        return {"result": res}


"""""" """""" """""" """""" """''
         Clear CMOS
""" """""" """""" """""" """""" ""


class bios_clear_cmos_node(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        cmd = f"/usr/local/bin/bios-util {self.name} --boot_order get --clear_CMOS"
        _, clear_cmos, _ = await async_exec(cmd, shell=True)
        clear_cmos = clear_cmos.split("\n")[0].split(": ")

        return {clear_cmos[0]: clear_cmos[1]}

    async def doAction(self, data, param={}):
        if data["action"] == "enable":
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --boot_order enable --clear_CMOS"
            )
            _, _, err = await async_exec(cmd, shell=True)

            res = "failure" if err.startswith("usage") else "success"
        elif data["action"] == "disable":
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --boot_order disable --clear_CMOS"
            )
            _, _, err = await async_exec(cmd, shell=True)
            res = "failure" if err.startswith("usage") else "success"
        else:
            res = "failure"

        return {"result": res}


"""""" """""" """""" """""" """''
    Force Boot BIOS Setup
""" """""" """""" """""" """""" ""


class bios_force_boot_setup_node(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        cmd = (
            "/usr/local/bin/bios-util "
            + self.name
            + " --boot_order get --force_boot_BIOS_setup"
        )
        _, data, _ = await async_exec(cmd, shell=True)

        force_boot_bios_setup = data.split("\n")[0].split(": ")

        return {force_boot_bios_setup[0]: force_boot_bios_setup[1]}

    async def doAction(self, data, param={}):
        if data["action"] == "enable":
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --boot_order enable --force_boot_BIOS_setup"
            )
            _, _, err = await async_exec(cmd, shell=True)

            res = "failure" if err.startswith("usage") else "success"
        elif data["action"] == "disable":
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --boot_order disable --force_boot_BIOS_setup"
            )
            _, _, err = await async_exec(cmd, shell=True)

            res = "failure" if err.startswith("usage") else "success"
        else:
            res = "failure"

        return {"result": res}


"""""" """""" """""" """""" """''
         Boot Order
""" """""" """""" """""" """""" ""


class bios_boot_order_node(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        cmd = f"/usr/local/bin/bios-util {self.name} --boot_order get --boot_order"
        _, data, _ = await async_exec(cmd, shell=True)

        boot_order = data.split("\n")[0].split(": ")

        return {
            boot_order[0]: boot_order[1],
            "Note #1: Actions Format:": "{'action': 'set', '1st': <1st_no>, '2nd': <2nd_no>, '3rd': <3rd_no>, '4th': <4th_no>, '5th': <5th_no>}",
            "Note #2: Boot Order No.": "{ 0: 'USB Device', 1: 'IPv4 Network', 9: 'IPv6 Network', 2: 'SATA HDD', 3: 'SATA-CDROM', 4: 'Other Removalbe Device', 255: 'Reserved' }",
        }

    async def doAction(self, data, param={}):
        if data["action"] == "set" and len(data) == 6:
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --boot_order set --boot_order "
                + data["1st"]
                + " "
                + data["2nd"]
                + " "
                + data["3rd"]
                + " "
                + data["4th"]
                + " "
                + data["5th"]
            )
            _, _, err = await async_exec(cmd, shell=True)

            res = "failure" if err != "" or data != "" else "success"
        elif data["action"] == "disable":
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --boot_order disable --boot_order"
            )
            _, _, err = await async_exec(cmd, shell=True)
            res = "failure" if err.startswith("usage") else "success"
        else:
            res = "failure"

        return {"result": res}


def get_node_bios_boot_order_trunk(name):
    return bios_boot_order_trunk_node(name)


def get_node_bios_boot_mode(name):
    actions = ["set"]
    return bios_boot_mode_node(name=name, actions=actions)


def get_node_bios_clear_cmos(name):
    actions = ["enable", "disable"]
    return bios_clear_cmos_node(name=name, actions=actions)


def get_node_bios_force_boot_setup(name):
    actions = ["enable", "disable"]
    return bios_force_boot_setup_node(name=name, actions=actions)


def get_node_bios_boot_order(name):
    actions = ["set", "disable"]
    return bios_boot_order_node(name=name, actions=actions)


"""""" """""" """""" """""" """""" """''
     BIOS POST Code Information
""" """""" """""" """""" """""" """""" ""


class bios_postcode_node(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        cmd = f"/usr/local/bin/bios-util {self.name} --postcode get"
        _, data, _ = await async_exec(cmd, shell=True)
        postcode = data.replace("\n", "").strip()

        return {"POST Code": postcode}


def get_node_bios_postcode_trunk(name):
    return bios_postcode_node(name)


"""""" """""" """""" """""" """""" """''
       Platform Information
""" """""" """""" """""" """""" """""" ""


class bios_plat_info_node(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        cmd = f"/usr/local/bin/bios-util {self.name} --plat_info get"
        _, plat_info, err = await async_exec(cmd, shell=True)

        if err.startswith("usage"):
            plat_info = "Currently the platform does not support plat-info\n"

        plat_info = plat_info.split("\n")
        return {"Platform Information": plat_info[:-1]}


def get_node_bios_plat_info_trunk(name):
    return bios_plat_info_node(name)


"""""" """""" """""" """""" """""" """''
     PCIe Port Configuration
""" """""" """""" """""" """""" """""" ""


class bios_pcie_port_config_node(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        cmd = f"/usr/local/bin/bios-util {self.name} --pcie_port_config get"
        _, pcie_port_config, err = await async_exec(cmd, shell=True)

        if err.startswith("usage"):
            pcie_port_config = (
                "Currently the platform does not support pcie-port-config\n"
            )

        pcie_port_config = pcie_port_config.split("\n")
        pcie_port_config_len = len(pcie_port_config)

        iom_type = get_iom_type()
        if iom_type == IOM_M2:
            return {
                "PCIe Port Configuration": pcie_port_config[
                    : pcie_port_config_len - 1
                ],
                "Note: Actions Format:": "{'action': <enable, disable>, 'pcie_dev': <scc_ioc, flash1, flash2, nic>}",
            }

        elif iom_type == IOM_IOC:
            return {
                "PCIe Port Configuration": pcie_port_config[
                    : pcie_port_config_len - 1
                ],
                "Note: Actions Format:": "{'action': <enable, disable>, 'pcie_dev': <scc_ioc, iom_ioc, nic>}",
            }

        else:
            return []

    async def doAction(self, data, param={}):
        if data["action"] == "enable" and len(data) == 2:
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --pcie_port_config enable --"
                + data["pcie_dev"]
            )
            _, _, err = await async_exec(cmd, shell=True)

            res = "failure" if err.startswith("usage") else "success"
        elif data["action"] == "disable":
            cmd = (
                "/usr/local/bin/bios-util "
                + self.name
                + " --pcie_port_config disable --"
                + data["pcie_dev"]
            )
            _, _, err = await async_exec(cmd, shell=True)

            res = "failure" if err.startswith("usage") else "success"
        else:
            res = "failure"

        return {"result": res}


def get_node_bios_pcie_port_config_trunk(name):
    actions = ["enable", "disable"]
    return bios_pcie_port_config_node(name=name, actions=actions)
