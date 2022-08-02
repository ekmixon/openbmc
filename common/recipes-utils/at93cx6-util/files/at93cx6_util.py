#!/usr/bin/python -S
# Copyright 2004-present Facebook. All rights reserved.
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


from argparse import ArgumentParser
import at93cx6
import sys
import os

GPIO_SHADOW_DIR = '/tmp/gpionames'

def gpio_name_to_num(name):
    shadowdir = os.path.join(GPIO_SHADOW_DIR, name)
    if os.path.islink(shadowdir):
        return int(os.path.realpath(shadowdir).split('/')[-1].split('gpio')[-1])
    else:
        return int(name) if name.isdigit() else -1

def is_gpio_valid(cs, clk, mosi, miso):
    if cs is -1:
        raise Exception("CS value is invalid!")
    if clk is -1:
        raise Exception("CLK value is invalid!")
    if mosi is -1:
        raise Exception("MOSI value is invalid!")
    if miso is -1:
        raise Exception("MISO value is invalid!")

    return True

def get_raw(args):
    cs_num = gpio_name_to_num(args.cs)
    clk_num = gpio_name_to_num(args.clk)
    mosi_num = gpio_name_to_num(args.mosi)
    miso_num = gpio_name_to_num(args.miso)

    if is_gpio_valid(cs_num, clk_num, mosi_num, miso_num):
        return at93cx6.AT93CX6SPI(args.bus_width, cs_num, clk_num, mosi_num,
                      miso_num, args.model, args.verbose)

def get_chip(args):
    cs_num = gpio_name_to_num(args.cs)
    clk_num = gpio_name_to_num(args.clk)
    mosi_num = gpio_name_to_num(args.mosi)
    miso_num = gpio_name_to_num(args.miso)

    if is_gpio_valid(cs_num, clk_num, mosi_num, miso_num):
        return at93cx6.AT93CX6(
                      args.bus_width, cs_num, clk_num, mosi_num, miso_num,
                      args.byte_swap if hasattr(args, 'byte_swap') else None,
                      args.model, args.verbose)

def model_parser(ap):
    # Default, based on currenct HW configuration
    MODEL_DEFAULT = at93cx6.AT93C46

    ap.add_argument('--model', default=at93cx6.AT93C46,
                    choices=[at93cx6.AT93C46, at93cx6.AT93C56,
                             at93cx6.AT93C66, at93cx6.AT93C86],
                    help='The chip model (default: %(default)s)')

def access_parser(ap):
    # Default, based on currenct HW configuration
    SPI_CS_DEFAULT = '68'
    SPI_CLK_DEFAULT = '69'
    SPI_MOSI_DEFAULT = '70'
    SPI_MISO_DEFAULT = '71'

    spi_group = ap.add_argument_group('SPI Access')
    spi_group.add_argument('--cs', type=str, default=SPI_CS_DEFAULT,
                           help='The GPIO number/shadow name '
                           'for SPI CS pin (default: %(default)s)')
    spi_group.add_argument('--clk', type=str, default=SPI_CLK_DEFAULT,
                           help='The GPIO number/shadow name '
                           'for SPI CLK pin (default: %(default)s)')
    spi_group.add_argument('--mosi', type=str, default=SPI_MOSI_DEFAULT,
                           help='The GPIO number/shadow name '
                           'for SPI MOSI pin (default: %(default)s)')
    spi_group.add_argument('--miso', type=str, default=SPI_MISO_DEFAULT,
                           help='The GPIO number/shadow name '
                           'for SPI MISO pin (default: %(default)s)')

def bus_width_parser(ap):
    # Default, based on currenct HW configuration
    AT83C46_BUS_WIDTH = 16

    bus_group = ap.add_argument_group('Bus Width')
    bus_group.add_argument('--bus-width', type=int, default=AT83C46_BUS_WIDTH,
                           help='The configured bus width '
                                '(default: %(default)s)')

def read_raw(args):
    raw = get_raw(args)
    val = raw.read(args.address)

    if args.int:
        print "{}".format(val)
    else:
        if args.bus_width == 16:
            print "0x{:04X}".format(val)
        else:
            print "0x{:02X}".format(val)

def write_raw(args):
    value = int(args.value, 16) if args.value[:2] == "0x" else int(args.value)
    raw = get_raw(args)
    raw.ewen()
    raw.erase(args.address)
    raw.write(args.address, value)
    raw.ewds()

def erase_raw(args):
    raw = get_raw(args)
    raw.ewen()
    raw.erase(args.address)
    raw.ewds()

def raw_subparser(subparsers):
    raw_parser = subparsers.add_parser(
        'raw', help='Raw memory access')
    raw_sub = raw_parser.add_subparsers()

    read_parser = raw_sub.add_parser(
        'read', help='Read a single memory address')
    read_parser.add_argument(
        'address', type=int, help='The memory address')
    read_parser.add_argument('--int', action='store_true',
                             help='Display output as an integer')
    read_parser.set_defaults(func=read_raw)

    write_parser = raw_sub.add_parser(
        'write', help='Write a single memory address')
    write_parser.add_argument(
        'address', type=int, help='The memory address')
    write_parser.add_argument(
        'value', type=str, help='The value to write, either integer or hex')
    write_parser.set_defaults(func=write_raw)

    erase_parser = raw_sub.add_parser(
        'erase', help='Erase a single memory address')
    erase_parser.add_argument('address', type=int, help='The memory address')
    erase_parser.set_defaults(func=erase_raw)

def read_chip(args):
    chip = get_chip(args)
    data = chip.read(args.start, args.length)

    if args.file is None:
        sys.stdout.write(data)
    else:
        with open(args.file, "wb") as fp:
            fp.write(data)

def write_chip(args):
    chip = get_chip(args)

    # Either way, limit reads to the size of the chip
    if args.file is None:
        data = sys.stdin.read(chip.get_memory_size())
    else:
        with open(args.file, "rb") as fp:
            data = fp.read(chip.get_memory_size())

    if args.length is not None:
        # Make sure length is correct
        if len(data) < args.length:
            data = data + '\x00' * (args.length - len(data))
        if len(data) > args.length:
            data = data[:args.length]

    chip.write(data, args.start)

def erase_chip(args):
    chip = get_chip(args)
    chip.erase(args.start, args.length)

def chip_subparser(subparsers):
    chip_parser = subparsers.add_parser('chip', help='Chip-level access')
    chip_sub = chip_parser.add_subparsers()

    read_parser = chip_sub.add_parser('read', help='Read from the chip')
    read_parser.add_argument('--start', type=int,
                             help='The memory address to start at (default: 0)')
    read_parser.add_argument('--length', type=int,
                             help='The number of bytes to read '
                             '(default: whole chip)')
    read_parser.add_argument('--file', type=str,
                             help='File to operate on (default: stdout)')
    read_parser.add_argument('--byte-swap', default=False, action='store_true',
                             help='Byte swap values for 16-bit reads/writes '
                                  '(default: %(default)s)')
    read_parser.set_defaults(func=read_chip)

    write_parser = chip_sub.add_parser('write', help='Write to the chip')
    write_parser.add_argument('--start', type=int,
                              help='The memory address to start at '
                              '(default: 0)')
    write_parser.add_argument('--length', type=int,
                              help='The number of bytes to write '
                              '(default: file length)')
    write_parser.add_argument('--file', type=str,
                              help='File to operate on (default: stdin)')
    write_parser.add_argument('--byte-swap', default=False, action='store_true',
                              help='Byte swap values for 16-bit reads/writes '
                                   '(default: %(default)s)')
    write_parser.set_defaults(func=write_chip)

    erase_parser = chip_sub.add_parser('erase', help='Erase the chip')
    erase_parser.add_argument('--start', type=int,
                              help='The memory address to start at '
                              '(default: 0)')
    erase_parser.add_argument('--length', type=int,
                              help='The number of bytes to erase '
                              '(default: whole chip)')
    erase_parser.set_defaults(func=erase_chip)

if __name__ == "__main__":
    # General arguments
    ap = ArgumentParser()
    ap.add_argument('--verbose', action='store_true',
                    help='Print verbose debugging information')

    # Model, SPI, and bus width arguments
    model_parser(ap)
    access_parser(ap)
    bus_width_parser(ap)

    # Functionality
    subparsers = ap.add_subparsers()
    raw_subparser(subparsers)
    chip_subparser(subparsers)

    # Command runner
    args = ap.parse_args()
    args.func(args)
