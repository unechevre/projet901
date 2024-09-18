import random
from time import sleep
from typing import Callable

from pyeventbus3.pyeventbus3 import *

from Message import Message, MessageTo
from Token import Token, TokenState
from SyncingMessage import SyncingMessage
from BroadcastMessage import BroadcastMessage

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

        PyBus.Instance().register(self, self)

        self.alive = True
        self.horloge = 0
        self.token_state = TokenState.Null
        self.nbSync = 0
        self.isSyncing = False
        self.start()

    def run(self):
        while self.nbProcess != Process.nbProcessCreated:
            pass
        if self.myId == 0:
            self.releaseToken()
        self.synchronize()
        loop = 0
        while self.alive:
            sleep(1)
            print(f"{self.name} Loop: {loop} with Lamport clock: {self.horloge}")

            # if self.name == "P1":
            #     self.sendTo("P2", "ga")
            #     self.doCriticalAction(self.criticalActionWarning, ["ploi"])
            # if self.name == "P2":
            self.broadcast("P2 broadcast")
            # if self.name == "P3":
            #     receiver = str(random.randint(0, self.nbProcess - 1))
            #     self.sendTo("P" + receiver, "j'envoi sms" + receiver)
            loop += 1
        sleep(1)

    def stop(self):
        self.alive = False
        self.join()

    def sendMessage(self, message: Message):
        self.horloge += 1
        message.horloge = self.horloge
        print(f"{self.name} sends message: {message} with Lamport clock: {self.horloge}")
        PyBus.Instance().post(message)

    def receiveMessage(self, message: Message):
        self.horloge = max(self.horloge, message.horloge) + 1
        print(f"{self.name} received message: {message} with updated Lamport clock: {self.horloge}")

    def sendAll(self, obj: any):
        self.sendMessage(Message(obj))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Message)
    def process(self, event: Message):
        print(f"{self.name} processes event: {event}")
        self.receiveMessage(event)

    def broadcast(self, obj: any):
        print(f"{self.name} broadcasts: {obj}")
        self.sendMessage(BroadcastMessage(obj, self.name))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def onBroadcast(self, event: BroadcastMessage):
        print(f"{self.name} received broadcast from {event.from_process}: {event}")
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
        print(f"{self.name} releases token to {token.to_process} with Lamport clock: {self.horloge}")
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
        print(f"{self.name} received token: {event}")
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
        print("[Critical Action], Token used by", self.name, " ---Message :", msg)

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