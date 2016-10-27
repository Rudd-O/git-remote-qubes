import fcntl
import os
import select
import subprocess
import threading


def nb(f):
    fd = f.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)


def b(f):
    fd = f.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl & (~os.O_NONBLOCK))


def copy(allfds, eager=True, closefds=True):
    """Copy from the keys of the dictionary allfds to the values of the
    allfds dictionary.   If eager is True and one of the readables in
    allfds' keys is closed, close down all fds if closefds=True, then return.
    Else wait until all fds are closed, copying data in the meantime."""
    for fd in allfds.keys() + allfds.values():
        nb(fd)

    allfds_reverse = dict((v, k) for k, v in allfds.items())
    already_readable = set()
    already_writable = set()
    readypairs = {}

    shutdown = False

    while allfds:
        query_readables = set(allfds.keys()) - already_readable
        query_writables = set(allfds.values()) - already_writable

        readables, writables, _ = select.select(
            query_readables,
            query_writables,
            [],
            0 if shutdown else None,
        )

        if shutdown and not (readables or writables):
            # A previous loop discovered that one of the readables was closed.
            # We polled one more time with timeout zero, and nothing came up
            # ready to be read or written.  This means we are ready to shut
            # down the entire copy loop.
            if closefds:
                for readable, writable in allfds.items():
                    readable.close()
                    writable.close()
            break

        already_readable.update(set(readables))
        already_writable.update(writables)

        for readable in allfds.keys():
            if readable in already_readable:
                if readable not in readypairs:
                    readypairs[readable] = False
        for writable in allfds.values():
            if writable in already_writable:
                matching_readable = allfds_reverse[writable]
                if matching_readable in readypairs:
                    readypairs[matching_readable] = writable

        for readable, writable in readypairs.items():
            del readypairs[readable]
            already_readable.remove(readable)
            already_writable.remove(writable)
            buf = readable.read()
            if not buf:
                if closefds:
                    readable.close()
                    writable.close()
                del allfds[readable]
                del allfds_reverse[writable]
                # Here we make the decision to shut the entire loop down
                # after the first time that a readable has been closed.
                # but only if eager is True.
                if eager:
                    shutdown = True
            else:
                try:
                    writable.write(buf)
                    writable.flush()
                except Exception:
                    readable.close()
                    writable.close()
                    del allfds[readable]
                    del allfds_reverse[writable]
                    raise


def call(cmd, stdin, stdout, env=None, eager=True, closefds=True):
    """call() runs a subprocess, copying data from stdin into the process'
    stdin, and stdout from the process into stdout.  The difference
    with subprocess.call is that, when eager is true, as soon as one of the
    read fds is closed, all other (both the passed ones and the subprocess
    ones) are closed, the copy loop exits, and call() switches to waiting
    for the process to finish."""
    if env is None:
        env = os.environ
    p = subprocess.Popen(list(cmd),
                         env=env,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE)

    ret = []

    def monitor():
        ret.append(p.wait())

    t = threading.Thread(target=monitor)
    t.setDaemon(True)
    t.start()

    allfds = {p.stdout: stdout, stdin: p.stdin}
    copy(allfds, eager=eager, closefds=closefds)

    t.join()

    if not closefds:
        p.stdin.close()
        p.stdout.close()

    return ret[0]
