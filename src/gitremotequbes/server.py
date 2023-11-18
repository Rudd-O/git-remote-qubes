import logging
import os
import shlex
import signal
import subprocess
import sys

import gitremotequbes.copier


def main():
    quotedlen = sys.stdin.readline()
    if not quotedlen:
        logging.basicConfig(format="remote:" + logging.BASIC_FORMAT, level=logging.INFO)
        l = logging.getLogger()
        logging.error("Peer disconnected early.")
        return 8
    quotedlen = int(quotedlen, 10)
    if quotedlen > 65535 or quotedlen < 1:
        assert 0, "invalid len"
    args = sys.stdin.read(quotedlen)
#    sys.stdout.write("STDOUT: args=" + args + "\n")
#    sys.stderr.write("STDERR: args=" + args + "\n")
    if len(args) != quotedlen:
        assert 0, "invalid argument list"
    try:
        args = shlex.split(args)
    except Exception as e:
        assert 0, "invalid argument list: %s" % e
    if args[0] == "-d":
        args = args[1:]
        level = logging.DEBUG
    else:
        level = logging.INFO
    git_dir = args[1]

    logging.basicConfig(format="remote:" + logging.BASIC_FORMAT, level=level)
    l = logging.getLogger()

    use_trusted_arg=True
    use_systemd_escape=False

    trustedarg = os.getenv("QREXEC_SERVICE_ARGUMENT")
#    sys.stderr.write("trustedarg=" + trustedarg + "\n")

    if use_trusted_arg:
        if trustedarg:
            # Qubes OS subsystem has sent us an argument, and that argument
            # is trusted, so trust that over whatever the remote process said.
            # FIXME: WTF? this systemd thing totally clobbers the incoming rirectory ... replaces `-' with ``/'`
            l.debug("trustworthy argument %r sent by Qubes OS", trustedarg)
            git_dir=trustedarg
            if use_systemd_escape:
                git_dir = subprocess.check_output([
                    "systemd-escape", "--unescape", "--", trustedarg
                ], universal_newlines=True)[:-1]

    sys.stdout.write("confirmed\n")

    while True:
        for f in sys.stdin, sys.stdout:
            gitremotequbes.copier.b(f)
        cmd = sys.stdin.readline()
#        sys.stderr.write("cmd=" + cmd + "\n")

        if not cmd:
            l.debug("no more commands, exiting")
            break
        if cmd.startswith("connect "):
            cmd = cmd[8:-1]
            assert cmd in ("git-upload-pack", "git-receive-pack"), \
                "remote: bad command %r" % cmd
            sys.stdout.write("\n")
            # And here we go.  We no longer are in control.  Child is.
#            sys.stderr.write("cmd[4:]=" + cmd[4:] + "\n")
#            sys.stderr.write("git_dir=" + git_dir + "\n")
            os.execvp("git", ["git", cmd[4:], git_dir])
        else:
            assert 0, "invalid command %r" % cmd
