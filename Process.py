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
        self.com.numerotation()
        while self.nbProcess != Process.nbProcessCreated:
            pass

        loop = 0
        while self.alive:
            sleep(1)
            print(f"{self.name} Loop: {loop} with Lamport clock: {self.com.clock}")
            # self.broadcast(loop)
            # self.sendTo(loop, 1)
            # self.tokenTest(loop)
            # self.broadcastSync(loop)
            self.sendToSync(loop, 1)

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
                message = self.com.getFirstMessage()  # Utilisez get_message() à la place de getFirstMessage()
                print(message.obj if message else "No message found")
    
    
    def sendTo(self, loop, to):
        # Send to test
        
        if loop == 2 and self.numero == 0:
            self.com.sendTo("bonjour", to)

        if loop == 4 and self.numero == to:
            if len(self.com.mailbox) > 0:
                print(self.com.getFirstMessage())

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
            sleep(random.uniform(1.0, 2.5))
            
            print(f"{self.name} is leaving the critical section.")
            self.com.releaseSC()  # Libère la section critique et passe le jeton au suivant


    def broadcastSync(self, loop):
        if loop == 1 and self.numero == 0:
            self.com.broadcastSync("bonjour", 0)
            
        if loop == 3 and self.numero == 1:
            self.com.broadcastSync("bonsoir", 1)

        if loop == 4:
            if len(self.com.mailbox) > 0:
                message = self.com.getLastMessage()  # Utilisez get_message() à la place de getFirstMessage()
                print(message.obj if message else "No message found")

    def sendToSync(self, loop, to):
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

    def waitStopped(self):
        self.join()
    
    def nbProcess():
        return Process.nbProcessCreated