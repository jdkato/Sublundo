import time

agescales = [("year", 3600 * 24 * 365), ("month", 3600 * 24 * 30),
             ("week", 3600 * 24 * 7), ("day", 3600 * 24), ("hour", 3600),
             ("minute", 60), ("second", 1)]


def age(ts):
    '''turn a timestamp into an age string.'''

    def plural(t, c):
        if c == 1:
            return t
        return t + "s"

    def fmt(t, c):
        return "%d %s" % (c, plural(t, c))

    now = time.time()
    then = ts
    if then > now:
        return 'in the future'

    delta = max(1, int(now - then))
    if delta > agescales[0][1] * 2:
        return time.strftime('%Y-%m-%d', time.gmtime(float(ts)))

    for t, s in agescales:
        n = delta // s
        if n >= 2 or s == 1:
            return '%s ago' % fmt(t, n)
