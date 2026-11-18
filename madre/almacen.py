"""El disco propio de cada célula madre.

    datos/celulas/<nombre>-<hash8>/genes/<CÓDIGO>/<versión>/{manifiesto.json, servicio.py}

Requisito M1 del enunciado: el microservicio debe **existir físicamente en
disco**. Por eso todo gen pasa por aquí antes de cargarse, venga de donde venga:

* del banco local ``microservicios/`` (madre que arranca con ``--genes``);
* de una inyección del gestor por el Campo de Datos (``GEN_INYECTA``);
* de otra célula que se lo entrega (``GEN_ENTREGA``), al regenerarse.

La madre carga a memoria siempre desde ESTA copia, nunca desde el banco ni
desde el mensaje: así lo que corre es exactamente lo que quedó en su disco.

Las rutas se construyen solo con códigos y versiones ya validados y se
comprueba que queden dentro del almacén: un mensaje no puede hacer que la madre
escriba fuera de su carpeta.
"""

import shutil
import threading
from pathlib import Path

from comun import codigos, config, microservicios
from comun.microservicios import Paquete

# Por dónde llegó un gen (bitácora y GEN_RES).
BANCO = "banco local"
INYECCION = "inyección del gestor"
ENTREGA = "entrega por el Campo de Datos"


class FueraDelAlmacen(ValueError):
    """Una ruta que saldría de la carpeta de la madre."""


class Almacen:
    def __init__(self, raiz: Path):
        self.raiz = raiz.resolve()
        self._lock = threading.Lock()

    def carpeta(self, codigo: str, version: str) -> Path:
        """La carpeta del gen, confinada al almacén."""
        if not codigos.es_gen(codigo) or not microservicios.es_version(version):
            raise FueraDelAlmacen(f"gen inválido: {codigo!r}@{version!r}")
        ruta = (self.raiz / codigo / version).resolve()
        if not ruta.is_relative_to(self.raiz):
            raise FueraDelAlmacen(f"{ruta} está fuera de {self.raiz}")
        return ruta

    def guardar(self, paquete: Paquete) -> Path:
        """Escribe el gen (manifiesto + programa) y devuelve su carpeta."""
        carpeta = self.carpeta(paquete.codigo, paquete.version)
        with self._lock:
            microservicios.escribir(carpeta, paquete)
        return carpeta

    def copiar_del_banco(self, origen: Path) -> Path:
        """Copia una carpeta del banco local tal cual (byte por byte)."""
        paquete = microservicios.leer(origen)
        return self.guardar(paquete)

    def leer(self, codigo: str, version: str) -> Paquete:
        with self._lock:
            return microservicios.leer(self.carpeta(codigo, version))

    def borrar(self, codigo: str, version: str) -> None:
        carpeta = self.carpeta(codigo, version)
        with self._lock:
            shutil.rmtree(carpeta, ignore_errors=True)
            padre = carpeta.parent
            if padre != self.raiz and padre.is_dir() and not any(padre.iterdir()):
                padre.rmdir()

    def ids(self) -> list[str]:
        """Los genes que hay en disco ahora mismo (``SUM@1.0``…)."""
        with self._lock:
            return [microservicios.gen_id(c.parent.name, c.name)
                    for c in microservicios.carpetas(self.raiz)]

    def relativa(self, ruta: Path) -> str:
        """Ruta legible para bitácoras: relativa a la raíz del proyecto si se puede."""
        try:
            return ruta.relative_to(config.RAIZ).as_posix()
        except ValueError:
            return ruta.as_posix()
