import errno
import os
import shlex
import subprocess
import sys


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
        print >> sys.stderr, "remote: running git", args
        return subprocess.Popen(["git"] + list(args),
                                env=env,
                                stdin=stdin,
                                stdout=stdout, bufsize=0)

    while True:
        cmd = sys.stdin.readline()
        if cmd.startswith("connect "):
            command = cmd[8:-1]
            assert command == "git-upload-pack", "remote: wrong command %r" % command
            command = command[4:]
            print >> sys.stderr, "remote: confirming command"
            print
            sys.stdout.flush()
            p = gitpopen(command,
                         git_dir,
                         stdin=sys.stdin,
                         stdout=sys.stdout)
            sys.stdin.close()
            sys.stdout.close()
            ret = p.wait()
            print >> sys.stderr, "remote: finished %s with status %s" % (command, ret)
            break
        else:
            assert 0, "remote: invalid command %r" % cmd
            break

