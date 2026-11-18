"""Hashes SHA-256 y el ranking HRW de la elección."""

import collections
import itertools
import random
import re
import unittest

from comun import foliado, hashes

HEX64 = re.compile(r"[0-9a-f]{64}")
GUI = hashes.de_entidad("INTERFAZ", "GUI-1")


class TestHashes(unittest.TestCase):
    def test_64_hex(self):
        for h in (hashes.generar("x"), hashes.de_entidad("NODO", "Nodo 1"),
                  hashes.de_mensaje("origen")):
            self.assertRegex(h, HEX64)

    def test_50000_unicos(self):
        generados = {hashes.de_mensaje("misma célula") for _ in range(50_000)}
        self.assertEqual(len(generados), 50_000)

    def test_mismos_datos_hash_distinto(self):
        """Dos entidades con el mismo nombre no chocan (ni sus folios)."""
        a, b = hashes.de_entidad("MADRE", "SUM-N1"), hashes.de_entidad("MADRE", "SUM-N1")
        self.assertNotEqual(a, b)
        self.assertNotEqual(foliado.folio(a, 1), foliado.folio(b, 1))

    def test_corto(self):
        h = hashes.generar("x")
        self.assertEqual(hashes.corto(h), h[:8])
        self.assertEqual(hashes.corto(None), "")


class TestRanking(unittest.TestCase):
    def setUp(self):
        self.celulas = [hashes.de_entidad("MADRE", f"SUM-N{k}") for k in range(1, 5)]

    def test_determinista(self):
        op = foliado.folio(GUI, 1)
        self.assertEqual(hashes.ranking(self.celulas, op, 1), hashes.ranking(self.celulas, op, 1))

    def test_independiente_del_orden_del_conjunto(self):
        """Cada célula arma su conjunto de acusadores en el orden en que le llegan
        los ACK; aun así todas deben calcular el mismo orden."""
        op = foliado.folio(GUI, 1)
        esperado = hashes.ranking(self.celulas, op, 1)
        for perm in itertools.permutations(self.celulas):
            self.assertEqual(hashes.ranking(perm, op, 1), esperado)
            self.assertEqual(hashes.ranking(set(perm), op, 1), esperado)

    def test_es_permutacion_del_conjunto(self):
        op = foliado.folio(GUI, 1)
        self.assertCountEqual(hashes.ranking(self.celulas, op, 1), self.celulas)

    def test_reparto_uniforme(self):
        """4 000 operaciones sobre 4 células: ~1 000 titularidades cada una.
        (σ binomial ≈ 27; el margen de ±150 es más de 5σ.)"""
        conteo = collections.Counter(
            hashes.ranking(self.celulas, foliado.folio(GUI, i), 1)[0]
            for i in range(4000))
        self.assertEqual(set(conteo), set(self.celulas))
        for c in self.celulas:
            self.assertLess(abs(conteo[c] - 1000), 150, dict(conteo))

    def test_el_intento_cambia_la_titular(self):
        """El intento entra al hash: un reintento puede tocarle a otra célula
        (si la titular del intento 1 murió, no siempre es la misma)."""
        rng = random.Random(7)
        ops = [foliado.folio(GUI, rng.randrange(10**6)) for _ in range(1000)]
        distintas = sum(hashes.ranking(self.celulas, op, 1)[0] != hashes.ranking(
            self.celulas, op, 2)[0] for op in ops)
        self.assertGreater(distintas, 650)  # se espera ~750 (3/4)
        self.assertLess(distintas, 850)

    def test_quitar_una_celula_no_reordena_a_las_demas(self):
        """Propiedad de HRW: si una acusadora falta, el orden relativo de las
        demás no cambia."""
        op = foliado.folio(GUI, 2)
        completo = hashes.ranking(self.celulas, op, 1)
        for quitada in self.celulas:
            resto = [c for c in self.celulas if c != quitada]
            self.assertEqual(hashes.ranking(resto, op, 1), [c for c in completo if c != quitada])


if __name__ == "__main__":
    unittest.main()
