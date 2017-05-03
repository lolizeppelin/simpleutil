class InvalidInput(Exception):
    message = "Invalid input received: "
    def __init__(self, msg):
        self.message = InvalidInput.message + msg

class InvalidArgument(InvalidInput):
    message = "Invalid argument: "
    def __init__(self, msg):
        self.message = InvalidArgument.message + msg