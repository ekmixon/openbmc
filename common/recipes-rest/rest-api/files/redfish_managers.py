import fcntl
import os
import socket
import struct
from uuid import getnode as get_mac
from subprocess import *
import rest_pal_legacy
from aiohttp import web
from common_utils import async_exec, dumps_bytestr
from redfish_base import validate_keys

SIOCGIFADDR = 0x8915  # get PA address


def get_fqdn_str() -> str:
    with open("/etc/hosts") as etc_hosts:
        fqdn_str = etc_hosts.readline().strip().split()[1]
    return fqdn_str


def get_mac_address(if_name: str) -> str:
    mac_addr = ""
    mac_path = f"/sys/class/net/{if_name}/address"
    if os.path.isfile(mac_path):
        mac = open(mac_path).read()
        return mac[:17].upper()
    else:
        mac = get_mac()
        return ":".join(("%012X" % mac)[i : i + 2] for i in range(0, 12, 2))


def get_ipv4_ip_address(if_name: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        v4_ip = socket.inet_ntoa(
            fcntl.ioctl(
                s.fileno(),
                SIOCGIFADDR,
                struct.pack("256s", if_name[:15].encode("utf-8")),
            )[20:24]
        )
    except IOError:
        return None

    return v4_ip


async def get_ipv4_netmask(if_name: str) -> str:
    ipv4_netmask = ""
    cmd = "/sbin/ifconfig %s |  awk '/Mask/{print $4}' " % if_name
    _, ipv4_netmask, _ = await async_exec(cmd, shell=True)
    if ipv4_netmask:
        ipv4_netmask = ipv4_netmask.strip().split(":")[1]
    return ipv4_netmask


async def get_ipv6_ip_address(if_name: str) -> str:
    v6_ip = ""
    cmd = "ip -6 -o addr show dev %s scope global | awk '{print $4}'" % if_name
    _, v6_ip, _ = await async_exec(cmd, shell=True)
    if v6_ip:
        v6_ip = v6_ip.strip().split("/64")[0]
    return v6_ip


def get_ipv4_gateway() -> str:
    """Returns the default gateway"""
    octet_list = []
    gw_from_route = None
    with open("/proc/net/route", "r") as proc_net_route:
        for line in proc_net_route:
            words = line.split()
            dest = words[1]
            try:
                if int(dest) == 0:
                    gw_from_route = words[2]
                    break
            except ValueError:
                pass
        if not gw_from_route:
            return None

    for i in range(8, 1, -2):
        octet = gw_from_route[i - 2 : i]
        octet = int(octet, 16)
        octet_list.append(str(octet))

    return ".".join(octet_list)


async def get_managers(request: str) -> web.Response:
    body = {
        "@odata.context": "/redfish/v1/$metadata#ManagerCollection.ManagerCollection",
        "@odata.id": "/redfish/v1/Managers",
        "@odata.type": "#ManagerCollection.ManagerCollection",
        "Name": "Manager Collection",
        "Members@odata.count": 1,
        "Members": [{"@odata.id": "/redfish/v1/Managers/1"}],
    }
    await validate_keys(body)
    return web.json_response(body, dumps=dumps_bytestr)


async def get_managers_members(request: str) -> web.Response:
    uuid_data = str(rest_pal_legacy.pal_get_uuid())
    with open("/etc/issue") as etc_issue:
        firmware_version = etc_issue.read().rstrip("\n")
    body = {
        "@odata.context": "/redfish/v1/$metadata#Manager.Manager",
        "@odata.id": "/redfish/v1/Managers/1",
        "@odata.type": "#Manager.v1_1_0.Manager",
        "ManagerType": "BMC",
        "UUID": uuid_data,
        "Status": {"State": "Enabled", "Health": "OK"},
        "FirmwareVersion": firmware_version,
        "NetworkProtocol": {"@odata.id": "/redfish/v1/Managers/1/NetworkProtocol"},
        "EthernetInterfaces": {
            "@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces"
        },
        "LogServices": {"@odata.id": "/redfish/v1/Managers/1/LogServices"},
        "Links": {},
        "Actions": {
            "#Manager.Reset": {
                "target": "/redfish/v1/Managers/1/Actions/Manager.Reset",
                "ResetType@Redfish.AllowableValues": [
                    "ForceRestart",
                    "GracefulRestart",
                ],
            }
        },
    }
    await validate_keys(body)
    return web.json_response(body, dumps=dumps_bytestr)


async def get_manager_ethernet(request: str) -> web.Response:
    body = {
        "@odata.context": "/redfish/v1/$metadata#EthernetInterfaceCollection.EthernetInterfaceCollection",  # noqa: B950
        "@odata.id": "/redfish/v1/Managers/System/EthernetInterfaces",
        "@odata.type": "#EthernetInterfaceCollection.EthernetInterfaceCollection",
        "Name": "Ethernet Network Interface Collection",
        "Description": "Collection of EthernetInterfaces for this Manager",
        "Members@odata.count": 1,
        "Members": [{"@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces/1"}],
    }
    await validate_keys(body)
    return web.json_response(body, dumps=dumps_bytestr)


async def get_ethernet_members(request: str) -> web.Response:
    eth_intf = rest_pal_legacy.pal_get_eth_intf_name()
    mac_address = get_mac_address(eth_intf)
    host_name = socket.gethostname()
    fqdn = get_fqdn_str()
    ipv4_ip = get_ipv4_ip_address(eth_intf)
    ipv4_netmask = await get_ipv4_netmask(eth_intf)
    ipv4_gateway = get_ipv4_gateway()
    ipv6_ip = await get_ipv6_ip_address(eth_intf)
    body = {
        "@odata.context": "/redfish/v1/$metadata#EthernetInterface.EthernetInterface",  # noqa: B950
        "@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces/1",
        "@odata.type": "#EthernetInterface.v1_4_0.EthernetInterface",
        "Id": "1",
        "Name": "Manager Ethernet Interface",
        "Description": "Management Network Interface",
        "Status": {"State": "Enabled", "Health": "OK"},
        "InterfaceEnabled": True,
        "MACAddress": mac_address,
        "SpeedMbps": 100,
        "HostName": host_name,
        "FQDN": fqdn,
        "IPv4Addresses": [
            {
                "Address": ipv4_ip,
                "SubnetMask": ipv4_netmask,
                "AddressOrigin": "DHCP",
                "Gateway": ipv4_gateway,
            }
        ],
        "IPv6Addresses": [
            {
                "Address": ipv6_ip,
                "PrefixLength": 64,
                "AddressOrigin": "SLAAC",
                "AddressState": "Preferred",
            }
        ],
        "StaticNameServers": [],
    }
    await validate_keys(body)
    return web.json_response(body, dumps=dumps_bytestr)


async def get_manager_network(request: str) -> web.Response:
    host_name = socket.gethostname()
    fqdn = get_fqdn_str()
    body = {
        "@odata.context": "/redfish/v1/$metadata#ManagerNetworkProtocol.ManagerNetworkProtocol",  # noqa: B950
        "@odata.id": "/redfish/v1/Managers/1/NetworkProtocol",
        "@odata.type": "#ManagerNetworkProtocol.v1_2_0.ManagerNetworkProtocol",
        "Id": "NetworkProtocol",
        "Name": "Manager Network Protocol",
        "Description": "Manager Network Service Status",
        "Status": {"State": "Enabled", "Health": "OK"},
        "HostName": host_name,
        "FQDN": fqdn,
        "HTTP": {"ProtocolEnabled": True, "Port": 8080},
        "HTTPS": {"ProtocolEnabled": True, "Port": 8443},
        "SSH": {"ProtocolEnabled": True, "Port": 22},
        "SSDP": {
            "ProtocolEnabled": True,
            "Port": 1900,
            "NotifyMulticastIntervalSeconds": 600,
            "NotifyTTL": 5,
            "NotifyIPv6Scope": "Site",
        },
    }
    await validate_keys(body)
    return web.json_response(body, dumps=dumps_bytestr)
