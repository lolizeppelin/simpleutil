class InvalidInput(Exception):
    message = "Received inpput is Invalid: "
    def __init__(self, msg):
        self.message = InvalidInput.message + msg
        super(InvalidInput, self).__init__(self.message)

class InvalidArgument(Exception):
    message = "Argument is Invalid: "
    def __init__(self, msg):
        self.message = InvalidArgument.message + msg
        super(InvalidArgument, self).__init__(self.message)