"""Lanzar, vigilar y tumbar procesos del sistema operativo. Sin Tkinter.

Esto NO es parte del sistema ADS: solo ahorra teclear comandos en la demo.
Cada proceso se lanza con el mismo comando que se podría escribir a mano
(``py -m nodo ...``, ``py -m madre ...``) y el panel lo muestra tal cual.

* Un hilo lector por proceso vacía su stdout (sin él, el pipe se llenaría y el
  hijo se bloquearía al escribir su bitácora). De esas líneas el panel saca
  qué genes tiene cada madre, para pintarla de su color: lo mismo que se lee en
  su consola, nada que el sistema no muestre ya.
* Los **reemplazos** no los lanza el panel sino las madres (la regeneración es
  de ellas). El panel los encuentra por su registro en ``run/``
  (``madre/lanzador.py``) y sigue su bitácora en ``logs/``. "Detener todo"
  también los termina.
"""

import os
import random
import re
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from comun import codigos
from comun.bitacora import CARPETA_LOGS
from madre import lanzador

RAIZ = Path(__file__).resolve().parent.parent
PUERTO_BASE = 5000
MAX_LINEAS = 2000
MADRES_POR_NODO = 4

NODO = "nodo"
GUI = "GUI"
MADRE = "madre"
GESTOR = "gestor"
CLON = "reemplazo"

VACIA = "vacía"               # modos de la configuración mínima
CON_SERVICIOS = "con servicios"

_GENES = re.compile(r"genes: (.+)$")
_SUSTITUIDO = re.compile(r"\[GEN_SUSTITUIDO\] (\S+) → (\S+)")


def puerto(k: int) -> int:
    return PUERTO_BASE + k


def endpoint(k: int) -> str:
    return f"127.0.0.1:{puerto(k)}"


@dataclass
class Proceso:
    nombre: str
    tipo: str          # NODO, GUI, MADRE, GESTOR o CLON
    fila: int          # número de nodo al que pertenece
    comando: list[str]
    popen: subprocess.Popen | None = None
    pid_clon: int | None = None          # CLON: no es hijo del panel
    inicio: float = field(default_factory=time.time)
    lineas: deque = field(default_factory=lambda: deque(maxlen=MAX_LINEAS))
    total_lineas: int = 0  # para que el visor sepa cuántas líneas nuevas hay
    tumbado: bool = False  # lo terminó el panel (en Windows su código queda en 1)
    genes: list[str] = field(default_factory=list)   # 'SUM@1.0' (madres y reemplazos)
    muda: bool = False
    terminado: bool = False                           # CLON que ya no vive
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def agregar_linea(self, linea: str) -> None:
        with self._lock:
            self.lineas.append(linea)
            self.total_lineas += 1
        self._leer_genes(linea)

    def _leer_genes(self, linea: str) -> None:
        """Lo que la madre escribe en su bitácora al cambiar de genes."""
        if "[GEN_ACTIVO]" in linea or "[GEN_BAJA]" in linea:
            m = _GENES.search(linea)
            if m:
                texto = m.group(1).strip()
                self.genes = [] if texto.startswith("ninguno") else [
                    g.strip() for g in texto.split(",") if g.strip()]
        elif "[GEN_SUSTITUIDO]" in linea:
            m = _SUSTITUIDO.search(linea)
            if m:
                self.genes = [m.group(2) if g == m.group(1) else g for g in self.genes]

    @property
    def codigos(self) -> list[str]:
        return [g.partition("@")[0] for g in self.genes]

    def lineas_desde(self, vistas: int | None) -> tuple[list[str], int]:
        """Las líneas posteriores a las ``vistas`` (todas si es None) y el total actual."""
        with self._lock:
            total = self.total_lineas
            if vistas is None:
                return list(self.lineas), total
            n = min(total - vistas, len(self.lineas))
            return (list(self.lineas)[-n:] if n > 0 else []), total

    @property
    def pid(self) -> int:
        return self.popen.pid if self.popen is not None else self.pid_clon

    @property
    def vivo(self) -> bool:
        if self.popen is None:
            return not self.terminado
        return self.popen.poll() is None

    @property
    def estado(self) -> str:
        if self.vivo:
            return "vivo"
        if self.tumbado:
            return "tumbado"
        if self.popen is None:
            return "terminado"
        return f"terminado ({self.popen.poll()})"

    def comando_legible(self) -> str:
        partes = ["py", *self.comando[2:]]  # [python, -u, -m, ...] -> py -m ...
        return " ".join(f'"{p}"' if " " in p else p for p in partes)


class Procesos:
    def __init__(self, raiz: Path = RAIZ):
        self.raiz = raiz
        self.procesos: list[Proceso] = []
        self._lock = threading.Lock()
        # (pid, inicio) -> reemplazo visto en run/: Windows recicla PIDs, así que un
        # reemplazo nuevo puede traer el PID de uno que ya murió.
        self._clones: dict[tuple[int, float], Proceso] = {}
        self._seguir: dict[tuple[int, float], tuple[Path | None, int]] = {}  # -> (log, leídos)

    # ---------------------------------------------------------------- consulta

    def vivos(self, fila: int | None = None, tipo: str | None = None) -> list[Proceso]:
        with self._lock:
            return [p for p in self.procesos if p.vivo
                    and (fila is None or p.fila == fila) and (tipo is None or p.tipo == tipo)]

    def madres(self, fila: int | None = None) -> list[Proceso]:
        """Madres vivas (originales y reemplazos) de un nodo, en orden de nombre."""
        return sorted((p for p in self.vivos(fila) if p.tipo in (MADRE, CLON)),
                      key=lambda p: _natural(p.nombre))

    def con_gen(self, codigo: str, fila: int | None = None) -> list[Proceso]:
        return [p for p in self.madres(fila) if codigo in p.codigos and not p.muda]

    def filas(self) -> list[int]:
        """Números de nodo que han existido (las filas de la matriz)."""
        with self._lock:
            return sorted({p.fila for p in self.procesos})

    # ---------------------------------------------------------------- lanzar

    def lanzar_nodo(self, k: int, geometria: str | None = None) -> Proceso:
        """Lanza el nodo k. Su semilla es un nodo vivo elegido AL AZAR (ninguno si es el
        primero): demuestra que basta conocer a cualquiera y que ningún nodo es especial."""
        otros = [p.fila for p in self.vivos(tipo=NODO) if p.fila != k]
        args = ["nodo", "--puerto", str(puerto(k)), "--nombre", f"Nodo {k}"]
        if otros:
            args += ["--semillas", endpoint(random.choice(otros))]
        if geometria:
            args += ["--geometria", geometria]
        return self._lanzar(f"Nodo {k}", NODO, k, args)

    def lanzar_gui(self, k: int, geometria: str | None = None) -> Proceso:
        n = len([p for p in self.procesos if p.tipo == GUI and p.fila == k])
        nombre = f"GUI-{k}{_sufijo(n)}"
        args = ["interfaz", "--nodo", endpoint(k), "--nombre", nombre]
        if geometria:
            args += ["--geometria", geometria]
        return self._lanzar(nombre, GUI, k, args)

    def lanzar_gestor(self, k: int, geometria: str | None = None) -> Proceso:
        """Uno por nodo, y solo cuando el usuario lo pide (nunca en la configuración)."""
        args = ["gestor", "--nodo", endpoint(k), "--nombre", f"G-N{k}"]
        if geometria:
            args += ["--geometria", geometria]
        return self._lanzar(f"G-N{k}", GESTOR, k, args)

    def lanzar_madre(self, k: int, *, gen: str | None = None, muda: bool = False) -> Proceso:
        """Vacía (``M3-N2``), con un gen del banco (``SUM-N2``) o muda (``SUM-N2m``)."""
        usados = {p.nombre for p in self.procesos}
        if gen is None:
            i = 1
            while f"M{i}-N{k}" in usados:
                i += 1
            nombre = f"M{i}-N{k}"
        else:
            base = f"{gen}-N{k}{'m' if muda else ''}"
            n = 0
            while (nombre := base + _sufijo(n)) in usados:
                n += 1
        args = ["madre", "--nodo", endpoint(k), "--nombre", nombre]
        if gen:
            args += ["--genes", f"{gen}@1.0"]
        if muda:
            args.append("--mudo")
        p = self._lanzar(nombre, MADRE, k, args)
        p.muda = muda
        return p

    def configuracion(self, k: int, modo: str) -> list[Proceso]:
        """Lo que le falte al nodo k para tener 1 GUI y 4 madres (sin gestor)."""
        lanzados = []
        faltan = MADRES_POR_NODO - len(self.madres(k))
        if modo == CON_SERVICIOS:
            for s in codigos.SERVICIOS:
                if faltan > 0 and not self.con_gen(s, k):
                    lanzados.append(self.lanzar_madre(k, gen=s))
                    faltan -= 1
        for _ in range(max(0, faltan)):
            lanzados.append(self.lanzar_madre(k))
        return lanzados

    def _lanzar(self, nombre: str, tipo: str, fila: int, args: list[str]) -> Proceso:
        comando = [sys.executable, "-u", "-m", *args]
        popen = subprocess.Popen(
            comando, cwd=self.raiz, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        proceso = Proceso(nombre, tipo, fila, comando, popen)
        with self._lock:
            self.procesos.append(proceso)
        threading.Thread(target=_leer, args=(proceso,), name=f"lector-{nombre}",
                         daemon=True).start()
        return proceso

    # ------------------------------------------------------------ reemplazos

    def buscar_reemplazos(self) -> None:
        """Agrega los reemplazos nuevos de ``run/``, marca los que murieron y lee lo
        nuevo de sus bitácoras (``logs/``)."""
        registrados = {(int(d["pid"]), float(d["inicio"])): d for d in lanzador.registrados()}
        with self._lock:
            for clave, d in registrados.items():
                if clave not in self._clones:
                    p = Proceso(d["nombre"], CLON, _fila(d.get("nodo")), list(d.get("comando", [])),
                                pid_clon=clave[0], inicio=clave[1])
                    self._clones[clave] = p
                    self.procesos.append(p)
            for clave, p in self._clones.items():
                if not p.terminado and clave not in registrados:
                    p.terminado = True
        for clave, p in list(self._clones.items()):
            self._leer_log(clave, p)

    def _leer_log(self, clave: tuple[int, float], p: Proceso) -> None:
        ruta, leidos = self._seguir.get(clave, (None, 0))
        if ruta is None:
            ruta = _log_de(p)
            if ruta is None:
                return
        try:
            with open(ruta, encoding="utf-8", errors="replace") as f:
                f.seek(leidos)
                nuevo = f.read()
                leidos = f.tell()
        except OSError:
            return
        self._seguir[clave] = (ruta, leidos)
        for linea in nuevo.splitlines():
            p.agregar_linea(linea)

    # ---------------------------------------------------------------- tumbar

    def tumbar(self, proceso: Proceso) -> None:
        """Simula una caída: termina el proceso sin avisarle a nadie."""
        if not proceso.vivo:
            return
        proceso.tumbado = True
        if proceso.popen is None:
            datos = next((d for d in lanzador.registrados() if int(d["pid"]) == proceso.pid),
                         None)
            if datos is not None:
                lanzador.terminar(datos)
            proceso.terminado = True
            return
        try:
            proceso.popen.terminate()
        except OSError:
            pass

    def detener_todo(self) -> None:
        """Todo lo del panel y todos los reemplazos registrados en ``run/``."""
        vivos = [p for p in self.vivos() if p.popen is not None]
        for d in lanzador.registrados():
            lanzador.terminar(d)
        for p in vivos:
            self.tumbar(p)
        for p in vivos:
            try:
                p.popen.wait(3)
            except subprocess.TimeoutExpired:
                p.popen.kill()
        with self._lock:
            for p in self._clones.values():
                p.terminado = True


def _leer(proceso: Proceso) -> None:
    try:
        for linea in proceso.popen.stdout:
            proceso.agregar_linea(linea.rstrip("\n"))
    except (OSError, ValueError):
        pass


def _sufijo(n: int) -> str:
    return "" if n == 0 else chr(ord("a") + n)   # SUM-N2, SUM-N2b, SUM-N2c…


def _natural(texto: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", texto)]


def _fila(nodo_nombre) -> int:
    m = re.search(r"(\d+)$", str(nodo_nombre or ""))
    return int(m.group(1)) if m else 0


def _log_de(p: Proceso) -> Path | None:
    """La bitácora del reemplazo: ``logs/<nombre>-<hash8>.log`` creada tras su arranque."""
    base = re.sub(r"[^\w.-]+", "_", p.nombre).strip("_")
    candidatos = [r for r in CARPETA_LOGS.glob(f"{base}-*.log")
                  if r.stat().st_mtime >= p.inicio - 5]
    return max(candidatos, key=lambda r: r.stat().st_mtime, default=None)
