"""Gestor de microservicios: una célula más del Campo de Datos (PLAN §4).

Se conecta a un nodo como cualquier GUI (entidad ``GESTOR``) y hace tres cosas:

1. **Catálogo** — su base de datos SQLite (``gestor/bd.py``) con los programas
   de ``microservicios/``.
2. **Topología** — la reconstruye con los latidos que oye (``gestor/topologia.py``)
   y la dibuja (``gestor/diagrama.py``). Puede pedir una foto inmediata con
   ``TOPO_REQ``: contestan todas las células.
3. **Órdenes** — cuando el administrador pulsa un botón, publica
   ``GEN_INYECTA`` / ``GEN_BAJA`` / ``CEL_RETIRO`` con un folio de orden
   (``O-<hash8>-<n>``) y el ``destino``; la madre contesta ``GEN_ACK`` al
   recibirla y ``GEN_RES`` con el resultado. Sin ``GEN_ACK`` en
   ``GEN_ACK_TIMEOUT`` s la orden queda "sin respuesta" (la célula murió o no
   existe). Todo queda en el historial de su BD.

Además, como tiene los programas, **entrega** genes a la madre que los pida
(``GEN_PIDE`` → ``GEN_ENTREGA``), igual que lo haría otra madre.

**No es un orquestador** (§4.1): nunca decide solo, no está en el camino de las
operaciones (no acusa ni responde ``X_REQ``), no guarda la topología "oficial"
y la madre puede rechazar lo que le manda. Puede haber uno por nodo, o ninguno:
cerrar el gestor no cambia nada del funcionamiento normal.

4. **Regeneración (solo la muestra)** — ``CLON_AVISO``, el primer latido del
   reemplazo, las entregas de genes y ``CLON_LISTO`` arman una línea de tiempo
   (caída → clonador → conectada → genes copiados → nivel ok). Quien decide y
   regenera son las madres (``madre/regeneracion.py``).

Sin Tkinter (regla del proyecto): la ventana lee ``topologia``, ``ordenes`` y
la cola ``eventos``: ``("log", (hora, evento, texto))``, ``("orden", fila)``,
``("regeneracion", (hora, evento, texto))``, ``("destello", (hash, tipo))``,
``("catalogo", lista)`` y ``("conexion", dict)``.
"""

import itertools
import re
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from pathlib import Path

from celula.base import Celula
from comun import codigos, config, foliado, hashes, mensajes, microservicios
from comun.bitacora import Bitacora, hora
from comun.pedidos import Proveedor
from comun.programador import Programador
from gestor.bd import BaseDatos
from gestor.topologia import CAIDA, VIVA, CelulaVista, Foto, Topologia
from madre.ordenes import ALTA, BAJA, CAMBIO, RETIRO

# Estados de una orden.
ENVIADA = "enviada"
RECIBIDA = "recibida"             # llegó el GEN_ACK de la célula destino
OK = "ok"
RECHAZADA = "rechazada"           # la madre decidió que no (p. ej. sha256 no coincide)
SIN_RESPUESTA = "sin respuesta"   # sin GEN_ACK: la célula no existe o murió
SIN_RESULTADO = "sin resultado"   # hubo GEN_ACK pero nunca GEN_RES
NO_SALIO = "no salió"             # el gestor no tenía conexión al Campo de Datos
TERMINADAS = (OK, RECHAZADA, SIN_RESPUESTA, SIN_RESULTADO, NO_SALIO)

MAX_ORDENES = 300


def natural(texto: str) -> list:
    """'Nodo 10' después de 'Nodo 9'; 'M2-N1' antes de 'M10-N1'."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", texto or "")]


@dataclass
class Orden:
    folio: str
    accion: str
    destino: str
    destino_nombre: str
    codigo: str | None = None
    version: str | None = None
    estado: str = ENVIADA
    detalle: str = ""
    ms: int | None = None              # lo que tardó la madre en el ciclo de vida
    ruta: str | None = None            # dónde quedó el gen en el disco de la madre
    t0: float = field(default_factory=time.monotonic)
    rtt_ms: int | None = None          # de publicar la orden al GEN_RES
    hora: str = field(default_factory=lambda: hora()[:8])

    @property
    def gen(self) -> str:
        if self.codigo and self.version:
            return microservicios.gen_id(self.codigo, self.version)
        return self.codigo or "—"

    def fila(self) -> dict:
        return {"folio": self.folio, "accion": self.accion, "destino": self.destino,
                "destino_nombre": self.destino_nombre, "gen": self.gen, "estado": self.estado,
                "detalle": self.detalle, "ms": self.ms, "rtt_ms": self.rtt_ms,
                "ruta": self.ruta, "hora": self.hora}


class Gestor(Celula):
    def __init__(self, nombre: str, nodo: str, *, bd: BaseDatos | Path | str | None = None,
                 banco: Path | None = None, bitacora: Bitacora | None = None, eventos=None):
        super().__init__(mensajes.GESTOR, nombre, nodo, None, bitacora=bitacora,
                         eventos=eventos)
        self.banco = banco or config.DIR_MICROSERVICIOS
        if not isinstance(bd, BaseDatos):
            bd = BaseDatos(bd or config.DIR_DATOS / "gestor" / f"{nombre}.sqlite3")
        self.bd = bd
        self.topologia = Topologia()
        self.programador = Programador(lambda e: self.log("ERROR", f"programador: {e!r}"),
                                       f"{nombre}-ordenes")
        self.proveedor = Proveedor(self, self.bd.buscar, self.programador)
        self._lock_ordenes = threading.Lock()
        self.ordenes: OrderedDict[str, Orden] = OrderedDict()
        self.linea_tiempo: deque = deque(maxlen=200)   # (hora, evento, texto) de regeneración
        self._entregas: set[tuple[str, str]] = set()   # (reemplazo, gen) ya en la línea
        self._listos: set[str] = set()                 # reemplazos que publicaron CLON_LISTO
        self._numeros = itertools.count(1)
        self._consultas = itertools.count(1)
        self._genes_en_bd = 0

    # ------------------------------------------------------------------ vida

    def iniciar(self) -> None:
        self.importar()  # al abrir, la BD se pone al día con la carpeta
        super().iniciar()

    def detener(self) -> None:
        super().detener()
        self.programador.detener()

    def cuerpo_latido(self) -> dict:
        return {"tipo": mensajes.GESTOR, "bd": self._genes_en_bd}

    def al_conectar(self, nodo: dict, como: str) -> None:
        # Sin enlace no oía latidos: eso no prueba que nadie muriera. Plazo nuevo.
        self.topologia.tregua()
        self._registrarme()
        self.anotar("CONEXION", f"conectado a {nodo['nombre']} ({nodo['endpoint']}); "
                                f"pido la topología a todos (TOPO_REQ)")
        self.consultar(silencioso=True)

    def al_latir(self) -> None:
        if not self.conectado:   # aislado no puedo saber quién murió (ver al_conectar)
            return
        self._registrarme()
        for evento, texto, h, tipo in self.topologia.caducar():
            self.anotar(evento, texto)
            c = self.topologia.celula(h) if tipo == mensajes.MADRE else None
            if c is None:
                continue
            with self._lock_ordenes:
                listo = c.hash in self._listos
            if c.reemplaza and not listo:
                # Igual que las madres: un reemplazo que muere antes de estar listo no es
                # otra pérdida; ellas reintentan la MISMA.
                self.topologia.olvidar(c.hash)
                self._regeneracion("CAIDA", f"{c.nombre} murió antes de estar listo: las "
                                            f"madres reintentan su pérdida")
            else:
                self._caida(c)

    def _caida(self, c: CelulaVista) -> None:
        self._regeneracion("CAIDA", f"{c.nombre} ({c.genes_texto()}) dejó de latir sin "
                                    f"CEL_ADIOS: es una pérdida", c.hash, "caida")

    def _registrarme(self) -> None:
        """Yo también salgo en mi diagrama (mi propio latido no me llega)."""
        cuerpo = self.latido_completo()
        if cuerpo and cuerpo.get("nodo"):
            self.topologia.celula_lat(self.hash, self.nombre, cuerpo)

    # ------------------------------------------------------------ catálogo

    def importar(self, carpeta: Path | None = None) -> list[str]:
        """Importa la carpeta de microservicios a la BD."""
        carpeta = carpeta or self.banco
        ids = self.bd.importar(carpeta)
        catalogo = self.bd.catalogo()
        self._genes_en_bd = len(catalogo)
        manipulados = [g["id"] for g in catalogo if not g["integro"]]
        aviso = f" · ✘ manipulado(s): {', '.join(manipulados)}" if manipulados else ""
        self.anotar("BD", f"importé {len(ids)} gen(es) de {carpeta.name}/ → "
                          f"{len(catalogo)} en la BD{aviso}")
        self._emitir("catalogo", catalogo)
        return ids

    def catalogo(self) -> list[dict]:
        return self.bd.catalogo()

    # -------------------------------------------------------------- órdenes

    def inyectar(self, destino: str, codigo: str, version: str, *,
                 accion: str = ALTA) -> Orden | str:
        """Alta (o cambio) de un gen en la madre ``destino``. Devuelve la orden o
        un texto con el motivo por el que no se pudo mandar."""
        paquete = self.bd.paquete(codigo, version)
        if paquete is None:
            return f"{microservicios.gen_id(codigo, version)} no está en la BD"
        return self._ordenar(codigos.GEN_INYECTA, accion, destino, codigo, version,
                             paquete.a_mensaje())

    def sustituir(self, destino: str, codigo: str, version: str) -> Orden | str:
        return self.inyectar(destino, codigo, version, accion=CAMBIO)

    def sustituir_en_todas(self, codigo: str, version: str) -> list[Orden | str]:
        """Cambio de versión en cada madre viva que tenga ``codigo`` con otra versión."""
        madres = [c for c in self.foto().madres() if any(
            g["codigo"] == codigo and g["version"] != version for g in c.genes)]
        return [self.sustituir(c.hash, codigo, version)
                for c in sorted(madres, key=lambda c: natural(c.nombre))]

    def baja(self, destino: str, codigo: str) -> Orden | str:
        return self._ordenar(codigos.GEN_BAJA, BAJA, destino, codigo, None, {"codigo": codigo})

    def retirar(self, destino: str) -> Orden | str:
        return self._ordenar(codigos.CEL_RETIRO, RETIRO, destino, None, None, {})

    def distribuir(self) -> tuple[list[Orden | str], list[str]]:
        """"Distribuir una de cada operación por nodo" (modo vacío → configuración
        del PDF en un clic). En cada nodo vivo, a cada operación que le falte se
        le asigna una madre vacía, en orden de nombre (``M1`` → SUM, ``M2`` →
        SUB…), con la versión base del catálogo. Lo que ya está no se toca."""
        foto = self.foto()
        versiones = {s: self.bd.version_base(s) for s in codigos.SERVICIOS}
        ordenes, notas = [], []
        nodos = sorted((n for n in foto.nodos.values() if n.estado == VIVA),
                       key=lambda n: natural(n.nombre))
        for nodo in nodos:
            madres = sorted(foto.madres(nodo.hash), key=lambda c: natural(c.nombre))
            # Lo que este nodo ya tiene o va a tener: madres vivas que responden (una muda
            # no cuenta), caídas que esperan su reemplazo y reemplazos naciendo aquí.
            en_espera = [c for c in foto.celulas.values()
                         if c.tipo == mensajes.MADRE and c.nodo == nodo.hash
                         and c.estado == CAIDA and c.reemplazada_en is None]
            naciendo = [c for c in foto.naciendo.values() if c.nodo == nodo.hash]
            presentes = {cod for c in (*madres, *en_espera, *naciendo) if not c.mudo
                         for cod in c.codigos}
            libres = [c for c in madres if c.vacia and not c.mudo]
            faltan = [s for s in codigos.SERVICIOS if s not in presentes and versiones[s]]
            for servicio, madre in zip(faltan, libres):
                ordenes.append(self.inyectar(madre.hash, servicio, versiones[servicio]))
            if len(faltan) > len(libres):
                notas.append(f"{nodo.nombre}: sin madre vacía para "
                             f"{', '.join(faltan[len(libres):])}")
        resumen = (f"Distribuir: {len(ordenes)} orden(es) en {len(nodos)} nodo(s)"
                   + (f" · {'; '.join(notas)}" if notas else ""))
        self.anotar("DISTRIBUIR", resumen)
        return ordenes, notas

    def publicar(self, codigo: str, cuerpo: dict, *, ttl: int | None = None) -> dict | None:
        m = super().publicar(codigo, cuerpo, ttl=ttl)
        if m is not None and codigo == codigos.GEN_ENTREGA:
            destino = self.topologia.celula(cuerpo.get("destino") or "")
            if destino is not None and destino.reemplaza:
                self._rx_entrega(m, destino)
        return m

    def consultar(self, *, silencioso: bool = False) -> None:
        """``TOPO_REQ``: todas las células contestan ya con su latido."""
        n = next(self._consultas)
        self.publicar(codigos.TOPO_REQ, {"consulta": n})
        if not silencioso:
            self.anotar("CONSULTA", f"TOPO_REQ #{n}: todas las células contestan con su "
                                    f"estado (TOPO_RES)")

    def _ordenar(self, codigo: str, accion: str, destino: str, cod: str | None,
                 version: str | None, extra: dict) -> Orden | str:
        celula = self.topologia.celula(destino)
        if celula is None or celula.tipo != mensajes.MADRE:
            return "el destino no es una célula madre conocida"
        folio = foliado.folio_admin(foliado.ORDEN, self.hash, next(self._numeros))
        orden = Orden(folio, accion, destino, celula.nombre, cod, version)
        with self._lock_ordenes:
            self.ordenes[folio] = orden
            while len(self.ordenes) > MAX_ORDENES:
                self.ordenes.popitem(last=False)
        self.bd.orden_nueva(folio, accion, destino, celula.nombre, cod, version, ENVIADA)
        enviado = self.publicar(codigo, {"orden": folio, "destino": destino, "accion": accion,
                                         **extra})
        if enviado is None:
            self._cerrar(orden, NO_SALIO, "sin conexión al Campo de Datos")
            return orden
        self.anotar("ORDEN", f"{folio} · {codigo} {accion} {orden.gen} → {celula.nombre} "
                             f"({hashes.corto(destino)}, en {celula.nodo_nombre or '?'})")
        self._emitir("orden", orden.fila())
        self._emitir("destello", (destino, "orden"))
        self.programador.en(config.GEN_ACK_TIMEOUT, lambda: self._vencer_ack(orden))
        return orden

    def _vencer_ack(self, orden: Orden) -> None:
        with self._lock_ordenes:   # revisar y apartar juntos: si no, pisa un GEN_RES
            if orden.estado != ENVIADA:
                return
            orden.estado = SIN_RESPUESTA
        self._cerrar(orden, SIN_RESPUESTA, f"sin GEN_ACK en {config.GEN_ACK_TIMEOUT:g} s: "
                                           f"{orden.destino_nombre} no contestó")

    def _vencer_res(self, orden: Orden) -> None:
        with self._lock_ordenes:
            if orden.estado != RECIBIDA:
                return
            orden.estado = SIN_RESULTADO
        self._cerrar(orden, SIN_RESULTADO, f"GEN_ACK sin GEN_RES en "
                                           f"{config.GEN_RES_TIMEOUT:g} s")

    def _cerrar(self, orden: Orden, estado: str, detalle: str) -> None:
        with self._lock_ordenes:
            orden.estado, orden.detalle = estado, detalle
        self.bd.orden_estado(orden.folio, estado, detalle, orden.ms, cerrada=True)
        evento = {OK: "ORDEN_OK", RECHAZADA: "RECHAZADA"}.get(estado, "SIN_RESPUESTA")
        self.anotar(evento, f"{orden.folio} · {orden.accion} {orden.gen} en "
                            f"{orden.destino_nombre}: {detalle}")
        self._emitir("orden", orden.fila())
        if estado in (OK, RECHAZADA):
            self._emitir("destello", (orden.destino, estado))

    # ------------------------------------------------------------ recepción

    def procesar(self, m: dict) -> None:
        codigo, cuerpo = m["codigo"], m["cuerpo"]
        if codigo == codigos.NODO_LAT:
            self.topologia.nodo_lat(m["origen"], cuerpo)
        elif codigo in (codigos.CEL_LAT, codigos.TOPO_RES):
            nacio = self.topologia.celula_lat(m["origen"], m.get("nombre_origen"), cuerpo)
            if nacio is not None:
                self._regeneracion("CONECTADA", f"{nacio.nombre} late en {nacio.nodo_nombre}: "
                                                f"nació vacía, copia sus genes…", m["origen"],
                                   "nace")
        elif codigo == codigos.CLON_AVISO:
            self._rx_aviso(m)
        elif codigo == codigos.CLON_LISTO:
            self._rx_listo(m)
        elif codigo == codigos.CEL_ADIOS:
            c = self.topologia.adios(m["origen"])
            if c is not None:
                self.anotar("ADIOS", f"{c.nombre} se despidió ({cuerpo.get('motivo')}): no es "
                                     f"una pérdida")
        elif codigo == codigos.GEN_ACK:
            self._rx_ack(m)
        elif codigo == codigos.GEN_RES:
            self._rx_res(m)
        elif codigo == codigos.GEN_PIDE:
            self._rx_pide(m)
        elif codigo == codigos.GEN_ENTREGA:
            self.proveedor.rx_entrega(m)
            destino = self.topologia.celula(cuerpo.get("destino") or "")
            if destino is not None and destino.reemplaza:
                self._rx_entrega(m, destino)
        elif codigo in (codigos.GEN_INYECTA, codigos.GEN_BAJA, codigos.CEL_RETIRO):
            self._orden_ajena(m)
        # Lo demás (operaciones X_*) no es asunto del gestor: no está en ese camino.

    def _mia(self, m: dict) -> Orden | None:
        """La orden de este GEN_ACK/GEN_RES, si es mía y lo manda su destino."""
        with self._lock_ordenes:
            orden = self.ordenes.get(m["cuerpo"].get("orden"))
        if orden is None or m["origen"] != orden.destino:
            return None
        return orden

    def _rx_ack(self, m: dict) -> None:
        orden = self._mia(m)
        if orden is None:
            return
        with self._lock_ordenes:
            if orden.estado != ENVIADA:
                return
            orden.estado = RECIBIDA
        self.anotar("GEN_ACK", f"{orden.folio}: {orden.destino_nombre} recibió la orden "
                               f"({(time.monotonic() - orden.t0) * 1000:.0f} ms)")
        self.bd.orden_estado(orden.folio, RECIBIDA)
        self._emitir("orden", orden.fila())
        self.programador.en(config.GEN_RES_TIMEOUT, lambda: self._vencer_res(orden))

    def _rx_res(self, m: dict) -> None:
        orden = self._mia(m)
        if orden is None:
            return
        cuerpo = m["cuerpo"]
        ok = cuerpo.get("ok") is True
        with self._lock_ordenes:
            tardia = orden.estado in (SIN_RESPUESTA, SIN_RESULTADO)
            if orden.estado in (OK, RECHAZADA):
                return
            orden.ms = cuerpo.get("ms") if isinstance(cuerpo.get("ms"), int) else None
            orden.ruta = cuerpo.get("ruta") if isinstance(cuerpo.get("ruta"), str) else None
            orden.rtt_ms = round((time.monotonic() - orden.t0) * 1000)
            orden.estado = OK if ok else RECHAZADA   # apartada: un vencimiento ya no la pisa
        detalle = str(cuerpo.get("detalle") or "")[:200]
        if cuerpo.get("sustituyo"):
            detalle = f"{cuerpo['sustituyo']} → {cuerpo.get('gen')} · {detalle}"
        if orden.ruta and ok:  # si la rechazó, la copia ya se borró de su disco
            detalle += f" · {orden.ruta}/"
        if orden.ms is not None:
            detalle += f" · {orden.ms} ms en la madre"
        if tardia:
            detalle += " · (llegó tarde)"
        self._cerrar(orden, OK if ok else RECHAZADA, detalle)

    def _rx_pide(self, m: dict) -> None:
        cuerpo = m["cuerpo"]
        gen = f"{cuerpo.get('codigo')}@{cuerpo.get('version')}"
        tengo = self.bd.buscar(cuerpo.get("codigo"), cuerpo.get("version"), cuerpo.get("sha")) \
            if isinstance(cuerpo.get("codigo"), str) and isinstance(cuerpo.get("version"),
                                                                     str) else None
        self.anotar("GEN_PIDE", f"{m.get('nombre_origen')} pide {gen} "
                                f"({cuerpo.get('pedido')}): "
                                f"{'lo tengo en la BD' if tengo else 'no lo tengo'}")
        self.proveedor.rx_pide(m)

    # ------------------------------------------------------- regeneración
    # El gestor NO regenera (eso lo deciden las madres): solo lo muestra.

    def _rx_aviso(self, m: dict) -> None:
        cuerpo = m["cuerpo"]
        caida = self.topologia.marcar_caida(cuerpo.get("reemplaza") or "")
        if caida is not None:  # las madres lo notaron antes que yo
            self._caida(caida)
        c = self.topologia.aviso_clon(cuerpo, m.get("nombre_origen") or "?")
        if c is None:
            return
        genes = c.genes_texto() if c.genes else "ningún gen (era vacía)"
        self._regeneracion("CLON_AVISO", f"{m.get('nombre_origen')} (rango "
                                         f"{cuerpo.get('rango', '?')}) regenera a "
                                         f"{cuerpo.get('perdida')} → {c.nombre} en "
                                         f"{c.nodo_nombre}; copiará {genes} "
                                         f"(intento {cuerpo.get('intento', 1)})")

    def _rx_entrega(self, m: dict, destino: CelulaVista) -> None:
        """Una entrega de gen a un reemplazo. Si dos proveedores coinciden (sus esperas
        escalonadas se cruzaron en la malla), el reemplazo usa la primera: en la línea
        de tiempo solo va esa; la otra, a la bitácora."""
        gen = m["cuerpo"].get("gen")
        texto = (f"{m.get('nombre_origen')} entrega {gen} a {destino.nombre} (de su disco, "
                 f"por el Campo de Datos)")
        with self._lock_ordenes:
            primera = (destino.hash, gen) not in self._entregas
            self._entregas.add((destino.hash, gen))
        if primera:
            self._regeneracion("ENTREGA", texto)
        else:
            self.anotar("ENTREGA", f"{texto}; sobra: el reemplazo ya usó la primera")

    def _rx_listo(self, m: dict) -> None:
        cuerpo = m["cuerpo"]
        fuentes = cuerpo.get("fuentes") if isinstance(cuerpo.get("fuentes"), dict) else {}
        faltan = cuerpo.get("faltan") if isinstance(cuerpo.get("faltan"), list) else []
        copiados = ", ".join(f"{g} de {de}" for g, de in fuentes.items()) or "sin genes"
        with self._lock_ordenes:
            self._listos.add(m["origen"])
        perdida = self.topologia.celula(cuerpo.get("reemplaza") or "")
        self._regeneracion("CLON_LISTO", f"{m.get('nombre_origen')} reemplaza a "
                                         f"{perdida.nombre if perdida else 'la perdida'}: "
                                         f"{copiados} (disco → memoria)"
                                         + (f" · faltan {', '.join(map(str, faltan))}"
                                            if faltan else ""), m["origen"], "ok")
        pendientes = self.topologia.pendientes()
        if pendientes:
            nombres = ", ".join(c.nombre for c in pendientes)
            self._regeneracion("EN_ESPERA", f"gradual: falta(n) {nombres}; va una a la vez")
        else:
            disp = " · ".join(f"{s} {n}" for s, n in self.foto().disponibilidad().items())
            self._regeneracion("NIVEL_OK", f"nivel recuperado ({disp}): las madres dejan de "
                                           f"clonar")

    def _regeneracion(self, evento: str, texto: str, h: str | None = None,
                      destello: str | None = None) -> None:
        """Una línea de la línea de tiempo de regeneración (y de la bitácora)."""
        self.log(evento, texto)
        linea = (hora(), evento, texto)
        with self._lock_ordenes:
            self.linea_tiempo.append(linea)
        self._emitir("regeneracion", linea)
        if h and destello:
            self._emitir("destello", (h, destello))

    def _orden_ajena(self, m: dict) -> None:
        """Otro gestor mandó una orden: se muestra (todos ven todo) y nada más."""
        cuerpo = m["cuerpo"]
        destino = self.topologia.celula(cuerpo.get("destino") or "")
        self.anotar("OTRO_GESTOR", f"{m.get('nombre_origen')} ordenó {m['codigo']} "
                                   f"{cuerpo.get('accion') or ''} a "
                                   f"{destino.nombre if destino else '?'} ({cuerpo.get('orden')})")

    # ------------------------------------------------------------ consultas

    def foto(self) -> Foto:
        return self.topologia.instantanea()

    def filas_ordenes(self) -> list[dict]:
        with self._lock_ordenes:
            return [o.fila() for o in self.ordenes.values()]

    def celula(self, h: str) -> CelulaVista | None:
        return self.topologia.celula(h)

    # ------------------------------------------------------------- utilidades

    def anotar(self, evento: str, texto: str) -> None:
        """Bitácora + la pestaña de bitácora de la ventana."""
        self.log(evento, texto)
        self._emitir("log", (hora(), evento, texto))
