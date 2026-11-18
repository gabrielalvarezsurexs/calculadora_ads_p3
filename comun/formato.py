"""Presentación: cómo se escriben números y operaciones para un humano.

Los flotantes se muestran **exactos** (``repr``: la representación más corta
que vuelve al mismo número). Antes se redondeaban a 12 cifras, pero eso
escondía justo lo que demuestra el gen ``SUM 2.0``: en ``SUM 1.0``,
0.1 + 0.2 = 0.30000000000000004. Los enteros se muestran sin ``.0``.

Este módulo no decide nada: solo formatea.
"""

from comun import codigos


def numero(valor) -> str:
    """7.0 -> '7'; 0.1 + 0.2 -> '0.30000000000000004'; 1e20 -> '1e+20'."""
    if valor is None:
        return "?"
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        if valor.is_integer() and abs(valor) < 1e16:
            return str(int(valor))
        return repr(valor)
    return str(valor)


def operacion(a, servicio: str, b, resultado=None, error=None) -> str:
    """Texto de una operación para logs y ventanas: '7 ÷ 2 = 3.5'."""
    izquierda = f"{numero(a)} {codigos.SIMBOLOS.get(servicio, servicio)} {numero(b)}"
    if error:
        return f"{izquierda} → ERROR: {error}"
    if resultado is None:
        return izquierda
    return f"{izquierda} = {numero(resultado)}"


def milisegundos(segundos: float) -> str:
    return f"{segundos * 1000:.0f} ms"
