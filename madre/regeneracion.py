"""Autorrecuperación: las madres regeneran solas a la que se pierde (PLAN §6).

**Nadie coordina.** Cada madre lleva, con lo que oye por el Campo de Datos, un
directorio de las demás (sus ``CEL_LAT``) y de los nodos (``NODO_LAT``), y
aplica la MISMA regla determinista. Como todas oyen lo mismo, todas llegan a la
misma decisión sin ponerse de acuerdo ni preguntarle a nadie:

1. **Detectar.** Una madre que deja de latir ``LATIDO_CADUCIDAD`` s **sin**
   ``CEL_ADIOS`` es una **pérdida**: necesita exactamente un reemplazo, con los
   genes que tenía. Un retiro o una baja hechos con el gestor no son pérdidas.
2. **Turno (gradual).** Una sola regeneración en curso en todo el sistema; la
   siguiente, ``PAUSA_REGENERACION`` s después de que la anterior termine. Va
   primero la pérdida de menor hash: todas eligen la misma.
3. **Clonador.** Ranking HRW de las madres aptas con la clave de la pérdida
   (el mismo truco de la elección de titular). El rango 0 regenera; el rango r
   espera ``r · RELEVO_CLON`` s y solo actúa si no oyó un ``CLON_AVISO`` (por si
   el clonador también cayó).
4. **Avisar y lanzar.** ``CLON_AVISO`` a todos y un proceso **madre vacía**
   (``madre/lanzador.py``) con ``--reemplaza`` y la lista de genes a copiar.
5. **Cerrar.** El reemplazo copia sus genes (``madre/copia.py``) y publica
   ``CLON_LISTO``; con eso la pérdida queda resuelta en todas. Si no llega en
   ``PLAZO_CLON`` s, se reintenta (hasta ``MAX_REINTENTOS_CLON`` veces); antes,
   el clonador termina a su hijo vencido, para que nunca queden dos reemplazos
   de la misma pérdida.
6. **Alto.** Sin pérdidas pendientes, cada madre anota ``NIVEL_OK`` y no se
   clona nada más: el nivel requerido es el que había antes de la falla.

**Ocho límites contra el cáncer** (§6.4), cada uno en un solo lugar de este
módulo: (1) solo por pérdida, en ``_detectar``; (2) uno a uno y (6) topes
duros, en ``_topes``; (3) un clonador por pérdida, en ``_turno`` (HRW +
``CLON_AVISO``); (4) el reemplazo en curso cuenta y (5) gradual, al inicio de
``_turno``; (7) telómeros y (8) cupo por madre, en ``_aptas``.

Sin Tkinter y con reloj y lanzador inyectables: las pruebas levantan los
reemplazos en el mismo proceso y adelantan el tiempo a mano.
"""

import re
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from comun import codigos, config, hashes, mensajes

# Estados de una pérdida.
PENDIENTE = "pendiente"      # espera su turno
EN_CURSO = "en curso"        # hubo CLON_AVISO: su reemplazo está naciendo
RESUELTA = "resuelta"        # CLON_LISTO (o su reemplazo ya late)
DESCARTADA = "descartada"    # un tope o los reintentos dijeron que no

VENTANA_CUPO = 60.0          # MAX_CLONES_MINUTO se cuenta en esta ventana (s)
RECORDAR_PERDIDAS = 300.0    # las resueltas se recuerdan este tiempo (avisos tardíos)
_SUFIJO_CLON = re.compile(r"·r\d+$")


def _gen_texto(genes: list[dict]) -> str:
    return ", ".join(f"{g['codigo']} {g['version']}" for g in genes) or "vacía"


@dataclass
class Ficha:
    """Lo que una madre sabe de otra por su latido."""

    hash: str
    nombre: str
    nodo: str | None = None
    nodo_nombre: str | None = None
    genes: list = field(default_factory=list)       # [{"codigo", "version", "sha8"}]
    generacion: int = 0
    reemplaza: str | None = None
    mudo: bool = False
    visto: float = 0.0                              # último latido
    desde: float = 0.0                              # primer latido que oí

    @property
    def codigos(self) -> set[str]:
        return {g["codigo"] for g in self.genes}


@dataclass
class Perdida:
    hash: str
    nombre: str
    nodo: str | None
    nodo_nombre: str | None
    genes: list
    generacion: int
    desde: float                     # desde cuándo puede tocarle turno
    estado: str = PENDIENTE
    intento: int = 1
    aviso_en: float | None = None
    clonador: str | None = None
    hijo: str | None = None
    anunciada: int = 0               # intento cuyo ranking ya se anotó en la bitácora
    cerrada_en: float | None = None
    motivo: str = ""


@dataclass(frozen=True)
class Encargo:
    """Lo que necesita el lanzador para levantar un reemplazo."""

    nombre: str                      # 'SUM-N2·r1'
    nodo: str                        # endpoint al que se conecta
    nodo_nombre: str
    reemplaza: str                   # hash de la pérdida
    perdida: str                     # su nombre
    genes: tuple[str, ...]           # ('SUM@1.0:1a2b3c4d', …): qué copiar
    generacion: int
    clonador: str

    def argumentos(self) -> list[str]:
        """Los de ``python -m madre`` (el mismo comando que se escribiría a mano)."""
        args = ["--nodo", self.nodo, "--nombre", self.nombre, "--reemplaza", self.reemplaza,
                "--perdida", self.perdida, "--generacion", str(self.generacion)]
        if self.genes:
            args += ["--copiar", ",".join(self.genes)]
        return args


Lanzador = Callable[[Encargo], object]     # devuelve con qué cancelarlo (o None)
Cancelar = Callable[[object], object]


class Regeneracion:
    def __init__(self, madre, lanzador: Lanzador | None,
                 reloj: Callable[[], float] = time.monotonic, cancelar: Cancelar | None = None):
        """``cancelar``: cómo terminar a un hijo que no estuvo listo a tiempo (recibe
        lo que devolvió ``lanzador``)."""
        self.madre = madre
        self.lanzador = lanzador
        self.cancelar = cancelar
        self._hijos: dict[str, object] = {}              # pérdida -> mi hijo en curso
        self.activa = lanzador is not None   # sin lanzador: lleva la cuenta pero no clona
        self._reloj = reloj
        self._lock = threading.Lock()
        self.directorio: dict[str, Ficha] = {}
        self.nodos: dict[str, dict] = {}                 # hash -> {nombre, endpoint, visto}
        self.perdidas: dict[str, Perdida] = {}
        self._avisos: dict[str, deque] = {}              # clonador -> cuándo avisó (cupo)
        self._fin_ultima = float("-inf")                 # última regeneración terminada
        self._nivel_ok = True
        self.desde = reloj()                             # se reajusta al conectarse
        self.lanzados = 0

    # ------------------------------------------------------------ entradas

    def conectada(self) -> None:
        """Conexión o reconexión. Desde aquí cuenta mi antigüedad: tras un hueco no
        clono hasta volver a oír a todas (mi directorio pudo quedar viejo). Y el
        hueco no prueba que nadie haya muerto: cada una recibe un plazo completo
        desde ahora (si no, al reconectarme daría por perdidas a todas)."""
        with self._lock:
            ahora = self._reloj()
            self.desde = ahora
            for f in self.directorio.values():
                f.visto = max(f.visto, ahora)

    def rx_latido(self, m: dict) -> None:
        """``CEL_LAT`` (o ``TOPO_RES``) de otra madre."""
        cuerpo = m["cuerpo"]
        if cuerpo.get("tipo") != mensajes.MADRE:
            return
        h, ahora, avisos = m["origen"], self._reloj(), []
        with self._lock:
            f = self.directorio.get(h)
            if f is None:
                f = self.directorio[h] = Ficha(h, m.get("nombre_origen") or hashes.corto(h),
                                               desde=ahora)
            f.nodo = cuerpo.get("nodo") if mensajes.es_hash(cuerpo.get("nodo")) else None
            f.nodo_nombre = cuerpo.get("nodo_nombre") if isinstance(
                cuerpo.get("nodo_nombre"), str) else None
            f.genes = _genes(cuerpo.get("genes"))
            f.generacion = _entero(cuerpo.get("generacion"))
            f.reemplaza = cuerpo.get("reemplaza") if mensajes.es_hash(
                cuerpo.get("reemplaza")) else None
            f.mudo = cuerpo.get("mudo") is True
            f.visto = ahora
            p = self.perdidas.get(h)
            if p is not None and p.estado == PENDIENTE:
                del self.perdidas[h]
                avisos.append(("REVIVIO", (f"{f.nombre} volvió a latir: solo estaba lenta, no "
                                          f"era una pérdida")))
                self._quizas_nivel_ok(avisos)
        self._anotar(avisos)

    def rx_nodo(self, m: dict) -> None:
        cuerpo = m["cuerpo"]
        with self._lock:
            self.nodos[m["origen"]] = {"nombre": cuerpo.get("nombre") or hashes.corto(m["origen"]),
                                       "endpoint": cuerpo.get("endpoint"),
                                       "visto": self._reloj()}

    def rx_adios(self, m: dict) -> None:
        """Cierre ordenado: NO es una pérdida (límite 1)."""
        avisos = []
        with self._lock:
            f = self.directorio.pop(m["origen"], None)
            if f is None:
                # Ya la daba por perdida (sus latidos no llegaban) y ahora se despide:
                # no era una pérdida. Si ya hay un reemplazo en curso, se deja seguir.
                p = self.perdidas.get(m["origen"])
                if p is None or p.estado != PENDIENTE:
                    return
                del self.perdidas[m["origen"]]
                avisos.append(("ADIOS", (f"{p.nombre} se despidió con CEL_ADIOS: no era una "
                                         f"pérdida, no se regenera")))
                self._quizas_nivel_ok(avisos)
            p = self.perdidas.get(f.reemplaza) if f is not None and f.reemplaza else None
            if p is not None and p.estado == EN_CURSO:
                # El administrador retiró al reemplazo antes de que estuviera listo:
                # ese es el nivel que quiso; no se insiste.
                self._cerrar(p, DESCARTADA, self._reloj(), "el administrador retiró el reemplazo")
                avisos.append(("NO_CLONA", (f"{p.nombre}: su reemplazo {f.nombre} se retiró "
                                           f"ordenadamente; no se insiste")))
                self._quizas_nivel_ok(avisos)
        if f is not None:
            self.madre.log("ADIOS", f"{f.nombre} se fue con CEL_ADIOS "
                                    f"({m['cuerpo'].get('motivo')}): no es una pérdida, no se "
                                    f"regenera", consola=False)
        self._anotar(avisos)

    def rx_aviso(self, m: dict) -> None:
        """``CLON_AVISO``: alguien ya regenera esa pérdida (las demás esperan)."""
        c, ahora = m["cuerpo"], self._reloj()
        h = c.get("reemplaza")
        if not mensajes.es_hash(h) or h == self.madre.hash:
            return
        with self._lock:
            p = self.perdidas.get(h)
            if p is None:
                # Aún no la daba por perdida (o llegué después): el aviso basta para
                # saber que hay una regeneración en curso.
                self.directorio.pop(h, None)
                nodo = c.get("nodo_perdida") if mensajes.es_hash(c.get("nodo_perdida")) else None
                p = self.perdidas[h] = Perdida(
                    h, str(c.get("perdida") or hashes.corto(h)), nodo,
                    None, _genes(c.get("genes")), max(0, _entero(c.get("generacion")) - 1),
                    desde=ahora)
            if p.estado in (RESUELTA, DESCARTADA):
                return
            p.estado, p.aviso_en = EN_CURSO, ahora
            p.intento = max(p.intento, _entero(c.get("intento"), 1))
            p.clonador = m.get("nombre_origen") or hashes.corto(m["origen"])
            p.hijo = str(c.get("hijo") or "?")
            self._avisos.setdefault(m["origen"], deque()).append(ahora)
            self._nivel_ok = False
        self.madre.log("CLON_AVISO", f"{p.clonador} (rango {c.get('rango', '?')}) regenera a "
                                     f"{p.nombre} → {p.hijo} en {c.get('nodo_nombre') or '?'} "
                                     f"(intento {p.intento}); yo espero")

    def rx_listo(self, m: dict) -> None:
        """``CLON_LISTO``: el reemplazo ya tiene sus genes; la pérdida queda resuelta."""
        c, ahora, avisos = m["cuerpo"], self._reloj(), []
        h = c.get("reemplaza")
        if not mensajes.es_hash(h):
            return
        with self._lock:
            p = self.perdidas.get(h)
            if p is None or p.estado in (RESUELTA, DESCARTADA):
                return
            self._cerrar(p, RESUELTA, ahora)
            self._fin_ultima = ahora
            self._hijos.pop(h, None)
            fuentes = c.get("fuentes") if isinstance(c.get("fuentes"), dict) else {}
            copiados = ", ".join(f"{g} de {de}" for g, de in fuentes.items()) or "sin genes"
            faltan = c.get("faltan") if isinstance(c.get("faltan"), list) else []
            avisos.append(("CLON_LISTO", f"{m.get('nombre_origen')} reemplaza a {p.nombre}: "
                                         f"{copiados}" + (f" · faltan {', '.join(map(str, faltan))}"
                                                          if faltan else "")))
            self._quizas_nivel_ok(avisos)
        self._anotar(avisos)

    # ------------------------------------------------------------ la regla

    def revisar(self) -> None:
        """Cada ``REVISION_REGENERACION`` s, en cada madre, sin input de nadie."""
        ahora, avisos, vencidos = self._reloj(), [], []
        with self._lock:
            self._detectar(ahora, avisos)
            self._vencer(ahora, avisos, vencidos)
            encargo = self._turno(ahora, avisos)
            self._quizas_nivel_ok(avisos)
            self._podar(ahora)
        self._anotar(avisos)
        for nombre, hijo in vencidos:
            self._cancelar(nombre, hijo)
        if encargo is not None:
            self._lanzar(*encargo)

    def _detectar(self, ahora: float, avisos: list) -> None:
        """Límite 1: solo una madre que dejó de latir SIN despedirse es pérdida."""
        for h, f in list(self.directorio.items()):
            if ahora - f.visto <= config.LATIDO_CADUCIDAD:
                continue
            del self.directorio[h]
            padre = self.perdidas.get(f.reemplaza) if f.reemplaza else None
            if padre is not None and padre.estado == EN_CURSO:
                # Murió el reemplazo antes de estar listo: es la MISMA pérdida; se
                # reintenta ya (no se agrega otra, o se clonaría de más). Solo si era
                # el del intento vigente (nació después de su aviso); si no, ya hay otro
                # intento en curso y basta con esperarlo.
                if padre.aviso_en is not None and f.desde >= padre.aviso_en:
                    padre.aviso_en = ahora - config.PLAZO_CLON - 1
                avisos.append(("CAIDA", (f"{f.nombre} (reemplazo de {padre.nombre}) sin latido "
                                        f"antes de estar listo: se reintenta {padre.nombre}")))
                continue
            previa = self.perdidas.get(h)
            if previa is not None and previa.estado in (PENDIENTE, EN_CURSO):
                continue
            self.perdidas[h] = Perdida(h, f.nombre, f.nodo, f.nodo_nombre, list(f.genes),
                                       f.generacion,
                                       desde=f.visto + config.LATIDO_CADUCIDAD + config.LATIDO)
            self._nivel_ok = False
            avisos.append(("CAIDA", (f"{f.nombre} ({_gen_texto(f.genes)}) sin latido en "
                                    f"{config.LATIDO_CADUCIDAD:g} s y sin CEL_ADIOS: pérdida → "
                                    f"necesita 1 reemplazo")))

    def _vencer(self, ahora: float, avisos: list, vencidos: list) -> None:
        for p in self.perdidas.values():
            if p.estado != EN_CURSO or ahora - p.aviso_en <= config.PLAZO_CLON:
                continue
            hijo = self._reemplazo_vivo(p.hash, ahora)
            if hijo is not None:
                self._cerrar(p, RESUELTA, ahora)
                self._fin_ultima = ahora
                self._hijos.pop(p.hash, None)
                avisos.append(("CLON_LISTO", (f"{hijo.nombre} reemplaza a {p.nombre} (late; su "
                                             f"CLON_LISTO no me llegó)")))
                continue
            # Límite 2 (uno a uno): si el hijo vencido es mío, lo termino antes de que
            # se reintente; si no, un hijo lento podría aparecer junto al del reintento.
            if p.hash in self._hijos:
                vencidos.append((p.hijo, self._hijos.pop(p.hash)))
            self._fin_ultima = ahora
            if p.intento > config.MAX_REINTENTOS_CLON:
                self._cerrar(p, DESCARTADA, ahora, f"{p.intento} intentos sin reemplazo listo")
                avisos.append(("NO_CLONA", (f"{p.nombre}: {p.motivo}; se deja (anti-cáncer: no "
                                           f"se insiste sin fin)")))
            else:
                p.estado, p.aviso_en, p.desde = PENDIENTE, None, ahora
                p.intento += 1
                avisos.append(("CLON_VENCIDO", (f"{p.nombre}: {p.hijo} no estuvo listo en "
                                               f"{config.PLAZO_CLON:g} s; intento {p.intento}")))

    def _turno(self, ahora: float, avisos: list) -> tuple | None:
        # Límites 4 y 5: una sola regeneración en curso en todo el sistema, y pausa.
        if any(p.estado == EN_CURSO for p in self.perdidas.values()):
            return None
        pausa = self._fin_ultima + config.PAUSA_REGENERACION
        listas = [p for p in self.perdidas.values() if p.estado == PENDIENTE and ahora >= p.desde]
        if not listas or ahora < pausa:
            return None
        p = min(listas, key=lambda p: p.hash)   # todas eligen la misma
        motivo = self._topes(p, ahora)
        if motivo:
            self._cerrar(p, DESCARTADA, ahora, motivo)
            avisos.append(("NO_CLONA", f"{p.nombre}: {motivo}"))
            return None
        # Límite 3: un clonador por pérdida (HRW; el resto espera su relevo).
        aptas, no_aptas = self._aptas(ahora)
        ranking = hashes.ranking(aptas, f"clon:{p.hash}", p.intento)
        rango = ranking.index(self.madre.hash) if self.madre.hash in ranking else None
        if p.anunciada != p.intento:
            p.anunciada = p.intento
            nombres = {f.hash: f.nombre for f in self.directorio.values()}
            nombres[self.madre.hash] = self.madre.nombre
            yo = (f"yo: rango {rango}" if rango is not None
                  else f"yo no clono ({no_aptas.get(self.madre.hash, 'no apta')})")
            avisos.append(("CLONADOR", (f"para {p.nombre} (intento {p.intento}): rango 0 = "
                                       f"{nombres.get(ranking[0], '?') if ranking else 'nadie'} "
                                       f"de {len(ranking)} aptas · {yo}")))
        if rango is None or not self.activa:
            return None
        if ahora < max(p.desde, pausa) + rango * config.RELEVO_CLON:
            return None
        encargo = self._encargo(p, ahora)
        p.estado, p.aviso_en = EN_CURSO, ahora
        p.clonador, p.hijo = self.madre.nombre, encargo.nombre
        self._avisos.setdefault(self.madre.hash, deque()).append(ahora)
        self._nivel_ok = False
        return encargo, rango, p

    def _topes(self, p: Perdida, ahora: float) -> str | None:
        """Límites 2 y 6 (iguales para todas: salen de lo que todas oyen)."""
        hijo = self._reemplazo_vivo(p.hash, ahora)
        if hijo is not None:
            return f"ya tiene un reemplazo vivo ({hijo.nombre}): uno a uno"
        vivas = self._vivas(ahora)
        if len(vivas) + 1 > config.MAX_MADRES:
            return f"tope duro: ya hay {len(vivas)} madres (máx. {config.MAX_MADRES})"
        for cod in sorted({g["codigo"] for g in p.genes}):
            n = sum(1 for f in vivas if cod in f.codigos)
            if n + 1 > config.MAX_POR_GEN:
                return f"tope duro: ya hay {n} madres con {cod} (máx. {config.MAX_POR_GEN})"
        return None

    def _aptas(self, ahora: float) -> tuple[list[str], dict[str, str]]:
        """Quién puede clonar. Límites 7 (telómeros) y 8 (cupo por madre)."""
        aptas, no = [], {}
        for f in self._vivas(ahora):
            if f.mudo:
                no[f.hash] = "muda"
            elif f.generacion >= config.MAX_GENERACION:
                no[f.hash] = f"telómeros: generación {f.generacion}"
            elif ahora - f.desde < config.LATIDO_CADUCIDAD:
                no[f.hash] = "recién llegada"   # aún no oye a todas: su ranking podría diferir
            elif self._cupo(f.hash, ahora) >= config.MAX_CLONES_MINUTO:
                no[f.hash] = f"cupo: {config.MAX_CLONES_MINUTO} clones en el último minuto"
            else:
                aptas.append(f.hash)
        return aptas, no

    # ------------------------------------------------------------ lanzar

    def _encargo(self, p: Perdida, ahora: float) -> Encargo:
        _, nombre_nodo, endpoint = self._nodo_para(p, ahora)
        generacion = p.generacion + 1
        hijo = f"{_SUFIJO_CLON.sub('', p.nombre)}·r{generacion}"
        genes = tuple(f"{g['codigo']}@{g['version']}" + (f":{g['sha8']}" if g.get("sha8") else "")
                      for g in p.genes)
        return Encargo(hijo, endpoint, nombre_nodo, p.hash, p.nombre, genes, generacion,
                       self.madre.nombre)

    def _nodo_para(self, p: Perdida, ahora: float) -> tuple[str | None, str, str]:
        """El nodo de la pérdida si sigue vivo; si no, el vivo con menos madres."""
        vivos = {h: n for h, n in self.nodos.items()
                 if ahora - n["visto"] <= config.LATIDO_CADUCIDAD and n.get("endpoint")}
        if p.nodo in vivos:
            n = vivos[p.nodo]
            return p.nodo, n["nombre"], n["endpoint"]
        if vivos:
            carga = {h: 0 for h in vivos}
            for f in self._vivas(ahora):
                if f.nodo in carga:
                    carga[f.nodo] += 1
            h = min(vivos, key=lambda h: (carga[h], vivos[h]["nombre"]))
            return h, vivos[h]["nombre"], vivos[h]["endpoint"]
        mio = self.madre.nodo_actual or {}
        return mio.get("hash"), mio.get("nombre", "?"), mio.get("endpoint") or self.madre.nodo_inicial

    def _lanzar(self, encargo: Encargo, rango: int, p: Perdida) -> None:
        aviso = self.madre.publicar(codigos.CLON_AVISO, {
            "reemplaza": p.hash, "perdida": p.nombre, "nodo_perdida": p.nodo,
            "genes": p.genes, "hijo": encargo.nombre, "nodo": encargo.nodo,
            "nodo_nombre": encargo.nodo_nombre, "generacion": encargo.generacion,
            "intento": p.intento, "rango": rango})
        if aviso is None:
            # Límite 3: si nadie oyó mi aviso, el rango siguiente también lanzaría.
            with self._lock:
                if p.estado == EN_CURSO and p.clonador == self.madre.nombre:
                    p.estado, p.aviso_en, p.clonador, p.hijo = PENDIENTE, None, None, None
            self.madre.log("NO_CLONA", f"mi CLON_AVISO para {p.nombre} no salió (sin enlace): no "
                                       f"lanzo; otra lo hará")
            return
        self.madre.log("CLON_AVISO", f"yo (rango {rango}) regenero a {p.nombre} → {encargo.nombre} "
                                     f"en {encargo.nodo_nombre}: nace vacía y copia "
                                     f"{_gen_texto(p.genes)} (intento {p.intento})")
        try:
            hijo = self.lanzador(encargo)
            self.lanzados += 1
        except Exception as e:  # el aviso caduca en PLAZO_CLON y se reintenta
            self.madre.log("ERROR", f"no se pudo lanzar {encargo.nombre}: {e!r}")
            return
        if hijo is not None:
            with self._lock:
                if p.estado == EN_CURSO:
                    self._hijos[p.hash] = hijo

    def _cancelar(self, nombre: str | None, hijo: object) -> None:
        if self.cancelar is None:
            return
        try:
            if self.cancelar(hijo) is not False:   # False: ya no vivía
                self.madre.log("CLON_CANCELADO", f"terminé a mi hijo {nombre}: no estuvo listo "
                                                 f"en {config.PLAZO_CLON:g} s (uno a uno: no "
                                                 f"quedan dos)")
        except Exception as e:
            self.madre.log("ERROR", f"no se pudo terminar a {nombre}: {e!r}")

    # ------------------------------------------------------------ utilidades

    def _mi_ficha(self, ahora: float) -> Ficha:
        m = self.madre
        nodo = m.nodo_actual or {}
        return Ficha(m.hash, m.nombre, nodo.get("hash"), nodo.get("nombre"), m.genoma.resumen(),
                     m.generacion, m.reemplaza, m.mudo, ahora, self.desde)

    def _vivas(self, ahora: float) -> list[Ficha]:
        return [f for f in self.directorio.values()
                if ahora - f.visto <= config.LATIDO_CADUCIDAD] + [self._mi_ficha(ahora)]

    def _reemplazo_vivo(self, h: str, ahora: float) -> Ficha | None:
        return next((f for f in self.directorio.values()
                     if f.reemplaza == h and ahora - f.visto <= config.LATIDO_CADUCIDAD), None)

    def _cupo(self, h: str, ahora: float) -> int:
        cola = self._avisos.get(h)
        if not cola:
            return 0
        while cola and ahora - cola[0] > VENTANA_CUPO:
            cola.popleft()
        return len(cola)

    def _cerrar(self, p: Perdida, estado: str, ahora: float, motivo: str = "") -> None:
        p.estado, p.cerrada_en, p.motivo = estado, ahora, motivo

    def _quizas_nivel_ok(self, avisos: list) -> None:
        """Límite de alto: sin pérdidas pendientes no se clona nada más."""
        if self._nivel_ok or any(p.estado in (PENDIENTE, EN_CURSO)
                                 for p in self.perdidas.values()):
            return
        self._nivel_ok = True
        vivas = self._vivas(self._reloj())
        cuenta = {s: sum(1 for f in vivas if s in f.codigos and not f.mudo)
                  for s in codigos.SERVICIOS}
        resumen = " · ".join(f"{s} {n}" for s, n in cuenta.items())
        avisos.append(("NIVEL_OK", (f"nivel recuperado: {len(vivas)} madres ({resumen}); "
                                   f"regeneración detenida, no se clona nada más")))

    def _podar(self, ahora: float) -> None:
        for h, p in list(self.perdidas.items()):
            if p.cerrada_en is not None and ahora - p.cerrada_en > RECORDAR_PERDIDAS:
                del self.perdidas[h]

    def _anotar(self, avisos: list) -> None:
        for evento, texto in avisos:
            self.madre.log(evento, texto)

    # ------------------------------------------------------------ consultas

    def resumen(self) -> dict:
        with self._lock:
            cuenta = {e: 0 for e in (PENDIENTE, EN_CURSO, RESUELTA, DESCARTADA)}
            for p in self.perdidas.values():
                cuenta[p.estado] += 1
            return {**cuenta, "lanzados": self.lanzados, "madres": len(self.directorio) + 1}

    def perdida(self, h: str) -> Perdida | None:
        with self._lock:
            return self.perdidas.get(h)


def _entero(valor, defecto: int = 0) -> int:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else defecto


def _genes(lista) -> list[dict]:
    if not isinstance(lista, list):
        return []
    return [{"codigo": g["codigo"], "version": str(g.get("version", "")),
             "sha8": str(g.get("sha8") or "")[:8]}
            for g in lista if isinstance(g, dict) and codigos.es_gen(g.get("codigo"))
            and isinstance(g.get("version"), str)]
