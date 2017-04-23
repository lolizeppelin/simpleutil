import threading

_request_store = threading.local()


def get_current():
    """Return this thread's current context

    If no context is set, returns None
    """
    return getattr(_request_store, 'context', None)