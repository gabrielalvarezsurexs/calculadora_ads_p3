"""Órdenes del gestor, del lado de la madre (PLAN §4.3).

    gestor ─ GEN_INYECTA {orden, destino, accion, manifiesto, fuente} ─▶ todos
    gestor ─ GEN_BAJA    {orden, destino, codigo}                     ─▶ todos
    gestor ─ CEL_RETIRO  {orden, destino}                             ─▶ todos
    madre destino ─ GEN_ACK {orden, destino, accion}                  (de inmediato)
    madre destino ─ GEN_RES {orden, destino, accion, ok, detalle, gen, genes, ms, ruta}

La orden viaja por broadcast como cualquier mensaje: el ``destino`` es el hash
de la célula que debe atenderla y todas las demás la ignoran. Lo importante es
**quién decide**: el gestor solo pide; la madre escribe el programa en SU disco,
lo valida, lo carga y lo prueba ella misma, y puede rechazarlo (``SUM 9.9``) o
quedarse con la versión que ya tenía. Por eso el gestor no es un orquestador.

* ``alta`` / ``cambio``: el ciclo de vida de ``madre/genes.py``. Un cambio de
  versión es una sustitución con reversión (la vieja sigue si la nueva falla).
* ``GEN_BAJA``: descarga el gen; deja de acusar ese código al instante.
* ``CEL_RETIRO``: la madre contesta, publica ``CEL_ADIOS`` y termina. No es una
  pérdida: nadie la regenera.

El ``GEN_ACK`` sale antes de trabajar (como el ``X_ACK`` de una operación) y el
trabajo corre en el programador de la madre, uno a la vez y fuera del hilo de
red. Una orden repetida (mismo folio) no se vuelve a ejecutar: se reenvía el
resultado que ya se dio.
"""

from collections import OrderedDict

from comun import codigos, foliado, hashes, mensajes
from comun.microservicios import Paquete
from madre.almacen import INYECCION

ALTA = "alta"
CAMBIO = "cambio"
BAJA = "baja"
RETIRO = "retiro"
ACCIONES = {codigos.GEN_INYECTA: (ALTA, CAMBIO), codigos.GEN_BAJA: (BAJA,),
            codigos.CEL_RETIRO: (RETIRO,)}
RECORDAR = 200


class Ordenes:
    def __init__(self, madre):
        self.madre = madre
        self.atendidas = 0
        self._resultados: OrderedDict[str, dict | None] = OrderedDict()  # orden -> GEN_RES

    def rx(self, m: dict) -> None:
        """Una ``GEN_INYECTA``, ``GEN_BAJA`` o ``CEL_RETIRO`` (para mí o no)."""
        madre, cuerpo, codigo = self.madre, m["cuerpo"], m["codigo"]
        orden, gestor = cuerpo.get("orden"), m.get("nombre_origen") or hashes.corto(m["origen"])
        if cuerpo.get("destino") != madre.hash:
            madre._ignorar(m, f"orden {orden} para otra célula")
            return
        accion = cuerpo.get("accion") or ACCIONES[codigo][0]
        if m.get("tipo_origen") != mensajes.GESTOR:
            madre.log("DROP", f"{codigo} de {gestor}: solo un gestor da órdenes")
            return
        if not foliado.es_folio_admin(orden, foliado.ORDEN) or accion not in ACCIONES[codigo]:
            madre.log("DROP", f"{codigo} de {gestor} mal formada (orden {orden!r}, "
                              f"acción {accion!r})")
            return

        madre.publicar(codigos.GEN_ACK, {"orden": orden, "destino": madre.hash, "accion": accion})
        if orden in self._resultados:  # repetida: no se ejecuta dos veces
            anterior = self._resultados[orden]
            madre.log("ORDEN", f"{orden} repetida ({codigo} de {gestor}): reenvío el resultado")
            if anterior is not None:
                madre.publicar(codigos.GEN_RES, anterior)
            return
        self._resultados[orden] = None
        while len(self._resultados) > RECORDAR:
            self._resultados.popitem(last=False)
        madre.log("ORDEN", f"{orden} de {gestor}: {self._describir(codigo, accion, cuerpo)} · "
                           f"GEN_ACK enviado")
        madre.programador.en(0, lambda: self._ejecutar(codigo, accion, orden, gestor, cuerpo))

    @staticmethod
    def _describir(codigo: str, accion: str, cuerpo: dict) -> str:
        if codigo == codigos.GEN_INYECTA:
            m = cuerpo.get("manifiesto")
            gen = (f"{m.get('codigo')}@{m.get('version')}" if isinstance(m, dict)
                   else "sin manifiesto")
            return f"{accion} de {gen}"
        if codigo == codigos.GEN_BAJA:
            return f"baja de {cuerpo.get('codigo')}"
        return "retiro de la célula"

    def _ejecutar(self, codigo: str, accion: str, orden: str, gestor: str, cuerpo: dict) -> None:
        madre = self.madre
        if codigo == codigos.GEN_INYECTA:
            try:
                r = madre.instalar(Paquete.de_mensaje(cuerpo), f"{INYECCION} {gestor}")
            except ValueError as e:
                self._responder(orden, accion, ok=False, detalle=str(e), gen=None)
                return
            self._responder(orden, accion, ok=r.ok, detalle=r.detalle, gen=r.gen, ms=r.ms,
                            ruta=r.ruta, sustituyo=r.sustituyo)
        elif codigo == codigos.GEN_BAJA:
            cod = cuerpo.get("codigo")
            if not codigos.es_gen(cod):
                self._responder(orden, accion, ok=False, detalle=f"código inválido: {cod!r}",
                                gen=None)
                return
            r = madre.dar_de_baja(cod)
            self._responder(orden, accion, ok=r.ok, detalle=r.detalle, gen=r.gen)
        else:  # CEL_RETIRO
            self._responder(orden, accion, ok=True, gen=None,
                            detalle="me retiro: CEL_ADIOS (no es una pérdida, nadie me regenera)")
            madre.detener(motivo=f"retiro ordenado por {gestor} ({orden})")

    def _responder(self, orden: str, accion: str, *, ok: bool, detalle: str, gen: str | None,
                   ms: int = 0, ruta: str | None = None, sustituyo: str | None = None) -> None:
        madre = self.madre
        cuerpo = {"orden": orden, "destino": madre.hash, "accion": accion, "ok": ok,
                  "detalle": detalle, "gen": gen, "ms": ms, "ruta": ruta, "sustituyo": sustituyo,
                  "genes": madre.genoma.resumen()}
        self._resultados[orden] = cuerpo
        self.atendidas += 1
        madre.publicar(codigos.GEN_RES, cuerpo)
        madre.log("GEN_RES", f"{orden}: {'ok' if ok else 'RECHAZADA'} · {gen or accion} · "
                             f"{detalle}")
