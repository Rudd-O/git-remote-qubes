import fcntl
import logging
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


class Copy(threading.Thread):
    """Copy from the keys of the dictionary allfds to the values of the
    allfds dictionary.

    Side effects: fds passed will be set to nonblocking.
    """

    def __init__(self, allfds):
        threading.Thread.__init__(self)
        self.l = logging.getLogger("copy")
        self.setDaemon(True)
        self.allfds = allfds
        for readable in allfds:
            nb(readable)
        self.enders = {}
        for r in self.allfds:
            pr, pw = os.pipe()
            pr = os.fdopen(pr, "rb")
            pw = os.fdopen(pw, "ab")
            nb(pr)
            self.enders[r] = [pr, pw]

    def fdname(self, f):
        return "[%s %r]" % (f.name, f.mode)

    def run(self):
        fdname = self.fdname
        l = self.l

        def copier(readable, writable):
            l.debug("beginning to copy from %s to %s",
                    fdname(readable), fdname(writable))
            stop = False
            readables = [readable, self.enders[readable][0]]
            while True:
                r, _, _ = select.select(
                    readables,
                    [],
                    [],
                    0 if stop else None
                )
                if self.enders[readable][0] in r:
                    l.debug("signaled to stop copying from %s to %s",
                            fdname(readable), fdname(writable))
                    self.enders[readable][0].close()
                    readables.remove(self.enders[readable][0])
                    stop = True
                    continue
                elif stop and not r:
                    break
                chunk = r[0].read()
                if type(chunk) is str:
                    chunk = str.encode("utf-8")
                if chunk == '' or chunk == b"":
                    l.debug("%s closed", fdname(readable))
                    readable.close()
                    l.debug("closing write end %s",
                            fdname(self.allfds[readable]))
                    self.allfds[readable].close()
                    self.enders[readable][0].close()
                    break
                l.debug("copying from %s to %s: %r",
                        fdname(readable), fdname(writable), chunk)
                writable.write(chunk)
                writable.flush()
            l.debug("done copying data from %s to %s",
                    fdname(readable), fdname(writable))

        self.l.debug("beginning to copy")

        threads = []
        for readable, writable in list(self.allfds.items()):
            threads.append(threading.Thread(target=copier,
                                            args=(readable, writable)))
            threads[-1].setDaemon(True)
            threads[-1].start()

        for t in threads:
            t.join()

        self.l.debug("done copying")

    def end(self):
        for readable, (_, wp) in list(self.enders.items()):
            self.l.debug("ending copy of data from %s",
                         self.fdname(readable))
            wp.close()


def call(cmd, stdin, stdout, env=None):
    """call() runs (or adopts) a subprocess, copying data from stdin into
    the process' stdin, and stdout from the process into stdout.
    """
    if env is None:
        env = os.environ

    l = logging.getLogger("call")

    if isinstance(cmd, subprocess.Popen):
        p = cmd
        l.debug("adopting command %s", cmd)
    else:
        l.debug("running command %s", cmd)
        p = subprocess.Popen(list(cmd),
                             env=env,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)

    copier = Copy({p.stdout: stdout, stdin: p.stdin})
    copier.start()

    l.debug("waiting for %s to end", cmd)
    ret = p.wait()
    l.debug("%s ended, signaling copier to end", cmd)
    copier.end()
    l.debug("copier signaled, waiting for readers and writers")
    copier.join()
    l.debug("readers and writers done")

    return ret
