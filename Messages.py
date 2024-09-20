from enum import Enum

class Messages:
    """Base class for messages exchanged between processes."""

    def __init__(self, machin):
        """
        Initializes a new message.

        Args:
            machin (any): The content of the message.
        """
        self.machin = machin
        self.lamport_clock = 0

    def getMachin(self):
        """Returns the content of the message."""
        return self.machin

class BroadcastMessage(Messages):
    """Class representing a broadcast message to all processes."""

    def __init__(self, obj: any, from_process: str):
        """
        Initializes a new broadcast message.

        Args:
            obj (any): The object to be broadcasted.
            from_process (str): The name of the process sending the message.
        """
        Messages.__init__(self, obj)
        self.from_process = from_process
        self.obj = obj

class MessageTo(Messages):
    """Class representing a direct message to a specific process."""

    def __init__(self, obj: any, from_process: str, to_process: str):
        """
        Initializes a new direct message.

        Args:
            obj (any): The object to send.
            from_process (str): The name of the process sending the message.
            to_process (str): The name of the process receiving the message.
        """
        Messages.__init__(self, obj)
        self.from_process = from_process
        self.to_process = to_process
        self.obj = obj

class Token(Messages):
    """Class representing a token for critical section management."""

    def __init__(self):
        """Initializes a new token."""
        Messages.__init__(self, "token")
        self.from_process = None
        self.to_process = None
        self.nbSync = 0

class TokenState(Enum):
    """Enumeration representing the state of a token."""
    Null = 1
    Requested = 2
    SC = 3  # In Critical Section
    Release = 4

class BroadcastMessageSync(Messages):
    """Class representing a synchronous broadcast message to all processes."""

    def __init__(self, obj: any, from_process: str):
        """
        Initializes a new synchronous broadcast message.

        Args:
            obj (any): The object to be broadcasted.
            from_process (str): The name of the process sending the message.
        """
        Messages.__init__(self, obj)
        self.from_process = from_process
        self.obj = obj

class MessageToSync(Messages):
    """Class representing a synchronous direct message to a specific process."""

    def __init__(self, obj: any, from_process: str, to_process: str):
        """
        Initializes a new synchronous direct message.

        Args:
            obj (any): The object to send.
            from_process (str): The name of the process sending the message.
            to_process (str): The name of the process receiving the message.
        """
        Messages.__init__(self, obj)
        self.from_process = from_process
        self.to_process = to_process
        self.obj = obj

class MessageReceivedSync(Messages):
    """Class representing the confirmation of receipt of a synchronous message."""

    def __init__(self, src: int, dest: int, lamport_clock: int):
        """
        Initializes a new confirmation message.

        Args:
            src (int): The source process sending the confirmation.
            dest (int): The destination process receiving the confirmation.
            lamport_clock (int): The Lamport clock value at the time of confirmation.
        """
        Messages.__init__(self, "received")
        self.src = src
        self.dest = dest
        self.lamport_clock = lamport_clock

class Exist:
    """Class representing the existence confirmation message with process number."""

    def __init__(self, name: str, numero: int):
        """
        Initializes a new existence message.

        Args:
            name (str): The name of the process.
            numero (int): The number associated with the process.
        """
        self.src = name
        self.numero = numero
