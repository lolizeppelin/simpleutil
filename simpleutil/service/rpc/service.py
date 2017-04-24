from goperation.service import ServiceBase
from simpleutil.utils.threadgroup import ThreadGroup


class RpcService(ServiceBase):
    """Service object for binaries running on hosts."""

    def __init__(self, name, threads=1000):
        ServiceBase.__init__(RpcService, name)
        self.tg = ThreadGroup(threads)

    def reset(self):
        """Reset a service in case it received a SIGHUP."""

    def start(self):
        """Start a service."""

    def stop(self, graceful=False):
        """Stop a service.

        :param graceful: indicates whether to wait for all threads to finish
               or terminate them instantly
        """
        self.tg.stop(graceful)

    def wait(self):
        """Wait for a service to shut down."""
        self.tg.wait()
