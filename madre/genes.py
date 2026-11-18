"""Ciclo de vida de un gen dentro de una célula madre (PDF §5.2).

    LOCALIZAR → VALIDAR → CARGAR → AUTOPRUEBA → ACTIVAR … DESCARGAR → LIBERAR

* **Localizar**: la carpeta del gen en el almacén de la madre (nunca otra).
* **Validar** sin ejecutar nada: forma del manifiesto, tamaño del programa y
  ``sha256(servicio.py) == manifiesto.sha256``. Un programa alterado después de
  firmarse (``SUM 9.9``) muere aquí.
* **Cargar** con ``importlib``: ``spec_from_file_location`` + ``module_from_spec``
  y se ejecutan **los mismos bytes que se validaron** (no se vuelve a leer el
  archivo: entre validar y cargar nadie puede cambiarlo). El módulo no se
  registra en ``sys.modules``: así, al descargarlo, nada más lo retiene.
* **Autoprueba**: los vectores ``[a, b, esperado]`` del manifiesto
  (``esperado = null`` significa "debe responder con error").
* **Activar / descargar**: ``Genoma`` es el conjunto de genes activos (un gen
  por código). Activar o quitar es atómico bajo su lock.
* **Liberar**: tras descargar, un ``weakref`` al módulo confirma que el
  recolector lo eliminó de memoria (si una ronda en curso aún lo usa, se libera
  cuando termine).

El programa del gen solo contiene la operación. Lo que es **protocolo** lo hace
``ejecutar``: operandos numéricos finitos y no ``bool``, resultado finito, y
cualquier excepción del gen se vuelve una respuesta con error (un gen roto no
tumba a la célula).
"""

import gc
import importlib.util
import itertools
import math
import sys
import threading
import time
import weakref
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from comun import config, microservicios

# Pasos del ciclo de vida (aparecen en bitácoras y en GEN_RES).
LOCALIZAR = "localizar"
VALIDAR = "validar"
CARGAR = "cargar"
AUTOPRUEBA = "autoprueba"

_secuencia = itertools.count(1)

Informar = Callable[[str, str], None]   # (evento, texto) para la bitácora


class GenRechazado(Exception):
    """El gen no pasó un paso del ciclo de vida. Nada quedó activo."""

    def __init__(self, paso: str, motivo: str):
        super().__init__(f"{paso}: {motivo}")
        self.paso = paso
        self.motivo = motivo


@dataclass(frozen=True, eq=False)
class Gen:
    """Un gen cargado en memoria y listo para atender su código."""

    codigo: str
    version: str
    sha256: str
    nombre: str
    carpeta: Path
    modulo: ModuleType
    cargado_ms: float

    @property
    def id(self) -> str:
        return microservicios.gen_id(self.codigo, self.version)

    @property
    def sha8(self) -> str:
        return self.sha256[:8]

    def resumen(self) -> dict:
        return {"codigo": self.codigo, "version": self.version, "sha8": self.sha8}


# --- Cargar ------------------------------------------------------------------

def cargar(carpeta: Path, informar: Informar | None = None) -> Gen:
    """Localiza, valida, carga y autoprueba el gen de ``carpeta``.

    Devuelve el ``Gen`` listo para activarse o lanza ``GenRechazado``.
    """
    def nota(evento: str, texto: str) -> None:
        if informar is not None:
            informar(evento, texto)

    # LOCALIZAR
    if not (carpeta / microservicios.MANIFIESTO).is_file():
        raise GenRechazado(LOCALIZAR, f"no hay {microservicios.MANIFIESTO} en {carpeta}")

    # VALIDAR (sin ejecutar nada)
    try:
        paquete = microservicios.leer(carpeta)
    except (OSError, ValueError) as e:
        raise GenRechazado(VALIDAR, f"no se pudo leer: {e}") from None
    problema = paquete.problema(config.GEN_MAX_BYTES)
    if problema:
        raise GenRechazado(VALIDAR, problema)
    nota("GEN_VALIDADO", f"{paquete.id} · sha256 {paquete.sha_real[:8]} coincide con el "
                         f"manifiesto · {len(paquete.fuente)} bytes")

    # CARGAR: importlib sobre los MISMOS bytes que se validaron
    t0 = time.perf_counter()
    nombre_modulo = (f"gen_{paquete.codigo}_{paquete.version.replace('.', '_')}"
                     f"_{paquete.sha_real[:8]}_{next(_secuencia)}")
    archivo = carpeta / microservicios.ARCHIVO
    spec = importlib.util.spec_from_file_location(nombre_modulo, archivo)
    if spec is None:
        raise GenRechazado(CARGAR, "importlib no pudo crear la especificación del módulo")
    modulo = importlib.util.module_from_spec(spec)
    try:
        codigo_objeto = compile(paquete.fuente, str(archivo), "exec")
        exec(codigo_objeto, modulo.__dict__)  # noqa: S102 — es justo lo que hace exec_module
    except Exception as e:
        raise GenRechazado(CARGAR, f"el programa falló al importarse: {e!r}"[:200]) from None
    finally:
        sys.modules.pop(nombre_modulo, None)  # por si el propio gen se registró
    problema = _revisar_interfaz(modulo, paquete.codigo, paquete.version)
    if problema:
        raise GenRechazado(CARGAR, problema)
    ms = (time.perf_counter() - t0) * 1000
    gen = Gen(paquete.codigo, paquete.version, paquete.sha_real,
              paquete.manifiesto["nombre"], carpeta, modulo, ms)
    nota("GEN_CARGADO", f"{gen.id} en memoria con importlib ({ms:.1f} ms) · módulo "
                        f"{nombre_modulo}")

    # AUTOPRUEBA
    pruebas = paquete.manifiesto["pruebas"]
    for a, b, esperado in pruebas:
        resultado, error = ejecutar(gen, a, b)
        if esperado is None:
            if error is None:
                raise GenRechazado(AUTOPRUEBA, f"calcular({a}, {b}) debía dar error y dio "
                                               f"{resultado!r}")
        elif error is not None or resultado != esperado:
            obtenido = error if error is not None else repr(resultado)
            raise GenRechazado(AUTOPRUEBA, f"calcular({a}, {b}) = {obtenido}; se esperaba "
                                           f"{esperado!r}")
    nota("GEN_AUTOPRUEBA", f"{gen.id} pasó {len(pruebas)} prueba(s) del manifiesto")
    return gen


def _revisar_interfaz(modulo: ModuleType, codigo: str, version: str) -> str | None:
    if getattr(modulo, "SERVICIO", None) != codigo:
        return f"SERVICIO = {getattr(modulo, 'SERVICIO', None)!r}, el manifiesto dice {codigo!r}"
    if getattr(modulo, "VERSION", None) != version:
        return f"VERSION = {getattr(modulo, 'VERSION', None)!r}, el manifiesto dice {version!r}"
    if not callable(getattr(modulo, "calcular", None)):
        return "el programa no define calcular(a, b)"
    return None


# --- Ejecutar (el protocolo alrededor de la lógica del gen) -------------------

def _operando(valor, nombre: str) -> tuple[float | None, str | None]:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None, f"operando {nombre} no es un número: {valor!r}"[:120]
    try:
        x = float(valor)
    except OverflowError:
        return None, f"operando {nombre} fuera de rango"
    if not math.isfinite(x):
        return None, f"operando {nombre} no es finito"
    return x, None


def ejecutar(gen: Gen, a, b) -> tuple[float | None, str | None]:
    """(resultado, error): exactamente uno es None. Nunca lanza."""
    x, error = _operando(a, "a")
    if error:
        return None, error
    y, error = _operando(b, "b")
    if error:
        return None, error
    try:
        resultado, error = gen.modulo.calcular(x, y)
    except OverflowError:
        return None, "resultado fuera de rango"
    except Exception as e:
        return None, f"el gen {gen.id} falló: {type(e).__name__}"
    if error is not None:
        return None, str(error)[:120]
    if isinstance(resultado, bool) or not isinstance(resultado, (int, float)):
        return None, f"el gen {gen.id} no devolvió un número"
    try:
        r = float(resultado)
    except OverflowError:
        return None, "resultado fuera de rango"
    if not math.isfinite(r):
        return None, "resultado fuera de rango (no finito)"
    return r, None


# --- Genes activos -----------------------------------------------------------

class Genoma:
    """Los genes activos de una madre: a lo más uno por código."""

    def __init__(self):
        self._lock = threading.Lock()
        self._activos: dict[str, Gen] = {}

    def activo(self, codigo: str) -> Gen | None:
        with self._lock:
            return self._activos.get(codigo)

    def activar(self, gen: Gen) -> Gen | None:
        """Pone ``gen`` como el activo de su código. Devuelve el que reemplazó."""
        with self._lock:
            anterior = self._activos.get(gen.codigo)
            self._activos[gen.codigo] = gen
            return anterior

    def quitar(self, codigo: str) -> Gen | None:
        with self._lock:
            return self._activos.pop(codigo, None)

    def codigos(self) -> list[str]:
        with self._lock:
            return sorted(self._activos)

    def ids(self) -> list[str]:
        with self._lock:
            return [self._activos[c].id for c in sorted(self._activos)]

    def resumen(self) -> list[dict]:
        with self._lock:
            return [self._activos[c].resumen() for c in sorted(self._activos)]

    def __len__(self) -> int:
        with self._lock:
            return len(self._activos)


# --- Liberación de memoria ----------------------------------------------------

def referencia(gen: Gen) -> weakref.ref:
    """Referencia débil al módulo del gen: no lo mantiene vivo."""
    return weakref.ref(gen.modulo)


def liberado(ref: weakref.ref) -> bool:
    """¿El recolector ya eliminó el módulo? (fuerza una recolección completa)."""
    gc.collect()
    return ref() is None
