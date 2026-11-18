"""SUM 2.0 — suma decimal exacta.

Convierte cada operando desde su representación más corta (repr) a Decimal, suma
sin error de redondeo binario y regresa el float más cercano: 0.1 + 0.2 = 0.3.
"""

from decimal import Decimal

SERVICIO = "SUM"
VERSION = "2.0"


def calcular(a, b):
    exacta = Decimal(repr(a)) + Decimal(repr(b))
    return float(exacta), None
