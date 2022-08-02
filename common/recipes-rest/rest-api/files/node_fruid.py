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

from subprocess import *

from common_utils import async_exec
from node import node


class fruidNode(node):
    def __init__(self, name, info=None, actions=None):
        self.name = name

        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def getInformation(self, param={}):
        result = {}
        cmd = f"/usr/local/bin/fruid-util {self.name}"
        _, stdout, _ = await async_exec(cmd, shell=True)
        sdata = stdout.splitlines()
        for line in sdata:
            # skip lines with --- or startin with FRU
            if line.startswith("FRU"):
                continue
            if line.startswith("-----"):
                continue

            kv = line.split(":", 1)
            if len(kv) < 2:
                continue

            result[kv[0].strip()] = kv[1].strip()

        return result


def get_node_fruid(name):
    return fruidNode(name)
