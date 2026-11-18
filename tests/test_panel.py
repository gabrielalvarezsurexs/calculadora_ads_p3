"""Herramientas de la demo, sin ventana: lo que el panel lee de las bitácoras y el
registro de reemplazos en ``run/`` (``madre/lanzador.py``)."""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from comun import config
from madre import lanzador
from panel.procesos import CLON, Proceso, _fila


class TestGenesDesdeLaBitacora(unittest.TestCase):
    def test_alta_cambio_y_baja(self):
        p = Proceso("M1-N2", CLON, 2, ["py", "-u", "-m", "madre"])
        p.agregar_linea("12:00:00.000 [GEN_ACTIVO] SUM@1.0 activo: ahora atiendo SUM_REQ · "
                        "genes: SUM@1.0")
        self.assertEqual(p.codigos, ["SUM"])
        p.agregar_linea("12:00:01.000 [GEN_ACTIVO] MUL@1.0 activo: ahora atiendo MUL_REQ · "
                        "genes: MUL@1.0, SUM@1.0")
        p.agregar_linea("12:00:02.000 [GEN_SUSTITUIDO] SUM@1.0 → SUM@2.0 (cambio atómico)")
        self.assertEqual(p.genes, ["MUL@1.0", "SUM@2.0"])
        p.agregar_linea("12:00:03.000 [GEN_BAJA] MUL@1.0 dado de baja: ya no acuso MUL_REQ · "
                        "genes: SUM@2.0")
        p.agregar_linea("12:00:04.000 [GEN_BAJA] SUM@2.0 dado de baja: ya no acuso SUM_REQ · "
                        "genes: ninguno (vacía)")
        self.assertEqual(p.genes, [])
        self.assertEqual(p.lineas_desde(None)[1], 5)

    def test_fila_del_nodo(self):
        self.assertEqual((_fila("Nodo 3"), _fila(None), _fila("raro")), (3, 0, 0))


class TestRegistroDeReemplazos(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="ads-run-"))
        self.addCleanup(shutil.rmtree, self.run, ignore_errors=True)
        parche = mock.patch.object(config, "DIR_RUN", self.run)
        parche.start()
        self.addCleanup(parche.stop)

    def test_registrar_listar_y_olvidar(self):
        # Este mismo proceso hace de "reemplazo": está vivo; se registra con su hora de
        # creación real (la suite puede llevar minutos corriendo).
        ruta = lanzador.registrar("SUM-N2·r1", os.getpid(), ["py"], reemplaza="SUM-N2")
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["inicio"] = lanzador._creacion(os.getpid())
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        self.assertEqual(ruta.name, f"SUM-N2_r1-{os.getpid()}.json")
        vivos = lanzador.registrados()
        self.assertEqual([(d["nombre"], d["reemplaza"]) for d in vivos], [("SUM-N2·r1", "SUM-N2")])
        lanzador.olvidar("SUM-N2·r1")
        self.assertEqual(lanzador.registrados(), [])

    def test_un_pid_muerto_o_reciclado_no_se_toca(self):
        ruta = lanzador.registrar("X·r1", os.getpid(), ["py"])
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["inicio"] -= 3600   # "arrancó" hace una hora: no es este proceso
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        self.assertEqual(lanzador.registrados(), [], "otro proceso con ese PID: se descarta")
        self.assertFalse(ruta.exists(), "y su registro viejo se borra")
        self.assertFalse(lanzador.terminar({"pid": os.getpid(), "inicio": time.time() - 3600}),
                         "nunca se termina un PID que no es el registrado")


if __name__ == "__main__":
    unittest.main()
