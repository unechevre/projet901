from threading import Lock, Semaphore, Thread
from time import sleep
from Bidule import *
from pyeventbus3.pyeventbus3 import *


class Com(Thread):
    def __init__(self, clock, process) -> None:
        Thread.__init__(self)
        self.setName(f"Com-{process.numero}")
        PyBus.Instance().register(self, self)

        self.owner = process.numero
        self.clock = clock
        self.sem = threading.Semaphore()  # Protection de l'horloge avec un sémaphore
        self.mailbox = []  # Boîte aux lettres
        self.process = process  # Référence vers le processus associé
        self.alive = True
        self.start()

    def stop(self):
        self.alive = False
        self.join()

    def inc_clock(self):
        """Incrémente l'horloge de Lamport"""
        self.sem.acquire()
        self.clock += 1
        self.sem.release()
        return self.clock

    def sendTo(self, obj: any, dest: str):
        """Envoie l'objet à un processus spécifique"""
        self.inc_clock()
        print(f"[Com-{self.process.name}] sends to {dest}: {obj} with Lamport clock: {self.clock}")
        PyBus.Instance().post(MessageTo(obj, self.process.name, dest))

    def broadcast(self, obj: any):
        """Diffusion de l'objet à tous les processus"""
        self.inc_clock()
        print(f"[Com-{self.process.name}] broadcasts: {obj} with Lamport clock: {self.clock}")
        PyBus.Instance().post(BroadcastMessage(obj, self.process.name))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Bidule)
    def onReceive(self, event: Bidule):
        """Traitement de la réception des messages"""
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
        """Récupération du message depuis la boîte aux lettres"""
        if self.mailbox:
            return self.mailbox.pop(0)
        return None
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def onBroadcast(self, event: BroadcastMessage):
         if event.from_process != self.process.name:
                self.mailbox.append(event)
                self.inc_clock()
                print(f"[Com-{self.process.name}] received broadcast from {event.from_process}: {event.obj}")

