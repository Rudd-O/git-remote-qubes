import argparse
import logging
import os
import pipes
import subprocess
import sys
import urlparse

import gitremotequbes.copier


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
    url = urlparse.urlparse(args.url)
    assert url.scheme == "qubes"

    l = logging.getLogger()

    rpcarg = subprocess.check_output([
        "systemd-escape", "--", url.path
    ])[:-1]
    if len(rpcarg) > 64:
        # Path is too long!  We must do without rpcarg.
        rpcarg = None

    vm = subprocess.Popen(
        ["/usr/lib/qubes/qrexec-client-vm",
         url.netloc,
         "ruddo.Git+%s" % rpcarg if rpcarg else "ruddo.Git"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    cmd = sys.stdin.readline()
    assert cmd == "capabilities\n"
    sys.stdout.write("connect\n\n")

    remoteargs = [args.name, url.path]
    if os.getenv("QUBES_DEBUG"):
        remoteargs = ["-d"] + remoteargs
    quotedargs = " ".join(pipes.quote(x) for x in remoteargs)
    quotedlen = len(quotedargs)
    vm.stdin.write("%s\n" % quotedlen + quotedargs)

    line = vm.stdout.readline()
    if line != "confirmed\n":
        l.debug("the request appears to have been refused or it malfunctioned")
        return 128

    ret = 0
    while ret == 0:
        for f in sys.stdin, vm.stdin, sys.stdout, vm.stdout:
            gitremotequbes.copier.b(f)
        cmd = sys.stdin.readline()

        if not cmd:
            l.debug("no more commands, exiting")
            break
        elif cmd.startswith("connect "):
            l.debug("asked to run %s", cmd)
            vm.stdin.write(cmd)
            reply = vm.stdout.readline()
            assert reply == "\n", "local: wrong reply %r" % reply
            sys.stdout.write(reply)

            ret = gitremotequbes.copier.call(
                vm,
                sys.stdin,
                sys.stdout
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
