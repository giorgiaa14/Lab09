from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # TODO: Aggiungere eventuali altri attributi

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()
        if relazioni is None or self.escursioni_map is None or self.punti_interesse_map is None:
            return

        for rel in relazioni:
            id_esc = rel["id_escursione"]
            id_pi = rel["id_punto_interesse"]

            if id_esc in self.escursioni_map and id_pi in self.punti_interesse_map:
                escursione = self.escursioni_map[id_esc]
                punto = self.punti_interesse_map[id_pi]

                escursione.punti_interesse.add(punto)
                punto.escursioni.add(escursione)

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        #salvo i vincoli e filtro solo le escursioni del parco selezionato
        self._max_giorni = max_giorni
        self._max_budget = max_budget
        self._escursioni_parco = [
            e for e in self.escursioni_map.values() if e.id_parco == id_parco
        ]

        #avvio la ricorsione a partire da 0 con pacchetto vuoto
        self._ricorsione(0, [], 0, 0.0, 0, set())


        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        # TODO: è possibile cambiare i parametri formali della funzione se ritenuto opportuno
        #uso schema
        # A aggiorno l'ottimo se il pacchetto corrente ha un gradimento migliore
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._costo = costo_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()

        #ciclo sulle escursioni rimanenti del parco (evita duplicati e permutazioni)
        for i in range(start_index, len(self._escursioni_parco)):
            escursione = self._escursioni_parco[i]

            # C controllo dei vincoli prima di scendere in ricorsione
            # vincolo giorni (se impostato)
            if self._max_giorni is not None and durata_corrente + escursione.durata_giorni > self._max_giorni:
                continue

            # vincolo budget (se impostato)
            if self._max_budget is not None and costo_corrente + escursione.costo > self._max_budget:
                continue

            # vincolo punti di interesse unici (nessuna sovrapposizione con punti_usati)
            if len(punti_usati.intersection(escursione.punti_interesse)) > 0:
                continue

            #D aggiorno lo stato parziale
            pacchetto_parziale.append(escursione)
            punti_usati.update(escursione.punti_interesse)
            valore_escursione = sum(p.voto_visitatori for p in escursione.punti_interesse)

            # E chiamata ricorsiva passando all'indice successivo
            self._ricorsione(
                i + 1,
                pacchetto_parziale,
                durata_corrente + escursione.durata_giorni,
                costo_corrente + escursione.costo,
                valore_corrente + valore_escursione,
                punti_usati
            )

            #  F backtracking: ripristino lista e set allo stato precedente
            pacchetto_parziale.pop()
            punti_usati.difference_update(escursione.punti_interesse)
