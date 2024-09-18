
class Message():
    def __init__(self, obj: any):
        self.object = obj
        self.horloge = None

    def getObject(self: any):
        return self.object



class MessageTo():
    def __init__(self, obj: any, from_process: str, to_process: str):
        Message.__init__(self, obj)
        self.from_process = from_process
        self.to_process = to_process
