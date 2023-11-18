import argparse
import logging
import os
import pipes
import subprocess
import socket
import sys
import urllib.parse

import gitremotequbes.copier

# NOTE: Some things here have been taken from
# /usr/lib/python3.8/site-packages/qrexec/client.py from a fedora system. For
# some reason, the installed stuff is different between debian and fedora
# ... that should probably be addressed.
#
import pathlib

QREXEC_CLIENT_DOM0 = "/usr/bin/qrexec-client"
QREXEC_CLIENT_VM = "/usr/bin/qrexec-client-vm"
QREXEC_CLIENT_VM_SELF = "/usr/bin/qrexec-client-vm-self"
RPC_MULTIPLEXER = "/usr/lib/qubes/qubes-rpc-multiplexer"

VERSION = None

if pathlib.Path(QREXEC_CLIENT_DOM0).is_file():
    VERSION = "dom0"
elif pathlib.Path(QREXEC_CLIENT_VM).is_file():
    VERSION = "vm"

# FROM /usr/lib/python3.8/site-packages/qrexec/client.py <<<


def get_main_parser():
    p = argparse.ArgumentParser()
    p.add_argument("name", metavar="NAME")
    p.add_argument("url", metavar="URL")
    return p


def main():
    logging.basicConfig(
        format="local:" + logging.BASIC_FORMAT,
        level=logging.DEBUG if os.getenv("QUBES_DEBUG") else logging.INFO,
    )

    p = get_main_parser()
    args = p.parse_args()
#    l.info("args=" + args)
#    sys.stderr.write("args=" + ' '.join(f'{k}={v}' for k, v in vars(args).items()) + "\n")

    url = urllib.parse.urlparse(args.url)
    assert url.scheme == "qubes"

    remoteargs = [args.name, url.path]
    if os.getenv("QUBES_DEBUG"):
        remoteargs = ["-d"] + remoteargs
    quotedargs = " ".join(pipes.quote(x) for x in remoteargs)
#    sys.stderr.write("quotedargs=" + quotedargs + "\n")
    quotedlen = len(quotedargs)

    l = logging.getLogger()

    rpcarg = subprocess.check_output([
        "systemd-escape", "--", url.path
    ], universal_newlines=True)[:-1]
    if len(rpcarg) > 64 or "\\" in rpcarg:
        # Path is too long!  We must do without rpcarg.
        rpcarg = None

    # FROM /usr/lib/python3.8/site-packages/qrexec/client.py >>>
    #
    subprocess_args=[]
    dest=url.netloc
    rpcname="ruddo.Git" + ("+%s" % rpcarg if rpcarg else "")

    client=socket.gethostname()

#    sys.stderr.write("rpcname=" + rpcname + "\n")
#    sys.stderr.write("dest=" + dest + "\n")
#    sys.stderr.write("client=" + client + "\n")

    if VERSION == "dom0":
        if dest == "dom0":
            # Invoke qubes-rpc-multiplexer directly. This will work for non-socket
            # services only.
            subprocess_args=[
                RPC_MULTIPLEXER, rpcname, "dom0"
            ]
        else:
            subprocess_args=[
                QREXEC_CLIENT_DOM0,
                "-d",
                dest,
                f"DEFAULT:QUBESRPC {rpcname} dom0",
            ]

    use_shell=False

    env = { **os.environ }

    if VERSION == "vm":
        if client == dest:
            use_client_vm_self=os.getenv("QUBES_USE_CLIENT_VM_SELF") \
                and pathlib.Path(QREXEC_CLIENT_VM_SELF).is_file()

            env = {
                **os.environ,
                "QREXEC_SERVICE_ARGUMENT": url.path,
            }

            if use_client_vm_self:
                subprocess_args=[
                    QREXEC_CLIENT_VM_SELF, rpcname
                ]
            else:
                use_shell=True
                subprocess_args=[
                    "/etc/qubes-rpc/" + rpcname
                ]
        else:
            subprocess_args=[
                QREXEC_CLIENT_VM, dest, rpcname
            ]

#    sys.stderr.write("subprocess_args=" + ' '.join(subprocess_args) + "\n")
#    l.info(subprocess_args)
    vm = subprocess.Popen(
        subprocess_args,
        shell=use_shell,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        bufsize=0,
    )

    cmd = sys.stdin.readline()
    assert cmd == "capabilities\n"
    sys.stdout.write("connect\n\n")
    sys.stdout.flush()

    vm.stdin.write(("%s\n" % quotedlen + quotedargs).encode("utf-8"))
    vm.stdin.flush()

    line = vm.stdout.readline()
    if line != b"confirmed\n":
        l.debug("the request appears to have been refused or it malfunctioned")
        return 128

    ret = 0
    while ret == 0:
        for f in sys.stdin.buffer, vm.stdin, sys.stdout.buffer, vm.stdout:
            gitremotequbes.copier.b(f)
        cmd = sys.stdin.readline()

        if not cmd:
            l.debug("no more commands, exiting")
            break
        elif cmd.startswith("connect "):
            l.debug("asked to run %s", cmd)
            vm.stdin.write(cmd.encode("utf-8"))
            reply = vm.stdout.readline().decode("utf-8")
            assert reply == "\n", "local: wrong reply %r" % reply
            sys.stdout.write(reply)
            sys.stdout.flush()

            ret = gitremotequbes.copier.call(
                vm,
                sys.stdin.buffer,
                sys.stdout.buffer,
            )
            if ret != 0:
                l.debug("remote side exited with %s", ret)
            else:
                l.debug("remote side exited normally")
            break
        elif cmd == "\n":
            l.debug("git sent us an empty line as command")
        else:
            l.error("invalid command %r", cmd)
            ret = 127

    return ret
