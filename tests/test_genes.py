"""Ciclo de vida de un gen (PDF §5.2): almacén en disco, validación, carga con
importlib, autoprueba, activación, sustitución con reversión, baja y
liberación de memoria confirmada por weakref. Todo sin red."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from comun import config, microservicios
from comun.microservicios import Paquete
from madre import genes
from madre.almacen import Almacen, FueraDelAlmacen
from madre.nucleo import Madre
from tests.apoyo import Registro, esperar

FUENTE = b'SERVICIO = "POW"\nVERSION = "1.0"\n\ndef calcular(a, b):\n    return a ** b, None\n'


def paquete(fuente: bytes = FUENTE, **cambios) -> Paquete:
    """Un gen POW 1.0 bien firmado; ``cambios`` altera el manifiesto."""
    manifiesto = {"codigo": "POW", "version": "1.0", "nombre": "Potencia",
                  "archivo": "servicio.py", "sha256": microservicios.sha256(fuente),
                  "interfaz": 1, "pruebas": [[2, 3, 8], [9, 0.5, 3]], "descripcion": "a^b"}
    manifiesto.update(cambios)
    return Paquete(manifiesto, fuente)


class BaseTmp(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.almacen = Almacen(self.tmp / "genes")

    def cargar(self, p: Paquete) -> genes.Gen:
        return genes.cargar(self.almacen.guardar(p))

    def rechazo(self, p: Paquete, paso: str, contiene: str) -> None:
        with self.assertRaises(genes.GenRechazado) as ctx:
            self.cargar(p)
        self.assertEqual(ctx.exception.paso, paso)
        self.assertIn(contiene, ctx.exception.motivo)


class TestAlmacen(BaseTmp):
    def test_guarda_byte_por_byte(self):
        fuente = FUENTE.replace(b"\n", b"\r\n")  # ni los finales de línea cambian
        carpeta = self.almacen.guardar(paquete(fuente))
        self.assertEqual((carpeta / "servicio.py").read_bytes(), fuente)
        self.assertTrue(self.almacen.leer("POW", "1.0").integro)
        self.assertEqual(self.almacen.ids(), ["POW@1.0"])

    def test_confinado_a_su_carpeta(self):
        for codigo, version in (("../x", "1.0"), ("POW", "../../1.0"), ("POW", "1"),
                                ("CEL", "1.0"), ("pow", "1.0")):
            with self.subTest(codigo=codigo, version=version), \
                    self.assertRaises(FueraDelAlmacen):
                self.almacen.carpeta(codigo, version)

    def test_borrar(self):
        self.almacen.guardar(paquete())
        self.almacen.borrar("POW", "1.0")
        self.assertEqual(self.almacen.ids(), [])
        self.assertFalse((self.almacen.raiz / "POW").exists())


class TestCargar(BaseTmp):
    def test_ciclo_completo(self):
        notas = []
        gen = genes.cargar(self.almacen.guardar(paquete()), lambda e, t: notas.append(e))
        self.assertEqual((gen.id, gen.sha8), ("POW@1.0", microservicios.sha256(FUENTE)[:8]))
        self.assertEqual(notas, ["GEN_VALIDADO", "GEN_CARGADO", "GEN_AUTOPRUEBA"])
        self.assertEqual(genes.ejecutar(gen, 2, 10), (1024.0, None))

    def test_localizar(self):
        with self.assertRaises(genes.GenRechazado) as ctx:
            genes.cargar(self.tmp / "no-existe")
        self.assertEqual(ctx.exception.paso, genes.LOCALIZAR)

    def test_validar(self):
        self.rechazo(paquete(sha256="0" * 64), genes.VALIDAR, "sha256 no coincide")
        self.rechazo(paquete(pruebas=[]), genes.VALIDAR, "al menos una prueba")
        self.rechazo(paquete(interfaz=2), genes.VALIDAR, "interfaz")
        with mock.patch.object(config, "GEN_MAX_BYTES", 10):
            self.rechazo(paquete(), genes.VALIDAR, "bytes")

    def test_programa_alterado_despues_de_guardarse(self):
        carpeta = self.almacen.guardar(paquete())
        (carpeta / "servicio.py").write_bytes(FUENTE.replace(b"a ** b", b"a ** b + 1"))
        with self.assertRaises(genes.GenRechazado) as ctx:
            genes.cargar(carpeta)
        self.assertIn("sha256 no coincide", ctx.exception.motivo)

    def test_cargar(self):
        self.rechazo(paquete(b"def calcular(:\n"), genes.CARGAR, "SyntaxError")
        self.rechazo(paquete(b"raise RuntimeError('al importar')\n"), genes.CARGAR, "RuntimeError")
        self.rechazo(paquete(FUENTE.replace(b'"POW"', b'"SUM"')), genes.CARGAR, "SERVICIO")
        self.rechazo(paquete(FUENTE.replace(b'"1.0"', b'"2.0"')), genes.CARGAR, "VERSION")
        self.rechazo(paquete(FUENTE.replace(b"def calcular", b"def otra")), genes.CARGAR,
                     "calcular")

    def test_autoprueba(self):
        self.rechazo(paquete(pruebas=[[2, 3, 9]]), genes.AUTOPRUEBA, "se esperaba 9")
        self.rechazo(paquete(pruebas=[[2, 3, None]]), genes.AUTOPRUEBA, "debía dar error")

    def test_el_modulo_no_queda_en_sys_modules(self):
        import sys
        gen = self.cargar(paquete())
        self.assertNotIn(gen.modulo.__name__, sys.modules)


class TestEjecutar(BaseTmp):
    def gen(self, cuerpo: bytes) -> genes.Gen:
        fuente = b'SERVICIO = "POW"\nVERSION = "1.0"\n' + cuerpo
        return self.cargar(paquete(fuente, pruebas=[[1, 1, None]]))

    def test_un_gen_roto_no_tumba_a_la_celula(self):
        casos = {b"def calcular(a, b):\n    return 1 / 0\n": "falló: ZeroDivisionError",
                 b"def calcular(a, b):\n    return 'x', None\n": "no devolvió un número",
                 b"def calcular(a, b):\n    return True, None\n": "no devolvió un número",
                 b"def calcular(a, b):\n    return 5\n": "falló: TypeError",
                 b"def calcular(a, b):\n    return float('inf'), None\n": "fuera de rango"}
        for cuerpo, contiene in casos.items():
            with self.subTest(contiene=contiene):
                r, e = genes.ejecutar(self.gen(cuerpo), 1, 1)
                self.assertIsNone(r)
                self.assertIn(contiene, e)


class TestGenomaYLiberacion(BaseTmp):
    def test_activar_reemplaza_y_quitar(self):
        genoma = genes.Genoma()
        uno = self.cargar(paquete())
        self.assertIsNone(genoma.activar(uno))
        self.assertIs(genoma.activo("POW"), uno)
        fuente2 = FUENTE.replace(b'"1.0"', b'"2.0"')
        dos = self.cargar(paquete(fuente2, version="2.0"))
        self.assertIs(genoma.activar(dos), uno)
        self.assertEqual(genoma.ids(), ["POW@2.0"])
        self.assertIs(genoma.quitar("POW"), dos)
        self.assertEqual(len(genoma), 0)

    def test_weakref_confirma_la_liberacion(self):
        gen = self.cargar(paquete())
        ref = genes.referencia(gen)
        self.assertFalse(genes.liberado(ref))
        del gen
        self.assertTrue(genes.liberado(ref), "nada más debe retener el módulo")


class TestMadreSinRed(BaseTmp):
    """El ciclo de vida dentro de la célula madre (sin conectarla a ningún nodo)."""

    def setUp(self):
        super().setUp()
        self.reg = Registro("M-T")
        self.madre = Madre("M-T", "127.0.0.1:1", datos=self.tmp, bitacora=self.reg.bitacora)
        self.addCleanup(self.madre.detener)

    def banco(self, texto: str) -> Paquete:
        return microservicios.leer(microservicios.resolver(config.DIR_MICROSERVICIOS, texto))

    def test_alta_desde_el_banco_queda_en_su_disco(self):
        r = self.madre.instalar_del_banco("SUM@1.0")
        self.assertTrue(r.ok, r.detalle)
        self.assertEqual(self.madre.genoma.ids(), ["SUM@1.0"])
        self.assertEqual(self.madre.almacen.ids(), ["SUM@1.0"])
        self.assertIn(f"M-T-{self.madre.hash[:8]}/genes/SUM/1.0", r.ruta)
        for evento in ("GEN_ESCRITO", "GEN_VALIDADO", "GEN_CARGADO", "GEN_AUTOPRUEBA",
                       "GEN_ACTIVO"):
            self.assertEqual(self.reg.contar(evento), 1, evento)

    def test_sustituir_1_a_2_y_liberar_la_vieja(self):
        self.madre.instalar_del_banco("SUM@1.0")
        r = self.madre.instalar(self.banco("SUM@2.0"), "inyección del gestor")
        self.assertTrue(r.ok, r.detalle)
        self.assertEqual(r.sustituyo, "SUM@1.0")
        self.assertEqual(self.madre.genoma.ids(), ["SUM@2.0"])
        self.assertEqual(genes.ejecutar(self.madre.genoma.activo("SUM"), 0.1, 0.2), (0.3, None))
        self.assertEqual(self.madre.almacen.ids(), ["SUM@2.0"], "la 1.0 se borra del disco")
        self.assertTrue(esperar(lambda: self.reg.contar("GEN_LIBERADO", "SUM@1.0") == 1, 5))

    def test_sustituir_por_manipulado_revierte(self):
        self.madre.instalar_del_banco("SUM@1.0")
        r = self.madre.instalar(self.banco("SUM@9.9"), "inyección del gestor")
        self.assertFalse(r.ok)
        self.assertIn("sha256 no coincide", r.detalle)
        self.assertIn("sigue activo SUM@1.0", r.detalle)
        self.assertEqual(self.madre.genoma.ids(), ["SUM@1.0"])
        self.assertEqual(self.madre.almacen.ids(), ["SUM@1.0"], "la 9.9 no se queda en disco")

    def test_baja_y_liberacion(self):
        self.madre.instalar_del_banco("DIV")
        r = self.madre.dar_de_baja("DIV")
        self.assertTrue(r.ok)
        self.assertEqual((self.madre.genoma.ids(), self.madre.almacen.ids()), ([], []))
        self.assertTrue(esperar(lambda: self.reg.contar("GEN_LIBERADO", "DIV@1.0") == 1, 5))
        self.assertFalse(self.madre.dar_de_baja("DIV").ok)

    def test_retenido_mas_alla_de_las_revisiones_se_libera_al_soltarlo(self):
        self.madre.instalar_del_banco("DIV")
        retenido = self.madre.genoma.activo("DIV")   # como una ronda que aún no termina
        with mock.patch.object(config, "GEN_LIBERACION", (0.05, 0.05, 0.1)):
            self.assertTrue(self.madre.dar_de_baja("DIV").ok)
            self.assertTrue(esperar(lambda: self.reg.contar("GEN_EN_USO", "DIV@1.0") == 1, 3))
            del retenido
            self.assertTrue(esperar(lambda: self.reg.contar("GEN_LIBERADO", "DIV@1.0") == 1, 3))
        self.assertEqual(self.reg.contar("GEN_EN_USO", "DIV@1.0"), 1, "un solo aviso")

    def test_reinstalar_lo_mismo_no_cambia_nada(self):
        self.madre.instalar_del_banco("MUL@1.0")
        r = self.madre.instalar(self.banco("MUL@1.0"), "inyección del gestor")
        self.assertTrue(r.ok)
        self.assertEqual(r.detalle, "ya estaba activo")

    def test_varios_genes_a_la_vez(self):
        for g in ("SUM@1.0", "SUB", "MUL", "DIV"):
            self.assertTrue(self.madre.instalar_del_banco(g).ok)
        self.assertEqual(self.madre.genoma.ids(), ["DIV@1.0", "MUL@1.0", "SUB@1.0", "SUM@1.0"])

    def test_gen_inexistente(self):
        r = self.madre.instalar_del_banco("POW")
        self.assertFalse(r.ok)
        self.assertEqual(self.madre.genoma.ids(), [])


if __name__ == "__main__":
    unittest.main()
