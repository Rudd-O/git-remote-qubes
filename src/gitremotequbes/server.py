import os
import shlex
import sys

import gitremotequbes.copier


def main():
    quotedlen = sys.stdin.readline()
    quotedlen = int(quotedlen, 10)
    if quotedlen > 65535 or quotedlen < 1:
        assert 0, "invalid len"
    args = sys.stdin.read(quotedlen)
    if len(args) != quotedlen:
        assert 0, "invalid argument list"
    try:
        args = shlex.split(args)
    except Exception, e:
        assert 0, "invalid argument list: %s" % e

    git_dir = args[1]

    ret = 0
    while True:
        cmd = sys.stdin.readline()
        if cmd.startswith("connect "):
            cmd = cmd[8:-1]
            assert cmd == "git-upload-pack", "remote: bad command %r" % cmd
            sys.stdout.write("\n")

            ret = gitremotequbes.copier.call(
                ["git", cmd[4:], git_dir],
                sys.stdin,
                sys.stdout
            )
            if ret != 0:
                print >> sys.stderr, \
                    "remote: %s exited with nonzero status %s" % (cmd, ret)
            break
        else:
            assert 0, "remote: invalid command %r" % cmd
            break

    return ret
