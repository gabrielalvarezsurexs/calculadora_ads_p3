"""Pedidos de genes por el Campo de Datos: el lado de quien ENTREGA.

    madre que necesita un gen ─ GEN_PIDE {pedido, intento, codigo, version, sha} ─▶ todos
    quien lo tenga ─ GEN_ENTREGA {pedido, intento, destino, gen, manifiesto, fuente} ─▶ todos

No hay un "servidor de genes": contesta cualquiera que tenga ese gen **exacto**
(mismo código, versión y sha256), sea otra madre (lo lee de SU disco) o un
gestor (lo lee de su BD). Para que normalmente salga UNA sola entrega, cada
proveedor espera un retardo que sale de su hash y del pedido (el mismo truco
HRW de la elección de titular: nadie se pone de acuerdo con nadie) y se calla
si mientras tanto vio la entrega de otro. Si aun así dos entregan casi a la
vez, no pasa nada: la que pidió toma la primera que valide y descarta el resto.

Lo usa la regeneración (S4): el reemplazo nace vacío y **copia** los genes de
la célula perdida pidiéndolos así. El lado de quien pide vive en
``madre/pedidos.py``.
"""

import re
import threading
from collections import OrderedDict
from collections.abc import Callable

from comun import codigos, config, foliado, hashes, microservicios
from comun.microservicios import Paquete
from comun.programador import Programador

RECORDAR = 500          # pedidos atendidos que se recuerdan (para callarse)
_SHA = re.compile(r"[0-9a-f]{8,64}")

# (código, versión, sha o prefijo) -> el paquete, si lo tengo
Buscar = Callable[[str, str, str | None], Paquete | None]


def retardo(proveedor: str, pedido: str, intento: int) -> float:
    """Cuánto espera ``proveedor`` antes de entregar: determinista, en
    ``[0, ENTREGA_RETARDO_MAX]``, distinto para cada proveedor y pedido."""
    peso = int(hashes.prioridad(proveedor, pedido, intento)[:8], 16) / 0xFFFFFFFF
    return peso * config.ENTREGA_RETARDO_MAX


def coincide(sha_pedido: str | None, sha_real: str) -> bool:
    """El sha del pedido puede venir completo o como prefijo (el ``sha8`` del latido)."""
    return not sha_pedido or sha_real.startswith(sha_pedido)


def leer_pide(cuerpo: dict) -> tuple[str, int, str, str, str | None] | None:
    """(pedido, intento, código, versión, sha) de un ``GEN_PIDE``; None si está mal."""
    pedido, intento = cuerpo.get("pedido"), cuerpo.get("intento", 1)
    codigo, version, sha = cuerpo.get("codigo"), cuerpo.get("version"), cuerpo.get("sha")
    if not foliado.es_folio_admin(pedido, foliado.PEDIDO):
        return None
    if not isinstance(intento, int) or isinstance(intento, bool) or intento < 1:
        return None
    if not codigos.es_gen(codigo) or not microservicios.es_version(version):
        return None
    if sha is not None and not (isinstance(sha, str) and _SHA.fullmatch(sha)):
        return None
    return pedido, intento, codigo, version, sha


class Proveedor:
    """Contesta ``GEN_PIDE`` si tiene el gen; se calla si otro ya entregó."""

    def __init__(self, celula, buscar: Buscar, programador: Programador):
        self.celula = celula
        self.buscar = buscar
        self.programador = programador
        self.entregas = 0
        self.calladas = 0
        self._lock = threading.Lock()
        self._atendidos: OrderedDict[tuple[str, int], str] = OrderedDict()  # -> quién entregó

    def rx_pide(self, m: dict) -> None:
        datos = leer_pide(m["cuerpo"])
        if datos is None:
            self.celula.log("DROP", f"GEN_PIDE mal formado de {m.get('nombre_origen')}")
            return
        pedido, intento, codigo, version, sha = datos
        paquete = self.buscar(codigo, version, sha)
        if paquete is None:
            return  # no tengo ese gen exacto: no me toca
        espera = retardo(self.celula.hash, pedido, intento)
        self.programador.en(espera, lambda: self._entregar(m, pedido, intento, paquete, espera))

    def rx_entrega(self, m: dict) -> None:
        """Otro entregó: anoto el pedido como atendido para callarme."""
        cuerpo = m["cuerpo"]
        pedido, intento = cuerpo.get("pedido"), cuerpo.get("intento", 1)
        if isinstance(pedido, str) and isinstance(intento, int):
            self._anotar((pedido, intento), m.get("nombre_origen") or hashes.corto(m["origen"]))

    def _anotar(self, clave: tuple[str, int], quien: str) -> bool:
        """True si la clave era nueva (nadie había entregado)."""
        with self._lock:
            if clave in self._atendidos:
                return False
            self._atendidos[clave] = quien
            while len(self._atendidos) > RECORDAR:
                self._atendidos.popitem(last=False)
            return True

    def _entregar(self, m: dict, pedido: str, intento: int, paquete: Paquete,
                  espera: float) -> None:
        pidio = m.get("nombre_origen") or hashes.corto(m["origen"])
        if not self._anotar((pedido, intento), self.celula.nombre):
            with self._lock:
                quien = self._atendidos.get((pedido, intento))
            self.calladas += 1
            self.celula.log("CALLA", f"{pedido}: {paquete.id} para {pidio} ya lo entregó "
                                     f"{quien}; no lo repito", consola=False)
            return
        enviado = self.celula.publicar(codigos.GEN_ENTREGA, {
            "pedido": pedido, "intento": intento, "destino": m["origen"], "gen": paquete.id,
            **paquete.a_mensaje()})
        if enviado is not None:
            self.entregas += 1
            self.celula.log("ENTREGA", f"{pedido}: {paquete.id} (sha {paquete.sha_real[:8]}) "
                                       f"→ {pidio} · tras {espera * 1000:.0f} ms de retardo propio")
