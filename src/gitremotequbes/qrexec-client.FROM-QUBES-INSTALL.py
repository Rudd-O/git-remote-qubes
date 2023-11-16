# FROM /usr/lib/python3.8/site-packages/qrexec/client.py
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2017-2018 Wojtek Porczyk <woju@invisiblethingslab.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, see <https://www.gnu.org/licenses/>.

import pathlib
import subprocess
import asyncio

from .utils import prepare_subprocess_kwds

QREXEC_CLIENT_DOM0 = "/usr/bin/qrexec-client"
QREXEC_CLIENT_VM = "/usr/bin/qrexec-client-vm"
RPC_MULTIPLEXER = "/usr/lib/qubes/qubes-rpc-multiplexer"

VERSION = None

if pathlib.Path(QREXEC_CLIENT_DOM0).is_file():
    VERSION = "dom0"
elif pathlib.Path(QREXEC_CLIENT_VM).is_file():
    VERSION = "vm"


def call(dest, rpcname, arg=None, *, input=None):
    """Invoke qrexec call

    The `input` parameter should be either :py:class:`str` or :py:class:`bytes`
    or a *real* file, which has file descriptor (as returned by ``.fileno()``
    method). Other file-like objects are not supported.

    :param str dest: name of the policied call
    :param str rpcname: name of a call from Policy API
    :param str or None arg: argument of the call
    :param str or bytes or file or None input: an input to the qrexec call
    :rtype: str
    :raises subprocess.CalledProcessError: on failure
    """
    # pylint: disable=redefined-builtin

    command = make_command(dest, rpcname, arg)
    return subprocess.check_output(
        command, **prepare_subprocess_kwds(input)
    ).decode()


async def call_async(dest, rpcname, arg=None, *, input=None):
    """Invoke qrexec call (async version)

    The `input` parameter should be either :py:class:`str` or :py:class:`bytes`
    or a *real* file, which has file descriptor (as returned by ``.fileno()``
    method). Other file-like objects are not supported.

    :param str dest: name of the policied call
    :param str rpcname: name of a call from Policy API
    :param str or None arg: argument of the call
    :param str or bytes or file or None input: an input to the qrexec call
    :rtype: str
    :raises subprocess.CalledProcessError: on failure
    """
    # pylint: disable=redefined-builtin

    command = make_command(dest, rpcname, arg)

    if input is None:
        stdin = subprocess.DEVNULL
        to_communicate = None
    elif isinstance(input, bytes):
        stdin = subprocess.PIPE
        to_communicate = input
    elif isinstance(input, str):
        stdin = subprocess.PIPE
        to_communicate = input.encode()
    else:
        # Assume this is a file
        stdin = input
        to_communicate = None

    process = await asyncio.create_subprocess_exec(
        *command, stdin=stdin, stdout=subprocess.PIPE
    )

    stdout, _stderr = await process.communicate(to_communicate)
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)
    return stdout.decode()


def make_command(dest, rpcname, arg):
    assert "+" not in rpcname
    if arg is not None:
        rpcname = f"{rpcname}+{arg}"

    if VERSION == "dom0" and dest == "dom0":
        # Invoke qubes-rpc-multiplexer directly. This will work for non-socket
        # services only.
        return [RPC_MULTIPLEXER, rpcname, "dom0"]

    if VERSION == "dom0":
        return [
            QREXEC_CLIENT_DOM0,
            "-d",
            dest,
            f"DEFAULT:QUBESRPC {rpcname} dom0",
        ]
    if VERSION == "vm":
        return [QREXEC_CLIENT_VM, dest, rpcname]

    assert VERSION is None
    raise NotImplementedError("qrexec not available")
