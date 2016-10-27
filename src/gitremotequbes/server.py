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
        for f in sys.stdin, sys.stdout:
            gitremotequbes.copier.b(f)
        cmd = sys.stdin.readline()

        if not cmd:
            print >> sys.stderr, "remote: no more commands, exiting"
            return 0
        if cmd.startswith("connect "):
            cmd = cmd[8:-1]
            assert cmd in ("git-upload-pack", "git-receive-pack"), \
                "remote: bad command %r" % cmd
            sys.stdout.write("\n")

            print >> sys.stderr, "remote: running command", cmd
            ret = gitremotequbes.copier.call(
                ["git", cmd[4:], git_dir],
                sys.stdin,
                sys.stdout,
                eager=True,
                closefds=False,
            )
            if ret != 0:
                print >> sys.stderr, \
                    "remote: %s exited with nonzero status %s" % (cmd, ret)
                break
            else:
                print >> sys.stderr, \
                    "remote: %s exited normally" % (cmd,)
            break
        else:
            assert 0, "remote: invalid command %r" % cmd
            break

    return ret
