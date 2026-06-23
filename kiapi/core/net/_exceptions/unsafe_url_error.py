class UnsafeURLError(ValueError):
    """A user-supplied URL was rejected before fetching (SSRF guard).

    Raised for non-http(s) schemes, unresolvable hosts, or hosts that resolve to
    a non-public address (loopback, private, link-local, etc.). Callers map this
    to a 400-class error.
    """
