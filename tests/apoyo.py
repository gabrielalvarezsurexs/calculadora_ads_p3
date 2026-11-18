"""Auxiliares de las pruebas de integración: todo en proceso, puertos efímeros.

* ``Registro``: bitácora en memoria (sin consola ni archivo) que permite contar
  eventos y engancharse a ellos, p. ej. "cuando esta célula sea TITULAR…".
* ``Receptor``: célula que solo anota lo que le llega.
* ``Espia``: célula que cuenta los ACK, RES y FIN de cada folio (para afirmar
  "exactamente un RES") y que también sirve para inyectar mensajes a mano.
* ``Sistema``: levanta N nodos en malla, células madre (con sus genes, cada una
  con su almacén en una carpeta temporal), interfaces y gestores (cada uno con
  su BD en la misma carpeta temporal), y lo apaga.
* ``acortar``: parcha ``comun.config`` mientras vive una clase de pruebas.
"""

import collections
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path
from unittest import mock

from celula.base import Celula
from comun import codigos, config, mensajes
from comun.bitacora import Bitacora
from gestor.nucleo import Gestor
from interfaz.nucleo import Interfaz
from madre.copia import leer_lista
from madre.nucleo import Madre
from madre.regeneracion import Encargo
from nodo.nucleo import Nodo

# Tiempos de prueba. RELEVO se deja en 1 s (plan §12): por debajo, la carga de la
# máquina podría provocar relevos falsos y romper las aserciones de "exactamente uno".
# VENTANA_ELECCION es la de producción: con 0.3 s y la máquina saturada, un ACK tardío
# hacía que dos madres se eligieran titulares (S5; la GUI descarta la DUPLICADA).
TIEMPOS = {
    "SUPERVISOR": 0.2,
    "BACKOFF_MIN": 0.2,
    "BACKOFF_MAX": 1.0,
    "LATIDO": 0.5,
    "LATIDO_CADUCIDAD": 2.0,
    "VENTANA_ELECCION": 0.5,
    "RELEVO": 1.0,
    "MARGEN_RESULTADO": 1.0,
}


def acortar(caso, **valores) -> None:
    """Desde ``setUpClass``: parcha config hasta que termine la clase."""
    parche = mock.patch.multiple(config, **(valores or TIEMPOS))
    parche.start()
    caso.addClassCleanup(parche.stop)


def esperar(condicion, plazo: float = 10.0, paso: float = 0.05) -> bool:
    fin = time.monotonic() + plazo
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(paso)
    return bool(condicion())


def puertos_libres(n: int) -> list[int]:
    socks = []
    try:
        for _ in range(n):
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            socks.append(s)
        return [s.getsockname()[1] for s in socks]
    finally:
        for s in socks:
            s.close()


class Registro:
    """Bitácora en memoria. ``bitacora`` es lo que se le pasa a nodos y células."""

    def __init__(self, nombre: str):
        self.nombre = nombre
        self._lock = threading.Lock()
        self.lineas: list[tuple[str, str]] = []
        self.ganchos: list = []  # funciones (evento, texto), llamadas en el hilo que registra
        self.bitacora = Bitacora(nombre, consola=False, archivo=False, callback=self._anotar)

    def _anotar(self, _hora, evento, texto) -> None:
        with self._lock:
            self.lineas.append((evento, texto))
        for gancho in list(self.ganchos):
            gancho(evento, texto)

    def eventos(self, evento: str, contiene: str = "") -> list[str]:
        with self._lock:
            return [t for e, t in self.lineas if e == evento and contiene in t]

    def contar(self, evento: str, contiene: str = "") -> int:
        return len(self.eventos(evento, contiene))


class Receptor(Celula):
    """Anota cada mensaje de datos que le entrega su nodo (ya deduplicado)."""

    def __init__(self, nombre: str, nodo: str):
        self.registro = Registro(nombre)
        super().__init__(mensajes.SONDA, nombre, nodo, bitacora=self.registro.bitacora)
        self.recibidos: list[dict] = []

    def procesar(self, m: dict) -> None:
        self.recibidos.append(m)

    def con_id(self, id_mensaje: str) -> list[dict]:
        return [m for m in list(self.recibidos) if m["id"] == id_mensaje]


class Espia(Celula):
    """Cuenta ACK, RES y FIN por folio. También publica mensajes a mano."""

    def __init__(self, nodo: str, nombre: str = "ESPIA"):
        self.registro = Registro(nombre)
        super().__init__(mensajes.SONDA, nombre, nodo, bitacora=self.registro.bitacora)
        self._lock_espia = threading.Lock()
        self.acks = collections.defaultdict(list)  # folio -> [(origen, intento)]
        self.res = collections.defaultdict(list)   # folio -> [mensaje]
        self.fin = collections.defaultdict(list)   # folio -> [mensaje]

    def procesar(self, m: dict) -> None:
        partes = codigos.separar(m["codigo"])
        if partes is None:
            return
        folio = m["cuerpo"].get("folio")
        with self._lock_espia:
            if partes[1] == codigos.ACK:
                self.acks[folio].append((m["origen"], m["cuerpo"].get("intento")))
            elif partes[1] == codigos.RES:
                self.res[folio].append(m)
            elif partes[1] == codigos.FIN:
                self.fin[folio].append(m)

    def respuestas(self, folio: str) -> list[dict]:
        with self._lock_espia:
            return list(self.res.get(folio, []))

    def fines(self, folio: str) -> list[dict]:
        with self._lock_espia:
            return list(self.fin.get(folio, []))

    def acusadores(self, folio: str, intento: int = 1) -> set[str]:
        with self._lock_espia:
            return {o for o, k in self.acks.get(folio, []) if k == intento}


class Sistema:
    """N nodos con semillas en cadena + células madre + interfaces, en proceso.

    ``regenerar``: las madres lanzan reemplazos (en este mismo proceso, con
    ``lanzar``). Por defecto no, para que las pruebas que tumban madres a
    propósito no vean aparecer clones a media aserción."""

    def __init__(self, *, regenerar: bool = False):
        self.nodos: list[Nodo] = []
        self.registros: dict[str, Registro] = {}
        self.madres: list[Madre] = []
        self.guis: list[Interfaz] = []
        self.gestores: list[Gestor] = []
        self.celulas: list[Celula] = []
        self.clones: list[Madre] = []
        self.encargos: list[Encargo] = []
        self.regenerar = regenerar
        self.datos = Path(tempfile.mkdtemp(prefix="ads-pruebas-"))
        self._lock = threading.Lock()

    # ------------------------------------------------------------ construir

    def nodo(self, nombre: str, semillas=(), puerto: int = 0) -> Nodo:
        reg = self.registros[nombre] = Registro(nombre)
        n = Nodo(puerto, nombre, semillas=semillas, bitacora=reg.bitacora)
        n.iniciar()
        self.nodos.append(n)
        return n

    def malla(self, n: int = 4) -> list[Nodo]:
        """Semillas en cadena: cada nodo solo conoce al anterior."""
        for k in range(1, n + 1):
            semillas = [self.nodos[-1].endpoint] if self.nodos else []
            self.nodo(f"Nodo {k}", semillas)
        return list(self.nodos)

    def madre(self, nodo: Nodo, nombre: str, genes=(), *, retardo_ms: int = 0,
              mudo: bool = False) -> Madre:
        reg = self.registros[nombre] = Registro(nombre)
        m = Madre(nombre, nodo.endpoint, genes_iniciales=genes, datos=self.datos,
                  retardo_ms=retardo_ms, mudo=mudo, bitacora=reg.bitacora,
                  lanzador=self.lanzar if self.regenerar else None)
        m.iniciar()
        self.madres.append(m)
        self.celulas.append(m)
        return m

    def lanzar(self, encargo: Encargo) -> None:
        """El lanzador de las pruebas: el reemplazo es una madre en este proceso,
        construida con los mismos datos que recibiría ``python -m madre``."""
        reg = Registro(encargo.nombre)
        m = Madre(encargo.nombre, encargo.nodo, datos=self.datos, generacion=encargo.generacion,
                  reemplaza=encargo.reemplaza, reemplaza_nombre=encargo.perdida,
                  copiar=leer_lista(",".join(encargo.genes)), bitacora=reg.bitacora,
                  lanzador=self.lanzar)
        with self._lock:
            self.registros[encargo.nombre] = reg
            self.encargos.append(encargo)
            self.madres.append(m)
            self.celulas.append(m)
            self.clones.append(m)
        m.iniciar()

    def con_gen(self, codigo: str) -> list[Madre]:
        """Madres vivas que tienen ``codigo`` activo."""
        return [m for m in self.madres if m.activo and m.genoma.activo(codigo)]

    def gui(self, nombre: str, nodo: Nodo, acuses_min: int | None = None) -> Interfaz:
        reg = self.registros[nombre] = Registro(nombre)
        g = Interfaz(nombre, nodo.endpoint, acuses_min=acuses_min, bitacora=reg.bitacora)
        g.iniciar()
        self.guis.append(g)
        self.celulas.append(g)
        return g

    def gestor(self, nodo: Nodo, nombre: str = "G-1") -> Gestor:
        reg = self.registros[nombre] = Registro(nombre)
        g = Gestor(nombre, nodo.endpoint, bd=self.datos / "gestor" / f"{nombre}.sqlite3",
                   bitacora=reg.bitacora)
        g.iniciar()
        self.gestores.append(g)
        self.celulas.append(g)
        return g

    def agregar(self, celula: Celula) -> Celula:
        celula.iniciar()
        self.celulas.append(celula)
        return celula

    def completo(self, n_nodos: int = 4) -> "Sistema":
        """Malla de n + en cada nodo 1 GUI y 4 madres, una con cada gen (modo "con
        servicios" de la configuración mínima)."""
        self.malla(n_nodos)
        assert self.esperar_malla(), "la malla no se formó"
        for k, nodo in enumerate(self.nodos, 1):
            for s in codigos.SERVICIOS:
                self.madre(nodo, f"{s}-N{k}", [f"{s}@1.0"])
        for k, nodo in enumerate(self.nodos, 1):
            self.gui(f"GUI-{k}", nodo)
        assert self.esperar_disponible(len(self.nodos)), "las GUIs no vieron a las madres"
        return self

    # ---------------------------------------------------------------- esperas

    def esperar_malla(self, plazo: float = 15.0) -> bool:
        def lista():
            vivos = [n for n in self.nodos if n.activo]
            hashes = {n.hash for n in vivos}
            return all(set(n.vecinos) == hashes - {n.hash} for n in vivos)
        return esperar(lista, plazo)

    def esperar_disponible(self, vivas: int, plazo: float = 15.0) -> bool:
        return esperar(lambda: all(d["vivas"] == vivas for g in self.guis
                                   for d in g.disponibilidad().values()), plazo)

    # ---------------------------------------------------------------- apagar

    def apagar(self) -> None:
        for m in self.madres:
            m.regeneracion.activa = False   # que nadie clone mientras se apaga todo
        for c in list(self.celulas):
            c.detener()
        for n in self.nodos:
            n.detener()
        for g in self.gestores:
            g.bd.cerrar()  # en Windows, una BD abierta no deja borrar la carpeta
        shutil.rmtree(self.datos, ignore_errors=True)
