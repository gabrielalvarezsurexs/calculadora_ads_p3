"""Célula GUI, sin Tkinter: solicita con folio, sigue cada evento por sus
cuatro fases, cuenta acuses, reintenta y decide qué operadores están
disponibles. La ventana (``interfaz/gui.py``) solo muestra lo que este módulo
empuja a ``eventos``.

Foliado (plan §5; definiciones en ``comun/foliado.py``):

* Cada solicitud recibe un **folio** propio (``F-<hash8>-<n>``) y una
  **huella** con su sello. La operación se **registra antes de publicar**: un
  acuse muy rápido podría llegar antes de que exista. Puede haber **varias
  operaciones en vuelo** a la vez: el folio las distingue.
* **Evento** = la vida de un folio: INICIO (``X_REQ``) → CONFIRMADO (mínimo de
  ``X_ACK`` del intento vigente) → PROCESADO (``X_RES`` aceptado) →
  FINALIZADO (``X_FIN`` publicado, con acuses, ausentes y el rastro completo).
* **Esperados / ausentes**: al iniciar cada intento se anotan las madres vivas
  con el gen. Al cerrar la ventana de confirmación (``VENTANA_ACUSES``, o
  antes si ya acusaron todas) las que no acusaron quedan como **AUSENTES**. Con
  el mínimo alcanzado el evento sigue (**tolerancia a fallas**); sin él,
  reintento con el mismo folio; agotados los intentos, FALLIDA.
* El ``X_FIN`` sale cuando hay desenlace (respuesta aceptada o FALLIDA) **y**
  la ventana de confirmación ya cerró, para que lleve la lista de ausentes.
* **Quórum por intento**: un acuse del intento 1 no cuenta para el 2 (la
  célula que acusó el 1 pudo morir después). El ``X_RES`` se acepta solo con
  el evento confirmado; si llega antes, se retiene.
* **Solo lo mío**: un ``X_ACK``/``X_RES`` se muestra si su folio es mío, su
  huella dice que el origen soy yo y su sello es el que generé. Todo lo demás
  (REQ y FIN de otras GUIs, respuestas a folios ajenos, sellos alterados) suma
  al contador **ajenas** y va a la bitácora como IGNORA. Los mensajes de sistema
  (latidos de nodo, órdenes del gestor, pedidos de genes) no son operaciones de
  nadie y no cuentan.
* **Disponibilidad por latidos**: cada ``CEL_LAT`` de una madre dice qué genes
  tiene activos; una madre cuenta para un servicio mientras lo anuncie (y cada
  ``X_ACK`` también prueba que vive). Si deja de anunciarlo o se despide
  (``CEL_ADIOS``) deja de contar al instante; si calla, caduca a los
  ``LATIDO_CADUCIDAD`` s. Con menos vivas que el mínimo, el operador se
  deshabilita.

Eventos que empuja a ``eventos`` (tuplas ``(tipo, datos)``):
``("log", (hora, evento, texto))`` para el mini log, ``("operacion", fila)``,
``("disponibilidad", dict)`` y ``("conexion", dict)``.
"""

import itertools
import math
import random
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from celula.base import FAILOVER, Celula
from comun import codigos, config, foliado, formato, hashes, mensajes
from comun.bitacora import Bitacora, hora

EN_VUELO = "en vuelo"
RESUELTA = "resuelta"
FALLIDA = "fallida"

HISTORIAL = 200        # operaciones propias que se recuerdan para clasificar respuestas tardías
MAX_EN_VUELO = 32      # más que suficiente para una ráfaga; evita inundar la malla por error
MINIMO_RANGO = (1, 16)


@dataclass
class Operacion:
    folio: str
    servicio: str
    a: float
    b: float
    huella: dict                                      # la del REQ: su sello vale todo el evento
    t0: float = field(default_factory=time.monotonic)
    intento: int = 1
    enviado_en: float = field(default_factory=time.monotonic)
    fase: str = foliado.INICIO
    esperados: dict = field(default_factory=dict)     # hash -> nombre (intento vigente)
    acusadores: dict = field(default_factory=dict)    # intento -> set(hash de célula)
    nombres: dict = field(default_factory=dict)       # hash -> nombre (para mostrar)
    solicitudes: dict = field(default_factory=dict)   # intento -> id del REQ
    t_confirmado: float | None = None
    ventana_cerrada: bool = False
    ausentes: list = field(default_factory=list)      # nombres
    retenido: dict | None = None                      # RES que llegó antes de confirmar
    estado: str = EN_VUELO
    resultado: float | None = None
    error: str | None = None
    rol: str | None = None
    respondio: str | None = None
    gen: str | None = None                            # 'SUM@1.0' de quien respondió
    id_solicitud: str | None = None                   # el REQ que atendió quien respondió
    id_respuesta: str | None = None
    ms: int | None = None
    motivo: str | None = None                         # por qué falló
    huella_final: dict | None = None                  # con el rastro completo (la del FIN)
    finalizado: bool = False

    @property
    def sello(self) -> str:
        return self.huella["sello"]

    def acuses(self) -> int:
        return len(self.acusadores.get(self.intento, ()))

    def acusaron(self) -> list[str]:
        return [self.nombres.get(h, hashes.corto(h)) for h in self.acusadores.get(self.intento, ())]


def _es_numero(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


class Interfaz(Celula):
    def __init__(self, nombre: str, nodo: str, *, acuses_min: int | None = None,
                 bitacora: Bitacora | None = None, eventos=None):
        super().__init__(mensajes.INTERFAZ, nombre, nodo, None,
                         bitacora=bitacora, eventos=eventos)
        minimo = acuses_min if acuses_min is not None else config.ACUSES_MIN_DEFECTO
        minimo = max(MINIMO_RANGO[0], min(MINIMO_RANGO[1], int(minimo)))
        self._lock_ops = threading.RLock()
        self._folios = itertools.count(1)
        self.acuses_min = {s: minimo for s in codigos.SERVICIOS}
        self.operaciones: OrderedDict[str, Operacion] = OrderedDict()   # folio -> operación
        # servicio -> {hash de célula: [último visto, nombre, nombre de su nodo]}
        self.vivas: dict[str, dict[str, list]] = {s: {} for s in codigos.SERVICIOS}
        self.habilitadas = {s: False for s in codigos.SERVICIOS}
        self.ajenas = 0          # mensajes que no eran para mí (contador visible)
        self._ultima_disp = None
        self._sin_enlace = False  # entre perder el nodo y terminar el failover

    # ------------------------------------------------------------------ vida

    def iniciar(self) -> None:
        super().iniciar()
        self._mini("ESPERANDO", "operadores deshabilitados: esperando latidos…")
        self._emitir_disponibilidad(forzar=True)
        threading.Thread(target=self._vigilar, name=f"{self.nombre}-reloj", daemon=True).start()

    def cuerpo_latido(self) -> dict:
        return {"tipo": mensajes.INTERFAZ}

    def al_conectar(self, nodo: dict, como: str) -> None:
        # Mientras estuve sin enlace no podía oír latidos: eso no prueba que nadie
        # haya muerto. Les doy un plazo completo desde ahora; las muertas de verdad
        # caducan después de LATIDO_CADUCIDAD.
        with self._lock_ops:
            ahora = time.monotonic()
            for celulas in self.vivas.values():
                for datos in celulas.values():
                    datos[0] = max(datos[0], ahora)
            self._sin_enlace = False
        if como == FAILOVER:
            self._mini("FAILOVER", f"→ {nodo['nombre']} ({nodo['endpoint']})", registrar=False)
        else:
            self._mini("CONEXION", f"conectada a {nodo['nombre']} ({nodo['endpoint']})",
                       registrar=False)

    def al_desconectar(self, motivo: str | None) -> None:
        with self._lock_ops:
            self._sin_enlace = True
        self._mini("DESCONEXION", f"se perdió el nodo ({motivo or 'sin motivo'}); buscando otro…",
                   registrar=False)

    # ------------------------------------------------------------ API (GUI)

    def solicitar(self, servicio: str, a, b) -> tuple[str | None, str]:
        """Inicia un evento: publica ``X_REQ``. Devuelve (folio, texto) o (None, motivo)."""
        if servicio not in codigos.SERVICIOS:
            return None, f"servicio desconocido: {servicio!r}"
        if not (_es_numero(a) and _es_numero(b)):
            return None, "los operandos deben ser números finitos"
        with self._lock_ops:
            if len(self.en_vuelo()) >= MAX_EN_VUELO:
                return None, f"ya hay {MAX_EN_VUELO} operaciones en vuelo"
            if not self.conectado:
                return None, "sin conexión al Campo de Datos"
            self._caducar(time.monotonic())
            self._evaluar()
            if not self.habilitadas[servicio]:
                n, m = len(self.vivas[servicio]), self.acuses_min[servicio]
                texto = f"{servicio} no disponible: {n} viva(s) < {m} mínima(s)"
                self._mini("NO_DISPONIBLE", texto)
                return None, texto
            op = self._registrar(servicio, a, b)  # registrar ANTES de publicar
            self._publicar_req(op)
        nombres = ", ".join(op.esperados.values())
        self._mini("EVENTO_INICIO", f"{op.folio} · {codigos.codigo(servicio, codigos.REQ)} "
                                    f"{formato.operacion(a, servicio, b)} · sello "
                                    f"{hashes.corto(op.sello)} · esperadas "
                                    f"{len(op.esperados)}: {nombres}")
        self._emitir_operacion(op)
        return op.folio, "enviada"

    def rafaga(self, n: int = 8, semilla: int | None = None) -> list[str]:
        """Varias operaciones en vuelo a la vez (escenario 2): ``n`` solicitudes
        seguidas, repartidas entre los operadores habilitados. Devuelve los folios."""
        rng = random.Random(semilla)
        servicios = [s for s in codigos.SERVICIOS if self.habilitadas[s]]
        folios = []
        for k in range(n if servicios else 0):
            folio, _ = self.solicitar(servicios[k % len(servicios)], rng.randint(1, 99),
                                      rng.randint(1, 99))
            if folio:
                folios.append(folio)
        return folios

    def ajustar_minimo(self, servicio: str, minimo: int) -> int:
        minimo = max(MINIMO_RANGO[0], min(MINIMO_RANGO[1], int(minimo)))
        with self._lock_ops:
            if self.acuses_min.get(servicio) == minimo:
                return minimo
            self.acuses_min[servicio] = minimo
            self._mini("MINIMO", f"{servicio}: mínimo de acuses = {minimo}")
            self._evaluar()
        return minimo

    def disponibilidad(self) -> dict:
        with self._lock_ops:
            return {s: {"vivas": len(self.vivas[s]), "minimo": self.acuses_min[s],
                        "habilitada": self.habilitadas[s],
                        "celulas": sorted((v[1], v[2] or "?") for v in self.vivas[s].values())}
                    for s in codigos.SERVICIOS}

    def operacion(self, folio: str) -> dict | None:
        with self._lock_ops:
            op = self.operaciones.get(folio)
            return self._fila(op) if op else None

    def en_vuelo(self) -> list[str]:
        """Folios que aún esperan respuesta."""
        with self._lock_ops:
            return [f for f, op in self.operaciones.items() if op.estado == EN_VUELO]

    # ------------------------------------------------------------ recepción

    def procesar(self, m: dict) -> None:
        codigo = m["codigo"]
        if codigo == codigos.CEL_LAT:
            self._rx_latido(m)
            return
        if codigo == codigos.CEL_ADIOS:
            self._rx_adios(m)
            return
        if codigo in codigos.SISTEMA:
            # Latidos de nodo, órdenes del gestor, pedidos de genes…: no son
            # operaciones de nadie, así que no cuentan como "ajenas".
            if codigo not in config.CODIGOS_SILENCIOSOS:
                self.log("IGNORA", f"{codigo} de {m.get('nombre_origen')}: mensaje de sistema",
                         consola=False)
            return
        partes = codigos.separar(codigo)
        if partes is None or partes[0] not in codigos.SERVICIOS:
            self._ignorar(m, "no es para una GUI")
            return
        servicio, tipo = partes
        if tipo in (codigos.REQ, codigos.FIN):
            self._ignorar(m, "evento de otra GUI")
            return
        cuerpo = m["cuerpo"]
        if tipo == codigos.ACK:  # un acuse también prueba que la célula vive
            self._marcar_viva(servicio, m["origen"], m.get("nombre_origen"), None)
        folio, intento = cuerpo.get("folio"), cuerpo.get("intento")
        with self._lock_ops:
            op = self.operaciones.get(folio) if isinstance(folio, str) else None
            if op is None or op.servicio != servicio:
                por = "folio ajeno"
            else:
                por = self._huella_ajena(op, cuerpo.get("huella"))
            if por is None:
                if not isinstance(intento, int) or isinstance(intento, bool):
                    self.log("DROP", f"{codigo} {folio} sin intento válido")
                    return
                if tipo == codigos.ACK:
                    self._rx_ack(op, m, intento)
                else:
                    self._rx_res(op, m)
                return
        self._ignorar(m, por)
        if por != "folio ajeno":
            self._mini("SELLO", f"{codigo} de {m.get('nombre_origen')} con mi folio {folio} "
                                f"pero {por}: ignorada")

    def _huella_ajena(self, op: Operacion, h) -> str | None:
        """None si la huella es la mía; si no, por qué no."""
        if not isinstance(h, dict):
            return "sin huella"
        if h.get("origen") != self.hash:
            return "la huella es de otro origen"
        if h.get("sello") != op.sello:
            return f"sello {hashes.corto(str(h.get('sello')))} alterado"
        return None

    def _ignorar(self, m: dict, por: str) -> None:
        self.ajenas += 1
        self.log("IGNORA", f"{m['codigo']} de {m.get('nombre_origen')} "
                           f"({hashes.corto(m['id'])}): {por}", consola=False)

    def _rx_latido(self, m: dict) -> None:
        cuerpo = m["cuerpo"]
        if cuerpo.get("tipo") != mensajes.MADRE:
            return  # GUIs y gestores también laten, pero no ofrecen servicios
        genes = cuerpo.get("genes")
        activos = {g.get("codigo") for g in genes if isinstance(g, dict)} if isinstance(
            genes, list) else set()
        for servicio in codigos.SERVICIOS:
            if servicio in activos:
                self._marcar_viva(servicio, m["origen"], m.get("nombre_origen"),
                                  cuerpo.get("nodo_nombre"))
            else:
                self._olvidar(servicio, m["origen"], "ya no tiene el gen")

    def _rx_adios(self, m: dict) -> None:
        for servicio in codigos.SERVICIOS:
            self._olvidar(servicio, m["origen"], "se despidió (CEL_ADIOS: cierre ordenado)")

    def _olvidar(self, servicio: str, h: str, por: str) -> None:
        with self._lock_ops:
            datos = self.vivas[servicio].pop(h, None)
            if datos is None:
                return
            self.log("SIN_GEN", f"{servicio} {datos[1]} ({hashes.corto(h)}) {por}")
            self._evaluar()

    def _marcar_viva(self, servicio: str, h: str, nombre, nodo_nombre) -> None:
        nombre = nombre or hashes.corto(h)
        with self._lock_ops:
            celulas = self.vivas[servicio]
            nueva = h not in celulas
            if nueva:
                celulas[h] = [time.monotonic(), nombre, nodo_nombre]
            else:
                celulas[h][0] = time.monotonic()
                celulas[h][1] = nombre
                if nodo_nombre:
                    celulas[h][2] = nodo_nombre
        if nueva:
            donde = f" en {nodo_nombre}" if nodo_nombre else ""
            self.log("VIVA", f"{servicio} {nombre} ({hashes.corto(h)}){donde}")
            with self._lock_ops:
                self._evaluar(nueva=(servicio, nombre, h))

    def _rx_ack(self, op: Operacion, m: dict, intento: int) -> None:
        """Con ``_lock_ops`` tomado."""
        origen, nombre = m["origen"], m.get("nombre_origen") or hashes.corto(m["origen"])
        if op.finalizado:
            self.log("ACUSE", f"de {nombre} para {op.folio} ya finalizado; no cambia nada",
                     consola=False)
            return
        op.acusadores.setdefault(intento, set()).add(origen)
        op.nombres[origen] = nombre
        minimo = self.acuses_min[op.servicio]
        if intento != op.intento:
            self._mini("ACUSE", f"{op.folio} · de {nombre} · intento {intento} (viejo: no "
                                f"cuenta para el intento {op.intento})")
            return
        self._mini("ACUSE", f"{op.folio} · {op.acuses()}/{minimo} de {nombre} "
                            f"({hashes.corto(origen)}) · intento {intento}")
        if op.estado == EN_VUELO and op.t_confirmado is None and op.acuses() >= minimo:
            self._confirmar(op)
        if (not op.ventana_cerrada and op.esperados
                and set(op.esperados) <= op.acusadores[intento]):
            self._cerrar_ventana(op)
        self._emitir_operacion(op)

    def _rx_res(self, op: Operacion, m: dict) -> None:
        """Con ``_lock_ops`` tomado."""
        nombre = m.get("nombre_origen") or hashes.corto(m["origen"])
        rol = m["cuerpo"].get("rol")
        if op.estado == RESUELTA:
            self._mini("DUPLICADA", f"{op.folio} · respuesta de {nombre} ({rol}): ya estaba "
                                    f"resuelta; descartada")
            return
        if op.estado == FALLIDA:
            self._mini("TARDÍA", f"{op.folio} · respuesta de {nombre} ({rol}): ya se dio por "
                                 f"fallida; descartada")
            return
        if op.t_confirmado is None:
            op.retenido = m
            self._mini("RETENIDA", f"{op.folio} · respuesta de {nombre} ({rol}) retenida: evento "
                                   f"aún sin confirmar ({op.acuses()}/"
                                   f"{self.acuses_min[op.servicio]})")
            return
        self._aceptar(op, m)

    # ---------------------------------------------------------- transiciones

    def _registrar(self, servicio: str, a, b) -> Operacion:
        """Crea la operación (folio + huella) y la guarda. Con ``_lock_ops`` tomado."""
        folio = foliado.folio(self.hash, next(self._folios))
        nodo = (self.nodo_actual or {}).get("hash")
        op = Operacion(folio, servicio, a, b,
                       foliado.huella(self.hash, nodo, folio, servicio, a, b, self.nombre))
        op.esperados = self._esperados(servicio)
        self.operaciones[folio] = op
        self._recortar_historial()
        return op

    def _esperados(self, servicio: str) -> dict:
        return {h: datos[1] for h, datos in self.vivas[servicio].items()}

    def _publicar_req(self, op: Operacion) -> None:
        nodo = (self.nodo_actual or {}).get("hash")
        if nodo and op.huella.get("nodo") != nodo:  # tras un failover entra por otro nodo
            op.huella = {**op.huella, "nodo": nodo}
        req = self.publicar(codigos.codigo(op.servicio, codigos.REQ),
                            {"folio": op.folio, "intento": op.intento, "a": op.a, "b": op.b,
                             "huella": op.huella})
        op.solicitudes[op.intento] = req["id"] if req else None

    def _confirmar(self, op: Operacion) -> None:
        op.t_confirmado = time.monotonic()
        op.fase = foliado.CONFIRMADO
        self._mini("CONFIRMADO", f"{op.folio} · ACK {op.acuses()}/"
                                 f"{self.acuses_min[op.servicio]} de {len(op.esperados)} "
                                 f"esperada(s) · intento {op.intento}: evento aceptado")
        if op.retenido is not None:
            m, op.retenido = op.retenido, None
            self._aceptar(op, m)

    def _cerrar_ventana(self, op: Operacion) -> None:
        """Fin de la confirmación del intento vigente: quién faltó."""
        op.ventana_cerrada = True
        acusaron = op.acusadores.get(op.intento, set())
        op.ausentes = [n for h, n in op.esperados.items() if h not in acusaron]
        if op.ausentes:
            sigue = ("el evento sigue (tolerancia)" if op.t_confirmado is not None
                     else "sin el mínimo")
            self._mini("AUSENTES", f"{op.folio} · intento {op.intento}: "
                                   f"{', '.join(op.ausentes)} no acusaron · ACK {op.acuses()}/"
                                   f"{self.acuses_min[op.servicio]} de {len(op.esperados)} "
                                   f"esperada(s) → {sigue}")
        self._quizas_finalizar(op)

    def _aceptar(self, op: Operacion, m: dict) -> None:
        cuerpo = m["cuerpo"]
        resultado, error = cuerpo.get("resultado"), cuerpo.get("error")
        if error is None and not _es_numero(resultado):
            error = f"respuesta sin resultado válido ({resultado!r})"[:120]
            resultado = None
        op.estado = RESUELTA
        op.fase = foliado.PROCESADO
        op.resultado, op.error = resultado, (str(error) if error is not None else None)
        op.rol = str(cuerpo.get("rol") or "?")
        op.respondio = m.get("nombre_origen") or hashes.corto(m["origen"])
        op.gen = str(cuerpo.get("gen") or "?")
        op.id_solicitud = cuerpo.get("id_solicitud")
        op.id_respuesta = m["id"]
        op.huella_final = cuerpo["huella"]  # ya se comprobó que es la mía
        op.ms = round((time.monotonic() - op.t0) * 1000)
        texto = formato.operacion(op.a, op.servicio, op.b, op.resultado, op.error)
        self._mini("RESULTADO", f"{op.folio} · {texto} · {op.rol} {op.respondio} · {op.gen} · "
                                f"solicitud {hashes.corto(op.id_solicitud)} ↔ respuesta "
                                f"{hashes.corto(op.id_respuesta)} · {op.ms} ms")
        self._quizas_finalizar(op)
        self._emitir_operacion(op)

    def _vencer(self, op: Operacion, motivo: str) -> None:
        if op.intento >= config.MAX_INTENTOS:
            op.estado = FALLIDA
            op.motivo = motivo
            op.ms = round((time.monotonic() - op.t0) * 1000)
            self._mini("FALLIDA", f"{op.folio} {formato.operacion(op.a, op.servicio, op.b)}: "
                                  f"{motivo} tras {op.intento} intento(s)")
            self._finalizar(op)
            self._emitir_operacion(op)
            return
        op.intento += 1
        op.enviado_en = time.monotonic()
        op.fase = foliado.INICIO
        op.t_confirmado = None
        op.ventana_cerrada = False
        op.ausentes = []
        op.esperados = self._esperados(op.servicio)
        self._publicar_req(op)
        self._mini("REINTENTO", f"{op.folio} · intento {op.intento} ({motivo}) · solicitud "
                                f"nueva {hashes.corto(op.solicitudes[op.intento]) or 'perdida'}")
        self._emitir_operacion(op)

    def _quizas_finalizar(self, op: Operacion) -> None:
        if op.estado != EN_VUELO and op.ventana_cerrada and not op.finalizado:
            self._finalizar(op)

    def _finalizar(self, op: Operacion) -> None:
        """Publica ``X_FIN``: las madres cierran sus rondas de este folio."""
        op.finalizado = True
        op.fase = foliado.FINALIZADO
        if op.huella_final is None:  # FALLIDA: el rastro llega hasta los acuses que vi
            acuses = [(h, op.nombres.get(h, "?"), foliado.ACK)
                      for h in op.acusadores.get(op.intento, ())]
            op.huella_final = foliado.con_pasos(op.huella, acuses)
        op.huella_final = foliado.con_paso(op.huella_final, self.hash, self.nombre, foliado.FIN)
        self.publicar(codigos.codigo(op.servicio, codigos.FIN), {
            "folio": op.folio, "intento": op.intento, "estado": op.estado,
            "id_respuesta": op.id_respuesta, "acuses": sorted(op.acusaron()),
            "ausentes": op.ausentes, "huella": op.huella_final})
        self._mini("FIN", f"{op.folio} · {op.estado} · rastro: "
                          f"{foliado.texto_rastro(op.huella_final)}")
        self._emitir_operacion(op)

    # ----------------------------------------------------------------- reloj

    def _vigilar(self) -> None:
        while not self._parar.wait(0.1):
            try:
                self._revisar()
            except Exception as e:
                self.log("ERROR", f"reloj: {e!r}")

    def _revisar(self) -> None:
        ahora = time.monotonic()
        with self._lock_ops:
            self._caducar(ahora)
            self._evaluar()
            for op in [o for o in self.operaciones.values() if not o.finalizado]:
                self._revisar_operacion(op, ahora)

    def _revisar_operacion(self, op: Operacion, ahora: float) -> None:
        minimo = self.acuses_min[op.servicio]
        if op.estado == EN_VUELO and op.t_confirmado is None and op.acuses() >= minimo:
            self._confirmar(op)  # p. ej. se bajó el mínimo en vivo
        vencio_ventana = ahora - op.enviado_en >= config.VENTANA_ACUSES
        if vencio_ventana and not op.ventana_cerrada:
            self._cerrar_ventana(op)
        if op.estado != EN_VUELO:
            return
        if op.t_confirmado is None:
            if vencio_ventana:
                self._vencer(op, f"acuses insuficientes ({op.acuses()}/{minimo})")
        else:
            plazo = (op.t_confirmado + config.VENTANA_ELECCION
                     + config.RELEVO * max(1, op.acuses()) + config.MARGEN_RESULTADO)
            if ahora >= plazo:
                self._vencer(op, "sin respuesta")

    def _caducar(self, ahora: float) -> None:
        """Con ``_lock_ops`` tomado. Sin enlace no se caduca a nadie (ver al_conectar)."""
        if self._sin_enlace or not self.conectado:
            return
        for servicio, celulas in self.vivas.items():
            for h, (visto, nombre, nodo_nombre) in list(celulas.items()):
                if ahora - visto > config.LATIDO_CADUCIDAD:
                    del celulas[h]
                    self.log("CADUCA", f"{servicio} {nombre} ({hashes.corto(h)}) sin latido en "
                                       f"{config.LATIDO_CADUCIDAD:.0f} s; se da por muerta")

    def _evaluar(self, nueva: tuple | None = None) -> None:
        """Habilita o deshabilita operadores. Con ``_lock_ops`` tomado."""
        for s in codigos.SERVICIOS:
            n, m = len(self.vivas[s]), self.acuses_min[s]
            hab = n >= m
            if hab == self.habilitadas[s]:
                continue
            self.habilitadas[s] = hab
            if hab:
                extra = ""
                if nueva and nueva[0] == s:
                    extra = f" (nueva: {nueva[1]} · {hashes.corto(nueva[2])})"
                self._mini("HABILITADA", f"{s} habilitada: {n}/{m}{extra}")
            else:
                self._mini("DESHABILITADA", f"{s} deshabilitada: {n} viva(s) < {m} mínima(s)")
        self._emitir_disponibilidad()

    # ------------------------------------------------------------- utilidades

    def _recortar_historial(self) -> None:
        sobran = len(self.operaciones) - HISTORIAL
        for folio in [f for f, op in self.operaciones.items() if op.finalizado][:max(0, sobran)]:
            del self.operaciones[folio]

    def _fila(self, op: Operacion) -> dict:
        minimo = self.acuses_min[op.servicio]
        partes = [op.folio, formato.operacion(op.a, op.servicio, op.b, op.resultado, op.error),
                  f"ACK {op.acuses()}/{minimo}"]
        if op.estado == RESUELTA:
            partes += [f"{op.rol} {op.respondio}", f"{op.ms} ms"]
        elif op.estado == FALLIDA:
            partes.append(f"FALLIDA: {op.motivo}")
        else:
            partes.append(f"intento {op.intento}")
        if op.ausentes:
            partes.append(f"ausentes: {', '.join(op.ausentes)}")
        huella = op.huella_final or op.huella
        return {"folio": op.folio, "servicio": op.servicio, "a": op.a, "b": op.b,
                "estado": op.estado, "fase": op.fase, "finalizado": op.finalizado,
                "intento": op.intento, "acuses": op.acuses(), "minimo": minimo,
                "acusaron": op.acusaron(), "esperados": list(op.esperados.values()),
                "ausentes": list(op.ausentes), "sello": op.sello,
                "rastro": foliado.rastro_de(huella), "resultado": op.resultado,
                "error": op.error, "rol": op.rol, "respondio": op.respondio, "gen": op.gen,
                "ms": op.ms, "motivo": op.motivo, "id_solicitud": op.id_solicitud,
                "id_respuesta": op.id_respuesta, "texto": " · ".join(partes)}

    def _mini(self, evento: str, texto: str, *, registrar: bool = True) -> None:
        """Una línea del mini log de protocolo (y de la bitácora)."""
        if registrar:
            self.log(evento, texto)
        self._emitir("log", (hora(), evento, texto))

    def _emitir_operacion(self, op: Operacion) -> None:
        self._emitir("operacion", self._fila(op))

    def _emitir_disponibilidad(self, forzar: bool = False) -> None:
        disp = self.disponibilidad()
        if forzar or disp != self._ultima_disp:
            self._ultima_disp = disp
            self._emitir("disponibilidad", disp)
