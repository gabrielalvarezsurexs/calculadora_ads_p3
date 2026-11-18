"""DIV 1.0 — división. Dividir entre cero es una respuesta válida con error."""

SERVICIO = "DIV"
VERSION = "1.0"


def calcular(a, b):
    if b == 0:
        return None, "división entre cero"
    return a / b, None
