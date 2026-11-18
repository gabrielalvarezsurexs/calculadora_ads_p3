"""Formato de un microservicio (gen) en disco y lectura del banco local.

Un gen es una carpeta con dos archivos::

    microservicios/SUM/2.0/
        manifiesto.json   ← quién es, cómo se prueba y el sha256 de su programa
        servicio.py       ← el programa: SERVICIO, VERSION y calcular(a, b)

El **manifiesto** declara el sha256 del programa. Quien recibe un gen (una
madre, un gestor) recalcula el hash de los bytes que le llegaron y lo compara:
si alguien modificó el programa después de firmarlo, no coincide y el gen se
rechaza. ``herramientas/firmar.py`` escribe ese hash.

Este módulo no ejecuta nada: solo lee, valida la forma y calcula hashes. Cargar
el programa en memoria es cosa de ``madre/genes.py``.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from comun import codigos

MANIFIESTO = "manifiesto.json"
ARCHIVO = "servicio.py"
INTERFAZ = 1          # versión del contrato SERVICIO / VERSION / calcular(a, b)

_VERSION = re.compile(r"\d{1,3}\.\d{1,3}")
_HEX64 = re.compile(r"[0-9a-f]{64}")


# --- Identificadores ---------------------------------------------------------

def es_version(v) -> bool:
    return isinstance(v, str) and _VERSION.fullmatch(v) is not None


def clave_version(v: str) -> tuple[int, int]:
    """'2.10' > '2.9': las versiones se comparan como números, no como texto."""
    mayor, menor = v.split(".")
    return int(mayor), int(menor)


def gen_id(codigo: str, version: str) -> str:
    """('SUM', '1.0') -> 'SUM@1.0'."""
    return f"{codigo}@{version}"


def separar_gen_id(texto: str) -> tuple[str, str | None]:
    """'SUM@1.0' -> ('SUM', '1.0'); 'sum' -> ('SUM', None). ValueError si no sirve."""
    codigo, _, version = texto.strip().partition("@")
    codigo = codigo.upper()
    if not codigos.es_gen(codigo):
        raise ValueError(f"código de gen inválido: {codigo!r}")
    if version and not es_version(version):
        raise ValueError(f"versión inválida: {version!r} (se espera mayor.menor)")
    return codigo, version or None


def sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


# --- Manifiesto --------------------------------------------------------------

def validar_manifiesto(m) -> str | None:
    """Revisa la FORMA del manifiesto. Devuelve el problema o None."""
    if not isinstance(m, dict):
        return "el manifiesto no es un objeto"
    if not codigos.es_gen(m.get("codigo")):
        return f"código inválido: {m.get('codigo')!r}"
    if not es_version(m.get("version")):
        return f"versión inválida: {m.get('version')!r}"
    if not isinstance(m.get("nombre"), str) or not m["nombre"].strip():
        return "falta el nombre"
    if m.get("archivo") != ARCHIVO:
        return f"el programa debe llamarse {ARCHIVO}"
    if not isinstance(m.get("sha256"), str) or not _HEX64.fullmatch(m["sha256"]):
        return "sha256 declarado inválido"
    if m.get("interfaz") != INTERFAZ:
        return f"interfaz {m.get('interfaz')!r} no soportada (se espera {INTERFAZ})"
    pruebas = m.get("pruebas")
    if not isinstance(pruebas, list) or not pruebas:
        return "el manifiesto debe traer al menos una prueba"
    for p in pruebas:
        if not (isinstance(p, list) and len(p) == 3):
            return f"prueba mal formada: {p!r} (se espera [a, b, esperado])"
    if not isinstance(m.get("descripcion", ""), str):
        return "descripción inválida"
    return None


# --- Paquete: manifiesto + programa ------------------------------------------

@dataclass(frozen=True)
class Paquete:
    """Un gen tal como viaja o se guarda: el manifiesto y los bytes del programa."""

    manifiesto: dict
    fuente: bytes

    @property
    def codigo(self) -> str:
        return self.manifiesto["codigo"]

    @property
    def version(self) -> str:
        return self.manifiesto["version"]

    @property
    def id(self) -> str:
        return gen_id(self.codigo, self.version)

    @property
    def sha_declarado(self) -> str:
        return self.manifiesto["sha256"]

    @property
    def sha_real(self) -> str:
        return sha256(self.fuente)

    @property
    def integro(self) -> bool:
        return self.sha_real == self.sha_declarado

    def problema(self, max_bytes: int) -> str | None:
        """Validación completa SIN ejecutar: forma, tamaño e integridad."""
        motivo = validar_manifiesto(self.manifiesto)
        if motivo:
            return f"manifiesto inválido: {motivo}"
        if len(self.fuente) > max_bytes:
            return f"programa de {len(self.fuente)} bytes > {max_bytes}"
        if not self.integro:
            return (f"sha256 no coincide (declarado {self.sha_declarado[:8]}, "
                    f"real {self.sha_real[:8]})")
        return None

    # Por el Campo de Datos el programa viaja como texto UTF-8 dentro del JSON.
    def a_mensaje(self) -> dict:
        return {"manifiesto": self.manifiesto, "fuente": self.fuente.decode("utf-8")}

    @classmethod
    def de_mensaje(cls, cuerpo: dict) -> "Paquete":
        """ValueError si el cuerpo no trae un paquete con la forma correcta."""
        manifiesto, fuente = cuerpo.get("manifiesto"), cuerpo.get("fuente")
        _exigir(isinstance(manifiesto, dict) and isinstance(fuente, str),
                "el mensaje no trae manifiesto y fuente")
        return cls(manifiesto, fuente.encode("utf-8"))


def _exigir(condicion: bool, motivo: str) -> None:
    """Datos que llegan de la red o del disco: si no tienen la forma, ValueError."""
    if not condicion:
        raise ValueError(motivo)


def leer(carpeta: Path) -> Paquete:
    """Lee un gen de disco. OSError / ValueError si no existe o no es JSON."""
    manifiesto = json.loads((carpeta / MANIFIESTO).read_text(encoding="utf-8"))
    _exigir(isinstance(manifiesto, dict), "el manifiesto no es un objeto")
    _exigir(manifiesto.get("archivo", ARCHIVO) == ARCHIVO,
            f"el programa debe llamarse {ARCHIVO}")
    return Paquete(manifiesto, (carpeta / ARCHIVO).read_bytes())


def escribir(carpeta: Path, paquete: Paquete) -> None:
    """Escribe el gen byte por byte (sin traducir finales de línea: el sha256 manda)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(paquete.manifiesto, ensure_ascii=False, indent=2) + "\n"
    (carpeta / MANIFIESTO).write_text(texto, encoding="utf-8", newline="\n")
    (carpeta / ARCHIVO).write_bytes(paquete.fuente)


# --- Banco local -------------------------------------------------------------

def carpetas(banco: Path) -> list[Path]:
    """Todas las carpetas ``CÓDIGO/versión`` con manifiesto, ordenadas."""
    if not banco.is_dir():
        return []
    encontradas = [m.parent for m in banco.glob(f"*/*/{MANIFIESTO}")
                   if codigos.es_gen(m.parent.parent.name) and es_version(m.parent.name)]
    return sorted(encontradas, key=lambda c: (c.parent.name, clave_version(c.name)))


def resolver(banco: Path, texto: str) -> Path:
    """'SUM@1.0' -> su carpeta; 'SUM' -> la versión más alta ÍNTEGRA del banco.

    LookupError si no existe. Pedir sin versión nunca elige un gen manipulado.
    """
    codigo, version = separar_gen_id(texto)
    if version:
        carpeta = banco / codigo / version
        if not (carpeta / MANIFIESTO).is_file():
            raise LookupError(f"{gen_id(codigo, version)} no está en {banco.name}/")
        return carpeta
    candidatas = []
    for carpeta in carpetas(banco):
        if carpeta.parent.name != codigo:
            continue
        try:
            if leer(carpeta).integro:
                candidatas.append(carpeta)
        except (OSError, ValueError):
            continue
    if not candidatas:
        raise LookupError(f"no hay ninguna versión íntegra de {codigo} en {banco.name}/")
    return candidatas[-1]
