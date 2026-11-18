"""Rondas de atención: acuse inmediato, elección HRW, relevo escalonado y foliado.

Es el motor del segundo parcial, ahora para **cualquier gen activo** y con el
**protocolo de foliado** (``comun/foliado.py``). Una ronda se identifica por
``(código, folio, intento)``; una madre con varios genes lleva rondas de varios
códigos en la misma cola (es una sola célula, con un solo trabajador).

Reglas de atención (plan §5.3): la madre atiende un mensaje solo si (1) el
código es de un gen que tiene activo (eso lo filtra ``nucleo.py``); (2) en el
``X_REQ``, la huella es de quien publicó y el sello recalculado coincide (si
no: ``DROP huella inválida``); (3) la ronda no está terminada; (4) un
``X_FIN`` cierra todas las rondas del folio.

Flujo de una ronda en cada madre que tiene el gen:

1. **RX X_REQ** → valida la huella y publica ``X_ACK`` de inmediato (en el
   hilo lector, antes de encolar; el retardo artificial nunca lo atrasa) con
   su paso ``ACK`` en el rastro. La ronda **fija el gen con el que acusó**
   (``SUM@1.0``) y lo usa hasta el final: si a media ronda se sustituye el
   gen, no se mezclan versiones. Las rondas anteriores del mismo folio quedan
   **superadas**; un REQ que llega después de uno posterior (desorden en la
   malla) también.
2. **RX X_ACK** de otra madre → la suma a ``acusadores``. Si la ronda aún no
   existe, crea un **esqueleto** (el acuse puede llegar antes que el REQ).
3. **RX X_RES** del intento k → marca **resueltas** las rondas con intento ≤ k.
4. **RX X_FIN** → el evento terminó (resuelto o fallido): se **cierran** todas
   las rondas del folio y cualquier copia tardía del REQ ya no se acusa.
5. **Trabajador**: espera ``VENTANA_ELECCION``, ordena a los acusadores con
   HRW y ve su posición r: r = 0 → TITULAR (calcula y responde); r > 0 →
   RESPALDO: si a los ``r·RELEVO`` s nadie respondió, toma el RELEVO. Antes de
   publicar revisa otra vez: si ya hubo respuesta, la suya se SUPRIME. El
   ``X_RES`` lleva en el rastro los acuses que vio y su paso ``RES``.

Todas calculan el mismo ranking sobre el mismo conjunto: una sola respuesta,
sin coordinador ni mensajes extra.
"""

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Protocol

from comun import codigos, config, foliado, formato, hashes
from comun.programador import Programador
from madre import genes as genes_mod
from madre.genes import Gen

# Estados de una ronda.
ESQUELETO = "esqueleto"   # solo se conocen acuses; el REQ no ha llegado
EN_COLA = "en_cola"
TITULAR = "titular"
RESPALDO = "respaldo"
RESUELTA = "resuelta"
SUPERADA = "superada"
CERRADA = "cerrada"       # la GUI publicó X_FIN: el evento terminó
TERMINADAS = (RESUELTA, SUPERADA, CERRADA)

Clave = tuple[str, str, int]   # (código, folio, intento)


class Anfitrion(Protocol):
    """Lo que el motor necesita de la célula madre que lo aloja."""

    hash: str
    nombre: str
    retardo_ms: int
    _parar: threading.Event

    def publicar(self, codigo: str, cuerpo: dict) -> dict | None: ...
    def log(self, evento: str, texto: str, *, consola: bool = True) -> None: ...


@dataclass
class Ronda:
    codigo: str
    folio: str
    intento: int
    creada: float = field(default_factory=time.monotonic)
    estado: str = ESQUELETO
    tiene_req: bool = False
    a: object = None
    b: object = None
    huella: dict | None = None        # la del REQ (ya validada)
    gen: Gen | None = None            # con el que acusó; se suelta al terminar
    gen_id: str = "?"
    id_solicitud: str | None = None
    t_rx: float | None = None
    gui: str = "?"
    acusadores: set = field(default_factory=set)
    nombres: dict = field(default_factory=dict)  # hash -> nombre, en orden de llegada

    @property
    def clave(self) -> Clave:
        return self.codigo, self.folio, self.intento

    def terminar(self, estado: str) -> None:
        """Pasa a un estado final y suelta el gen (para que pueda liberarse)."""
        self.estado = estado
        self.gen = None

    def __str__(self) -> str:
        return f"{self.codigo} {self.folio} · intento {self.intento}"


class Rondas:
    def __init__(self, madre: Anfitrion):
        self.madre = madre
        self._lock = threading.RLock()
        self.tabla: dict[Clave, Ronda] = {}
        self._resueltas: dict[tuple[str, str], tuple[int, float]] = {}  # (cód, folio) -> (k, t)
        self._finalizados: dict[tuple[str, str], float] = {}           # (cód, folio) -> t
        self._cola: queue.Queue = queue.Queue()
        self.atendidas = 0
        self.invalidas = 0   # REQ descartados por huella inválida
        self._programador: Programador | None = None

    # ------------------------------------------------------------------ vida

    def iniciar(self) -> None:
        self._programador = Programador(lambda e: self.madre.log("ERROR", f"programador: {e!r}"),
                                        f"{self.madre.nombre}-respaldos")
        threading.Thread(target=self._trabajar, name=f"{self.madre.nombre}-trabajador",
                         daemon=True).start()

    def detener(self) -> None:
        if self._programador:
            self._programador.detener()
        self._cola.put(None)

    def en_cola(self) -> int:
        return self._cola.qsize()

    def conoce(self, codigo: str) -> bool:
        with self._lock:
            return any(c == codigo for c, _, _ in self.tabla)

    def purgar(self) -> None:
        limite = time.monotonic() - config.RONDAS_VIGENCIA
        with self._lock:
            for clave in [c for c, r in self.tabla.items() if r.creada < limite]:
                del self.tabla[clave]
            for f in [f for f, (_, t) in self._resueltas.items() if t < limite]:
                del self._resueltas[f]
            for f in [f for f, t in self._finalizados.items() if t < limite]:
                del self._finalizados[f]

    # ------------------------------------------------------------ recepción

    def _clave(self, m: dict, codigo: str) -> Clave | None:
        cuerpo = m["cuerpo"]
        folio, intento = cuerpo.get("folio"), cuerpo.get("intento")
        if (not foliado.es_folio(folio) or not isinstance(intento, int)
                or isinstance(intento, bool) or intento < 1):
            self.madre.log("DROP", f"{m['codigo']} {hashes.corto(m['id'])} sin folio o intento "
                                   f"válidos")
            return None
        return codigo, folio, intento

    def _ronda(self, clave: Clave) -> Ronda:
        """La ronda de la clave; la crea (esqueleto) si no existe. Con el lock tomado."""
        ronda = self.tabla.get(clave)
        if ronda is None:
            ronda = Ronda(*clave)
            k, _ = self._resueltas.get(clave[:2], (0, 0))
            if clave[:2] in self._finalizados:
                ronda.estado = CERRADA   # el evento ya terminó
            elif clave[2] <= k:
                ronda.estado = RESUELTA  # ya se respondió esta ronda (o una posterior)
            self.tabla[clave] = ronda
        return ronda

    def rx_req(self, m: dict, codigo: str, gen: Gen) -> None:
        clave = self._clave(m, codigo)
        if clave is None:
            return
        madre, cuerpo = self.madre, m["cuerpo"]
        cod_req = codigos.codigo(codigo, codigos.REQ)
        gui = m.get("nombre_origen") or "?"
        a, b, huella = cuerpo.get("a"), cuerpo.get("b"), cuerpo.get("huella")
        motivo = foliado.validar(huella, origen=m["origen"], folio_=clave[1], codigo=codigo,
                                 a=a, b=b)
        if motivo:
            self.invalidas += 1
            madre.log("DROP", f"{cod_req} {clave[1]} de {gui}: huella inválida ({motivo}); "
                              f"no se acusa")
            return
        with self._lock:
            ronda = self._ronda(clave)
            repetido = ronda.tiene_req
            terminada = not repetido and ronda.estado in TERMINADAS
            if not repetido and not terminada:
                ronda.tiene_req = True
                ronda.a, ronda.b, ronda.huella = a, b, huella
                ronda.gen, ronda.gen_id = gen, gen.id
                ronda.id_solicitud = m["id"]
                ronda.t_rx = time.monotonic()
                ronda.gui = gui
                ronda.acusadores.add(madre.hash)
                ronda.nombres[madre.hash] = madre.nombre
                ronda.estado = EN_COLA
                # Desorden en la malla: si ya conozco un intento posterior, este REQ
                # llegó tarde. La GUI ya no lo espera; responderlo sería un RES de más.
                posterior = max((k for c, f, k in self.tabla
                                 if (c, f) == clave[:2] and k > clave[2]), default=0)
                if posterior:
                    ronda.terminar(SUPERADA)
                superadas = []
                for (c, f, k), vieja in self.tabla.items():
                    if (c, f) == clave[:2] and k < clave[2] and vieja.estado not in TERMINADAS:
                        vieja.terminar(SUPERADA)
                        superadas.append(k)
        if repetido:
            madre.log("RX", f"{cod_req} {ronda} repetido; ya estaba en mi cola")
            return
        if terminada:
            madre.log("RX", f"{cod_req} {ronda} de {gui}: ya está {ronda.estado}; no se acusa")
            return

        texto = formato.operacion(ronda.a, codigo, ronda.b)
        madre.log("RX", f"{cod_req} {ronda} de {gui}: {texto} con {gen.id} · sello "
                        f"{hashes.corto(huella['sello'])} ✓ (solicitud "
                        f"{hashes.corto(ronda.id_solicitud)})")
        if ronda.estado == SUPERADA:
            madre.log("SUPERADA", f"{ronda} llegó después del intento {posterior}; "
                                  f"no se acusa ni se encola")
            return
        # Acuse INMEDIATO, antes de encolar: prueba de recepción, no de cálculo.
        en_cola = self._cola.qsize()
        cod_ack = codigos.codigo(codigo, codigos.ACK)
        ack = madre.publicar(cod_ack, {
            "folio": clave[1], "intento": clave[2], "id_solicitud": ronda.id_solicitud,
            "en_cola": en_cola, "gen": gen.id,
            "huella": foliado.con_paso(huella, madre.hash, madre.nombre, foliado.ACK)})
        if ack is not None:
            madre.log("ACUSE", f"{cod_ack} {ronda} → {gui} con {gen.id} "
                               f"(acuse {hashes.corto(ack['id'])})")
        for k in superadas:
            madre.log("SUPERADA", f"{codigo} {clave[1]} · intento {k}: la GUI ya va en el "
                                  f"intento {clave[2]}")
        self._cola.put(("eleccion", clave))
        madre.log("COLA", f"{ronda} encolada ({en_cola} antes en espera)")

    def rx_ack(self, m: dict, codigo: str, crear: bool) -> None:
        """``crear``: si la ronda no existe, ¿se crea un esqueleto? (solo si tengo el gen)."""
        clave = self._clave(m, codigo)
        if clave is None:
            return
        with self._lock:
            if clave not in self.tabla and not crear:
                return
            ronda = self._ronda(clave)
            ronda.acusadores.add(m["origen"])
            ronda.nombres[m["origen"]] = m.get("nombre_origen") or hashes.corto(m["origen"])
            esqueleto = not ronda.tiene_req
            n = len(ronda.acusadores)
        nota = " (aún sin REQ: ronda esqueleto)" if esqueleto else ""
        self.madre.log("RX", f"{m['codigo']} {ronda} de {m.get('nombre_origen')} "
                             f"→ {n} acusador(es){nota}")

    def rx_res(self, m: dict, codigo: str) -> None:
        clave = self._clave(m, codigo)
        if clave is None:
            return
        n = self._marcar_resueltas(clave)
        self.madre.log("RX", f"{m['codigo']} {clave[1]} · intento {clave[2]} "
                             f"de {m.get('nombre_origen')} ({m['cuerpo'].get('rol')}); "
                             f"{n} ronda(s) mía(s) quedan resueltas")

    def rx_fin(self, m: dict, codigo: str) -> None:
        """``X_FIN``: la GUI cerró el evento. Se cierran todas las rondas del folio."""
        folio, estado = m["cuerpo"].get("folio"), m["cuerpo"].get("estado")
        if not foliado.es_folio(folio):
            self.madre.log("DROP", f"{m['codigo']} {hashes.corto(m['id'])} sin folio válido")
            return
        cerradas = 0
        with self._lock:
            self._finalizados[(codigo, folio)] = time.monotonic()
            for (c, f, _), ronda in self.tabla.items():
                if (c, f) == (codigo, folio) and ronda.estado not in TERMINADAS:
                    ronda.terminar(CERRADA)
                    cerradas += 1
        nota = f"cerré {cerradas} ronda(s) abierta(s)" if cerradas else "nada abierto"
        self.madre.log("FIN", f"{m['codigo']} {codigo} {folio} {estado} por "
                              f"{m.get('nombre_origen')}: evento finalizado; {nota}")

    def _marcar_resueltas(self, clave: Clave) -> int:
        """Una respuesta a la ronda k resuelve las rondas ≤ k, nunca las posteriores."""
        codigo, folio, k = clave
        n = 0
        with self._lock:
            previo, _ = self._resueltas.get((codigo, folio), (0, 0))
            self._resueltas[(codigo, folio)] = (max(previo, k), time.monotonic())
            for (c, f, i), ronda in self.tabla.items():
                if (c, f) == (codigo, folio) and i <= k and ronda.estado not in TERMINADAS:
                    ronda.terminar(RESUELTA)
                    n += 1
        return n

    # ------------------------------------------------------------ trabajador

    def _trabajar(self) -> None:
        while True:
            item = self._cola.get()
            if item is None:
                return
            try:
                if item[0] == "eleccion":
                    self._elegir(item[1])
                else:
                    _, clave, r = item
                    self._ejecutar(clave, f"relevo {r}")
            except Exception as e:
                self.madre.log("ERROR", f"trabajador: {e!r}")

    def _elegir(self, clave: Clave) -> None:
        with self._lock:
            ronda = self.tabla.get(clave)
            if ronda is None:
                return
            t_rx = ronda.t_rx
        espera = t_rx + config.VENTANA_ELECCION - time.monotonic()
        if espera > 0 and self.madre._parar.wait(espera):
            return

        with self._lock:
            if ronda.estado in TERMINADAS:
                estado, r = ronda.estado, None
            else:
                orden = hashes.ranking(ronda.acusadores, clave[1], clave[2])
                r = orden.index(self.madre.hash)
                ronda.estado = TITULAR if r == 0 else RESPALDO
                titular = ronda.nombres.get(orden[0], hashes.corto(orden[0]))
                lista = ", ".join(ronda.nombres.get(h, hashes.corto(h)) for h in orden)
        if r is None:
            self.madre.log("RETIRADA", f"{ronda} ya está {estado}; no participo")
            return
        if r == 0:
            self.madre.log("TITULAR", f"{ronda} · rank 0 de {len(orden)} [{lista}]")
            self._ejecutar(clave, "titular")
            return
        plazo = t_rx + config.VENTANA_ELECCION + r * config.RELEVO
        self.madre.log("RESPALDO", f"{ronda} · rank {r} de {len(orden)} [{lista}]; titular "
                                   f"{titular}; relevo si nadie responde en "
                                   f"{r * config.RELEVO:.1f} s")
        self._programador.agendar(plazo, lambda: self._revisar_respaldo(clave, r))

    def _revisar_respaldo(self, clave: Clave, r: int) -> None:
        with self._lock:
            ronda = self.tabla.get(clave)
            if ronda is None:
                return
            estado = ronda.estado
        if estado in TERMINADAS:
            self.madre.log("LIBERADO", f"{ronda} ya está {estado}; respaldo {r} liberado")
            return
        self.madre.log("RELEVO", f"{ronda}: nadie respondió; tomo el relevo {r}")
        self._cola.put(("relevo", clave, r))

    def _ejecutar(self, clave: Clave, rol: str) -> None:
        with self._lock:
            ronda = self.tabla.get(clave)
            gen = ronda.gen if ronda else None
        if ronda is None or gen is None:
            return
        retardo = self.madre.retardo_ms
        if retardo and self.madre._parar.wait(retardo / 1000):
            return
        resultado, error = genes_mod.ejecutar(gen, ronda.a, ronda.b)
        del gen

        # Doble revisión: mientras calculaba pudo llegar otra respuesta, un reintento o el FIN.
        with self._lock:
            estado = ronda.estado
            acuses = [(h, n, foliado.ACK) for h, n in ronda.nombres.items()
                      if h in ronda.acusadores]
        if estado in TERMINADAS:
            self.madre.log("SUPRIMIDA", f"{ronda} ya está {estado}; no envío mi respuesta ({rol})")
            return
        self._marcar_resueltas(clave)
        ms = round((time.monotonic() - ronda.t_rx) * 1000)
        cod_res = codigos.codigo(clave[0], codigos.RES)
        huella = foliado.con_pasos(ronda.huella, [*acuses, (self.madre.hash, self.madre.nombre,
                                                            foliado.RES)])
        res = self.madre.publicar(cod_res, {
            "folio": clave[1], "intento": clave[2], "id_solicitud": ronda.id_solicitud,
            "resultado": resultado, "error": error, "rol": rol, "ms": ms, "gen": ronda.gen_id,
            "huella": huella,
        })
        if res is None:
            return  # ya se registró como PERDIDO; la GUI reintentará
        self.atendidas += 1
        texto = formato.operacion(ronda.a, clave[0], ronda.b, resultado, error)
        self.madre.log("RES", f"{cod_res} {ronda} · {texto} · {rol} · {ronda.gen_id} · solicitud "
                              f"{hashes.corto(ronda.id_solicitud)} ↔ respuesta "
                              f"{hashes.corto(res['id'])} · {ms} ms")
