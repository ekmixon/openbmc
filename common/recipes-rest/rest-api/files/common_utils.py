import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Union

from common_webapp import WebApp

common_executor = ThreadPoolExecutor(5)

# cache for endpoint_children
ENDPOINT_CHILDREN = {}


def common_force_async(func):
    # common handler will use its own executor (thread based),
    # we initentionally separated this from the executor of
    # board-specific REST handler, so that any problem in
    # common REST handlers will not interfere with board-specific
    # REST handler, and vice versa
    async def func_wrapper(self, *args, **kwargs):
        # Convert the possibly blocking helper function into async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            common_executor, func, self, *args, **kwargs
        )
        return result

    return func_wrapper


# When we call request.json() in asynchronous function, a generator
# will be returned. Upon calling next(), the generator will either :
#
# 1) return the next data as usual,
#   - OR -
# 2) throw StopIteration, with its first argument as the data
#    (this is for indicating that no more data is available)
#
# Not sure why aiohttp's request generator is implemented this way, but
# the following function will handle both of the cases mentioned above.
def get_data_from_generator(self, data_generator):
    data = None
    try:
        data = next(data_generator)
    except StopIteration as e:
        data = e.args[0]
    return data


def get_endpoints(path: str):
    app = WebApp.instance()
    endpoints = set()
    splitpaths = {}
    if path in ENDPOINT_CHILDREN:
        endpoints = ENDPOINT_CHILDREN[path]
    else:
        position = len(path.split("/"))
        for route in app.router.resources():
            rest_route_path = route.url().split("/")
            if len(rest_route_path) > position and path in route.url():
                endpoints.add(rest_route_path[position])
        endpoints = sorted(endpoints)
        ENDPOINT_CHILDREN[path] = endpoints
    return endpoints


# aiohttp allows users to pass a "dumps" function, which will convert
# different data types to JSON. This new dumps function will simply call
# the original dumps function, along with the new type handler that can
# process byte strings.
def dumps_bytestr(obj):
    # aiohttp's json_response function uses py3 JSON encoder, which
    # doesn't know how to handle a byte string. So we extend this function
    # to handle the case. This is a standard way to add a new type,
    # as stated in JSON encoder source code.
    def default_bytestr(o):
        # If the object is a byte string, it will be converted
        # to a regular string. Otherwise we move on (pass) to
        # the usual error generation routine
        try:
            o = o.decode("utf-8")
            return o
        except AttributeError:
            pass
        raise TypeError(f"{repr(o)} is not JSON serializable")

    # Just call default dumps function, but pass the new default function
    # that is capable of process byte strings.
    return json.dumps(obj, default=default_bytestr)


def running_systemd():
    return "systemd" in os.readlink("/proc/1/exe")


async def async_exec(
    cmd: Union[List[str], str], shell: bool = False
) -> (int, str, str):
    if shell:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

    stdout, stderr = await proc.communicate()
    data = stdout.decode()
    err = stderr.decode()

    await proc.wait()

    return proc.returncode, data, err
