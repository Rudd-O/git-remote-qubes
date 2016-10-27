import argparse
import logging
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
    logging.basicConfig(format="local:" + logging.BASIC_FORMAT,
                        level=logging.DEBUG)

    p = get_main_parser()
    args = p.parse_args()
    url = urlparse.urlparse(args.url)
    assert url.scheme == "qubes"

    l = logging.getLogger("remote")

    vm = subprocess.Popen(
        ["/usr/lib/qubes/qrexec-client-vm",
         url.netloc,
         "ruddo.Git"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    cmd = sys.stdin.readline()
    assert cmd == "capabilities\n"
    sys.stdout.write("connect\n\n")

    quotedargs = " ".join(pipes.quote(x) for x in [args.name, url.path])
    quotedlen = len(quotedargs)
    vm.stdin.write("%s\n" % quotedlen + quotedargs)

    while True:
        for f in sys.stdin, vm.stdin, sys.stdout, vm.stdout:
            gitremotequbes.copier.b(f)
        cmd = sys.stdin.readline()

        if not cmd:
            l.debug("no more commands, exiting")
            return 0
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
        else:
            l.error("local: invalid command %s", cmd)
            ret = 127
            break

    return ret
