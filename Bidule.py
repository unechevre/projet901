from enum import Enum


class Bidule:
    
    def __init__(self, machin):
        self.machin = machin
        self.lamport_clock = 0

    def getMachin(self):
        return self.machin
    
    
class BroadcastMessage(Bidule):
    def __init__(self, obj: any, from_process: str):
        Bidule.__init__(self, obj)
        self.from_process = from_process
        self.obj = obj


class MessageTo(Bidule):
    def __init__(self, obj: any, from_process: str, to_process: str):
        Bidule.__init__(self, obj)
        self.from_process = from_process
        self.to_process = to_process
        self.obj = obj


class Token(Bidule):
    def __init__(self):
        Bidule.__init__(self, "token")
        self.from_process = None
        self.to_process = None
        self.nbSync = 0

class TokenState(Enum):
    Null = 1
    Requested = 2
    SC = 3
    Release = 4


class SyncingMessage(Bidule):
    def __init__(self, from_process: int):
        Bidule.__init__(self, "SYNCING")
        self.from_process = from_process
        
class BroadcastMessageSync(Bidule):
    """Message pour la diffusion synchrone à tous les processus."""
    def __init__(self, obj: any, from_process: str):
        Bidule.__init__(self, obj)
        self.from_process = from_process
        self.obj = obj


class MessageReceivedSync(Bidule):
    """Confirmation de réception d'un message synchrone."""
    def __init__(self, src: int, dest: int, lamport_clock: int):
        Bidule.__init__(self, "received")
        self.src = src  # Ajoute cet attribut pour indiquer l'émetteur de la confirmation
        self.dest = dest
        self.lamport_clock = lamport_clock
