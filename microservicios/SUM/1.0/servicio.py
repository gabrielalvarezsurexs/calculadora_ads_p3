"""SUM 1.0 — suma en punto flotante (IEEE 754), como la calculadora original.

0.1 + 0.2 da 0.30000000000000004: así suman los float. La versión 2.0 lo corrige.
"""

SERVICIO = "SUM"
VERSION = "1.0"


def calcular(a, b):
    return a + b, None
