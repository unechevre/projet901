from threading import Event, Lock, Semaphore, Thread, Barrier
from time import sleep
from Messages import *
from pyeventbus3.pyeventbus3 import *
import random

class Token:
    """Class representing a token for critical section management."""

    def __init__(self, from_process=None, to_process=None):
        """
        Initializes a new token.

        Args:
            from_process (int, optional): The process sending the token. Defaults to None.
            to_process (int, optional): The process receiving the token. Defaults to None.
        """
        self.from_process = from_process
        self.to_process = to_process

class Com(Thread):
    """Class managing communication between processes."""

    sync_barrier = None
    sync_lock = Lock()
    sync_counter = 0
    confirmations_received = 0
    confirmations_lock = Lock()
    total_processes = None
    total_processes2 = 0

    def __init__(self, clock, process) -> None:
        """
        Initializes a new communicator for a process.

        Args:
            clock (int): Initial Lamport clock value.
            process (Process): Reference to the associated process.
        """
        Thread.__init__(self)
        self.setName(f"Com-{process.numero}")
        PyBus.Instance().register(self, self)

        with Com.sync_lock:
            if Com.sync_barrier is None:
                Com.sync_barrier = Barrier(process.nbProcessCreated)
            self.total_processes2 = Com.sync_barrier.parties

        self.owner = process.numero
        self.clock = clock
        self.sem = Semaphore()
        self.mailbox = []
        self.process = process
        self.alive = True
        self.token_holder = False
        self.token = None
        self.lock = Lock()
        self.sync_event = Event()
        self.received_sync = False
        self.received_from_all = False
        self.process_ids = {}
        self.start()

        with Com.sync_lock:
            if Com.sync_barrier is None:
                Com.sync_barrier = Barrier(process.nbProcessCreated)

        if self.process.numero == 1:
            self.token_holder = True
            self.token = Token(from_process=None, to_process=self.process.numero)

        self.token_thread = Thread(target=self.token_manager)

        if Com.total_processes is None:
            Com.total_processes = process.nbProcess

        self.token_thread.start()

    def synchronize(self):
        """Synchronizes the process with all other processes."""
        print(f"[Com-{self.process.name}] Synchronizing...")
        with Com.sync_lock:
            Com.sync_counter += 1

        Com.sync_barrier.wait()
        print(f"[Com-{self.process.name}] Synchronization complete.")

    def stop(self):
        """Stops the communicator and its associated thread."""
        self.alive = False
        self.token_thread.join()
        self.join()

    def inc_clock(self):
        """Increments the Lamport clock and returns the updated value."""
        self.sem.acquire()
        self.clock += 1
        self.sem.release()
        return self.clock

    def sendTo(self, obj: any, dest: int):
        """
        Sends an object to a specific process.

        Args:
            obj (any): The object to send.
            dest (int): The number of the destination process.
        """
        self.inc_clock()
        print(f"[Com-{self.process.name}] sends to {dest}: {obj} with Lamport clock: {self.clock}")
        PyBus.Instance().post(MessageTo(obj, self.process.name, f"P{dest}"))

    def broadcast(self, obj: any):
        """
        Broadcasts an object to all processes.

        Args:
            obj (any): The object to broadcast.
        """
        self.inc_clock()
        print(f"[Com-{self.process.name}] broadcasts: {obj} with Lamport clock: {self.clock}")
        PyBus.Instance().post(BroadcastMessage(obj, self.process.name))

    def requestSC(self):
        """Requests access to the critical section and waits until the token is obtained."""
        print(f"[Com-{self.process.name}] Requesting access to critical section.")
        with self.lock:
            while not self.token_holder:
                sleep(0.1)

    def releaseSC(self):
        """Releases the critical section and passes the token to the next process."""
        print(f"[Com-{self.process.name}] Releasing critical section.")
        with self.lock:
            next_process = (self.process.numero + 1) % self.process.nbProcessCreated
            self.token.to_process = next_process
            self.token_holder = False
            self.sendToken(self.token)

    def sendToken(self, token):
        """
        Sends the token to the next process.

        Args:
            token (Token): The token to send.
        """
        print(f"[Com-{self.process.name}] Passing the token to process {token.to_process}.")
        PyBus.Instance().post(token)

    def token_manager(self):
        """Manages the circulation of the token among processes."""
        while self.alive:
            sleep(1)

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Token)
    def onToken(self, event: Token):
        """
        Handles the reception of a token.

        Args:
            event (Token): The received token.
        """
        if event.to_process == self.process.numero:
            print(f"[Com-{self.process.name}] Received the token.")
            self.token_holder = True
            self.token = event

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Messages)
    def onReceive(self, event: Messages):
        """
        Handles the reception of user messages.

        Args:
            event (Messages): The received message.
        """
        if isinstance(event, MessageTo):
            if event.to_process == self.process.name:
                self.mailbox.append(event)
                self.inc_clock()
                print(f"[Com-{self.process.name}] received direct message from {event.from_process}: {event.obj}")
        elif isinstance(event, BroadcastMessage):
            if event.from_process != self.process.name:
                self.mailbox.append(event)
                self.inc_clock()
                print(f"[Com-{self.process.name}] received broadcast from {event.from_process}: {event.obj}")

    def getFirstMessage(self):
        """Retrieves the first message from the mailbox, if available."""
        if self.mailbox:
            return self.mailbox.pop(0)
        return None

    def getLastMessage(self):
        """Retrieves the last message from the mailbox, if available."""
        if self.mailbox:
            return self.mailbox.pop(-1)
        return None

    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def onBroadcastReceive(self, event: BroadcastMessage):
        """
        Handles the reception of broadcast messages.

        Args:
            event (BroadcastMessage): The received broadcast message.
        """
        if event.from_process != self.process.name:
            self.mailbox.append(event)
            self.inc_clock()
            print(f"[Com-{self.process.name}] received broadcast from {event.from_process}: {event.obj}")

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def onMessageTo(self, event: MessageTo):
        """
        Handles the reception of direct messages.

        Args:
            event (MessageTo): The received direct message.
        """
        if event.to_process == self.process.name:
            self.mailbox.append(event.obj)
            self.inc_clock()
            print(f"[Com-{self.process.name}] received direct message from {event.from_process}: {event.obj}")

    def broadcastSync(self, obj: any, from_process: int):
        """
        Synchronously broadcasts a message to all processes.

        Args:
            obj (any): The object to broadcast.
            from_process (int): The number of the sending process.
        """
        if self.process.numero == from_process:
            self.inc_clock()
            print(f"[Com-{self.process.name}] broadcastsSync: {obj} with Lamport clock: {self.clock}")
            PyBus.Instance().post(BroadcastMessageSync(obj, self.process.name))

            while Com.confirmations_received < Com.total_processes - 1:
                sleep(0.1)
            print(f"[Com-{self.process.name}] All processes received the message.")
            with Com.confirmations_lock:
                Com.confirmations_received = 0
            self.received_from_all = False
        else:
            print(f"[Com-{self.process.name}] Waiting to receive broadcastSync from {from_process}.")
            while not self.received_sync:
                sleep(0.1)
            print(f"[Com-{self.process.name}] Received broadcastSync from {from_process}.")
            self.received_sync = False

    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessageSync)
    def onBroadcastSync(self, event: BroadcastMessageSync):
        """
        Handles the reception of synchronous broadcast messages.

        Args:
            event (BroadcastMessageSync): The received synchronous broadcast message.
        """
        if event.from_process != self.process.name:
            self.mailbox.append(event)
            self.inc_clock()
            print(f"[Com-{self.process.name}] received sync broadcast from {event.from_process}: {event.obj}")
            self.received_sync = True
            PyBus.Instance().post(MessageReceivedSync(event.from_process, self.process.numero, self.clock))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageReceivedSync)
    def onMessageReceivedSync(self, event: MessageReceivedSync):
        """
        Handles confirmations of received synchronous messages.

        Args:
            event (MessageReceivedSync): The received confirmation.
        """
        if event.dest == self.process.numero:
            print(f"[Com-{self.process.name}] Confirmation received from process {event.src}.")
            with Com.confirmations_lock:
                Com.confirmations_received += 1
            self.received_from_all = True

    def sendToSync(self, obj: any, dest: int):
        """
        Sends a message synchronously to a specific process.

        Args:
            obj (any): The object to send.
            dest (int): The number of the destination process.
        """
        self.inc_clock()
        print(f"[Com-{self.process.name}] sendToSync to {dest}: {obj} with Lamport clock: {self.clock}")
        PyBus.Instance().post(MessageToSync(obj, self.process.name, f"P{dest}"))

        while not self.received_from_all:
            sleep(0.1)

        print(f"[Com-{self.process.name}] Message synchronously received by P{dest}.")
        self.received_from_all = False

    def receiveFromSync(self, from_process: int):
        """
        Waits to receive a synchronous message from a specific process.

        Args:
            from_process (int): The number of the sending process.
        """
        print(f"[Com-{self.process.name}] Waiting to receive sync message from {from_process}.")
        while not self.received_sync:
            sleep(0.1)
        print(f"[Com-{self.process.name}] Received sync message from {from_process}.")
        self.received_sync = False

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageToSync)
    def onMessageToSync(self, event: MessageToSync):
        """
        Handles the reception of synchronous direct messages.

        Args:
            event (MessageToSync): The received synchronous direct message.
        """
        if event.to_process == self.process.name:
            self.mailbox.append(event.obj)
            self.inc_clock()
            print(f"[Com-{self.process.name}] received direct message from {event.from_process}: {event.obj}")
            PyBus.Instance().post(MessageReceivedSync(src=self.process.numero, dest=int(event.from_process[-1]), lamport_clock=self.clock))
            self.received_sync = True

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Exist)
    def onExist(self, event: Exist):
        """
        Receives an existing number and checks for conflicts.

        Args:
            event (Exist): The event containing the process number.
        """
        self.total_processes2 += 1
        with Com.sync_lock:
            print(f"[Com-{self.process.name}] received Exist event from {event.src}, process number: {event.numero}")
            self.process_ids[event.src] = event.numero

        if event.numero == self.process.numero and event.src != self.process.name:
            print(f"[Com-{self.process.name}] Conflict detected with {event.src}. Regenerating a new number.")
            self.regenerate_number()

    def numerotation(self):
        """Starts the process numbering procedure."""
        sleep(2)
        if self.process.name == "P0":
            self.process.numero = 0
            self.process.myId = 0
            print(f"{self.process.name} is the leader with number {self.process.numero}.")
            PyBus.Instance().post(Exist(self.process.name, self.process.numero))
        else:
            self.regenerate_number()

    def regenerate_number(self):
        """Generates a new random number and broadcasts it to other processes."""
        self.process.numero = random.randint(1, (self.total_processes2 * 1000))
        self.process.myId = self.process.numero
        print(f"{self.process.name} has generated a new number: {self.process.numero}")
        PyBus.Instance().post(Exist(self.process.name, self.process.numero))

    def check_for_conflicts(self):
        """Checks for conflicts after receiving numbers from other processes."""
        for process_name, numero in self.process_ids.items():
            if numero == self.process.numero and process_name != self.process.name:
                return True
        return False
