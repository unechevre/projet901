from threading import Lock, Semaphore, Thread, Barrier  
from time import sleep
from Bidule import *
from pyeventbus3.pyeventbus3 import *


class Token:
    """Classe représentant un jeton pour la gestion de la section critique."""
    def __init__(self, from_process=None, to_process=None):
        self.from_process = from_process
        self.to_process = to_process


class Com(Thread):
    # Barrière pour synchroniser tous les processus ensemble
    sync_barrier = None
    sync_lock = Lock()
    sync_counter = 0

    def __init__(self, clock, process) -> None:
        Thread.__init__(self)
        self.setName(f"Com-{process.numero}")
        PyBus.Instance().register(self, self)

        self.owner = process.numero
        self.clock = clock
        self.sem = Semaphore()  # Protection de l'horloge avec un sémaphore
        self.mailbox = []  # Boîte aux lettres
        self.process = process  # Référence vers le processus associé
        self.alive = True
        self.token_holder = False  # Indique si le processus détient le jeton
        self.token = None  # Jeton initialisé à None
        self.lock = Lock()  # Verrou pour la gestion de la section critique
        self.start()

        # Initialiser la barrière pour synchroniser tous les processus
        with Com.sync_lock:
            if Com.sync_barrier is None:
                Com.sync_barrier = Barrier(process.nbProcessCreated)

           # Initialiser le jeton pour le premier processus
        if self.process.numero == 1:  # Processus 0 reçoit le jeton initial
            self.token_holder = True
            self.token = Token(from_process=None, to_process=self.process.numero)
        # Thread pour gérer le jeton
        self.token_thread = Thread(target=self.token_manager)
        self.token_thread.start()

    def synchronize(self):
        """Synchronise le processus avec tous les autres, bloquant jusqu'à ce que tous les processus aient appelé cette méthode."""
        print(f"[Com-{self.process.name}] Synchronizing...")
        with Com.sync_lock:
            Com.sync_counter += 1
        
        # Attendre que tous les processus aient atteint la barrière
        Com.sync_barrier.wait()
        
        print(f"[Com-{self.process.name}] Synchronization complete.")
    
    def stop(self):
        self.alive = False
        self.token_thread.join()
        self.join()

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