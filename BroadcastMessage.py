from Message import Message

class BroadcastMessage(Message):
    def __init__(self, obj: any, from_process: str):
        Message.__init__(self, obj)
        self.from_process = from_process