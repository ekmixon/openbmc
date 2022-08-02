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

import asyncio
import functools
import json
import os
import os.path
import re
import typing as t
from shlex import quote
from subprocess import PIPE, Popen, check_output, CalledProcessError
from uuid import getnode as get_mac

import kv
import rest_pal_legacy
from boot_source import is_boot_from_secondary
from common_utils import async_exec
from node import node
from vboot import get_vboot_status

PROC_MTD_PATH = "/proc/mtd"

# Read all contents of file path specified
def read_file_contents(path):
    try:
        with open(path, "r") as proc_file:
            content = proc_file.readlines()
    except IOError:
        content = None

    return content


def SPIVendorID2Name(manufacturer_id):
    # Define Manufacturer ID
    MFID_WINBOND = "EF"  # Winbond
    MFID_MICRON = "20"  # Micron
    MFID_MACRONIX = "C2"  # Macronix

    vendor_name = {
        MFID_WINBOND: "Winbond",
        MFID_MICRON: "Micron",
        MFID_MACRONIX: "Macronix",
    }

    return vendor_name.get(manufacturer_id, "Unknown")


async def getSPIVendorLegacy(spi_id):
    cmd = "cat /tmp/spi0.%d_vendor.dat | cut -c1-2" % (spi_id)
    _, stdout, _ = await async_exec(cmd, shell=True)
    manufacturer_id = stdout.strip("\n")
    return SPIVendorID2Name(manufacturer_id)


def getMTD(name):
    mtd_name = quote(name)
    with open(PROC_MTD_PATH) as f:
        lines = f.readlines()
        for line in lines:
            if mtd_name in line:
                return line.split(":")[0]
    return None


def getSPIVendorNew(spi_id):
    mtd = getMTD("flash%d" % (spi_id))
    if mtd is None:
        return "Unknown"
    debugfs_path = f"/sys/kernel/debug/mtd/{mtd}/partid"
    try:
        with open(debugfs_path) as f:
            data = f.read().strip()
            # Example spi-nor:ef4019
            mfg_id = data.split(":")[-1][:2].upper()
            return SPIVendorID2Name(mfg_id)
    except Exception:
        pass
    return "Unknown"


async def getSPIVendor(spi_id):
    if os.path.isfile("/tmp/spi0.%d_vendor.dat" % (spi_id)):
        return await getSPIVendorLegacy(spi_id)
    return getSPIVendorNew(spi_id)


@functools.lru_cache(maxsize=1)
def read_proc_mtd() -> t.List[str]:
    mtd_list = []
    with open(PROC_MTD_PATH) as f:
        # e.g. 'mtd5: 02000000 00010000 "flash0"' -> dev="mtd5", size="02000000", erasesize="00010000", name="flash0"   # noqa B950
        RE_MTD_INFO = re.compile(
            r"""^(?P<dev>[^:]+): \s+ (?P<size>[0-9a-f]+) \s+ (?P<erasesize>[0-9a-f]+) \s+ "(?P<name>[^"]+)"$""",  # noqa B950
            re.MULTILINE | re.VERBOSE,
        )
        mtd_list.extend(m.group("name") for m in RE_MTD_INFO.finditer(f.read()))
    return mtd_list


class bmcNode(node):
    def __init__(self, info=None, actions=None):
        self.info = {} if info is None else info
        self.actions = [] if actions is None else actions

    async def _getUbootVer(self):
        # Get U-boot Version
        uboot_version = None
        uboot_ver_regex = r"^U-Boot\W+(?P<uboot_ver>20\d{2}\.\d{2})\W+.*$"
        uboot_ver_re = re.compile(uboot_ver_regex)
        mtd_meta = getMTD("meta")
        if mtd_meta is None:
            mtd0_str_dump_cmd = ["/usr/bin/strings", "/dev/mtd0"]
            _, stdout, _ = await async_exec(mtd0_str_dump_cmd)
            for line in stdout.splitlines():
                if matched := uboot_ver_re.fullmatch(line.strip()):
                    uboot_version = matched["uboot_ver"]
                    break
        else:
            try:
                mtd_dev = f"/dev/{mtd_meta}"
                with open(mtd_dev, "r") as f:
                    raw_data = f.readline()
                uboot_version = json.loads(raw_data)["version_infos"]["uboot_ver"]
            except Exception:
                uboot_version = None
        return uboot_version

    async def getUbootVer(self):
        UBOOT_VER_KV_KEY = "u-boot-ver"
        uboot_version = None
        try:
            uboot_version = kv.kv_get(UBOOT_VER_KV_KEY)
        except kv.KeyOperationFailure:
            # not cahced, read and cache it
            uboot_version = await self._getUbootVer()
            if uboot_version:
                kv.kv_set(UBOOT_VER_KV_KEY, uboot_version, kv.FCREATE)
        return uboot_version

    async def getTpmTcgVer(self):
        out_str = "NA"
        tpm1_caps = "/sys/class/tpm/tpm0/device/caps"
        if os.path.isfile(tpm1_caps):
            with open(tpm1_caps) as f:
                for line in f:
                    if "TCG version:" in line:
                        out_str = line.strip("TCG version: ").strip("\n")
        elif os.path.isfile("/usr/bin/tpm2_getcap"):
            cmd_list = [
                "/usr/bin/tpm2_getcap -c properties-fixed 2>/dev/null | grep -A2 TPM_PT_FAMILY_INDICATOR",
                "/usr/bin/tpm2_getcap properties-fixed 2>/dev/null | grep -A2 TPM2_PT_FAMILY_INDICATOR",
            ]

            for cmd in cmd_list:
                try:
                    retcode, stdout, _ = await async_exec(cmd, shell=True)
                    if retcode != 0:
                        # non-async implementation was using raising check_output
                        raise Exception(f"Command {cmd} returned non-0 exit code")
                    out_str = stdout.splitlines()[2].rstrip().split('"')[1]
                    break
                except Exception:
                    pass
        return out_str

    async def getTpmFwVer(self):
        out_str = "NA"
        tpm1_caps = "/sys/class/tpm/tpm0/device/caps"
        if os.path.isfile(tpm1_caps):
            with open(tpm1_caps) as f:
                for line in f:
                    if "Firmware version:" in line:
                        out_str = line.strip("Firmware version: ").strip("\n")
        elif os.path.isfile("/usr/bin/tpm2_getcap"):
            cmd_list = [
                "/usr/bin/tpm2_getcap -c properties-fixed 2>/dev/null | grep TPM_PT_FIRMWARE_VERSION_1",
                "/usr/bin/tpm2_getcap properties-fixed 2>/dev/null | grep -A1 TPM2_PT_FIRMWARE_VERSION_1 | grep raw",
            ]

            for cmd in cmd_list:
                try:
                    retcode, stdout, _ = await async_exec(cmd, shell=True)
                    if retcode != 0:
                        # non-async implementation was using raising check_output
                        raise Exception(f"Command {cmd} returned non-0 exit code")
                    value = int(stdout.rstrip().split(":")[1], 16)
                    out_str = "%d.%d" % (value >> 16, value & 0xFFFF)
                    break
                except Exception:
                    pass
        return out_str

    def getMemInfo(self):
        desired_keys = (
            "MemTotal",
            "MemAvailable",
            "MemFree",
            "Shmem",
            "Buffers",
            "Cached",
        )
        meminfo = {}
        with open("/proc/meminfo", "r") as mi:
            for line in mi:
                try:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    if key not in desired_keys:
                        continue
                    memval, _ = value.strip().split(" ", 1)
                    meminfo[key] = int(memval)
                except ValueError:
                    pass
        return meminfo

    async def getInformation(self, param=None):
        # Get Platform Name
        name = rest_pal_legacy.pal_get_platform_name()

        # Get MAC Address
        eth_intf = rest_pal_legacy.pal_get_eth_intf_name()
        mac_path = f"/sys/class/net/{eth_intf}/address"
        if os.path.isfile(mac_path):
            mac = open(mac_path).read()
            mac_addr = mac[:17].upper()
        else:
            mac = get_mac()
            mac_addr = ":".join(("%012X" % mac)[i : i + 2] for i in range(0, 12, 2))

        # Get BMC Reset Reason
        _, wdt_counter, _ = await async_exec(["devmem", "0x1e785010"])
        wdt_counter = int(wdt_counter, 0)
        wdt_counter &= 0xFF00

        por_flag = 0 if wdt_counter else 1
        if por_flag:
            reset_reason = "Power ON Reset"
        else:
            reset_reason = "User Initiated Reset or WDT Reset"

        # Get BMC's Up Time
        _, stdout, _ = await async_exec("uptime", shell=True)
        uptime = stdout.strip()

        # Use another method, ala /proc, but keep the old one for backwards
        # compat.
        # See http://man7.org/linux/man-pages/man5/proc.5.html for details
        # on full contents of proc endpoints.
        uptime_seconds = read_file_contents("/proc/uptime")[0].split()[0]

        # Pull load average directory from proc instead of processing it from
        # the contents of uptime command output later.
        load_avg = read_file_contents("/proc/loadavg")[0].split()[:3]

        # Get Usage information
        _, stdout, _ = await async_exec(["top", "-b", "n1"])
        adata = stdout.split("\n")
        mem_usage = adata[0]
        cpu_usage = adata[1]

        memory = self.getMemInfo()

        # Get OpenBMC version
        obc_version = ""
        _, stdout, _ = await async_exec(["cat", "/etc/issue"])

        if ver := re.search(r"[v|V]([\w\d._-]*)\s", stdout):
            obc_version = ver[1]

        # U-Boot version
        uboot_version = await self.getUbootVer()
        if uboot_version is None:
            uboot_version = "NA"

        # Get kernel release and kernel version
        kernel_release = ""
        _, stdout, _ = await async_exec(["uname", "-r"])
        kernel_release = stdout.strip("\n")

        kernel_version = ""
        _, stdout, _ = await async_exec(["uname", "-v"])
        kernel_version = stdout.strip("\n")

        # Get TPM version
        tpm_tcg_version = "NA"
        tpm_fw_version = "NA"
        if os.path.exists("/sys/class/tpm/tpm0"):
            tpm_tcg_version = await self.getTpmTcgVer()
            tpm_fw_version = await self.getTpmFwVer()

        spi0_vendor = await getSPIVendor(0)
        spi1_vendor = await getSPIVendor(1)

        # ASD status - check if ASD daemon/asd-test is currently running
        _, asd_status, _ = await async_exec("ps | grep -i [a]sd", shell=True)
        asd_status = bool(asd_status)
        boot_from_secondary = is_boot_from_secondary()

        vboot_info = await get_vboot_status()

        used_fd_count = read_file_contents("/proc/sys/fs/file-nr")[0].split()[0]

        return {
            "Description": f"{name} BMC",
            "MAC Addr": mac_addr,
            "Reset Reason": reset_reason,
            "Uptime": uptime,
            "uptime": uptime_seconds,
            "Memory Usage": mem_usage,
            "memory": memory,
            "CPU Usage": cpu_usage,
            "OpenBMC Version": obc_version,
            "u-boot version": uboot_version,
            "kernel version": f"{kernel_release} {kernel_version}",
            "TPM TCG version": tpm_tcg_version,
            "TPM FW version": tpm_fw_version,
            "SPI0 Vendor": spi0_vendor,
            "SPI1 Vendor": spi1_vendor,
            "At-Scale-Debug Running": asd_status,
            "Secondary Boot Triggered": boot_from_secondary,
            "vboot": vboot_info,
            "load-1": load_avg[0],
            "load-5": load_avg[1],
            "load-15": load_avg[2],
            "open-fds": used_fd_count,
            "MTD Parts": read_proc_mtd(),
        }

    async def doAction(self, data, param=None):
        await async_exec("sleep 1; /sbin/reboot", shell=True)
        return {"result": "success"}


def get_node_bmc():
    actions = ["reboot"]
    return bmcNode(actions=actions)
