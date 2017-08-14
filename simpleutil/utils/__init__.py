from eventlet import patcher
_threadlocal = patcher.original('threading').local()

def get_current():
    """Return this thread's current context

    If no context is set, returns None
    """
    return getattr(_threadlocal, 'context', None)
