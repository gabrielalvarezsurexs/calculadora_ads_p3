"""Los genes reales del banco ``microservicios/``: firmas, autopruebas y la
lógica de cada operación (lo que antes era ``servidor/calculo.py``), ejecutada
a través del protocolo de ``madre.genes.ejecutar``."""

import math
import unittest

from comun import config, microservicios
from madre import genes


def cargar(texto: str) -> genes.Gen:
    return genes.cargar(microservicios.resolver(config.DIR_MICROSERVICIOS, texto))


class TestBanco(unittest.TestCase):
    def test_contenido_del_banco(self):
        ids = {f"{c.parent.name}@{c.name}" for c in microservicios.carpetas(config.DIR_MICROSERVICIOS)}
        self.assertEqual(ids, {"SUM@1.0", "SUM@2.0", "SUM@9.9", "SUB@1.0", "MUL@1.0", "DIV@1.0"})

    def test_todos_firmados_salvo_el_manipulado(self):
        for carpeta in microservicios.carpetas(config.DIR_MICROSERVICIOS):
            paquete = microservicios.leer(carpeta)
            with self.subTest(gen=paquete.id):
                self.assertEqual(paquete.integro, paquete.id != "SUM@9.9")

    def test_resolver_sin_version_toma_la_mas_alta_integra(self):
        carpeta = microservicios.resolver(config.DIR_MICROSERVICIOS, "sum")
        self.assertEqual((carpeta.parent.name, carpeta.name), ("SUM", "2.0"),
                         "nunca la 9.9 manipulada")
        with self.assertRaises(LookupError):
            microservicios.resolver(config.DIR_MICROSERVICIOS, "POW")
        with self.assertRaises(ValueError):
            microservicios.resolver(config.DIR_MICROSERVICIOS, "CEL")  # prefijo reservado

    def test_sum_9_9_se_rechaza_antes_de_ejecutarse(self):
        with self.assertRaises(genes.GenRechazado) as ctx:
            cargar("SUM@9.9")
        self.assertEqual(ctx.exception.paso, genes.VALIDAR)
        self.assertIn("sha256 no coincide", ctx.exception.motivo)


class TestOperaciones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = {t: cargar(t) for t in ("SUM@1.0", "SUM@2.0", "SUB@1.0", "MUL@1.0", "DIV@1.0")}

    def calc(self, gen: str, a, b):
        return genes.ejecutar(self.g[gen], a, b)

    def test_cuatro_operaciones(self):
        casos = [("SUM@1.0", 7, 5, 12), ("SUB@1.0", 10, 4, 6), ("MUL@1.0", 6, 7, 42),
                 ("DIV@1.0", 7, 2, 3.5), ("SUM@1.0", -1.5, 0.5, -1), ("SUB@1.0", 0, 3, -3),
                 ("MUL@1.0", -2, -2.5, 5), ("DIV@1.0", -9, 3, -3), ("SUM@2.0", 7, 5, 12)]
        for gen, a, b, esperado in casos:
            with self.subTest(gen=gen, a=a, b=b):
                self.assertEqual(self.calc(gen, a, b), (esperado, None))

    def test_sum_1_flotante_y_sum_2_decimal_exacta(self):
        self.assertEqual(self.calc("SUM@1.0", 0.1, 0.2), (0.30000000000000004, None))
        self.assertEqual(self.calc("SUM@2.0", 0.1, 0.2), (0.3, None))
        self.assertEqual(self.calc("SUM@2.0", 1.1, 2.2), (3.3, None))

    def test_resultado_es_float(self):
        r, _ = self.calc("SUM@1.0", 2, 3)
        self.assertIsInstance(r, float)

    def test_division_entre_cero(self):
        for b in (0, 0.0, -0.0):
            with self.subTest(b=b):
                self.assertEqual(self.calc("DIV@1.0", 1, b), (None, "división entre cero"))
        self.assertEqual(self.calc("DIV@1.0", 0, 0), (None, "división entre cero"))

    def test_resultado_no_finito(self):
        for gen, a, b in (("MUL@1.0", 1e308, 10), ("SUM@1.0", 1.7e308, 1.7e308),
                          ("SUM@2.0", 1.7e308, 1.7e308), ("SUB@1.0", -1.7e308, 1.7e308)):
            with self.subTest(gen=gen):
                r, e = self.calc(gen, a, b)
                self.assertIsNone(r)
                self.assertIn("fuera de rango", e)

    def test_operandos_no_finitos(self):
        for v in (math.inf, -math.inf, math.nan):
            with self.subTest(v=v):
                r, e = self.calc("SUM@1.0", v, 1)
                self.assertIsNone(r)
                self.assertIn("no es finito", e)

    def test_entero_enorme(self):
        r, e = self.calc("SUM@1.0", 10 ** 400, 1)
        self.assertIsNone(r)
        self.assertIn("fuera de rango", e)

    def test_bool_y_str_no_son_numeros(self):
        for a, b in ((True, 1), (1, False), ("7", 5), (1, "2"), (None, 1), ([1], 2), ({}, 1)):
            with self.subTest(a=a, b=b):
                r, e = self.calc("SUM@1.0", a, b)
                self.assertIsNone(r)
                self.assertIn("no es un número", e)

    def test_exactamente_uno_es_none(self):
        for gen, a, b in (("SUM@1.0", 1, 2), ("DIV@1.0", 1, 0), ("MUL@1.0", "x", 1)):
            r, e = self.calc(gen, a, b)
            self.assertTrue((r is None) != (e is None), (gen, a, b))

    def test_error_acotado(self):
        _, e = self.calc("SUM@1.0", "x" * 1000, 1)
        self.assertLessEqual(len(e), 120)


if __name__ == "__main__":
    unittest.main()
