class Waiter(object):

    def __init__(self, wait, stop):
        self.funwait = wait
        self.funstop = stop

    def wait(self):
        self.funwait()

    def stop(self):
        self.funstop()
