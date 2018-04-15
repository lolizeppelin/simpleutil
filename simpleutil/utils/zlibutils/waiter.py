class Waiter(object):

    def __init__(self, wait, stop):
        self.funwait = wait
        self.funstop = stop
        self.stoped = False

    def wait(self):
        self.funwait()

    def stop(self):
        if not self.stoped:
            self.stoped = True
            self.funstop()

    def force(self):
        self.funstop()
