from Message import Message
class SyncingMessage(Message):
    def __init__(self, from_process: int):
        Message.__init__(self, "Syncing")
        self.from_process = from_process