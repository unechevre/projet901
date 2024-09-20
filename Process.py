from threading import Lock, Thread
from typing import Callable
from time import sleep
import random
#from geeteventbus.subscriber import subscriber
#from geeteventbus.eventbus import eventbus
#from geeteventbus.event import event

#from EventBus import EventBus
from Messages import *
from Com import Com
from pyeventbus3.pyeventbus3 import *

def mod(x: int, y: int) -> int:
    """
    Calculate the modulo operation with a correction for negative values.

    Args:
        x (int): The dividend.
        y (int): The divisor.

    Returns:
        int: The positive remainder of x divided by y.
    """
    return ((x % y) + y) % y


class Process(Thread):
    nbProcessCreated = 0

    def __init__(self, name: str, nbProcess: int):
        """
        Initialize a new process thread.

        Args:
            name (str): The name of the process.
            nbProcess (int): The total number of processes in the system.
        """
        Thread.__init__(self)
        self.nbProcess = nbProcess
        self.myId = Process.nbProcessCreated
        self.numero = Process.nbProcessCreated

        Process.nbProcessCreated += 1
        self.name = name

        PyBus.Instance().register(self, self)

        self.alive = True
        self.lamport_clock = 0
        self.token_state = TokenState.Null

        self.com = Com(0, self)
        self.in_critical_section = False
        self.nbSync = 0
        self.isSyncing = False
        self.start()

    def run(self):
        """
        Main loop of the process that runs while the process is alive.
        Handles communication and synchronization tasks.
        """
        while self.nbProcess != Process.nbProcessCreated:
            pass

        loop = 0
        while self.alive:
            sleep(1)
            print(f"{self.name} Loop: {loop} with Lamport clock: {self.com.clock}")
            self.sendToSync(loop, 1)
            loop += 1

        print(self.getName() + " stopped")

    def broadcast(self, loop):
        """
        Test method for broadcasting messages based on loop and process number.

        Args:
            loop (int): The current loop iteration.
        """
        if loop == 2 and self.numero == 0:
            self.com.broadcast("bonjour")

        if loop == 3 and self.numero == 1:
            self.com.broadcast("bonsoir")

        if loop == 4:
            if len(self.com.mailbox) > 0:
                message = self.com.getFirstMessage()
                print(message.obj if message else "No message found")

    def sendTo(self, loop, to):
        """
        Test method for sending messages to a specific process.

        Args:
            loop (int): The current loop iteration.
            to (int): The target process number to send the message to.
        """
        if loop == 2 and self.numero == 0:
            self.com.sendTo("bonjour", to)

        if loop == 4 and self.numero == to:
            if len(self.com.mailbox) > 0:
                print(self.com.getFirstMessage())

    def tokenTest(self, loop):
        """
        Test method for synchronizing and managing tokens for critical section access.

        Args:
            loop (int): The current loop iteration.
        """
        if loop == 2:
            print(f"{self.name} is about to synchronize.")
            self.com.synchronize()
            print(f"{self.name} passed synchronization.")

        elif loop == 4:
            print(f"{self.name} is requesting access to critical section.")
            self.com.requestSC()
            print(f"{self.name} has entered the critical section.")

            sleep(random.uniform(1.0, 2.5))

            print(f"{self.name} is leaving the critical section.")
            self.com.releaseSC()

    def broadcastSync(self, loop):
        """
        Test method for broadcasting synchronized messages.

        Args:
            loop (int): The current loop iteration.
        """
        if loop == 1 and self.numero == 0:
            self.com.broadcastSync("bonjour", 0)

        if loop == 3 and self.numero == 1:
            self.com.broadcastSync("bonsoir", 1)

        if loop == 4:
            if len(self.com.mailbox) > 0:
                message = self.com.getLastMessage()
                print(message.obj if message else "No message found")

    def sendToSync(self, loop, to):
        """
        Test method for sending synchronized messages to a specific process.

        Args:
            loop (int): The current loop iteration.
            to (int): The target process number to send the synchronized message to.
        """
        if loop == 0 and self.numero == 1:
            self.com.receiveFromSync(0)
        if loop == 2 and self.numero == 0:
            self.com.sendToSync("bonjour", to)
        if loop == 1 and self.numero == 1:
            self.com.receiveFromSync(2)
        if loop == 3 and self.numero == 2:
            self.com.sendToSync("bonjour", to)

        if loop == 4 and self.numero == to:
            if len(self.com.mailbox) > 0:
                print(self.com.getFirstMessage())

    def stop(self):
        """
        Stop the process and terminate its thread.
        """
        self.alive = False
        self.com.stop()
        self.join()

    def requestSC(self):
        """
        Request access to the critical section.
        """
        print(f"{self.name} is requesting to enter critical section")
        if self.com.request_token():
            self.enter_critical_section()

    def enter_critical_section(self):
        """
        Enter the critical section.
        """
        self.token_state = TokenState.SC
        self.in_critical_section = True
        print(f"{self.name} has entered the critical section")

    def releaseSC(self):
        """
        Release the critical section and pass the token to the next process.
        """
        print(f"{self.name} is releasing the critical section")
        self.token_state = TokenState.Release
        self.in_critical_section = False
        self.com.release_token()

    def waitStopped(self):
        """
        Wait for the process to stop completely.
        """
        self.join()

    def nbProcess():
        """
        Get the number of processes created.

        Returns:
            int: The number of processes created.
        """
        return Process.nbProcessCreated
