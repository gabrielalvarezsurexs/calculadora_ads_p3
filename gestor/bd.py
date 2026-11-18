"""Base de datos del gestor (SQLite, librería estándar): el catálogo de genes y
el historial de órdenes (PLAN §4.2).

    datos/gestor/<nombre>.sqlite3
      microservicio(codigo, version, nombre, descripcion, manifiesto, fuente,
                    sha256_declarado, sha256_real, importado)
      orden(folio, accion, destino, destino_nombre, codigo, version, estado,
            detalle, ms, creada, cerrada)

Se llena **importando la carpeta** ``microservicios/`` (al abrir el gestor y con
el botón *Importar carpeta*). Guarda el programa completo, no una ruta: así el
gestor puede inyectarlo por el Campo de Datos y entregarlo a una madre que lo
pida (``GEN_PIDE``) aunque la carpeta ya no esté.

Se guardan **los dos** sha256, el declarado en el manifiesto y el calculado de
los bytes: si no coinciden, el gen está manipulado (``SUM 9.9``) y la ventana
lo marca con ✘. El gestor no lo esconde ni lo bloquea: si alguien lo inyecta,
es la madre la que lo rechaza (ella decide qué corre en su memoria).

Cada gestor tiene su propia BD: ninguna es "la oficial" y perder una no le
quita nada al sistema.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path

from comun import microservicios
from comun.microservicios import Paquete
from comun.pedidos import coincide

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS microservicio (
  codigo TEXT NOT NULL, version TEXT NOT NULL, nombre TEXT, descripcion TEXT,
  manifiesto TEXT NOT NULL, fuente TEXT NOT NULL,
  sha256_declarado TEXT, sha256_real TEXT NOT NULL,
  importado TEXT NOT NULL,
  PRIMARY KEY (codigo, version));
CREATE TABLE IF NOT EXISTS orden (
  folio TEXT PRIMARY KEY, accion TEXT NOT NULL, destino TEXT, destino_nombre TEXT,
  codigo TEXT, version TEXT, estado TEXT NOT NULL, detalle TEXT, ms INTEGER,
  creada TEXT NOT NULL, cerrada TEXT);
"""


def _ahora() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class BaseDatos:
    def __init__(self, ruta: Path | str):
        """``ruta`` = archivo ``.sqlite3`` (se crea con su carpeta) o ``":memory:"``."""
        if ruta != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.ruta = ruta
        self._lock = threading.Lock()  # una conexión compartida por la ventana y la red
        self._con = sqlite3.connect(str(ruta), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        with self._lock, self._con:
            self._con.executescript(_ESQUEMA)

    def cerrar(self) -> None:
        with self._lock:
            self._con.close()

    # ---------------------------------------------------------------- catálogo

    def importar(self, carpeta: Path) -> list[str]:
        """Lee cada ``CÓDIGO/versión`` de ``carpeta`` y la guarda (o actualiza).

        Devuelve los ids importados. Un gen ilegible se salta; uno manipulado SÍ
        se importa (marcado), para poder mostrar que las madres lo rechazan.
        """
        importados = []
        for sub in microservicios.carpetas(carpeta):
            try:
                paquete = microservicios.leer(sub)
                fuente = paquete.fuente.decode("utf-8")
            except (OSError, ValueError):
                continue
            if microservicios.validar_manifiesto(paquete.manifiesto):
                continue
            m = paquete.manifiesto
            with self._lock, self._con:
                self._con.execute(
                    "INSERT OR REPLACE INTO microservicio VALUES (?,?,?,?,?,?,?,?,?)",
                    (paquete.codigo, paquete.version, m.get("nombre"), m.get("descripcion", ""),
                     json.dumps(m, ensure_ascii=False), fuente, paquete.sha_declarado,
                     paquete.sha_real, _ahora()))
            importados.append(paquete.id)
        return importados

    def catalogo(self) -> list[dict]:
        """Todos los genes, ordenados por código y versión (numérica)."""
        with self._lock:
            filas = self._con.execute(
                "SELECT codigo, version, nombre, descripcion, sha256_declarado, sha256_real, "
                "importado FROM microservicio").fetchall()
        genes = [{"codigo": f["codigo"], "version": f["version"], "nombre": f["nombre"],
                  "descripcion": f["descripcion"], "sha8": f["sha256_real"][:8],
                  "integro": f["sha256_declarado"] == f["sha256_real"],
                  "id": microservicios.gen_id(f["codigo"], f["version"]),
                  "importado": f["importado"]} for f in filas]
        return sorted(genes, key=lambda g: (g["codigo"], microservicios.clave_version(
            g["version"])))

    def paquete(self, codigo: str, version: str) -> Paquete | None:
        with self._lock:
            f = self._con.execute(
                "SELECT manifiesto, fuente FROM microservicio WHERE codigo=? AND version=?",
                (codigo, version)).fetchone()
        if f is None:
            return None
        return Paquete(json.loads(f["manifiesto"]), f["fuente"].encode("utf-8"))

    def buscar(self, codigo: str, version: str, sha: str | None) -> Paquete | None:
        """Para ``GEN_PIDE``: el gen exacto, solo si está íntegro."""
        paquete = self.paquete(codigo, version)
        if paquete is None or not paquete.integro or not coincide(sha, paquete.sha_real):
            return None
        return paquete

    def version_base(self, codigo: str) -> str | None:
        """La versión íntegra MÁS ANTIGUA de ``codigo`` (la que instala "Distribuir")."""
        versiones = [g["version"] for g in self.catalogo() if g["codigo"] == codigo
                     and g["integro"]]
        return versiones[0] if versiones else None

    # ----------------------------------------------------------------- órdenes

    def orden_nueva(self, folio: str, accion: str, destino: str | None,
                    destino_nombre: str | None, codigo: str | None, version: str | None,
                    estado: str) -> None:
        with self._lock, self._con:
            self._con.execute(
                "INSERT OR REPLACE INTO orden (folio, accion, destino, destino_nombre, codigo, "
                "version, estado, creada) VALUES (?,?,?,?,?,?,?,?)",
                (folio, accion, destino, destino_nombre, codigo, version, estado, _ahora()))

    def orden_estado(self, folio: str, estado: str, detalle: str | None = None,
                     ms: int | None = None, *, cerrada: bool = False) -> None:
        with self._lock, self._con:
            self._con.execute(
                "UPDATE orden SET estado=?, detalle=COALESCE(?, detalle), ms=COALESCE(?, ms), "
                "cerrada=CASE WHEN ? THEN ? ELSE cerrada END WHERE folio=?",
                (estado, detalle, ms, cerrada, _ahora(), folio))

    def ordenes(self, limite: int = 200) -> list[dict]:
        """Las más recientes primero."""
        with self._lock:
            filas = self._con.execute(
                "SELECT * FROM orden ORDER BY creada DESC, folio DESC LIMIT ?",
                (limite,)).fetchall()
        return [dict(f) for f in filas]
