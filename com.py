from threading import Lock, Semaphore, Thread, Barrier ,Event
from time import sleep
from Bidule import *
from pyeventbus3.pyeventbus3 import *


class Token:
    """Classe représentant un jeton pour la gestion de la section critique."""
    def __init__(self, from_process=None, to_process=None):
        self.from_process = from_process
        self.to_process = to_process


class Com(Thread):
    # Ajout des compteurs et événements pour la synchronisation
    confirmations_received = 0
    confirmations_lock = Lock()
    total_processes = None
    sync_event = Event()  # Utilisé pour synchroniser les envois et réceptions synchrones

    def __init__(self, clock, process) -> None:
        Thread.__init__(self)
        self.setName(f"Com-{process.numero}")
        PyBus.Instance().register(self, self)

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

        if Com.total_processes is None:
            Com.total_processes = process.nbProcess
        self.start()

    def sendToSync(self, obj: any, dest: int):
        """Envoie un message de manière synchrone à un processus spécifique."""
        self.inc_clock()
        print(f"[Com-{self.process.name}] sendToSync to {dest}: {obj} with Lamport clock: {self.clock}")
        PyBus.Instance().post(MessageTo(obj, self.process.name, f"P{dest}"))  # Envoie le message

        # Attendre la confirmation de réception du destinataire
        while not self.received_from_all:
            sleep(0.1)
        print(f"[Com-{self.process.name}] Message synchronously received by {dest}.")
        self.received_from_all = False

    def receiveFromSync(self, from_process: int):
        """Attend de recevoir un message synchrone d'un processus spécifique."""
        print(f"[Com-{self.process.name}] Waiting to receive sync message from {from_process}.")
        while not self.received_sync:
            sleep(0.1)
        print(f"[Com-{self.process.name}] Received sync message from {from_process}.")
        self.received_sync = False

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def onReceive(self, event: MessageTo):
        """Gère les messages reçus et les confirmations de réception."""
        if event.to_process == self.process.name:
            self.mailbox.append(event)
            self.inc_clock()
            print(f"[Com-{self.process.name}] received direct message from {event.from_process}: {event.obj}")

            # Envoyer une confirmation de réception synchrone
            PyBus.Instance().post(MessageReceivedSync(src=self.process.numero, dest=int(event.from_process[-1]), lamport_clock=self.clock))
            self.received_sync = True

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageReceivedSync)
    def onMessageReceivedSync(self, event: MessageReceivedSync):
        """Gère les confirmations de réception des messages synchrones."""
        if event.dest == self.process.numero:
            print(f"[Com-{self.process.name}] Confirmation received from process {event.src}.")
            with Com.confirmations_lock:
                Com.confirmations_received += 1
            self.received_from_all = True

    def synchronize(self):
        """Synchronise le processus avec tous les autres, bloquant jusqu'à ce que tous les processus aient appelé cette méthode."""
        print(f"[Com-{self.process.name}] Synchronizing...")
        with Com.sync_lock:
            Com.sync_counter += 1
        
        # Attendre que tous les processus aient atteint la barrière
        Com.sync_barrier.wait()
        
        print(f"[Com-{self.process.name}] Synchronization complete.")
    
    def broadcastSync(self, obj: any, from_process: int):
        """Diffusion synchrone de l'objet à tous les processus."""
        if self.process.numero == from_process:
            # Si le processus est l'émetteur, il envoie le message et attend que tous l'aient reçu.
            self.inc_clock()
            print(f"[Com-{self.process.name}] broadcastsSync: {obj} with Lamport clock: {self.clock}")
            PyBus.Instance().post(BroadcastMessage(obj, self.process.name))

            # Attendre que toutes les confirmations soient reçues
            while Com.confirmations_received < Com.total_processes - 1:
                sleep(0.1)
            print(f"[Com-{self.process.name}] All processes received the message.")
            # Réinitialiser le compteur après la confirmation
            with Com.confirmations_lock:
                Com.confirmations_received = 0
            self.received_from_all = False
        else:
            # Si le processus n'est pas l'émetteur, attendre de recevoir le message de `from_process`.
            print(f"[Com-{self.process.name}] Waiting to receive broadcastSync from {from_process}.")
            while not self.received_sync:
                sleep(0.1)
            print(f"[Com-{self.process.name}] Received broadcastSync from {from_process}.")
            self.received_sync = False


    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def onBroadcastSync(self, event: BroadcastMessage):
        """Gère la réception des messages de diffusion synchrone."""
        if event.from_process != self.process.name:
            # Ajouter le message à la boîte aux lettres et incrémenter l'horloge.
            self.mailbox.append(event)
            self.inc_clock()
            print(f"[Com-{self.process.name}] received sync broadcast from {event.from_process}: {event.obj}")

            # Marquer que le message sync a été reçu par ce processus.
            self.received_sync = True

            # Envoyer une confirmation de réception au processus émetteur.
            PyBus.Instance().post(MessageReceivedSync(event.from_process, self.process.numero, self.clock))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageReceivedSync)
    def onMessageReceivedSync(self, event: MessageReceivedSync):
        """Gère les confirmations de réception des messages synchrones."""
        if event.dest == self.process.numero:
            print(f"[Com-{self.process.name}] Confirmation received from process {event.src}.")
            # Incrémente le compteur de confirmations reçues
            with Com.confirmations_lock:
                Com.confirmations_received += 1
            self.received_from_all = True
    

    def stop(self):
        self.alive = False
        # Vérifie si token_thread est défini et en cours d'exécution avant d'essayer de l'arrêter
        if hasattr(self, 'token_thread') and self.token_thread is not None:
            self.token_thread.join()
        self.join()  # Arrête le thread principal du Com


    def inc_clock(self):
        """Incrémente l'horloge de Lamport."""
        self.sem.acquire()
        self.clock += 1
        self.sem.release()
        return self.clock

    def sendTo(self, obj: any, dest: str):
        """Envoie l'objet à un processus spécifique."""
        self.inc_clock()
        print(f"[Com-{self.process.name}] sends to {dest}: {obj} with Lamport clock: {self.clock}")
        PyBus.Instance().post(MessageTo(obj, self.process.name, dest))

    def broadcast(self, obj: any):
        """Diffusion de l'objet à tous les processus."""
        self.inc_clock()
        print(f"[Com-{self.process.name}] broadcasts: {obj} with Lamport clock: {self.clock}")
        PyBus.Instance().post(BroadcastMessage(obj, self.process.name))

    def requestSC(self):
        """Demande l'accès à la section critique et bloque jusqu'à l'obtention du jeton."""
        print(f"[Com-{self.process.name}] Requesting access to critical section.")
        with self.lock:
            while not self.token_holder:
                sleep(0.1)  # Bloque jusqu'à ce que le jeton soit reçu

    def releaseSC(self):
        """Libère la section critique en passant le jeton au processus suivant."""
        print(f"[Com-{self.process.name}] Releasing critical section.")
        with self.lock:
            next_process = (self.process.numero + 1) % self.process.nbProcessCreated  # Détermine le prochain processus
            self.token.to_process = next_process
            self.token_holder = False
            self.sendToken(self.token)

    def sendToken(self, token):
        """Envoie le jeton au processus suivant."""
        print(f"[Com-{self.process.name}] Passing the token to process {token.to_process}.")
        PyBus.Instance().post(token)

    def token_manager(self):
        """Thread pour gérer la circulation du jeton."""
        while self.alive:
            sleep(1)  # Gère le timing pour la circulation du jeton

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Token)
    def onToken(self, event: Token):
        """Réception du jeton."""
        if event.to_process == self.process.numero:
            print(f"[Com-{self.process.name}] Received the token.")
            self.token_holder = True  # Ce processus reçoit le jeton
            self.token = event

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Bidule)
    def onReceive(self, event: Bidule):
        """Traitement de la réception des messages utilisateurs."""
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
        """Récupération du message depuis la boîte aux lettres."""
        if self.mailbox:
            return self.mailbox.pop(0)
        return None