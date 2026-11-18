"""Catálogo de Códigos de Contenido.

En ADS un mensaje no dice A QUIÉN va, sino QUÉ es. Cada célula mira el código
y decide si le interesa. Este catálogo lo usan las células; el nodo NO lo
importa, porque solo inunda sin interpretar el contenido.

Hay dos familias:

* **Operaciones** ``<GEN>_<TIPO>``: ``SUM_REQ``, ``SUM_ACK``, ``SUM_RES``,
  ``SUM_FIN``. ``<GEN>`` es el código de un microservicio. Una célula madre
  atiende las operaciones de los genes que tiene **activos**, sean cuales sean:
  el programa base no conoce ``SUM`` ni ``DIV``; solo sabe cargar genes.
* **Sistema**: latidos (``CEL_LAT``, ``NODO_LAT``), cierre ordenado
  (``CEL_ADIOS``), órdenes del gestor (``GEN_*``, ``CEL_RETIRO``),
  regeneración (``CLON_*``) y topología (``TOPO_*``). Sus prefijos están
  reservados: ningún gen puede llamarse así.
"""

import re

from comun import mensajes

# Los cuatro servicios de la calculadora (lo que ofrece la GUI). Una madre puede
# cargar cualquier otro gen con un código válido; la GUI solo sabe pedir estos.
SERVICIOS = ("SUM", "SUB", "MUL", "DIV")

NOMBRES = {"SUM": "Suma", "SUB": "Resta", "MUL": "Multiplicación", "DIV": "División"}
SIMBOLOS = {"SUM": "+", "SUB": "−", "MUL": "×", "DIV": "÷"}

# --- Operaciones ------------------------------------------------------------
REQ = "REQ"   # INICIO del evento (GUI)
ACK = "ACK"   # CONFIRMACIÓN: la madre recibió y participa
RES = "RES"   # PROCESAMIENTO: el resultado
FIN = "FIN"   # FINALIZACIÓN: la GUI cierra el evento
TIPOS = (REQ, ACK, RES, FIN)

# --- Sistema ----------------------------------------------------------------
CEL_LAT = "CEL_LAT"          # latido de una célula (madre: con sus genes)
CEL_ADIOS = "CEL_ADIOS"      # cierre ordenado: NO es una pérdida, no se regenera
CEL_RETIRO = "CEL_RETIRO"    # gestor → madre: ciérrate ordenadamente
NODO_LAT = mensajes.NODO_LAT  # latido de un nodo (vecinos reales, para la topología)

GEN_INYECTA = "GEN_INYECTA"  # gestor → madre: instala este programa
GEN_BAJA = "GEN_BAJA"        # gestor → madre: descarga este gen
GEN_ACK = "GEN_ACK"          # madre → gestor: recibí la orden
GEN_RES = "GEN_RES"          # madre → gestor: resultado del ciclo de vida
GEN_PIDE = "GEN_PIDE"        # cualquier madre → todos: ¿quién tiene este gen?
GEN_ENTREGA = "GEN_ENTREGA"  # quien lo tenga → la que pidió

CLON_AVISO = "CLON_AVISO"    # el clonador anuncia que regenera una pérdida
CLON_LISTO = "CLON_LISTO"    # el reemplazo ya copió sus genes

TOPO_REQ = "TOPO_REQ"        # gestor: consulta inmediata de topología
TOPO_RES = "TOPO_RES"

SONDA_PRUEBA = "SONDA_PRUEBA"  # solo lo inyecta la sonda; ninguna célula lo procesa

SISTEMA = (CEL_LAT, CEL_ADIOS, CEL_RETIRO, NODO_LAT, GEN_INYECTA, GEN_BAJA, GEN_ACK, GEN_RES,
           GEN_PIDE, GEN_ENTREGA, CLON_AVISO, CLON_LISTO, TOPO_REQ, TOPO_RES, SONDA_PRUEBA)

# Prefijos que no puede usar un gen (chocarían con los códigos de sistema).
RESERVADOS = frozenset(c.partition("_")[0] for c in SISTEMA)

_GEN = re.compile(r"[A-Z]{3,4}")


def es_gen(cod) -> bool:
    """¿Es un código válido de microservicio? (3–4 mayúsculas, no reservado)."""
    return isinstance(cod, str) and _GEN.fullmatch(cod) is not None and cod not in RESERVADOS


def codigo(servicio: str, tipo: str) -> str:
    """codigo("SUM", REQ) -> "SUM_REQ"."""
    return f"{servicio}_{tipo}"


def separar(cod) -> tuple[str, str] | None:
    """"SUM_REQ" -> ("SUM", "REQ"). None si no es un código de operación."""
    if not isinstance(cod, str):
        return None
    servicio, _, tipo = cod.partition("_")
    if es_gen(servicio) and tipo in TIPOS:
        return servicio, tipo
    return None
