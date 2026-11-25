"""La topología del sistema, armada solo con lo que cualquiera puede oír (PLAN §4.4).

Nadie le "pregunta" la topología a un servidor central, porque no lo hay. Este
modelo la reconstruye con los mensajes que ya viajan por el Campo de Datos:

* ``NODO_LAT``  → nodos vivos, su endpoint, sus **enlaces reales** y sus células;
* ``CEL_LAT``   → cada célula: tipo, nodo, genes (con versión y sha8), mudo,
  generación, a quién reemplaza, cola y atendidas;
* ``TOPO_RES``  → lo mismo, como respuesta inmediata a un ``TOPO_REQ``;
* ``CEL_ADIOS`` → la célula se fue ordenadamente (retiro, Ctrl+C): se borra;
* ``CLON_AVISO`` → un reemplazo está **naciendo** (se dibuja punteado junto a
  su nodo hasta que late por primera vez).

Una célula o un nodo que deja de latir ``LATIDO_CADUCIDAD`` s se marca **caído**
(el diagrama lo pinta en rojo) y a los ``CAIDA_VISIBLE`` s se olvida. Una
**madre** caída es una pérdida: sigue en rojo hasta que aparece su reemplazo
(o ``ESPERA_REEMPLAZO`` s). Si vuelve a latir, revive. Todo es estado local de
cada gestor: dos gestores ven lo mismo porque oyen lo mismo, no porque se
sincronicen.

Sin Tkinter: el diagrama (``gestor/diagrama.py``) solo dibuja ``instantanea()``.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from comun import codigos, config, hashes, mensajes

VIVA = "viva"
CAIDA = "caida"
NACIENDO = "naciendo"
REEMPLAZADA_VISIBLE = 2.5   # lo que sigue en rojo una madre caída tras aparecer su reemplazo


@dataclass
class NodoVisto:
    hash: str
    nombre: str
    endpoint: str | None = None
    vecinos: dict = field(default_factory=dict)      # hash -> nombre
    celulas: int = 0
    contadores: dict = field(default_factory=dict)
    visto: float = 0.0
    estado: str = VIVA
    caido_en: float | None = None
    confirmado: bool = False                         # ya llegó su NODO_LAT


@dataclass
class CelulaVista:
    hash: str
    nombre: str
    tipo: str                                        # MADRE, INTERFAZ, GESTOR
    nodo: str | None = None
    nodo_nombre: str | None = None
    genes: list = field(default_factory=list)        # [{"codigo", "version", "sha8"}]
    mudo: bool = False
    generacion: int = 0
    reemplaza: str | None = None
    en_cola: int = 0
    atendidas: int = 0
    visto: float = 0.0
    estado: str = VIVA
    caido_en: float | None = None
    reemplazada_en: float | None = None              # cuándo apareció su reemplazo
    desde: float = 0.0                               # su primer latido (para "recién nacida")
    clonador: str | None = None                      # solo en un reemplazo NACIENDO

    @property
    def codigos(self) -> list[str]:
        return [g["codigo"] for g in self.genes]

    @property
    def vacia(self) -> bool:
        return self.tipo == mensajes.MADRE and not self.genes

    def genes_texto(self) -> str:
        return ", ".join(f"{g['codigo']} {g['version']}" for g in self.genes) or "vacía"


@dataclass(frozen=True)
class Foto:
    """Copia inmutable para dibujar (y para las pruebas)."""

    nodos: dict
    celulas: dict
    version: int
    naciendo: dict = field(default_factory=dict)     # reemplaza -> CelulaVista (NACIENDO)

    def madres(self, nodo: str | None = None, *, vivas: bool = True) -> list[CelulaVista]:
        return sorted((c for c in self.celulas.values() if c.tipo == mensajes.MADRE
                       and (nodo is None or c.nodo == nodo)
                       and (not vivas or c.estado == VIVA)), key=lambda c: c.nombre)

    def disponibilidad(self) -> dict[str, int]:
        """Madres vivas (no mudas) por código: lo que puede atender cada operación."""
        cuenta = {s: 0 for s in codigos.SERVICIOS}
        for c in self.madres():
            if not c.mudo:
                for cod in c.codigos:
                    cuenta[cod] = cuenta.get(cod, 0) + 1
        return cuenta


def _texto(valor, defecto=None):
    return valor if isinstance(valor, str) and valor else defecto


def _entero(valor, defecto: int = 0) -> int:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else defecto


def _genes(lista) -> list[dict]:
    if not isinstance(lista, list):
        return []
    return [{"codigo": g["codigo"], "version": str(g.get("version", "?")),
             "sha8": str(g.get("sha8", ""))[:8]}
            for g in lista if isinstance(g, dict) and codigos.es_gen(g.get("codigo"))]


class Topologia:
    def __init__(self, reloj: Callable[[], float] = time.monotonic):
        self._reloj = reloj
        self._lock = threading.Lock()
        self._nodos: dict[str, NodoVisto] = {}
        self._celulas: dict[str, CelulaVista] = {}
        self._naciendo: dict[str, CelulaVista] = {}       # reemplaza -> reemplazo naciendo
        self._version = 0

    # ------------------------------------------------------------ entradas

    def nodo_lat(self, origen: str, cuerpo: dict) -> None:
        vecinos = {v["hash"]: _texto(v.get("nombre"), hashes.corto(v["hash"]))
                   for v in cuerpo.get("vecinos") or []
                   if isinstance(v, dict) and mensajes.es_hash(v.get("hash"))}
        celulas = cuerpo.get("celulas")
        with self._lock:
            n = self._nodos.get(origen) or NodoVisto(origen, hashes.corto(origen))
            n.nombre = _texto(cuerpo.get("nombre"), n.nombre)
            n.endpoint = _texto(cuerpo.get("endpoint"), n.endpoint)
            n.vecinos = vecinos
            n.celulas = len(celulas) if isinstance(celulas, list) else n.celulas
            n.contadores = cuerpo.get("contadores") if isinstance(
                cuerpo.get("contadores"), dict) else {}
            n.visto, n.estado, n.caido_en, n.confirmado = self._reloj(), VIVA, None, True
            self._nodos[origen] = n
            self._version += 1

    def celula_lat(self, origen: str, nombre: str | None, cuerpo: dict) -> CelulaVista | None:
        """Un ``CEL_LAT`` o ``TOPO_RES`` (mismo cuerpo). Devuelve la célula si es un
        **reemplazo que acaba de nacer** (su primer latido), para la línea de tiempo."""
        tipo = cuerpo.get("tipo")
        if tipo not in (mensajes.MADRE, mensajes.INTERFAZ, mensajes.GESTOR):
            return None
        ahora = self._reloj()
        nodo = cuerpo.get("nodo") if mensajes.es_hash(cuerpo.get("nodo")) else None
        with self._lock:
            nueva = origen not in self._celulas
            c = self._celulas.get(origen) or CelulaVista(origen, nombre or hashes.corto(origen),
                                                         tipo, desde=ahora)
            c.nombre, c.tipo = nombre or c.nombre, tipo
            c.nodo, c.nodo_nombre = nodo, _texto(cuerpo.get("nodo_nombre"))
            c.genes = _genes(cuerpo.get("genes"))
            c.mudo = cuerpo.get("mudo") is True
            c.generacion = _entero(cuerpo.get("generacion"))
            c.reemplaza = cuerpo.get("reemplaza") if mensajes.es_hash(
                cuerpo.get("reemplaza")) else None
            c.en_cola, c.atendidas = _entero(cuerpo.get("en_cola")), _entero(
                cuerpo.get("atendidas"))
            c.visto, c.estado, c.caido_en = ahora, VIVA, None
            c.reemplazada_en = None   # late: ya no es una pérdida (si alguna vez lo fue)
            self._celulas[origen] = c
            if nodo and nodo not in self._nodos:
                # Aún no llega su NODO_LAT: se dibuja ya con lo que dice la célula.
                self._nodos[nodo] = NodoVisto(nodo, c.nodo_nombre or hashes.corto(nodo),
                                              visto=ahora)
            nacio = None
            if c.reemplaza:
                perdida = self._celulas.get(c.reemplaza)
                if (perdida is not None and perdida.estado == CAIDA
                        and perdida.reemplazada_en is None):
                    perdida.reemplazada_en = ahora
                estaba_naciendo = self._naciendo.pop(c.reemplaza, None) is not None
                if nueva and (estaba_naciendo or perdida is not None):
                    nacio = replace(c, genes=list(c.genes))
                elif nueva:
                    # Un reemplazo viejo que este gestor ve por primera vez (lo abrieron
                    # después): no es "recién nacido".
                    c.desde = ahora - 3600.0
            self._version += 1
            return nacio

    def aviso_clon(self, cuerpo: dict, clonador: str) -> CelulaVista | None:
        """``CLON_AVISO``: el reemplazo se dibuja "naciendo…" junto a su nodo."""
        perdida, nodo = cuerpo.get("reemplaza"), cuerpo.get("nodo")
        if not mensajes.es_hash(perdida):
            return None
        with self._lock:
            n = next((x for x in self._nodos.values() if x.endpoint == nodo), None)
            c = CelulaVista(f"n:{perdida}", _texto(cuerpo.get("hijo"), "reemplazo"),
                            mensajes.MADRE, n.hash if n else None,
                            _texto(cuerpo.get("nodo_nombre")), _genes(cuerpo.get("genes")),
                            generacion=_entero(cuerpo.get("generacion")), reemplaza=perdida,
                            visto=self._reloj(), estado=NACIENDO, clonador=clonador)
            self._naciendo[perdida] = c
            self._version += 1
            return replace(c)

    def marcar_caida(self, h: str) -> CelulaVista | None:
        """Las madres ya la dan por perdida (``CLON_AVISO``) antes de que este gestor
        lo notara: se marca caída ya. Devuelve la célula si estaba viva."""
        with self._lock:
            c = self._celulas.get(h)
            if c is None or c.estado != VIVA:
                return None
            c.estado, c.caido_en = CAIDA, self._reloj()
            self._version += 1
            return replace(c, genes=list(c.genes))

    def tregua(self) -> None:
        """Tras un hueco sin enlace: plazo completo desde ahora para todo lo vivo."""
        with self._lock:
            ahora = self._reloj()
            for x in (*self._nodos.values(), *self._celulas.values()):
                if x.estado == VIVA:
                    x.visto = max(x.visto, ahora)

    def olvidar(self, h: str) -> None:
        """Se quita de inmediato (un reemplazo que murió antes de estar listo): su
        pérdida vuelve a esperar reemplazo, porque las madres la reintentan."""
        with self._lock:
            c = self._celulas.pop(h, None)
            if c is None:
                return
            perdida = self._celulas.get(c.reemplaza) if c.reemplaza else None
            if perdida is not None:
                perdida.reemplazada_en = None
            self._version += 1

    def pendientes(self) -> list[CelulaVista]:
        """Madres caídas sin reemplazo todavía + reemplazos naciendo (para "nivel ok")."""
        with self._lock:
            return [replace(c) for c in self._celulas.values()
                    if c.tipo == mensajes.MADRE and c.estado == CAIDA and c.reemplazada_en is None
                    ] + [replace(c) for c in self._naciendo.values()]

    def adios(self, origen: str) -> CelulaVista | None:
        """La célula se despidió (``CEL_ADIOS``): se quita sin pasar por "caída"."""
        with self._lock:
            c = self._celulas.pop(origen, None)
            if c is not None:
                self._version += 1
            return c

    def caducar(self) -> list[tuple[str, str, str, str | None]]:
        """Marca caídos y olvida los viejos. Devuelve ``[(evento, texto, hash, tipo)]``
        nuevos (``tipo`` None para un nodo)."""
        ahora, avisos = self._reloj(), []
        with self._lock:
            for tabla, que in ((self._celulas, "célula"), (self._nodos, "nodo")):
                for h, x in list(tabla.items()):
                    tipo = getattr(x, "tipo", None)
                    if x.estado == VIVA and ahora - x.visto > config.LATIDO_CADUCIDAD:
                        x.estado, x.caido_en = CAIDA, ahora
                        texto = f"{que} {x.nombre} sin latido en {config.LATIDO_CADUCIDAD:g} s"
                        avisos.append(("CAIDA", texto, h, tipo))
                        self._version += 1
                    elif x.estado == CAIDA and self._olvidar(x, tipo, ahora):
                        del tabla[h]
                        self._version += 1
            for h, c in list(self._naciendo.items()):
                if ahora - c.visto > config.PLAZO_CLON:   # el aviso caducó: se reintentará
                    del self._naciendo[h]
                    self._version += 1
        return avisos

    @staticmethod
    def _olvidar(x, tipo: str | None, ahora: float) -> bool:
        if tipo != mensajes.MADRE:
            return ahora - x.caido_en > config.CAIDA_VISIBLE
        # Una madre caída es una pérdida: sigue en rojo hasta que aparece su reemplazo.
        if x.reemplazada_en is not None:
            return ahora - x.reemplazada_en > REEMPLAZADA_VISIBLE
        return ahora - x.caido_en > config.ESPERA_REEMPLAZO

    # ------------------------------------------------------------ consultas

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def instantanea(self) -> Foto:
        with self._lock:
            return Foto({h: replace(n, vecinos=dict(n.vecinos)) for h, n in self._nodos.items()},
                        {h: replace(c, genes=list(c.genes)) for h, c in self._celulas.items()},
                        self._version,
                        {h: replace(c, genes=list(c.genes)) for h, c in self._naciendo.items()})

    def celula(self, h: str) -> CelulaVista | None:
        with self._lock:
            c = self._celulas.get(h)
            return replace(c, genes=list(c.genes)) if c else None
