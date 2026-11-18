"""Protocolo de foliado (§5.1 del enunciado): folio, huella, sello y rastro.

Definiciones (plan §5.1; son las del PDF):

* **Folio** — ``F-<hash8 de la GUI>-<n:04d>``. Lo genera la GUI con su propio
  contador, sin autoridad central. Es el mismo en todos los reintentos y viaja
  en **todos** los mensajes del evento (``X_REQ``, ``X_ACK``, ``X_RES``,
  ``X_FIN``): es lo que los correlaciona.
* **Huella** — identifica el origen y la trayectoria lógica de la solicitud::

      {"origen": <hash de la GUI>, "nodo": <hash del nodo de entrada>,
       "sello": sha256(origen|folio|código|a|b),
       "rastro": [[hash8, nombre, paso], ...]}

  El **sello** amarra folio, origen y datos: si alguien cambia un operando o
  se hace pasar por otra GUI, el sello ya no cuadra. El **rastro** dice quién
  participó y cómo: ``REQ`` (la GUI), ``ACK`` (cada madre que acusó), ``RES``
  (la que respondió) y ``FIN`` (la GUI). La ``ruta`` del sobre sigue siendo la
  trayectoria *física* (los nodos por los que pasó).
* **Evento** — el ciclo de vida de un folio, con cuatro fases: INICIO (la GUI
  publica ``X_REQ``), CONFIRMADO (llegan ``X_ACK`` del intento vigente hasta
  el mínimo), PROCESADO (una madre publica ``X_RES``) y FINALIZADO (la GUI
  acepta la respuesta o agota los intentos y publica ``X_FIN``).

Este módulo no hace red ni guarda estado: solo construye y valida.
"""

import hashlib
import json
import math
import re

from comun import hashes

# Pasos del rastro.
REQ = "REQ"
ACK = "ACK"
RES = "RES"
FIN = "FIN"
PASOS = (REQ, ACK, RES, FIN)

# Fases del evento, en orden.
INICIO = "INICIO"
CONFIRMADO = "CONFIRMADO"
PROCESADO = "PROCESADO"
FINALIZADO = "FINALIZADO"
FASES = (INICIO, CONFIRMADO, PROCESADO, FINALIZADO)

MAX_RASTRO = 32   # el rastro crece con cada acuse; con esto un mensaje nunca se infla
_FOLIO = re.compile(r"F-[0-9a-f]{8}-\d{4,}")
_HEX64 = re.compile(r"[0-9a-f]{64}")


def folio(origen: str, n: int) -> str:
    """El folio número ``n`` de la GUI ``origen``: ``F-1a2b3c4d-0007``."""
    return f"F-{hashes.corto(origen)}-{n:04d}"


def es_folio(valor) -> bool:
    return isinstance(valor, str) and _FOLIO.fullmatch(valor) is not None


# Lo administrativo también se correlaciona por folio, con su propia letra:
# ``O-…`` una orden de un gestor (GEN_INYECTA → GEN_ACK → GEN_RES) y ``P-…`` un
# pedido de gen de una madre (GEN_PIDE → GEN_ENTREGA).
ORDEN = "O"
PEDIDO = "P"
_ADMIN = {p: re.compile(rf"{p}-[0-9a-f]{{8}}-\d{{4,}}") for p in (ORDEN, PEDIDO)}


def folio_admin(prefijo: str, origen: str, n: int) -> str:
    """``folio_admin(ORDEN, gestor, 3)`` -> ``O-1a2b3c4d-0003``."""
    return f"{prefijo}-{hashes.corto(origen)}-{n:04d}"


def es_folio_admin(valor, prefijo: str) -> bool:
    return isinstance(valor, str) and _ADMIN[prefijo].fullmatch(valor) is not None


def sello(origen: str, folio_: str, codigo: str, a, b) -> str:
    """sha256(origen|folio|código|a|b). Determinista en cualquier célula.

    Los operandos se normalizan a ``float`` (``7`` y ``7.0`` sellan igual) y
    se escriben con ``repr``, que en Python ida y vuelta es exacto: el sello
    que calcula la madre con lo que recibió por JSON es el mismo que calculó
    la GUI. ``ValueError`` si un operando no es un número finito.
    """
    datos = [origen, folio_, codigo, _operando(a), _operando(b)]
    return hashlib.sha256("|".join(datos).encode("utf-8")).hexdigest()


def huella(origen: str, nodo: str | None, folio_: str, codigo: str, a, b,
           nombre: str) -> dict:
    """La huella con la que nace el evento: el rastro empieza con el REQ de la GUI."""
    return {"origen": origen, "nodo": nodo, "sello": sello(origen, folio_, codigo, a, b),
            "rastro": [[hashes.corto(origen), nombre, REQ]]}


def con_paso(h: dict, quien: str, nombre: str, paso: str) -> dict:
    """Copia de la huella con un paso más en el rastro (la original no cambia)."""
    rastro = [*rastro_de(h), [hashes.corto(quien), nombre, paso]]
    return {**h, "rastro": rastro[-MAX_RASTRO:]}


def con_pasos(h: dict, pasos) -> dict:
    """Varios pasos de una vez: ``pasos`` es un iterable de (hash, nombre, paso)."""
    rastro = [*rastro_de(h), *([hashes.corto(q), n, p] for q, n, p in pasos)]
    return {**h, "rastro": rastro[-MAX_RASTRO:]}


def rastro_de(h) -> list[list[str]]:
    """El rastro bien formado de una huella recibida por la red (lo demás se omite)."""
    rastro = h.get("rastro") if isinstance(h, dict) else None
    if not isinstance(rastro, list):
        return []
    return [list(p) for p in rastro if isinstance(p, list) and len(p) == 3
            and all(isinstance(x, str) for x in p) and p[2] in PASOS]


def texto_rastro(h) -> str:
    """``GUI-1 REQ → SUM-N1 ACK → SUM-N3 ACK → SUM-N3 RES → GUI-1 FIN``."""
    return " → ".join(f"{nombre} {paso}" for _, nombre, paso in rastro_de(h))


def validar(h, *, origen: str, folio_: str, codigo: str, a, b) -> str | None:
    """Revisa la huella de un ``X_REQ``. Devuelve el motivo del rechazo o None.

    ``origen`` es el del sobre: la huella debe decir lo mismo (nadie publica a
    nombre de otra GUI) y el sello recalculado debe coincidir (nadie cambió el
    folio, el código ni los operandos por el camino).
    """
    if not isinstance(h, dict):
        return "sin huella"
    if not es_folio(folio_):
        return f"folio inválido {folio_!r}"
    if h.get("origen") != origen:
        return "el origen de la huella no es quien publicó"
    if not isinstance(h.get("sello"), str) or not _HEX64.fullmatch(h["sello"]):
        return "sello mal formado"
    try:
        esperado = sello(origen, folio_, codigo, a, b)
    except ValueError as e:
        return str(e)
    if h["sello"] != esperado:
        return f"sello {hashes.corto(h['sello'])} no coincide (esperado {hashes.corto(esperado)})"
    return None


def _operando(x) -> str:
    try:
        if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x):
            return repr(float(x))
    except OverflowError:  # un entero enorme llegado por JSON
        pass
    raise ValueError(f"operando inválido {json.dumps(x, default=str)[:40]}")
