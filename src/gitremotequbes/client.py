import argparse
import errno
import fcntl
import md5
import os
import pipes
import select
import signal
import subprocess
import sys
import threading
import urlparse


def get_main_parser():
    p = argparse.ArgumentParser()
    p.add_argument("name", metavar="NAME")
    p.add_argument("url", metavar="URL")
    return p


def main():
    p = get_main_parser()
    args = p.parse_args()
    url = urlparse.urlparse(args.url)
    assert url.scheme == "qubes"

    os.execv(
        "/usr/lib/qubes/qrexec-client-vm",
        ["/usr/lib/qubes/qrexec-client-vm",
         url.netloc,
         "ruddo.Git",
         sys.executable,
         "-u",
         __file__, args.name, url.path]
    )


def nb(f):
    fd = f.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)


def get_helper_parser():
    p = argparse.ArgumentParser()
    p.add_argument("name", metavar="NAME")
    p.add_argument("path", metavar="PATH")
    return p


def helper():
    p = get_helper_parser()
    args = p.parse_args()

    gitoutput = os.fdopen(int(os.getenv("SAVED_FD_0")), "rb")
    gitinput = os.fdopen(int(os.getenv("SAVED_FD_1")), "ab")

    cmd = gitoutput.readline()
    assert cmd == "capabilities\n"

    gitinput.write("connect\n\n")
    gitinput.flush()

    quotedargs = " ".join(pipes.quote(x) for x in [args.name, args.path])
    quotedlen = len(quotedargs)
    sys.stdout.write("%s\n" % quotedlen + quotedargs)
    sys.stdout.flush()

    while True:
        cmd = gitoutput.readline()
        if cmd.startswith("connect "):
            sys.stdout.write(cmd)
            reply = sys.stdin.readline()
            assert reply == "\n", "local: wrong reply %r" % reply
            gitinput.write(reply)
            gitinput.flush()
            nb(gitoutput)
            nb(sys.stdin)
            allfds = [gitoutput, sys.stdin]
            while allfds:
                fds = select.select(allfds, [], [])
                byte = fds[0][0].read()
                if fds[0][0] == gitoutput:
                    out = sys.stdout
                else:
                    out = gitinput
                if byte:
                    out.write(byte)
                    out.flush()
                else:
                    fds[0][0].close()
                    out.close()
                    allfds.remove(fds[0][0])
            break
        else:
            assert 0, "remote: invalid command %r" % cmd
            break


if __name__ == "__main__":
    helper()
