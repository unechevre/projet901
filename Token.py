from Message import Message
from enum import Enum

class TokenState(Enum):
    Null = 1
    Requested = 2
    SC = 3
    Release = 4


class Token(Message):
    def __init__(self):
        Message.__init__(self, "Token")
        self.from_process = None
        self.to_process = None
        self.nbSync = 0
