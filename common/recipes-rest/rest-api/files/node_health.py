#!/usr/bin/env python

from subprocess import *

from kv import FPERSIST, kv_get
from node import node
from rest_pal_legacy import *


class healthNode(node):
    def __init__(self, name=None, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        # Get Platform Name
        name = pal_get_platform_name()

        result = "NA"
        # Enclosure health LED status (GOOD/BAD)
        if name == "FBTTN":
            dpb_hlth = kv_get("dpb_sensor_health", FPERSIST)
            iom_hlth = kv_get("iom_sensor_health", FPERSIST)
            nic_hlth = kv_get("nic_sensor_health", FPERSIST)
            scc_hlth = kv_get("scc_sensor_health", FPERSIST)
            slot1_hlth = kv_get("slot1_sensor_health", FPERSIST)

            if (
                (dpb_hlth == "1")
                & (iom_hlth == "1")
                & (nic_hlth == "1")
                & (scc_hlth == "1")
                & (slot1_hlth == "1")
            ):
                result = "Good"
            else:
                result = "Bad"
        elif name == "Lightning":
            peb_hlth = kv_get("peb_sensor_health")
            pdpb_hlth = kv_get("pdpb_sensor_health")
            fcb_hlth = kv_get("fcb_sensor_health")
            bmc_hlth = kv_get("bmc_health")

            if (
                (peb_hlth == "1")
                and (pdpb_hlth == "1")
                and (fcb_hlth == "1")
                and (bmc_hlth == "1")
            ):
                result = "Good"
            else:
                result = "Bad"
        elif name == "Grand Canyon":
            server_hlth = kv_get("server_sensor_health", FPERSIST)
            uic_hlth = kv_get("uic_sensor_health", FPERSIST)
            dpb_hlth = kv_get("dpb_sensor_health", FPERSIST)
            scc_hlth = kv_get("scc_sensor_health", FPERSIST)
            nic_hlth = kv_get("nic_sensor_health", FPERSIST)
            e1s_iocm_hlth = kv_get("e1s_iocm_sensor_health", FPERSIST)
            bmc_hlth = kv_get("bmc_health", FPERSIST)

            if (
                (server_hlth == "1")
                and (uic_hlth == "1")
                and (dpb_hlth == "1")
                and (scc_hlth == "1")
                and (nic_hlth == "1")
                and (e1s_iocm_hlth == "1")
                and (bmc_hlth == "1")
            ):
                result = "Good"
            else:
                result = "Bad"
        return {"Status of enclosure health LED": result}


def get_node_health():
    return healthNode()
