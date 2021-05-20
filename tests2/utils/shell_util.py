#!/usr/bin/env python3
#
# Copyright 2018-present Facebook. All Rights Reserved.
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

import subprocess
import sys

from utils.cit_logger import Logger


def cli_logging(func):
    def wrap(*args, **kwargs):
        if "-c" in sys.argv:
            f = open("/tmp/cli.txt", "a")
            if "cmd" in kwargs:
                cmd = kwargs["cmd"]
            else:
                cmd = args[0]
            f.write(cmd + "\n")
            f.close()
        return func(*args, **kwargs)

    return wrap


@cli_logging
def run_cmd(cmd=None):
    if not cmd:
        raise Exception("cmd not set")
    info = subprocess.check_output(cmd).decode("utf-8")
    return info


@cli_logging
def run_shell_cmd(cmd=None, ignore_err=False, expected_return_code=0):
    if not cmd:
        raise Exception("cmd not set")
    try:
        Logger.info("Executing cmd= {}".format(cmd))

        f = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        data, err = f.communicate()
        if not ignore_err:
            err = err.decode("utf-8")
            if len(err) > 0:
                raise Exception(err + " [FAILED]")
        if f.returncode != expected_return_code:
            raise Exception(
                "{} exited with non {} exit code".format(cmd, expected_return_code)
            )
        info = data.decode("utf-8")
    except Exception as e:
        raise Exception("Failed to run command = {} and exception {}".format(cmd, e))
    return info
