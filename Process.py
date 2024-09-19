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
        self.numero = Process.nbProcessCreated

        Process.nbProcessCreated += 1
        self.name = name

        PyBus.Instance().register(self, self)

        self.alive = True
        self.lamport_clock = 0
        self.token_state = TokenState.Null
        
        self.com = Com(0,self)
        self.in_critical_section = False
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
        
            if loop == 2:
                if self.numero == 0:
                    print(f"{self.name} is about to perform sendToSync to P1.")
                    self.com.sendToSync("Synchronous message to P1", dest=1)
                    print(f"{self.name} has completed sendToSync.")

                elif self.numero == 1:
                    print(f"{self.name} is waiting to receive sync message from P0.")
                    self.com.receiveFromSync(from_process=0)

            loop += 1

        print(self.getName() + " stopped")
        
    # Broadcast test
    def broadcast(self, loop):
        
        if loop == 2 and self.numero == 0:
            self.com.broadcast("bonjour")
            
        if loop == 3 and self.numero == 1:
            self.com.broadcast("bonsoir")

        if loop == 4:
            if len(self.com.mailbox) > 0:
                message = self.com.get_FirstMessage()  # Utilisez get_message() à la place de getFirstMessage()
                print(message.obj if message else "No message found")
    
    
    def sendTo(self, loop, to):
        # Send to test
        
        if loop == 2 and self.numero == 0:
            self.com.sendTo("bonjour", to)

        if loop == 4 and self.numero == to:
            if len(self.com.mailbox) > 0:
                print(self.com.get_FirstMessage())

    def tokenTest(self, loop):
        # Token to test
         # Test de synchronisation et gestion des jetons pour la section critique.
        if loop == 2:
            print(f"{self.name} is about to synchronize.")
            self.com.synchronize()  # Appel à la synchronisation
            print(f"{self.name} passed synchronization.") 
            
        elif loop == 4:
            print(f"{self.name} is requesting access to critical section.")
            self.com.requestSC()  # Demande d'accès à la section critique
            print(f"{self.name} has entered the critical section.")
            
            # Simule l'exécution dans la section critique pendant un temps aléatoire
            sleep(random.uniform(2.0, 2.5))
            
            print(f"{self.name} is leaving the critical section.")
            self.com.releaseSC()  # Libère la section critique et passe le jeton au suivant


    def stop(self):
        self.alive = False
        self.com.stop()  
        self.join() 
    
    
    def requestSC(self):
        """Demande d'entrée en section critique"""
        print(f"{self.name} is requesting to enter critical section")
        if self.com.request_token():
            self.enter_critical_section()

    def enter_critical_section(self):
        """Entrée en section critique"""
        self.token_state = TokenState.SC
        self.in_critical_section = True
        print(f"{self.name} has entered the critical section")

    def releaseSC(self):
        """Libération de la section critique"""
        print(f"{self.name} is releasing the critical section")
        self.token_state = TokenState.Release
        self.in_critical_section = False
        self.com.release_token()

    
    # def sendMessage(self, message: Bidule):
    #     self.lamport_clock += 1
    #     message.lamport_clock = self.lamport_clock
    #     print(f"{self.name} sends message: {message.getMachin()} with Lamport clock: {self.lamport_clock}")
    #     PyBus.Instance().post(message)

    # def receiveMessage(self, message: Bidule):
    #     self.lamport_clock = max(self.lamport_clock, message.lamport_clock) + 1
    #     print(f"{self.name} received message: {message.getMachin()} with updated Lamport clock: {self.lamport_clock}")

    # def sendAll(self, obj: any):
    #     self.sendMessage(Bidule(obj))

    # @subscribe(threadMode=Mode.PARALLEL, onEvent=Bidule)
    # def process(self, event: Bidule):
    #     print(f"{self.name} processes event: {event}")
    #     self.receiveMessage(event)

    # def broadcast(self, obj: any):
    #     print(f"{self.name} broadcasts: {obj}")
    #     self.sendMessage(BroadcastMessage(obj, self.name))


    # def sendTo(self, dest: str, obj: any):
    #     print(f"{self.name} sends to {dest}: {obj}")
    #     self.sendMessage(MessageTo(obj, self.name, dest))

    # @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    # def onReceive(self, event: MessageTo):
    #     print(f"{self.name} received message to {event.to_process}: {event}")
    #     if event.to_process == self.name:
    #         self.receiveMessage(event)

    # def releaseToken(self):
    #     if self.token_state == TokenState.SC:
    #         self.token_state = TokenState.Release
    #     token = Token()
    #     token.from_process = self.myId
    #     token.to_process = mod(self.myId + 1, Process.nbProcessCreated)
    #     token.nbSync = self.nbSync
    #     print(f"{self.name} releases token to {token.to_process} with Lamport clock: {self.lamport_clock}")
    #     self.sendMessage(token)
    #     self.token_state = TokenState.Null

    # def requestToken(self):
    #     self.token_state = TokenState.Requested
    #     print(f"{self.name} requests token")
    #     while self.token_state == TokenState.Requested:
    #         if not self.alive:
    #             return
    #     self.token_state = TokenState.SC
    #     print(f"{self.name} acquired token")

    # @subscribe(threadMode=Mode.PARALLEL, onEvent=Token)
    # def onToken(self, event: Token):
    #     print(f"{self.name} received token from_process : {event.from_process} and to_process : {event.to_process} ")
    #     if event.to_process == self.myId:
    #         self.receiveMessage(event)
    #         if not self.alive:
    #             return
    #         if self.token_state == TokenState.Requested:
    #             self.token_state = TokenState.SC
    #             return
    #         if self.isSyncing:
    #             self.isSyncing = False
    #             self.nbSync = mod(event.nbSync + 1, Process.nbProcessCreated)
    #             if self.nbSync == 0:
    #                 self.sendMessage(SyncingMessage(self.myId))
    #         self.releaseToken()

    # def doCriticalAction(self, funcToCall: Callable, args: list):
    #     self.requestToken()
    #     if self.alive:
    #         print(f"{self.name} performing critical action")
    #         funcToCall(*args)
    #         self.releaseToken()

    # def criticalActionWarning(self, msg: str):
    #     print("[Critical Action], Token used by", self.name, " ---Bidule :", msg)

    # def synchronize(self):
    #     self.isSyncing = True
    #     print(f"{self.name} starts synchronizing")
    #     while self.isSyncing:
    #         if not self.alive:
    #             return
    #     while self.nbSync != 0:
    #         if not self.alive:
    #             return
    #     print(f"{self.name} finished synchronizing")

    # @subscribe(threadMode=Mode.PARALLEL, onEvent=SyncingMessage)
    # def onSyncing(self, event: SyncingMessage):
    #     print(f"{self.name} received syncing message: {event}")
    #     if event.from_process != self.myId:
    #         self.receiveMessage(event)
    #         self.nbSync = 0


    def waitStopped(self):
        self.join()
    
    def nbProcess():
        return Process.nbProcessCreated