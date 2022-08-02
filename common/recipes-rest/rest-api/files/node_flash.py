#!/usr/bin/env python

from kv import kv_get
from node import node
from rest_pal_legacy import *


class flashNode(node):
    def __init__(self, name=None, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        # Get vendor name
        vendor_name = " "
        data = kv_get("ssd_vendor")
        vendor_name = data.strip("\n")

        # Get flash type
        flash_type = " "
        data = kv_get("ssd_sku_info")
        flash_type = data.strip("\n")

        return {"flash type": flash_type, "vendor name": vendor_name}


def get_node_flash():
    return flashNode()
