"""Foliado: folio, sello, huella, rastro y validación (``comun/foliado.py``)."""

import json
import unittest

from comun import foliado, hashes

GUI = hashes.de_entidad("INTERFAZ", "GUI-1")
OTRA = hashes.de_entidad("INTERFAZ", "GUI-2")
MADRE = hashes.de_entidad("MADRE", "SUM-N1")


class TestFolio(unittest.TestCase):
    def test_formato(self):
        self.assertEqual(foliado.folio(GUI, 7), f"F-{GUI[:8]}-0007")
        self.assertEqual(foliado.folio(GUI, 12345), f"F-{GUI[:8]}-12345")
        self.assertTrue(foliado.es_folio(foliado.folio(GUI, 1)))

    def test_folios_de_dos_guis_no_chocan(self):
        self.assertNotEqual(foliado.folio(GUI, 1), foliado.folio(OTRA, 1))

    def test_no_folios(self):
        for x in (None, 7, "", "F-xyz-0001", f"F-{GUI[:8]}-1", f"F-{GUI[:8]}-0001 ", GUI):
            self.assertFalse(foliado.es_folio(x), x)


class TestSello(unittest.TestCase):
    def setUp(self):
        self.f = foliado.folio(GUI, 1)

    def test_determinista_y_64_hex(self):
        s = foliado.sello(GUI, self.f, "SUM", 7, 5)
        self.assertEqual(s, foliado.sello(GUI, self.f, "SUM", 7, 5))
        self.assertRegex(s, r"^[0-9a-f]{64}$")

    def test_sensible_a_cada_campo(self):
        base = foliado.sello(GUI, self.f, "SUM", 7, 5)
        variantes = [(OTRA, self.f, "SUM", 7, 5), (GUI, foliado.folio(GUI, 2), "SUM", 7, 5),
                     (GUI, self.f, "SUB", 7, 5), (GUI, self.f, "SUM", 8, 5),
                     (GUI, self.f, "SUM", 7, 5.000000001), (GUI, self.f, "SUM", 5, 7)]
        sellos = {foliado.sello(*v) for v in variantes}
        self.assertEqual(len(sellos), len(variantes))
        self.assertNotIn(base, sellos)

    def test_entero_y_flotante_sellan_igual_y_sobreviven_a_json(self):
        """La madre recalcula con lo que llegó por JSON: debe dar lo mismo."""
        a, b = 0.1, 7
        ida = json.loads(json.dumps({"a": a, "b": b}))
        self.assertEqual(foliado.sello(GUI, self.f, "SUM", a, b),
                         foliado.sello(GUI, self.f, "SUM", ida["a"], ida["b"]))
        self.assertEqual(foliado.sello(GUI, self.f, "SUM", 7, 5),
                         foliado.sello(GUI, self.f, "SUM", 7.0, 5.0))

    def test_operandos_invalidos(self):
        for malo in (None, "7", True, float("nan"), float("inf"), 10 ** 400, [1]):
            with self.assertRaises(ValueError, msg=repr(malo)[:20]):
                foliado.sello(GUI, self.f, "SUM", malo, 1)


class TestHuellaYRastro(unittest.TestCase):
    def setUp(self):
        self.f = foliado.folio(GUI, 3)
        self.h = foliado.huella(GUI, "nodo", self.f, "MUL", 6, 7, "GUI-1")

    def test_huella_inicial(self):
        self.assertEqual(self.h["origen"], GUI)
        self.assertEqual(self.h["nodo"], "nodo")
        self.assertEqual(self.h["sello"], foliado.sello(GUI, self.f, "MUL", 6, 7))
        self.assertEqual(self.h["rastro"], [[GUI[:8], "GUI-1", "REQ"]])

    def test_con_paso_no_modifica_la_original(self):
        h2 = foliado.con_paso(self.h, MADRE, "MUL-N1", foliado.ACK)
        self.assertEqual(len(self.h["rastro"]), 1)
        self.assertEqual(h2["rastro"][-1], [MADRE[:8], "MUL-N1", "ACK"])
        self.assertEqual(h2["sello"], self.h["sello"])

    def test_rastro_completo_y_texto(self):
        h = foliado.con_pasos(self.h, [(MADRE, "MUL-N1", foliado.ACK),
                                       (MADRE, "MUL-N1", foliado.RES)])
        h = foliado.con_paso(h, GUI, "GUI-1", foliado.FIN)
        self.assertEqual([p[2] for p in h["rastro"]], ["REQ", "ACK", "RES", "FIN"])
        self.assertEqual(foliado.texto_rastro(h),
                         "GUI-1 REQ → MUL-N1 ACK → MUL-N1 RES → GUI-1 FIN")

    def test_rastro_acotado(self):
        h = self.h
        for _ in range(foliado.MAX_RASTRO + 10):
            h = foliado.con_paso(h, MADRE, "MUL-N1", foliado.ACK)
        self.assertEqual(len(h["rastro"]), foliado.MAX_RASTRO)

    def test_rastro_de_la_red_se_sanea(self):
        sucio = {"rastro": [["a", "b", "ACK"], ["solo dos", "x"], [1, 2, 3], ["a", "b", "OTRO"],
                            "texto"]}
        self.assertEqual(foliado.rastro_de(sucio), [["a", "b", "ACK"]])
        self.assertEqual(foliado.rastro_de(None), [])
        self.assertEqual(foliado.rastro_de({"rastro": "x"}), [])


class TestValidar(unittest.TestCase):
    def setUp(self):
        self.f = foliado.folio(GUI, 9)
        self.h = foliado.huella(GUI, None, self.f, "DIV", 1, 4, "GUI-1")

    def validar(self, h=None, **cambios):
        datos = {"origen": GUI, "folio_": self.f, "codigo": "DIV", "a": 1, "b": 4, **cambios}
        return foliado.validar(self.h if h is None else h, **datos)

    def test_valida(self):
        self.assertIsNone(self.validar())

    def test_motivos(self):
        casos = {
            "sin huella": self.validar(h="no"),
            "folio inválido": self.validar(folio_="F-1"),
            "origen": self.validar(origen=OTRA),            # alguien publica a nombre de otra GUI
            "no coincide": self.validar(b=5),               # operando cambiado por el camino
            "mal formado": self.validar(h={**self.h, "sello": "abc"}),
            "operando inválido": self.validar(a="1"),
        }
        for esperado, motivo in casos.items():
            self.assertIsNotNone(motivo, esperado)
            self.assertIn(esperado, motivo)

    def test_otro_codigo_no_coincide(self):
        self.assertIn("no coincide", self.validar(codigo="MUL"))


if __name__ == "__main__":
    unittest.main()
