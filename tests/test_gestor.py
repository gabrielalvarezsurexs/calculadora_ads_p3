"""Gestor de microservicios (PLAN §4): BD, topología, órdenes por el Campo de
Datos, pedidos de genes y latido de los nodos.

* ``TestBaseDatos`` y ``TestTopologia``: sin red.
* ``TestGestorEnVivo``: 4 nodos en malla con 16 madres VACÍAS (modo vacío de la
  configuración mínima), una GUI, un gestor y un espía. Los métodos llevan
  letra porque cuentan una historia en orden: "Distribuir" llena las madres y
  las pruebas siguientes trabajan sobre eso (sustituir, baja, retiro…).
* ``TestPedidos``: ``GEN_PIDE`` / ``GEN_ENTREGA`` entre madres y gestor.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from comun import codigos, config, foliado, mensajes, microservicios
from gestor import nucleo as gn
from gestor.bd import BaseDatos
from gestor.topologia import CAIDA, VIVA, Topologia
from interfaz.nucleo import EN_VUELO
from madre import pedidos as mp
from tests.apoyo import TIEMPOS, Espia, Receptor, Sistema, acortar, esperar

SHA_SUM_10 = microservicios.leer(config.DIR_MICROSERVICIOS / "SUM" / "1.0").sha_real


def hash_falso(n: int) -> str:
    return f"{n:064x}"


class TestBaseDatos(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp(prefix="ads-bd-"))
        self.ruta = self.carpeta / "g.sqlite3"
        self.bd = BaseDatos(self.ruta)
        self.addCleanup(lambda: self.bd.cerrar())  # la que esté abierta al final

    def test_importar_banco_y_marcar_manipulado(self):
        ids = self.bd.importar(config.DIR_MICROSERVICIOS)
        self.assertEqual(sorted(ids), sorted(["DIV@1.0", "MUL@1.0", "SUB@1.0", "SUM@1.0",
                                              "SUM@2.0", "SUM@9.9"]))
        catalogo = {g["id"]: g for g in self.bd.catalogo()}
        self.assertFalse(catalogo["SUM@9.9"]["integro"], "SUM 9.9 está manipulado")
        self.assertTrue(all(g["integro"] for i, g in catalogo.items() if i != "SUM@9.9"))
        self.assertEqual([g["id"] for g in self.bd.catalogo() if g["codigo"] == "SUM"],
                         ["SUM@1.0", "SUM@2.0", "SUM@9.9"])
        self.assertEqual(self.bd.importar(config.DIR_MICROSERVICIOS), ids, "reimportar no duplica")
        self.assertEqual(len(self.bd.catalogo()), 6)

    def test_paquete_buscar_y_version_base(self):
        self.bd.importar(config.DIR_MICROSERVICIOS)
        paquete = self.bd.paquete("SUM", "1.0")
        self.assertEqual(paquete.sha_real, SHA_SUM_10)
        self.assertIsNotNone(self.bd.buscar("SUM", "1.0", SHA_SUM_10[:8]))
        self.assertIsNotNone(self.bd.buscar("SUM", "1.0", None))
        self.assertIsNone(self.bd.buscar("SUM", "1.0", "deadbeef"), "otro sha: no es ese gen")
        self.assertIsNone(self.bd.buscar("SUM", "9.9", None), "un manipulado no se entrega")
        self.assertIsNone(self.bd.paquete("XYZ", "1.0"))
        self.assertEqual(self.bd.version_base("SUM"), "1.0")
        self.assertEqual(self.bd.version_base("DIV"), "1.0")

    def test_historial_de_ordenes_y_persistencia(self):
        self.bd.importar(config.DIR_MICROSERVICIOS)
        self.bd.orden_nueva("O-00000000-0001", "alta", hash_falso(1), "M1-N1", "SUM", "1.0",
                            gn.ENVIADA)
        self.bd.orden_estado("O-00000000-0001", gn.OK, "activo", 12, cerrada=True)
        fila = self.bd.ordenes()[0]
        self.assertEqual((fila["estado"], fila["detalle"], fila["ms"]), (gn.OK, "activo", 12))
        self.assertIsNotNone(fila["cerrada"])
        self.bd.cerrar()
        self.bd = BaseDatos(self.ruta)  # otra sesión del gestor: todo sigue ahí
        self.assertEqual(len(self.bd.catalogo()), 6)
        self.assertEqual(len(self.bd.ordenes()), 1)


class TestTopologia(unittest.TestCase):
    def setUp(self):
        self.t = 100.0
        self.topo = Topologia(reloj=lambda: self.t)
        self.n1, self.n2 = hash_falso(1), hash_falso(2)

    def latido_madre(self, h: str, nombre: str, genes=(), **extra) -> None:
        self.topo.celula_lat(h, nombre, {"tipo": mensajes.MADRE, "nodo": self.n1,
                                         "nodo_nombre": "Nodo 1",
                                         "genes": [{"codigo": c, "version": v, "sha8": "abcd1234"}
                                                   for c, v in genes], **extra})

    def test_nodos_enlaces_celulas_y_disponibilidad(self):
        self.topo.nodo_lat(self.n1, {"nombre": "Nodo 1", "endpoint": "127.0.0.1:5001",
                                     "vecinos": [{"hash": self.n2, "nombre": "Nodo 2"}],
                                     "celulas": [{}, {}]})
        self.latido_madre(hash_falso(10), "SUM-N1", [("SUM", "1.0")])
        self.latido_madre(hash_falso(11), "M2-N1")
        self.latido_madre(hash_falso(12), "SUM-N1m", [("SUM", "1.0")], mudo=True)
        foto = self.topo.instantanea()
        self.assertEqual(foto.nodos[self.n1].vecinos, {self.n2: "Nodo 2"})
        self.assertEqual(foto.nodos[self.n1].celulas, 2)
        self.assertEqual([c.nombre for c in foto.madres(self.n1)], ["M2-N1", "SUM-N1", "SUM-N1m"])
        self.assertTrue(foto.celulas[hash_falso(11)].vacia)
        self.assertEqual(foto.disponibilidad()["SUM"], 1, "la muda no cuenta")
        self.assertEqual(foto.celulas[hash_falso(10)].genes_texto(), "SUM 1.0")

    def test_caida_olvido_regreso_y_adios(self):
        h = hash_falso(10)
        self.latido_madre(h, "SUM-N1", [("SUM", "1.0")])
        self.assertIn(self.n1, self.topo.instantanea().nodos, "nodo provisional por la célula")
        self.t += config.LATIDO_CADUCIDAD + 0.1
        avisos = self.topo.caducar()
        self.assertIn(("CAIDA", f"célula SUM-N1 sin latido en {config.LATIDO_CADUCIDAD:g} s",
                       h, mensajes.MADRE), avisos)
        self.assertEqual(self.topo.celula(h).estado, CAIDA)
        self.assertEqual(self.topo.instantanea().disponibilidad()["SUM"], 0)
        self.latido_madre(h, "SUM-N1", [("SUM", "1.0")])  # solo estaba lenta
        self.assertEqual(self.topo.celula(h).estado, VIVA)
        self.t += config.LATIDO_CADUCIDAD + 0.1
        self.topo.caducar()
        self.t += config.CAIDA_VISIBLE + 0.1
        self.topo.caducar()
        self.assertIsNotNone(self.topo.celula(h), "una MADRE caída espera a su reemplazo")
        self.assertEqual([c.nombre for c in self.topo.pendientes()], ["SUM-N1"])
        self.t += config.ESPERA_REEMPLAZO
        self.topo.caducar()
        self.assertIsNone(self.topo.celula(h), "…o se olvida tras ESPERA_REEMPLAZO")
        self.latido_madre(h, "SUM-N1")
        self.assertIsNotNone(self.topo.adios(h))
        self.assertIsNone(self.topo.celula(h), "CEL_ADIOS la quita sin pasar por caída")

    def test_reemplazo_naciendo_y_conectado(self):
        h = hash_falso(10)
        self.topo.nodo_lat(self.n1, {"nombre": "Nodo 1", "endpoint": "127.0.0.1:5001"})
        self.latido_madre(h, "SUM-N1", [("SUM", "1.0")])
        self.t += config.LATIDO_CADUCIDAD + 0.1
        self.topo.caducar()
        nace = self.topo.aviso_clon({"reemplaza": h, "hijo": "SUM-N1·r1", "nodo": "127.0.0.1:5001",
                                     "nodo_nombre": "Nodo 1", "generacion": 1,
                                     "genes": [{"codigo": "SUM", "version": "1.0"}]}, "DIV-N1")
        self.assertEqual((nace.estado, nace.nodo, nace.clonador), ("naciendo", self.n1, "DIV-N1"))
        self.assertIn(h, self.topo.instantanea().naciendo)
        self.assertEqual(len(self.topo.pendientes()), 2, "la caída y el que nace")
        hijo = hash_falso(20)
        nacio = self.topo.celula_lat(hijo, "SUM-N1·r1", {
            "tipo": mensajes.MADRE, "nodo": self.n1, "genes": [], "generacion": 1,
            "reemplaza": h})
        self.assertEqual(nacio.nombre, "SUM-N1·r1", "primer latido del reemplazo")
        self.assertEqual(self.topo.instantanea().naciendo, {})
        self.assertEqual(self.topo.pendientes(), [], "la caída ya tiene reemplazo")
        self.assertIsNone(self.topo.celula_lat(hijo, "SUM-N1·r1", {
            "tipo": mensajes.MADRE, "nodo": self.n1, "reemplaza": h}), "solo la primera vez")
        self.t += 3.0
        self.topo.caducar()
        self.assertIsNone(self.topo.celula(h), "reemplazada: se olvida enseguida")

    def test_la_que_revive_deja_de_contar_como_reemplazada(self):
        h, hijo = hash_falso(10), hash_falso(20)
        self.latido_madre(h, "SUM-N1", [("SUM", "1.0")])
        self.t += config.LATIDO_CADUCIDAD + 0.1
        self.topo.caducar()
        self.latido_madre(hijo, "SUM-N1·r1", [("SUM", "1.0")], reemplaza=h)
        self.latido_madre(h, "SUM-N1", [("SUM", "1.0")])   # solo estaba lenta: vuelve
        self.assertIsNone(self.topo.celula(h).reemplazada_en)
        self.t += 1.0
        self.latido_madre(hijo, "SUM-N1·r1", [("SUM", "1.0")], reemplaza=h)
        self.assertIsNone(self.topo.celula(h).reemplazada_en, "viva: no se marca reemplazada")
        self.t += config.LATIDO_CADUCIDAD + 0.1                 # ahora sí muere
        self.latido_madre(hijo, "SUM-N1·r1", [("SUM", "1.0")], reemplaza=h)
        self.topo.caducar()
        self.t += 3.0
        self.topo.caducar()
        self.assertIsNotNone(self.topo.celula(h), "sigue en rojo: es una pérdida nueva")
        self.assertEqual([c.nombre for c in self.topo.pendientes()], ["SUM-N1"])

    def test_tregua_tras_un_hueco_sin_enlace(self):
        h = hash_falso(10)
        self.latido_madre(h, "SUM-N1", [("SUM", "1.0")])
        self.t += config.LATIDO_CADUCIDAD + 5   # estuve aislado
        self.topo.tregua()
        self.assertEqual(self.topo.caducar(), [], "el hueco no prueba que alguien muriera")
        self.t += config.LATIDO_CADUCIDAD + 0.1
        self.assertIn(h, [a[2] for a in self.topo.caducar()], "si sigue sin latir, entonces sí")

    def test_datos_mal_formados_no_rompen(self):
        self.topo.celula_lat(hash_falso(3), "X", {"tipo": "OTRO"})
        self.topo.celula_lat(hash_falso(4), "Y", {"tipo": mensajes.MADRE, "genes": "nada",
                                                  "nodo": "no-hash", "generacion": "x"})
        self.topo.nodo_lat(self.n2, {"vecinos": [{"hash": "x"}, 3], "celulas": None})
        foto = self.topo.instantanea()
        self.assertNotIn(hash_falso(3), foto.celulas)
        self.assertEqual(foto.celulas[hash_falso(4)].genes, [])
        self.assertEqual(foto.nodos[self.n2].vecinos, {})


class TestLineaDeTiempo(unittest.TestCase):
    def test_entrega_repetida_solo_una_vez(self):
        """Dos proveedores cuyas esperas se cruzaron entregan el mismo gen: el reemplazo
        usa la primera y la línea de tiempo solo muestra esa."""
        carpeta = Path(tempfile.mkdtemp(prefix="ads-gestor-"))
        self.addCleanup(shutil.rmtree, carpeta, ignore_errors=True)
        g = gn.Gestor("G-T", "127.0.0.1:1", bd=carpeta / "g.sqlite3")
        self.addCleanup(g.bd.cerrar)
        self.addCleanup(g.programador.detener)
        hijo = hash_falso(20)
        g.topologia.celula_lat(hijo, "SUM-N1·r1", {"tipo": mensajes.MADRE, "nodo": hash_falso(1),
                                                   "reemplaza": hash_falso(10)})
        for proveedor in ("SUM-N3", "SUM-N4"):
            g.procesar({"codigo": codigos.GEN_ENTREGA, "origen": hash_falso(30),
                        "nombre_origen": proveedor,
                        "cuerpo": {"destino": hijo, "gen": "SUM@1.0"}})
        eventos = [(e, t.split()[0]) for _, e, t in g.linea_tiempo]
        self.assertEqual(eventos, [("ENTREGA", "SUM-N3")])

    def gestor_sin_red(self):
        carpeta = Path(tempfile.mkdtemp(prefix="ads-gestor-"))
        self.addCleanup(shutil.rmtree, carpeta, ignore_errors=True)
        g = gn.Gestor("G-T", "127.0.0.1:1", bd=carpeta / "g.sqlite3")
        self.addCleanup(g.bd.cerrar)
        self.addCleanup(g.programador.detener)
        self.t = 100.0
        g.topologia = Topologia(reloj=lambda: self.t)
        conectado = mock.patch.object(gn.Gestor, "conectado", new_callable=mock.PropertyMock,
                                      return_value=True)
        conectado.start()
        self.addCleanup(conectado.stop)
        return g

    def test_reemplazo_que_muere_antes_de_estar_listo_no_es_otra_perdida(self):
        g = self.gestor_sin_red()
        perdida, hijo = hash_falso(10), hash_falso(20)
        lat = {"tipo": mensajes.MADRE, "nodo": hash_falso(1),
               "genes": [{"codigo": "SUM", "version": "1.0"}]}
        g.topologia.celula_lat(perdida, "SUM-N1", lat)
        self.t += config.LATIDO_CADUCIDAD + 0.1
        g.al_latir()                                               # CAIDA SUM-N1
        g.topologia.celula_lat(hijo, "SUM-N1·r1", {**lat, "genes": [], "reemplaza": perdida})
        self.t += config.LATIDO_CADUCIDAD + 0.1
        g.al_latir()                                               # muere sin CLON_LISTO
        self.assertIsNone(g.topologia.celula(hijo), "se olvida: las madres reintentan")
        caidas = [t for _, e, t in g.linea_tiempo if e == "CAIDA"]
        self.assertEqual(len(caidas), 2)
        self.assertIn("antes de estar listo", caidas[1])
        self.assertNotIn("SUM-N1·r1", [c.nombre for c in g.topologia.pendientes()],
                         "no bloquea el NIVEL_OK: lo que se reintenta es la pérdida original")

    def test_distribuir_no_duplica_lo_que_se_esta_regenerando(self):
        g = self.gestor_sin_red()
        g.importar()
        n1 = hash_falso(1)
        g.topologia.nodo_lat(n1, {"nombre": "Nodo 1", "endpoint": "127.0.0.1:5001"})
        lat = {"tipo": mensajes.MADRE, "nodo": n1, "nodo_nombre": "Nodo 1"}
        g.topologia.celula_lat(hash_falso(10), "SUM-N1",
                               {**lat, "genes": [{"codigo": "SUM", "version": "1.0"}]})
        g.topologia.celula_lat(hash_falso(11), "SUB-N1m",
                               {**lat, "genes": [{"codigo": "SUB", "version": "1.0"}],
                                "mudo": True})
        for k in range(12, 16):
            g.topologia.celula_lat(hash_falso(k), f"M{k}-N1", lat)
        self.t += 1.0
        g.topologia.nodo_lat(n1, {"nombre": "Nodo 1", "endpoint": "127.0.0.1:5001"})
        for k in range(11, 16):
            g.topologia.celula_lat(hash_falso(k), *([f"M{k}-N1", lat] if k > 11 else
                                                    ["SUB-N1m", {**lat, "genes": [
                                                        {"codigo": "SUB", "version": "1.0"}],
                                                        "mudo": True}]))
        self.t += config.LATIDO_CADUCIDAD - 0.5
        g.topologia.nodo_lat(n1, {"nombre": "Nodo 1", "endpoint": "127.0.0.1:5001"})
        for k in range(11, 16):
            g.topologia.celula_lat(hash_falso(k), *([f"M{k}-N1", lat] if k > 11 else
                                                    ["SUB-N1m", {**lat, "genes": [
                                                        {"codigo": "SUB", "version": "1.0"}],
                                                        "mudo": True}]))
        self.t += 1.0
        g.topologia.caducar()                       # SUM-N1 cae: su reemplazo está en camino
        self.assertEqual(g.topologia.celula(hash_falso(10)).estado, CAIDA)
        ordenes, _ = g.distribuir()
        self.assertEqual(sorted(o.codigo for o in ordenes), ["DIV", "MUL", "SUB"],
                         "SUM no (se regenera); SUB sí (la muda no responde)")


class TestGestorEnVivo(unittest.TestCase):
    """Modo vacío + gestor: la historia de los escenarios 0, 4, 5 y 8."""

    @classmethod
    def setUpClass(cls):
        acortar(cls, **TIEMPOS, GEN_ACK_TIMEOUT=1.0)
        cls.sis = Sistema()
        cls.addClassCleanup(cls.sis.apagar)
        cls.sis.malla(4)
        assert cls.sis.esperar_malla(), "la malla no se formó"
        for k, nodo in enumerate(cls.sis.nodos, 1):
            for i in range(1, 5):
                cls.sis.madre(nodo, f"M{i}-N{k}")
        cls.gui = cls.sis.gui("GUI-1", cls.sis.nodos[0])
        cls.gestor = cls.sis.gestor(cls.sis.nodos[1], "G-N2")
        cls.espia = cls.sis.agregar(Espia(cls.sis.nodos[2].endpoint))
        assert esperar(lambda: len(cls.gestor.foto().madres()) == 16
                       and len(cls.gestor.foto().nodos) == 4, 15), "el gestor no vio todo"

    def madre(self, nombre: str):
        return next(m for m in self.sis.madres if m.nombre == nombre)

    def reg(self, celula):
        return self.sis.registros[celula.nombre]

    def terminada(self, orden, plazo: float = 8.0) -> gn.Orden:
        self.assertIsInstance(orden, gn.Orden, orden)
        self.assertTrue(esperar(lambda: orden.estado in gn.TERMINADAS, plazo), orden.estado)
        return orden

    def en_topologia(self, condicion, plazo: float = 8.0) -> bool:
        return esperar(lambda: condicion(self.gestor.foto()), plazo)

    def test_a_topologia_por_latidos(self):
        hashes_nodos = {n.hash for n in self.sis.nodos}
        self.assertTrue(self.en_topologia(lambda f: set(f.nodos) == hashes_nodos and all(
            n.confirmado and len(n.vecinos) == 3 for n in f.nodos.values())))
        foto = self.gestor.foto()
        self.assertEqual(set(foto.nodos), hashes_nodos)
        for n in self.sis.nodos:
            with self.subTest(nodo=n.nombre):
                visto = foto.nodos[n.hash]
                self.assertEqual(set(visto.vecinos), hashes_nodos - {n.hash},
                                 "enlaces reales de la malla, por NODO_LAT")
                self.assertEqual(visto.endpoint, n.endpoint)
        self.assertTrue(all(m.vacia for m in foto.madres()), "modo vacío")
        tipos = sorted(c.tipo for c in foto.celulas.values())
        self.assertEqual(tipos.count(mensajes.INTERFAZ), 1)
        self.assertEqual(tipos.count(mensajes.GESTOR), 1, "el gestor se dibuja a sí mismo")
        madre = foto.celulas[self.madre("M3-N4").hash]
        self.assertEqual(madre.nodo, self.sis.nodos[3].hash)

    def test_b_distribuir_deja_la_configuracion_del_pdf(self):
        ordenes, notas = self.gestor.distribuir()
        self.assertEqual(len(ordenes), 16)
        self.assertEqual(notas, [])
        for o in ordenes:
            self.terminada(o)
        self.assertEqual({o.estado for o in ordenes}, {gn.OK}, [o.fila() for o in ordenes])
        for k in range(1, 5):
            for i, servicio in enumerate(codigos.SERVICIOS, 1):
                self.assertEqual(self.madre(f"M{i}-N{k}").genoma.ids(), [f"{servicio}@1.0"])
        self.assertTrue(self.en_topologia(lambda f: all(
            n == 4 for n in f.disponibilidad().values())))
        self.assertTrue(esperar(lambda: all(d["vivas"] == 4 for d in
                                            self.gui.disponibilidad().values()), 8))
        folio, _ = self.gui.solicitar("MUL", 6, 7)
        self.assertTrue(esperar(lambda: self.gui.operacion(folio)["estado"] != EN_VUELO, 10))
        self.assertEqual(self.gui.operacion(folio)["resultado"], 42)
        # Cada orden queda en el historial de la BD y en la bitácora de la madre.
        self.assertEqual(sum(1 for f in self.gestor.bd.ordenes() if f["estado"] == gn.OK), 16)
        self.assertEqual(self.reg(self.madre("M1-N3")).contar("ORDEN", "alta de SUM@1.0"), 1)
        self.assertEqual(self.reg(self.madre("M1-N3")).contar("GEN_ESCRITO",
                                                              "inyección del gestor"), 1)
        self.assertEqual(self.gestor.distribuir()[0], [], "lo que ya está no se toca")

    def test_c_sustituir_y_rechazar_manipulado(self):
        m = self.madre("M1-N1")
        orden = self.terminada(self.gestor.sustituir(m.hash, "SUM", "2.0"))
        self.assertEqual(orden.estado, gn.OK, orden.detalle)
        self.assertIn("SUM@1.0 → SUM@2.0", orden.detalle)
        self.assertEqual(m.genoma.ids(), ["SUM@2.0"])
        malo = self.terminada(self.gestor.sustituir(m.hash, "SUM", "9.9"))
        self.assertEqual(malo.estado, gn.RECHAZADA)
        self.assertIn("sha256 no coincide", malo.detalle)
        self.assertIn("sigue activo SUM@2.0", malo.detalle)
        self.assertEqual(m.genoma.ids(), ["SUM@2.0"], "la versión vieja sigue")
        self.assertTrue(self.en_topologia(lambda f: f.celulas[m.hash].genes_texto() == "SUM 2.0"))

    def test_d_baja_deja_de_acusar(self):
        m = self.madre("M1-N2")
        orden = self.terminada(self.gestor.baja(m.hash, "SUM"))
        self.assertEqual(orden.estado, gn.OK, orden.detalle)
        self.assertIsNone(m.genoma.activo("SUM"))
        self.assertTrue(self.en_topologia(lambda f: f.celulas[m.hash].vacia))
        self.assertTrue(esperar(lambda: self.gui.disponibilidad()["SUM"]["vivas"] == 3, 5))
        otra = self.terminada(self.gestor.baja(m.hash, "SUM"))
        self.assertEqual(otra.estado, gn.RECHAZADA, "no lo tiene: la madre dice que no")

    def test_e_alta_en_madre_nueva_y_retiro(self):
        nueva = self.sis.madre(self.sis.nodos[2], "M5-N3")
        self.assertTrue(self.en_topologia(lambda f: nueva.hash in f.celulas))
        orden = self.terminada(self.gestor.inyectar(nueva.hash, "MUL", "1.0"))
        self.assertEqual(orden.estado, gn.OK, orden.detalle)
        self.assertTrue(orden.ruta.endswith(f"celulas/M5-N3-{nueva.hash[:8]}/genes/MUL/1.0"),
                        orden.ruta)
        for evento in ("GEN_ESCRITO", "GEN_VALIDADO", "GEN_CARGADO", "GEN_ACTIVO"):
            self.assertEqual(self.reg(nueva).contar(evento, "MUL@1.0"), 1, evento)
        # Las demás vieron la orden y la ignoraron (no era para ellas).
        self.assertTrue(esperar(lambda: self.reg(self.madre("M2-N2")).contar(
            "IGNORA", f"orden {orden.folio} para otra célula") == 1, 3))
        retiro = self.terminada(self.gestor.retirar(nueva.hash))
        self.assertEqual(retiro.estado, gn.OK, retiro.detalle)
        self.assertTrue(esperar(lambda: not nueva.activo, 3), "la madre se cierra sola")
        self.assertTrue(self.en_topologia(lambda f: nueva.hash not in f.celulas, 3),
                        "CEL_ADIOS: sale del diagrama sin pasar por caída")
        self.assertEqual(self.reg(self.gestor).contar("ADIOS", "M5-N3"), 1)

    def test_f_orden_a_celula_muerta_queda_sin_respuesta(self):
        muerta = self.sis.madre(self.sis.nodos[3], "M6-N4")
        self.assertTrue(self.en_topologia(lambda f: muerta.hash in f.celulas))
        muerta.tumbar()
        orden = self.terminada(self.gestor.inyectar(muerta.hash, "DIV", "1.0"))
        self.assertEqual(orden.estado, gn.SIN_RESPUESTA)
        self.assertTrue(self.en_topologia(
            lambda f: muerta.hash in f.celulas and f.celulas[muerta.hash].estado == CAIDA, 6),
            "deja de latir: el diagrama la marca caída")

    def test_g_sustituir_en_todas(self):
        ordenes = self.gestor.sustituir_en_todas("SUM", "2.0")
        nombres = sorted(o.destino_nombre for o in ordenes)
        self.assertEqual(nombres, ["M1-N3", "M1-N4"], "M1-N1 ya tenía 2.0; M1-N2 sin SUM")
        for o in ordenes:
            self.assertEqual(self.terminada(o).estado, gn.OK, o.detalle)
        self.assertEqual(self.madre("M1-N4").genoma.ids(), ["SUM@2.0"])

    def test_h_consulta_inmediata_y_latido_de_nodo(self):
        receptor = self.sis.agregar(Receptor("RX", self.sis.nodos[0].endpoint))
        self.assertTrue(esperar(lambda: receptor.conectado, 5))
        self.gestor.consultar()
        vivas = sum(1 for m in self.sis.madres if m.activo) + 1  # + la GUI
        self.assertTrue(esperar(lambda: sum(1 for m in receptor.recibidos
                                            if m["codigo"] == codigos.TOPO_RES) == vivas, 5))
        self.assertTrue(esperar(lambda: {m["origen"] for m in receptor.recibidos
                                         if m["codigo"] == codigos.NODO_LAT}
                                == {n.hash for n in self.sis.nodos}, 5))
        lat = next(m for m in receptor.recibidos if m["codigo"] == codigos.NODO_LAT)
        self.assertEqual(len(lat["cuerpo"]["vecinos"]), 3)
        self.assertEqual(lat["tipo_origen"], mensajes.NODO)

    def test_i_solo_un_gestor_da_ordenes(self):
        m = self.madre("M2-N1")
        folio = foliado.folio_admin(foliado.ORDEN, self.espia.hash, 1)
        self.espia.publicar(codigos.GEN_BAJA, {"orden": folio, "destino": m.hash,
                                               "accion": "baja", "codigo": "SUB"})
        self.assertTrue(esperar(lambda: self.reg(m).contar("DROP", "solo un gestor") == 1, 3))
        self.assertEqual(m.genoma.ids(), ["SUB@1.0"])

    def test_j_nodo_nuevo_entra_a_la_topologia_y_recibe_genes(self):
        n5 = self.sis.nodo("Nodo 5", [self.sis.nodos[0].endpoint])
        madre = self.sis.madre(n5, "M1-N5")
        todos = {n.hash for n in self.sis.nodos}
        self.assertTrue(self.en_topologia(lambda f: madre.hash in f.celulas and all(
            h in f.nodos and set(f.nodos[h].vecinos) == todos - {h} for h in todos), 15),
            "el Nodo 5 aparece con enlaces a todos, y todos con enlace a él")
        orden = self.terminada(self.gestor.inyectar(madre.hash, "SUM", "2.0"))
        self.assertEqual(orden.estado, gn.OK, orden.detalle)
        self.assertEqual(madre.genoma.ids(), ["SUM@2.0"])

    def test_z_sin_gestor_el_sistema_sigue(self):
        self.gestor.detener()
        folio, _ = self.gui.solicitar("DIV", 7, 2)
        self.assertTrue(esperar(lambda: self.gui.operacion(folio)["estado"] != EN_VUELO, 10))
        self.assertEqual(self.gui.operacion(folio)["resultado"], 3.5)


class TestPedidos(unittest.TestCase):
    """Copiar un gen por el Campo de Datos (lo usará el reemplazo en S4)."""

    @classmethod
    def setUpClass(cls):
        acortar(cls, **TIEMPOS, PLAZO_PEDIDO=0.8, REINTENTOS_PEDIDO=2)
        cls.sis = Sistema()
        cls.addClassCleanup(cls.sis.apagar)
        cls.sis.malla(2)
        assert cls.sis.esperar_malla()

    def reg(self, celula):
        return self.sis.registros[celula.nombre]

    # Letras: en "a" todavía no hay gestor (si no, también podría entregar él).
    def test_a_otra_madre_entrega_y_la_que_pide_lo_carga_de_su_disco(self):
        donante = self.sis.madre(self.sis.nodos[0], "DON-1", ["SUM@1.0"])
        pide = self.sis.madre(self.sis.nodos[1], "PIDE-1")
        self.assertTrue(esperar(lambda: donante.conectado and pide.conectado
                                and donante.genoma.activo("SUM"), 5))
        pedido = pide.pedir_gen("SUM", "1.0", SHA_SUM_10[:8])
        self.assertTrue(foliado.es_folio_admin(pedido.folio, foliado.PEDIDO))
        self.assertTrue(pedido.esperar(5))
        self.assertEqual((pedido.estado, pedido.de), (mp.LISTO, "DON-1"))
        self.assertEqual(pide.genoma.ids(), ["SUM@1.0"])
        self.assertEqual(self.reg(pide).contar("GEN_ESCRITO", "entrega por el Campo de Datos "
                                                              "de DON-1"), 1)
        self.assertTrue((pide.almacen.raiz / "SUM" / "1.0" / "servicio.py").is_file())
        self.assertEqual(self.reg(donante).contar("ENTREGA", pedido.folio), 1)

    def test_b_el_gestor_entrega_de_su_bd(self):
        gestor = self.sis.gestor(self.sis.nodos[0], "G-P")
        pide = self.sis.madre(self.sis.nodos[1], "PIDE-2")
        self.assertTrue(esperar(lambda: gestor.conectado and pide.conectado, 5))
        pedido = pide.pedir_gen("DIV", "1.0")  # nadie más tiene DIV
        self.assertTrue(pedido.esperar(5))
        self.assertEqual((pedido.estado, pedido.de), (mp.LISTO, "G-P"))
        self.assertEqual(pide.genoma.ids(), ["DIV@1.0"])
        self.assertEqual(self.reg(gestor).contar("GEN_PIDE", "lo tengo en la BD"), 1)

    def test_c_nadie_entrega_un_manipulado(self):
        pide = self.sis.madre(self.sis.nodos[1], "PIDE-3")
        self.assertTrue(esperar(lambda: pide.conectado, 5))
        pedido = pide.pedir_gen("SUM", "9.9")
        self.assertTrue(pedido.esperar(config.PLAZO_PEDIDO * config.REINTENTOS_PEDIDO + 3))
        self.assertEqual(pedido.estado, mp.FALLIDO)
        self.assertEqual(self.reg(pide).contar("GEN_PIDE", "SUM@9.9"), 2, "reintenta y se rinde")
        self.assertEqual(pide.genoma.ids(), [])

    def test_d_varias_pueden_entregar_y_solo_se_instala_una_vez(self):
        donantes = [self.sis.madre(self.sis.nodos[k % 2], f"DON-M{k}", ["MUL@1.0"])
                    for k in range(3)]
        pide = self.sis.madre(self.sis.nodos[0], "PIDE-4")
        self.assertTrue(esperar(lambda: pide.conectado and all(
            d.conectado and d.genoma.activo("MUL") for d in donantes), 5))
        pedido = pide.pedir_gen("MUL", "1.0")
        self.assertTrue(pedido.esperar(5))
        self.assertEqual(pedido.estado, mp.LISTO)
        self.assertTrue(esperar(lambda: sum(d.proveedor.entregas + d.proveedor.calladas
                                            for d in donantes) == 3, 3),
                        "cada donante entregó o se calló")
        self.assertEqual(self.reg(pide).contar("GEN_COPIADO", pedido.folio), 1)


class TestDiagrama(unittest.TestCase):
    """El diagrama dibuja cada tipo de célula y su estado (sin mostrar la ventana)."""

    def setUp(self):
        import tkinter as tk
        try:
            self.raiz = tk.Tk()
        except tk.TclError:
            self.skipTest("Tk sin pantalla")
        self.raiz.withdraw()
        self.addCleanup(self.raiz.destroy)

    def test_cada_tipo_de_celula_y_su_estado(self):
        from comun import tema
        from gestor.diagrama import Diagrama

        t = [100.0]
        topo = Topologia(reloj=lambda: t[0])
        n1, n2 = hash_falso(1), hash_falso(2)
        topo.nodo_lat(n1, {"nombre": "Nodo 1", "vecinos": [{"hash": n2}]})
        topo.nodo_lat(n2, {"nombre": "Nodo 2", "vecinos": [{"hash": n1}]})

        def celula(n: int, tipo: str, genes=(), nodo=n1, **extra) -> str:
            h = hash_falso(100 + n)
            topo.celula_lat(h, f"C{n}", {"tipo": tipo, "nodo": nodo, "genes": [
                {"codigo": c, "version": "1.0", "sha8": "abcd1234"} for c in genes], **extra})
            return h

        una = celula(1, mensajes.MADRE, ["SUM"])
        varias = celula(2, mensajes.MADRE, ["SUM", "MUL"])
        vacia = celula(3, mensajes.MADRE)
        muda = celula(4, mensajes.MADRE, ["DIV"], mudo=True)
        clon = celula(5, mensajes.MADRE, ["SUB"], nodo=n2, generacion=1)
        gui = celula(6, mensajes.INTERFAZ)
        yo = celula(7, mensajes.GESTOR, nodo=n2)
        t[0] += config.LATIDO_CADUCIDAD + 0.1
        for h in (una, varias, vacia, muda, clon, gui, yo):
            if h != una:  # todas laten otra vez menos "una": esa queda caída
                c = topo.celula(h)
                topo.celula_lat(h, c.nombre, {"tipo": c.tipo, "nodo": c.nodo, "genes": c.genes,
                                              "mudo": c.mudo, "generacion": c.generacion})
        topo.nodo_lat(n1, {"nombre": "Nodo 1", "vecinos": [{"hash": n2}]})
        topo.nodo_lat(n2, {"nombre": "Nodo 2", "vecinos": [{"hash": n1}]})
        topo.caducar()

        elegidas = []
        d = Diagrama(self.raiz, al_elegir=elegidas.append, width=900, height=560)
        d.dibujar(topo.instantanea(), seleccion=vacia, yo=yo)

        def items(h):
            return d.find_withtag(f"h:{h}")

        def rellenos(h):
            return {d.itemcget(i, "fill") for i in items(h) if d.type(i) != "line"}

        def textos(h):
            return {d.itemcget(i, "text") for i in items(h) if d.type(i) == "text"}

        self.assertIn(tema.ERROR_SUAVE, rellenos(una), "caída: roja con ✕")
        self.assertIn("✕", textos(una))
        self.assertEqual(sum(1 for i in items(varias) if d.type(i) == "arc"), 2,
                         "dos genes: dos rebanadas")
        self.assertIn("vacía", textos(vacia))
        self.assertIn(tema.ACENTO, {d.itemcget(i, "outline") for i in items(vacia)
                                    if d.type(i) == "oval"}, "la seleccionada lleva anillo")
        self.assertIn(tema.ERROR, {d.itemcget(i, "fill") for i in items(muda)
                                   if d.type(i) == "line"}, "muda: tachada")
        self.assertIn("r1", textos(clon), "clon con insignia de generación")
        self.assertIn(tema.color_gen("SUB"), rellenos(clon))
        textos_lienzo = {d.itemcget(i, "text") for i in d.find_all() if d.type(i) == "text"}
        self.assertTrue({"GUI", "G", "este gestor", "Nodo 1", "Nodo 2"} <= textos_lienzo)
        self.assertTrue({"SUM 1", "DIV 0", "SUB 1", "MUL 1"} <= textos_lienzo,
                        "disponibilidad: solo cuentan las vivas que no son mudas")
        d.destello(vacia, "ok")
        self.raiz.update()
        self.assertTrue(d.find_withtag("destello"), "anillo del destello")
        d._al_elegir(vacia)
        self.assertEqual(elegidas, [vacia])


if __name__ == "__main__":
    unittest.main()
