"""Levantar el proceso de un reemplazo (PLAN §6.3, paso 5) y llevar su registro.

El clonador lanza ``python -m madre --reemplaza … --copiar …``: el MISMO
programa base que cualquier madre, vacío. El proceso queda **desacoplado** de
quien lo lanzó (``DETACHED_PROCESS`` + grupo propio): si el clonador muere, el
reemplazo sigue vivo. No tiene consola; su bitácora va a ``logs/``.

Cada lanzamiento deja un archivo en ``run/`` con el PID, el nombre y la hora de
arranque. Lo usa el panel (que no lanzó esos procesos) para mostrarlos y para
"Detener todo"; el reemplazo lo borra al cerrarse ordenadamente. Antes de
terminar un PID se comprueba que el proceso vivo sea el mismo que se registró
(su hora de creación): Windows recicla los PIDs.

Se usa el intérprete base (no el lanzador del ``.venv``) para que el PID
registrado sea el del proceso que de verdad corre la madre. Basta la librería
estándar y ``cwd`` = la raíz del proyecto.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from comun import config

_DESACOPLADO = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
_TOLERANCIA_INICIO = 10.0                # s entre la hora registrada y la de creación del PID


def interprete() -> str:
    return getattr(sys, "_base_executable", None) or sys.executable


def archivo(nombre: str, pid: int, carpeta: Path | None = None) -> Path:
    seguro = re.sub(r"[^\w.-]+", "_", nombre).strip("_") or "madre"
    return (carpeta or config.DIR_RUN) / f"{seguro}-{pid}.json"


def lanzar_proceso(encargo) -> dict:
    """El ``Lanzador`` de producción: un proceso nuevo por reemplazo. Devuelve su
    registro (``pid``, ``inicio``, ``archivo``), que es lo que recibe ``terminar``."""
    comando = [interprete(), "-u", "-m", "madre", *encargo.argumentos()]
    opciones = {"creationflags": _DESACOPLADO} if os.name == "nt" else {"start_new_session": True}
    popen = subprocess.Popen(comando, cwd=config.RAIZ, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"}, **opciones)
    ruta = registrar(encargo.nombre, popen.pid, comando, reemplaza=encargo.perdida,
                     clonador=encargo.clonador, nodo=encargo.nodo_nombre)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {**datos, "archivo": str(ruta)}


def registrar(nombre: str, pid: int, comando: list[str], **extra) -> Path:
    ruta = archivo(nombre, pid)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"nombre": nombre, "pid": pid, "inicio": time.time(),
                                "comando": comando, **extra}, ensure_ascii=False),
                    encoding="utf-8")
    return ruta


def olvidar(nombre: str, pid: int | None = None) -> None:
    """El reemplazo se cierra ordenadamente: borra su registro."""
    try:
        archivo(nombre, pid or os.getpid()).unlink(missing_ok=True)
    except OSError:
        pass


def registrados(carpeta: Path | None = None) -> list[dict]:
    """Los reemplazos lanzados que siguen vivos. Los registros de procesos muertos se borran."""
    vivos = []
    for ruta in sorted((carpeta or config.DIR_RUN).glob("*.json")):
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            pid, inicio = int(datos["pid"]), float(datos["inicio"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if es_el_mismo(pid, inicio):
            vivos.append({**datos, "archivo": str(ruta)})
        else:
            ruta.unlink(missing_ok=True)
    return vivos


def terminar(datos: dict) -> bool:
    """Termina un reemplazo registrado (como ``tumbar``: sin avisar a nadie)."""
    pid = int(datos["pid"])
    if not es_el_mismo(pid, float(datos["inicio"])):
        return False
    ok = _terminar(pid)
    if ok and datos.get("archivo"):
        Path(datos["archivo"]).unlink(missing_ok=True)
    return ok


# --- Procesos del sistema operativo -------------------------------------------------

def es_el_mismo(pid: int, inicio: float) -> bool:
    """¿Vive ``pid`` y es el proceso que arrancó a la hora ``inicio``?"""
    creado = _creacion(pid)
    return creado is not None and abs(creado - inicio) <= _TOLERANCIA_INICIO


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    _k32.GetProcessTimes.argtypes = (wintypes.HANDLE, *[ctypes.POINTER(wintypes.FILETIME)] * 4)
    _k32.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _CONSULTA, _TERMINAR, _ACTIVO = 0x1000, 0x0001, 259

    def _creacion(pid: int) -> float | None:
        h = _k32.OpenProcess(_CONSULTA, False, pid)
        if not h:
            return None
        try:
            codigo = wintypes.DWORD()
            if not _k32.GetExitCodeProcess(h, ctypes.byref(codigo)) or codigo.value != _ACTIVO:
                return None
            tiempos = [wintypes.FILETIME() for _ in range(4)]
            if not _k32.GetProcessTimes(h, *map(ctypes.byref, tiempos)):
                return None
            ft = tiempos[0].dwHighDateTime << 32 | tiempos[0].dwLowDateTime
            return ft / 1e7 - 11_644_473_600   # de 1601 (FILETIME) a 1970
        finally:
            _k32.CloseHandle(h)

    def _terminar(pid: int) -> bool:
        h = _k32.OpenProcess(_TERMINAR, False, pid)
        if not h:
            return False
        try:
            return bool(_k32.TerminateProcess(h, 1))
        finally:
            _k32.CloseHandle(h)
else:  # pragma: no cover - el proyecto se entrega en Windows
    import signal

    def _creacion(pid: int) -> float | None:
        try:
            os.kill(pid, 0)
            return Path(f"/proc/{pid}").stat().st_ctime
        except OSError:
            return None

    def _terminar(pid: int) -> bool:
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except OSError:
            return False
