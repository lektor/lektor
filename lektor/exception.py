class LektorException(Exception):
    def __init__(self, message=None):
        Exception.__init__(self)
        if isinstance(message, bytes):
            message = message.decode("utf-8", "replace")
        self.message = message

    def to_json(self):
        return {
            "type": self.__class__.__name__,
            "message": self.message,
        }

    def __str__(self):
        return str(self.message)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.message)
