import fcntl
import os
import select
import sys


def nb(f):
    fd = f.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)


def copy(allfds, log=False, prefix=""):
    for fd in allfds.keys() + allfds.values():
        nb(fd)

    def names(sockets):
        if log:
            return [log[s] for s in sockets]
        return ""

    allfds_reverse = dict((v, k) for k, v in allfds.items())
    already_readable = set()
    already_writable = set()
    readypairs = {}

    while allfds:
        query_readables = set(allfds.keys()) - already_readable
        query_writables = set(allfds.values()) - already_writable
        if log:
            print >> sys.stderr, "%salready readables:  %s" % (prefix, names(already_readable))
            print >> sys.stderr, "%salready writables:  %s" % (prefix, names(already_writable))
            print >> sys.stderr, "%squerying readables: %s" % (prefix, names(query_readables))
            print >> sys.stderr, "%squerying writables: %s" % (prefix, names(query_writables))

        readables, writables, _ = select.select(
            query_readables,
            query_writables,
            []
        )

        already_readable.update(readables)
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

        if log:
            print >> sys.stderr, "%spairs: %s" % (prefix, readypairs)

        for readable, writable in readypairs.items():
            del readypairs[readable]
            already_readable.remove(readable)
            already_writable.remove(writable)
            buf = readable.read()
            if not buf:
                if log:
                    args = tuple([prefix] + names([readable, writable]))
                    print >> sys.stderr, "%sCLOSER readable %s closed, closing writable %s" % args
                readable.close()
                writable.close()
                del allfds[readable]
                del allfds_reverse[writable]
            else:
                try:
                    if log:
                        args = tuple([prefix] + names([readable, writable]) + [buf])
                        print >> sys.stderr, "%sCOPIER readable %s read, writing to writable %s: %r" % args
                    writable.write(buf)
                    writable.flush()
                except Exception:
                    readable.close()
                    writable.close()
                    del allfds[readable]
                    del allfds_reverse[writable]
                    raise
