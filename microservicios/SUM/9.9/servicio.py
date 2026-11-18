"""SUM 9.9 — suma "turbo".

Gen MANIPULADO a propósito para la demo: este archivo se modificó después de
firmar el manifiesto (se le agregó el "+ 1"), así que su sha256 ya no coincide
con el declarado. Toda madre y todo gestor deben rechazarlo sin ejecutarlo.
"""

SERVICIO = "SUM"
VERSION = "9.9"


def calcular(a, b):
    return a + b + 1, None
