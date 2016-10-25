import errno
import fcntl
import os
import select
import shlex
import struct
import subprocess
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

    def gitpopen(*args, **kwargs):
        env = dict(os.environ)
        env["GIT_DIR"] = git_dir
        stdin = kwargs.get("stdin")
        stdout = kwargs.get("stdout")
        # print >> sys.stderr, "remote: running git", args
        return subprocess.Popen(["git"] + list(args),
                                env=env,
                                stdin=stdin,
                                stdout=stdout)

    ret = 0
    while True:
        cmd = sys.stdin.readline()
        if cmd.startswith("connect "):
            command = cmd[8:-1]
            assert command == "git-upload-pack", "remote: wrong command %r" % command
            sys.stdout.write("\n")
            sys.stdout.flush()
            p = gitpopen(command[4:],
                         git_dir,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE)

            allfds = {p.stdout: sys.stdout, sys.stdin: p.stdin}
            allnames = None and {
                p.stdout: "git-receive-pack output",
                p.stdin: "git-receive-pack input",
                sys.stdin: "master output",
                sys.stdout: "master input",
            }
            gitremotequbes.copier.copy(allfds, allnames, "remote: ")

            ret = p.wait()
            if ret != 0:
                print >> sys.stderr, "remote: finished %s with status %s" % (command, ret)
            break
        else:
            assert 0, "remote: invalid command %r" % cmd
            break

    return ret
