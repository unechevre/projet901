from threading import Lock, Thread
from typing import Callable
from time import sleep
import random
#from geeteventbus.subscriber import subscriber
#from geeteventbus.eventbus import eventbus
#from geeteventbus.event import event

#from EventBus import EventBus
from Bidule import *
from Com import Com
from pyeventbus3.pyeventbus3 import *

def mod(x: int, y: int) -> int:
    return ((x % y) + y) % y


class Process(Thread):
    nbProcessCreated = 0

    def __init__(self, name: str, nbProcess: int):
        Thread.__init__(self)

        self.nbProcess = nbProcess
        self.myId = Process.nbProcessCreated
        Process.nbProcessCreated += 1
        self.name = name
        self.numero = -1

        PyBus.Instance().register(self, self)

        self.alive = True
        self.lamport_clock = 0
        self.token_state = TokenState.Null
        
        self.com = Com(0,self)
        
        self.nbSync = 0
        self.isSyncing = False
        self.start()

    def run(self):
        while self.nbProcess != Process.nbProcessCreated:
            pass

        loop = 0
        while self.alive:

            sleep(1)
            print(f"{self.name} Loop: {loop} with Lamport clock: {self.com.clock}")

            self.broadcast2(loop)

            loop += 1
        
        print(self.getName() + " stopped")
        
    def broadcast2(self, loop):
        # Broadcast test
        if loop == 2 and self.numero == 0:
            self.com.broadcast("bonjour")

        if loop == 4:
            if len(self.com.mailbox) > 0:
                print(self.com.getFirstMessage().payload)
    
    def stop(self):
        self.alive = False
        self.com.stop()
        self.join()

    def sendMessage(self, message: Bidule):
        self.lamport_clock += 1
        message.lamport_clock = self.lamport_clock
        print(f"{self.name} sends message: {message.getMachin()} with Lamport clock: {self.lamport_clock}")
        PyBus.Instance().post(message)

    def receiveMessage(self, message: Bidule):
        self.lamport_clock = max(self.lamport_clock, message.lamport_clock) + 1
        print(f"{self.name} received message: {message.getMachin()} with updated Lamport clock: {self.lamport_clock}")

    def sendAll(self, obj: any):
        self.sendMessage(Bidule(obj))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Bidule)
    def process(self, event: Bidule):
        print(f"{self.name} processes event: {event}")
        self.receiveMessage(event)

    def broadcast(self, obj: any):
        print(f"{self.name} broadcasts: {obj}")
        self.sendMessage(BroadcastMessage(obj, self.name))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def onBroadcast(self, event: BroadcastMessage):
        print(f"{self.name} received broadcast from {event.from_process}: {event.obj}")
        if event.from_process != self.name:
            self.receiveMessage(event)

    def sendTo(self, dest: str, obj: any):
        print(f"{self.name} sends to {dest}: {obj}")
        self.sendMessage(MessageTo(obj, self.name, dest))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def onReceive(self, event: MessageTo):
        print(f"{self.name} received message to {event.to_process}: {event}")
        if event.to_process == self.name:
            self.receiveMessage(event)

    def releaseToken(self):
        if self.token_state == TokenState.SC:
            self.token_state = TokenState.Release
        token = Token()
        token.from_process = self.myId
        token.to_process = mod(self.myId + 1, Process.nbProcessCreated)
        token.nbSync = self.nbSync
        print(f"{self.name} releases token to {token.to_process} with Lamport clock: {self.lamport_clock}")
        self.sendMessage(token)
        self.token_state = TokenState.Null

    def requestToken(self):
        self.token_state = TokenState.Requested
        print(f"{self.name} requests token")
        while self.token_state == TokenState.Requested:
            if not self.alive:
                return
        self.token_state = TokenState.SC
        print(f"{self.name} acquired token")

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Token)
    def onToken(self, event: Token):
        print(f"{self.name} received token from_process : {event.from_process} and to_process : {event.to_process} ")
        if event.to_process == self.myId:
            self.receiveMessage(event)
            if not self.alive:
                return
            if self.token_state == TokenState.Requested:
                self.token_state = TokenState.SC
                return
            if self.isSyncing:
                self.isSyncing = False
                self.nbSync = mod(event.nbSync + 1, Process.nbProcessCreated)
                if self.nbSync == 0:
                    self.sendMessage(SyncingMessage(self.myId))
            self.releaseToken()

    def doCriticalAction(self, funcToCall: Callable, args: list):
        self.requestToken()
        if self.alive:
            print(f"{self.name} performing critical action")
            funcToCall(*args)
            self.releaseToken()

    def criticalActionWarning(self, msg: str):
        print("[Critical Action], Token used by", self.name, " ---Bidule :", msg)

    def synchronize(self):
        self.isSyncing = True
        print(f"{self.name} starts synchronizing")
        while self.isSyncing:
            if not self.alive:
                return
        while self.nbSync != 0:
            if not self.alive:
                return
        print(f"{self.name} finished synchronizing")

    @subscribe(threadMode=Mode.PARALLEL, onEvent=SyncingMessage)
    def onSyncing(self, event: SyncingMessage):
        print(f"{self.name} received syncing message: {event}")
        if event.from_process != self.myId:
            self.receiveMessage(event)
            self.nbSync = 0

    def stop(self):
        self.alive = False

    def waitStopped(self):
        self.join()