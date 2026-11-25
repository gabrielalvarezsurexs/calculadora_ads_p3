"""Pedir un gen por el Campo de Datos: el lado de la madre que lo NECESITA.

    yo ─ GEN_PIDE {pedido, intento, codigo, version, sha} ─▶ todos
    quien lo tenga ─ GEN_ENTREGA {pedido, intento, destino = yo, …} ─▶ todos
    yo: lo escribo en MI disco, lo valido, lo cargo y lo pruebo (como cualquier gen)

Es la tercera vía por la que un gen llega a una madre (además del banco local y
la inyección del gestor). La usa el reemplazo de una célula perdida para
**copiar** sus genes (S4). Toma la primera entrega que valide: si una llega
alterada (sha distinto), la rechaza y sigue esperando a otra. Sin entrega en
``PLAZO_PEDIDO`` s vuelve a pedir (``intento`` + 1), hasta ``REINTENTOS_PEDIDO``
veces; después el pedido queda fallido y quien pidió decide (la regeneración
cae al banco local si el sha coincide).

El lado de quien entrega es ``comun/pedidos.py`` (lo comparten madres y gestores).
"""

import itertools
import threading
from dataclasses import dataclass, field

from comun import codigos, config, foliado, hashes, microservicios
from comun.microservicios import Paquete
from comun.pedidos import coincide
from madre.almacen import ENTREGA

ESPERANDO = "esperando"
INSTALANDO = "instalando"
LISTO = "listo"
FALLIDO = "fallido"


@dataclass
class Pedido:
    folio: str
    codigo: str
    version: str
    sha: str | None
    intento: int = 1
    estado: str = ESPERANDO
    de: str | None = None            # quién lo entregó
    resultado: object = None         # la Instalacion final
    detalle: str = ""
    hecho: threading.Event = field(default_factory=threading.Event)

    @property
    def gen(self) -> str:
        return microservicios.gen_id(self.codigo, self.version)

    def esperar(self, plazo: float | None = None) -> bool:
        """True si terminó (bien o mal) dentro del plazo."""
        return self.hecho.wait(plazo)


class Pedidos:
    def __init__(self, madre):
        self.madre = madre
        self._lock = threading.Lock()
        self._numeros = itertools.count(1)
        self._pedidos: dict[str, Pedido] = {}

    def pedir(self, codigo: str, version: str, sha: str | None = None) -> Pedido:
        """Publica ``GEN_PIDE`` y devuelve el pedido (se sigue con ``esperar``)."""
        folio = foliado.folio_admin(foliado.PEDIDO, self.madre.hash, next(self._numeros))
        p = Pedido(folio, codigo, version, sha)
        with self._lock:
            self._pedidos[folio] = p
        self._publicar(p)
        return p

    def _publicar(self, p: Pedido) -> None:
        self.madre.publicar(codigos.GEN_PIDE, {"pedido": p.folio, "intento": p.intento,
                                               "codigo": p.codigo, "version": p.version,
                                               "sha": p.sha})
        sha = f" sha {p.sha[:8]}" if p.sha else ""
        self.madre.log("GEN_PIDE", f"{p.folio} · intento {p.intento}: ¿quién tiene {p.gen}{sha}?")
        intento = p.intento
        self.madre.programador.en(config.PLAZO_PEDIDO, lambda: self._vencer(p, intento))

    def _vencer(self, p: Pedido, intento: int) -> None:
        with self._lock:
            if p.intento != intento or p.estado in (LISTO, FALLIDO):
                return
            if p.estado == INSTALANDO:
                # Se está instalando una entrega: si falla, el pedido vuelve a esperar y
                # necesita su plazo; se revisa de nuevo después.
                self.madre.programador.en(config.PLAZO_PEDIDO, lambda: self._vencer(p, intento))
                return
            if p.intento >= config.REINTENTOS_PEDIDO:
                p.estado = FALLIDO
                p.detalle = f"nadie entregó {p.gen} en {p.intento} intento(s)"
            else:
                p.intento += 1
        if p.estado == FALLIDO:
            self.madre.log("PEDIDO_FALLIDO", f"{p.folio}: {p.detalle}")
            p.hecho.set()
        else:
            self._publicar(p)

    def rx_entrega(self, m: dict) -> None:
        cuerpo = m["cuerpo"]
        if cuerpo.get("destino") != self.madre.hash:
            return
        de = m.get("nombre_origen") or hashes.corto(m["origen"])
        with self._lock:
            p = self._pedidos.get(cuerpo.get("pedido"))
            if p is None:
                return
            if p.estado != ESPERANDO:
                self.madre.log("IGNORA", f"GEN_ENTREGA de {de} para {p.folio}: ya está "
                                         f"{p.estado}", consola=False)
                return
            p.estado = INSTALANDO
        problema = self._revisar(p, cuerpo)
        if problema:
            self.madre.log("GEN_RECHAZADO", f"{p.folio}: entrega de {de} rechazada: {problema}; "
                                            f"sigo esperando otra")
            with self._lock:
                p.estado = ESPERANDO
            return
        paquete = Paquete.de_mensaje(cuerpo)
        self.madre.programador.en(0, lambda: self._instalar(p, paquete, de))

    @staticmethod
    def _revisar(p: Pedido, cuerpo: dict) -> str | None:
        try:
            paquete = Paquete.de_mensaje(cuerpo)
        except ValueError as e:
            return str(e)
        if microservicios.validar_manifiesto(paquete.manifiesto):
            return "manifiesto inválido"
        if (paquete.codigo, paquete.version) != (p.codigo, p.version):
            return f"llegó {paquete.id}, pedí {p.gen}"
        if not coincide(p.sha, paquete.sha_real):
            return f"sha {paquete.sha_real[:8]} no es el pedido ({p.sha[:8]})"
        return None

    def _instalar(self, p: Pedido, paquete: Paquete, de: str) -> None:
        r = self.madre.instalar(paquete, f"{ENTREGA} de {de}")
        with self._lock:
            if r.ok:
                p.estado, p.de, p.resultado, p.detalle = LISTO, de, r, r.detalle
            else:
                p.estado = ESPERANDO  # quizá otro entregue uno bueno; si no, vence
                return
        self.madre.log("GEN_COPIADO", f"{p.folio}: {r.gen} copiado de {de} (disco → memoria, "
                                      f"{r.ms} ms)")
        p.hecho.set()

    def pendientes(self) -> list[Pedido]:
        with self._lock:
            return [p for p in self._pedidos.values() if p.estado in (ESPERANDO, INSTALANDO)]
