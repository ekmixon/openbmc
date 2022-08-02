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
from node import node
from rest_pal_legacy import *


class spbNode(node):
    def __init__(self, info=None, actions=None):
        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def doAction(self, data, param={}):
        res = "failure" if pal_sled_action(data["action"]) == -1 else "success"
        return {"result": res}


def get_node_spb():
    name = pal_get_platform_name()
    info = {"Description": f"{name} Side Plane"}
    actions = ["sled-cycle", "sled-identify-on", "sled-identify-off"]
    return spbNode(info, actions)
