"""Sistema completo en proceso: 4 nodos, 16 células madre (una por gen en cada
nodo), 4 interfaces y una célula espía que cuenta los ACK, RES y FIN de cada
folio (§5, §9, §11).

Las aserciones de "exactamente un RES" esperan a que venzan TODOS los relevos
posibles (``asentar``): si hubiera una respuesta de más, el espía la vería.

Para provocar una titular lenta o muerta se usa un gancho en su bitácora: al
registrar TITULAR para ese folio, se le pone retardo o se detiene. Es el
mismo camino de código que ``--retardo-ms`` o que tumbar el proceso, pero sin
depender de a quién le toque ser titular.
"""

import itertools
import operator
import time
import unittest
from unittest import mock

from comun import codigos, config, foliado, hashes, mensajes, microservicios
from interfaz.nucleo import EN_VUELO, FALLIDA, RESUELTA, Interfaz, Operacion
from madre import rondas as rnd
from tests.apoyo import Espia, Registro, Sistema, acortar, esperar

OPERADORES = {"SUM": operator.add, "SUB": operator.sub, "MUL": operator.mul,
              "DIV": operator.truediv}
_numeros = itertools.count(1)   # folios del espía: únicos en toda la corrida


def asentar() -> None:
    """Lo que tarda en vencer el último respaldo posible de una ronda."""
    time.sleep(config.VENTANA_ELECCION + 3 * config.RELEVO + 1.0)


class BaseFlujo(unittest.TestCase):
    sis: Sistema
    espia: Espia

    @classmethod
    def armar(cls) -> None:
        cls.sis = Sistema().completo()
        cls.espia = cls.sis.agregar(Espia(cls.sis.nodos[1].endpoint))
        assert esperar(lambda: cls.espia.conectado, 5)

    def operar(self, gui: Interfaz, servicio: str, a, b, plazo: float = 15.0) -> dict:
        folio, texto = gui.solicitar(servicio, a, b)
        self.assertIsNotNone(folio, texto)
        self.assertTrue(esperar(lambda: gui.operacion(folio)["estado"] != EN_VUELO, plazo))
        return gui.operacion(folio)

    def finalizado(self, gui: Interfaz, folio: str, plazo: float = 5.0) -> dict:
        self.assertTrue(esperar(lambda: gui.operacion(folio)["finalizado"], plazo))
        return gui.operacion(folio)

    def servidores(self, servicio: str):
        return self.sis.con_gen(servicio)

    def reg(self, celula) -> Registro:
        return self.sis.registros[celula.nombre]

    def contar(self, servicio: str, evento: str, folio: str) -> int:
        return sum(self.reg(s).contar(evento, folio)
                   for s in self.sis.madres if s.nombre.startswith(f"{servicio}-"))

    def afirmar_un_res(self, folio: str, intento: int | None = None) -> dict:
        res = self.espia.respuestas(folio)
        self.assertEqual(len(res), 1, [(m["nombre_origen"], m["cuerpo"]) for m in res])
        if intento is not None:
            self.assertEqual(res[0]["cuerpo"]["intento"], intento)
        return res[0]

    # ------------------------------------------------ mensajes a mano (espía)

    def nuevo_folio(self) -> str:
        return foliado.folio(self.espia.hash, next(_numeros))

    def publicar(self, servicio: str, tipo: str, folio: str, intento: int, *,
                 huella: dict | None = None, **extra) -> dict:
        """Publica como el espía. Un REQ lleva una huella válida salvo que se dé otra."""
        cuerpo = {"folio": folio, "intento": intento, **extra}
        if tipo == codigos.REQ:
            cuerpo["huella"] = huella or foliado.huella(self.espia.hash, None, folio, servicio,
                                                        extra["a"], extra["b"], "ESPIA")
        m = self.espia.publicar(codigos.codigo(servicio, tipo), cuerpo)
        self.assertIsNotNone(m)
        return m


class TestFlujo(BaseFlujo):
    @classmethod
    def setUpClass(cls):
        acortar(cls)
        cls.armar()
        cls.addClassCleanup(cls.sis.apagar)

    # ----------------------------------------------------- operaciones normales

    def test_cuatro_operaciones_un_solo_res_y_evento_completo(self):
        casos = [("SUM", 7, 5, 12), ("SUB", 10, 4, 6), ("MUL", 6, 7, 42), ("DIV", 7, 2, 3.5)]
        folios = []
        for gui, (s, a, b, _) in zip(self.sis.guis, casos, strict=True):
            folio, texto = gui.solicitar(s, a, b)  # las cuatro a la vez, una por GUI
            self.assertIsNotNone(folio, texto)
            self.assertTrue(foliado.es_folio(folio))
            self.assertTrue(folio.startswith(f"F-{hashes.corto(gui.hash)}-"))
            folios.append(folio)
        self.assertTrue(esperar(lambda: all(g.operacion(f)["finalizado"]
                                            for g, f in zip(self.sis.guis, folios, strict=True)),
                                15))
        asentar()
        for gui, folio, (s, a, b, esperado) in zip(self.sis.guis, folios, casos, strict=True):
            with self.subTest(gui=gui.nombre, servicio=s):
                fila = gui.operacion(folio)
                self.assertEqual(fila["estado"], RESUELTA)
                self.assertEqual(fila["fase"], foliado.FINALIZADO)
                self.assertEqual(fila["resultado"], esperado)
                self.assertIsNone(fila["error"])
                self.assertEqual(fila["gen"], f"{s}@1.0")
                self.assertEqual(fila["acuses"], 4)
                self.assertEqual(sorted(fila["esperados"]), sorted(fila["acusaron"]))
                self.assertEqual(fila["ausentes"], [])
                self.assertEqual(len(self.espia.acusadores(folio)), 4, "acusan las 4 células")
                res = self.afirmar_un_res(folio, 1)
                # Asociación solicitud ↔ respuesta (§10.2, §11).
                self.assertEqual(fila["id_respuesta"], res["id"])
                self.assertEqual(fila["id_solicitud"], res["cuerpo"]["id_solicitud"])
                self.assertNotEqual(fila["id_respuesta"], fila["id_solicitud"])
                self.assertEqual(fila["rol"], "titular")
                # Huella: el sello de la GUI viaja intacto; el rastro cuenta la historia.
                self.assertEqual(res["cuerpo"]["huella"]["sello"], fila["sello"])
                self.assertEqual(res["cuerpo"]["huella"]["origen"], gui.hash)
                pasos = [p[2] for p in fila["rastro"]]
                self.assertEqual(fila["rastro"][0], [hashes.corto(gui.hash), gui.nombre, "REQ"])
                self.assertEqual(pasos[-2:], ["RES", "FIN"])
                self.assertGreaterEqual(pasos.count("ACK"), config.ACUSES_MIN_DEFECTO)
                self.assertEqual(fila["rastro"][-2][1], res["nombre_origen"])
                # X_FIN: uno por folio, y cada madre del gen cierra sus rondas.
                fines = self.espia.fines(folio)
                self.assertEqual(len(fines), 1)
                self.assertEqual(fines[0]["cuerpo"]["estado"], RESUELTA)
                self.assertEqual(fines[0]["cuerpo"]["id_respuesta"], res["id"])
                self.assertEqual(self.contar(s, "FIN", folio), 4)
                for m in self.servidores(s):
                    self.assertIn(m.rondas.tabla[(s, folio, 1)].estado, rnd.TERMINADAS)
                # En las bitácoras: 1 TITULAR, 3 respaldos que se liberan o se retiran.
                self.assertEqual(self.contar(s, "TITULAR", folio), 1)
                self.assertEqual(self.contar(s, "LIBERADO", folio)
                                 + self.contar(s, "RETIRADA", folio), 3)
                self.assertEqual(self.contar(s, "ACUSE", folio), 4)
                self.assertEqual(self.contar(s, "RES", folio), 1)
                # Las otras GUIs no registran el folio ajeno.
                for otra in self.sis.guis:
                    if otra is not gui:
                        self.assertIsNone(otra.operacion(folio), otra.nombre)
        for gui in self.sis.guis:
            self.assertGreater(self.reg(gui).contar("IGNORA", "evento de otra GUI"), 0,
                               f"{gui.nombre} ve los REQ ajenos y los ignora")
            self.assertGreater(self.reg(gui).contar("IGNORA", "folio ajeno"), 0)
            self.assertGreater(gui.ajenas, 0)

    def test_division_entre_cero(self):
        fila = self.operar(self.sis.guis[1], "DIV", 1, 0)
        self.assertEqual(fila["estado"], RESUELTA)
        self.assertIsNone(fila["resultado"])
        self.assertEqual(fila["error"], "división entre cero")
        asentar()
        res = self.afirmar_un_res(fila["folio"])
        self.assertEqual(res["cuerpo"]["error"], "división entre cero")

    def test_flotantes_y_negativos(self):
        fila = self.operar(self.sis.guis[2], "SUM", 0.1, -0.3)
        self.assertAlmostEqual(fila["resultado"], -0.2)

    def test_rafagas_simultaneas_un_res_por_folio(self):
        """Escenario 2: dos GUIs con varias operaciones en vuelo a la vez."""
        g1, g2 = self.sis.guis[0], self.sis.guis[1]
        folios = {g1: g1.rafaga(8, semilla=1), g2: g2.rafaga(8, semilla=2)}
        for gui, propios in folios.items():
            self.assertEqual(len(propios), 8)
            self.assertEqual(len(set(propios)), 8)
        self.assertGreater(len(g1.en_vuelo()) + len(g2.en_vuelo()), 1,
                           "hubo varias operaciones en vuelo a la vez")
        self.assertTrue(esperar(lambda: all(g.operacion(f)["finalizado"]
                                            for g, fs in folios.items() for f in fs), 20))
        asentar()
        for gui, propios in folios.items():
            otra = g2 if gui is g1 else g1
            for folio in propios:
                with self.subTest(gui=gui.nombre, folio=folio):
                    fila = gui.operacion(folio)
                    self.assertEqual(fila["estado"], RESUELTA)
                    esperado = OPERADORES[fila["servicio"]](fila["a"], fila["b"])
                    self.assertEqual(fila["resultado"], esperado)
                    self.afirmar_un_res(folio)
                    self.assertEqual(len(self.espia.fines(folio)), 1)
                    self.assertIsNone(otra.operacion(folio))

    # -------------------------------------------------------- respuesta única

    def test_titular_lenta_relevo_y_suprimida(self):
        gui = self.sis.guis[0]
        lentas = []

        def gancho(s, folio):
            def f(evento, texto):
                if evento == "TITULAR" and folio in texto:
                    s.retardo_ms = int((config.RELEVO * 2 + 1) * 1000)
                    lentas.append(s)
            return f

        folio, _ = gui.solicitar("MUL", 9, 9)
        self.assertIsNotNone(folio)
        mul = self.servidores("MUL")
        for s in mul:
            self.reg(s).ganchos.append(gancho(s, folio))
        try:
            self.assertTrue(esperar(lambda: gui.operacion(folio)["estado"] != EN_VUELO, 15))
            fila = gui.operacion(folio)
            self.assertEqual(fila["estado"], RESUELTA)
            self.assertEqual(fila["resultado"], 81)
            self.assertEqual(fila["rol"], "relevo 1")
            time.sleep(config.RELEVO * 2 + 1.5)  # que la lenta termine de calcular
            self.afirmar_un_res(folio)
            self.assertEqual(len(lentas), 1)
            # La lenta suprime su respuesta: la ronda ya estaba resuelta (o cerrada por el FIN).
            self.assertEqual(self.reg(lentas[0]).contar("SUPRIMIDA", folio), 1)
            self.assertEqual(self.contar("MUL", "RELEVO", folio), 1)
        finally:
            for s in mul:
                self.reg(s).ganchos.clear()
                s.retardo_ms = 0

    # --------------------------------------------- rondas inyectadas a mano

    def test_reintento_mismo_folio_atendido(self):
        """Regla ≤ k: el RES del intento 1 NO resuelve el intento 2. Un
        reintento significa que esa GUI no recibió la respuesta."""
        folio = self.nuevo_folio()
        self.publicar("SUB", codigos.REQ, folio, 1, a=5, b=3)
        self.assertTrue(esperar(lambda: len(self.espia.respuestas(folio)) == 1, 10))
        self.publicar("SUB", codigos.REQ, folio, 2, a=5, b=3)
        self.assertTrue(esperar(lambda: len(self.espia.respuestas(folio)) == 2, 10))
        asentar()
        res = self.espia.respuestas(folio)
        self.assertEqual([m["cuerpo"]["intento"] for m in res], [1, 2])
        self.assertEqual([m["cuerpo"]["resultado"] for m in res], [2, 2])

    def test_req_repetido_de_una_ronda_resuelta_no_responde(self):
        folio = self.nuevo_folio()
        self.publicar("SUB", codigos.REQ, folio, 1, a=1, b=1)
        self.assertTrue(esperar(lambda: len(self.espia.respuestas(folio)) == 1, 10))
        self.publicar("SUB", codigos.REQ, folio, 1, a=1, b=1)  # otra copia con id nuevo
        asentar()
        self.afirmar_un_res(folio, 1)
        repetidos = sum(self.reg(s).contar("RX", f"{folio} · intento 1 repetido")
                        for s in self.servidores("SUB"))
        self.assertEqual(repetidos, 4, "cada SUB lo reconoce como repetido y no vuelve a acusar")

    def test_ronda_vieja_superada_sin_respuesta_extra(self):
        """El reintento llega mientras la ronda 1 sigue en cola: la 1 queda
        superada y solo responde la 2."""
        folio = self.nuevo_folio()
        self.publicar("DIV", codigos.REQ, folio, 1, a=8, b=2)
        self.publicar("DIV", codigos.REQ, folio, 2, a=8, b=2)
        self.assertTrue(esperar(lambda: self.espia.respuestas(folio), 10))
        asentar()
        res = self.afirmar_un_res(folio, 2)
        self.assertEqual(res["cuerpo"]["resultado"], 4)
        self.assertEqual(self.contar("DIV", "SUPERADA", folio), 4)

    def test_req_viejo_que_llega_despues_del_nuevo(self):
        """Desorden en la malla: el REQ del intento 2 llega antes que el del 1.
        El 1 ya es historia: no debe generar otra respuesta.

        Sin la regla, el RES de más dependía de una carrera de milisegundos (se
        vio en 1 de 6 operaciones); por eso, además de contar respuestas, se
        exige que cada madre marque el REQ tardío como SUPERADA."""
        folios = [self.nuevo_folio() for _ in range(6)]
        for folio in folios:
            self.publicar("DIV", codigos.REQ, folio, 2, a=9, b=3)
            self.publicar("DIV", codigos.REQ, folio, 1, a=9, b=3)
        self.assertTrue(esperar(lambda: all(self.espia.respuestas(f) for f in folios), 15))
        asentar()
        for folio in folios:
            with self.subTest(folio=folio):
                self.afirmar_un_res(folio, 2)
                self.assertEqual(self.contar("DIV", "SUPERADA", folio), 4)
                self.assertEqual(self.contar("DIV", "TITULAR", folio), 1)
                self.assertEqual(len(self.espia.acusadores(folio, 1)), 0, "el tardío no se acusa")

    def test_ack_antes_del_req_ranking_correcto(self):
        """El ACK llega antes que el REQ (viajan por caminos distintos): se crea
        una ronda esqueleto que el REQ completa. El acusador "fantasma" entra al
        ranking; se elige un folio donde le toca rank 0, así que la titular
        nunca responde y lo hace el rank 1 con su relevo."""
        sumas = {s.hash: s for s in self.servidores("SUM")}
        while True:
            folio = self.nuevo_folio()
            orden = hashes.ranking({self.espia.hash, *sumas}, folio, 1)
            if orden[0] == self.espia.hash:
                break
        self.publicar("SUM", codigos.ACK, folio, 1)
        self.assertTrue(esperar(lambda: all(
            ("SUM", folio, 1) in s.rondas.tabla
            and s.rondas.tabla[("SUM", folio, 1)].estado == rnd.ESQUELETO
            for s in sumas.values()), 5))
        for s in sumas.values():
            self.assertEqual(s.rondas.tabla[("SUM", folio, 1)].acusadores, {self.espia.hash})
            self.assertEqual(self.reg(s).contar("RX", "ronda esqueleto"), 1)
        self.publicar("SUM", codigos.REQ, folio, 1, a=2, b=3)
        self.assertTrue(esperar(lambda: self.espia.respuestas(folio), 10))
        asentar()
        res = self.afirmar_un_res(folio, 1)
        self.assertEqual(res["origen"], orden[1])
        self.assertEqual(res["cuerpo"]["rol"], "relevo 1")
        self.assertEqual(res["cuerpo"]["resultado"], 5)
        for s in sumas.values():
            self.assertIn("de 5 [", " ".join(self.reg(s).eventos("RESPALDO", folio)
                                              + self.reg(s).eventos("TITULAR", folio)))

    # ------------------------------------------------------------- foliado

    def test_huella_invalida_no_se_acusa(self):
        """Regla 2 de atención: sello que no cuadra con los datos, o huella a
        nombre de otra GUI → ``DROP huella inválida`` y ni un acuse."""
        alterado = self.nuevo_folio()
        huella = foliado.huella(self.espia.hash, None, alterado, "MUL", 2, 2, "ESPIA")
        self.publicar("MUL", codigos.REQ, alterado, 1, a=2, b=3, huella=huella)  # b cambió
        suplantado = self.nuevo_folio()
        gui = self.sis.guis[0]
        ajena = foliado.huella(gui.hash, None, suplantado, "MUL", 2, 2, gui.nombre)
        self.publicar("MUL", codigos.REQ, suplantado, 1, a=2, b=2, huella=ajena)
        sin_huella = self.nuevo_folio()
        self.espia.publicar("MUL_REQ", {"folio": sin_huella, "intento": 1, "a": 1, "b": 1})
        time.sleep(config.VENTANA_ELECCION + 1.0)
        for folio, motivo in ((alterado, "no coincide"), (suplantado, "origen"),
                              (sin_huella, "sin huella")):
            with self.subTest(motivo=motivo):
                self.assertEqual(self.espia.acusadores(folio), set())
                self.assertEqual(self.espia.respuestas(folio), [])
                self.assertEqual(self.contar("MUL", "DROP", folio), 4)
                for m in self.servidores("MUL"):
                    self.assertIn(motivo, " ".join(self.reg(m).eventos("DROP", folio)))
        self.assertTrue(all(m.rondas.invalidas >= 3 for m in self.servidores("MUL")))

    def test_fin_cierra_las_rondas_del_folio(self):
        """Un ``X_FIN`` que llega antes de la elección cierra todo: nadie
        responde, y una copia tardía del REQ ya no se acusa."""
        folio = self.nuevo_folio()
        self.publicar("SUB", codigos.REQ, folio, 1, a=9, b=1)
        self.publicar("SUB", codigos.FIN, folio, 1, estado=FALLIDA)
        asentar()
        self.assertEqual(self.espia.respuestas(folio), [])
        self.assertEqual(self.contar("SUB", "FIN", folio), 4)
        # Lo normal es RETIRADA (el FIN llegó antes de la elección); si en alguna madre el
        # FIN se adelantó al REQ por otro camino de la malla, ni siquiera acusa.
        self.assertEqual(self.contar("SUB", "RETIRADA", folio)
                         + self.contar("SUB", "RX", f"{folio} · intento 1 de ESPIA: ya está "
                                                    f"cerrada"), 4)
        for m in self.servidores("SUB"):
            self.assertEqual(m.rondas.tabla[("SUB", folio, 1)].estado, rnd.CERRADA)
            self.assertIsNone(m.rondas.tabla[("SUB", folio, 1)].gen, "la ronda soltó el gen")
        self.publicar("SUB", codigos.REQ, folio, 2, a=9, b=1)
        time.sleep(config.VENTANA_ELECCION + 0.5)
        self.assertEqual(self.espia.acusadores(folio, 2), set())
        self.assertEqual(sum(self.reg(m).contar("RX", f"{folio} · intento 2 de ESPIA: ya está "
                                                      f"cerrada")
                             for m in self.servidores("SUB")), 4)


class TestFallas(BaseFlujo):
    """Cada prueba rompe algo, así que cada una arma su propio sistema."""

    @classmethod
    def setUpClass(cls):
        acortar(cls)

    def setUp(self):
        self.armar()
        self.addCleanup(self.sis.apagar)

    def test_titular_tumbada_despues_de_acusar(self):
        gui = self.sis.guis[2]
        muertas = []

        def gancho(s, folio):
            def f(evento, texto):
                if evento == "TITULAR" and folio in texto:
                    muertas.append(s)
                    s.tumbar()  # ya acusó; muere antes de publicar su RES
            return f

        folio, _ = gui.solicitar("MUL", 3, 4)
        self.assertIsNotNone(folio)
        for s in self.servidores("MUL"):
            self.reg(s).ganchos.append(gancho(s, folio))
        self.assertTrue(esperar(lambda: gui.operacion(folio)["estado"] != EN_VUELO, 15))
        fila = gui.operacion(folio)
        self.assertEqual((fila["estado"], fila["resultado"]), (RESUELTA, 12))
        self.assertEqual(fila["rol"], "relevo 1")
        asentar()
        self.afirmar_un_res(folio)
        self.assertEqual(len(muertas), 1)
        self.assertEqual(self.reg(muertas[0]).contar("PERDIDO"), 1,
                         "la titular no alcanzó a responder")
        self.assertNotEqual(self.espia.respuestas(folio)[0]["origen"], muertas[0].hash)

    def test_madre_muda_sale_en_ausentes_y_el_evento_sigue(self):
        """Escenario 3: una madre esperada no acusa. Con el mínimo alcanzado el
        evento termina (tolerancia) y la muda queda en AUSENTES; si el mínimo
        exige a todas, el evento falla y el FIN lo dice."""
        self.sis.madre(self.sis.nodos[0], "SUM-N1m", ["SUM@1.0"], mudo=True)
        gui = self.sis.guis[0]
        self.assertTrue(esperar(lambda: gui.disponibilidad()["SUM"]["vivas"] == 5, 5))
        fila = self.operar(gui, "SUM", 2, 2)
        self.assertEqual((fila["estado"], fila["resultado"]), (RESUELTA, 4))
        fila = self.finalizado(gui, fila["folio"])
        self.assertEqual(len(fila["esperados"]), 5)
        self.assertEqual(fila["acuses"], 4)
        self.assertEqual(fila["ausentes"], ["SUM-N1m"])
        self.assertEqual(self.reg(gui).contar("AUSENTES", "tolerancia"), 1)
        self.assertTrue(esperar(lambda: self.espia.fines(fila["folio"]), 3))
        self.assertEqual(self.espia.fines(fila["folio"])[0]["cuerpo"]["ausentes"], ["SUM-N1m"])

        gui.ajustar_minimo("SUM", 5)   # ahora hacen falta las cinco: nunca se confirma
        fila = self.operar(gui, "SUM", 3, 3)
        self.assertEqual(fila["estado"], FALLIDA)
        self.assertIn("acuses insuficientes (4/5)", fila["motivo"])
        self.assertEqual(fila["intento"], config.MAX_INTENTOS)
        self.assertTrue(fila["finalizado"])
        self.assertTrue(esperar(lambda: self.espia.fines(fila["folio"]), 3))
        fin = self.espia.fines(fila["folio"])[0]["cuerpo"]
        self.assertEqual((fin["estado"], fin["ausentes"]), (FALLIDA, ["SUM-N1m"]))
        self.assertTrue(esperar(lambda: self.contar("SUM", "FIN", fila["folio"]) == 4, 3))

    def test_tres_sum_tumbadas_deshabilita_y_una_nueva_habilita(self):
        sumas = self.servidores("SUM")
        for s in sumas[:3]:
            s.tumbar()
        guis = self.sis.guis
        self.assertTrue(esperar(lambda: not any(g.habilitadas["SUM"] for g in guis),
                                config.LATIDO_CADUCIDAD + 3))
        for g in guis:
            self.assertEqual(g.disponibilidad()["SUM"]["vivas"], 1)
            self.assertTrue(all(g.habilitadas[s] for s in ("SUB", "MUL", "DIV")))
            self.assertEqual(self.reg(g).contar("DESHABILITADA", "SUM"), 1)
        folio, texto = guis[0].solicitar("SUM", 1, 1)
        self.assertIsNone(folio)
        self.assertIn("no disponible", texto)

        self.sis.madre(self.sis.nodos[0], "SUM-NUEVA", ["SUM@1.0"])
        self.assertTrue(esperar(lambda: all(g.habilitadas["SUM"] for g in guis), 5))
        for g in guis:
            self.assertEqual(self.reg(g).contar("HABILITADA", "SUM-NUEVA"), 1)
        fila = self.operar(guis[0], "SUM", 1, 1)
        self.assertEqual((fila["estado"], fila["resultado"]), (RESUELTA, 2))
        asentar()
        self.afirmar_un_res(fila["folio"])

    def test_nodo_tumbado_failover_y_el_servicio_sigue(self):
        # Caducidad real (6 s): el failover (~3 s) debe completarse sin que ninguna
        # GUI dé por muertas a las células que se están mudando de nodo.
        parche = mock.patch.object(config, "LATIDO_CADUCIDAD", 6.0)
        parche.start()
        self.addCleanup(parche.stop)
        n1 = self.sis.nodos[0]
        del1 = [c for c in self.sis.celulas if c.nodo_actual and c.nodo_actual["hash"] == n1.hash]
        self.assertEqual(len(del1), 5, "1 GUI + 4 madres en el Nodo 1")
        propios = {c.hash for c in del1}
        n1.detener()

        def migradas():
            return all(c.conectado and c.nodo_actual["hash"] != n1.hash for c in del1)
        self.assertTrue(esperar(migradas, 15))
        for c in del1:
            self.assertEqual(self.reg(c).contar("FAILOVER"), 1, c.nombre)
        # El hash de cada célula se conserva: los otros nodos la tienen en su tabla.
        en_tablas = set()
        for n in self.sis.nodos[1:]:
            en_tablas |= set(n.celulas)
        self.assertLessEqual(propios, en_tablas)

        gui1 = self.sis.guis[0]
        for g in self.sis.guis:
            self.assertEqual(self.reg(g).contar("CADUCA"), 0, f"{g.nombre} no da por muerto a nadie")
        self.assertTrue(self.sis.esperar_disponible(4, 5))
        for s, a, b, r in (("SUM", 2, 2, 4), ("DIV", 9, 3, 3)):
            fila = self.operar(gui1, s, a, b)
            self.assertEqual((fila["estado"], fila["resultado"]), (RESUELTA, r))
        asentar()
        self.afirmar_un_res(fila["folio"])
        # La huella dice por qué nodo entró ahora la GUI (ya no el Nodo 1).
        self.assertEqual(self.espia.respuestas(fila["folio"])[0]["cuerpo"]["huella"]["nodo"],
                         gui1.nodo_actual["hash"])


class TestGenesEnVivo(BaseFlujo):
    """Las madres cambian de genes con el sistema andando (sin red de por medio
    para la orden: eso es S3; aquí se llama al método de la madre)."""

    @classmethod
    def setUpClass(cls):
        acortar(cls)

    def setUp(self):
        self.armar()
        self.addCleanup(self.sis.apagar)

    def test_madre_vacia_late_pero_no_acusa(self):
        vacia = self.sis.madre(self.sis.nodos[2], "M-VACIA")
        self.assertTrue(esperar(lambda: vacia.conectado, 5))
        fila = self.operar(self.sis.guis[0], "SUM", 2, 2)
        self.assertEqual((fila["estado"], fila["resultado"]), (RESUELTA, 4))
        asentar()
        self.assertNotIn(vacia.hash, self.espia.acusadores(fila["folio"]))
        self.assertEqual(len(self.espia.acusadores(fila["folio"])), 4)
        self.assertGreater(self.reg(vacia).contar("IGNORA", "no tengo el gen SUM"), 0)
        for g in self.sis.guis:
            self.assertEqual(g.disponibilidad()["SUM"]["vivas"], 4, "la vacía no cuenta")

    def test_baja_en_vivo_deja_de_acusar_al_instante(self):
        sub = self.servidores("SUB")[0]
        self.assertTrue(sub.dar_de_baja("SUB").ok)
        self.assertTrue(esperar(lambda: all(g.disponibilidad()["SUB"]["vivas"] == 3
                                            for g in self.sis.guis), 3),
                        "las GUIs lo saben por el latido inmediato, sin esperar la caducidad")
        fila = self.operar(self.sis.guis[1], "SUB", 9, 4)
        self.assertEqual((fila["estado"], fila["resultado"]), (RESUELTA, 5))
        asentar()
        self.assertEqual(len(self.espia.acusadores(fila["folio"])), 3)
        self.assertNotIn(sub.hash, self.espia.acusadores(fila["folio"]))
        self.assertEqual(self.sis.guis[1].operacion(fila["folio"])["ausentes"], [],
                         "dada de baja no es esperada: no es ausente")
        self.assertTrue(esperar(lambda: self.reg(sub).contar("GEN_LIBERADO", "SUB@1.0") == 1, 5))

    def test_sustitucion_en_vivo_cambia_el_resultado(self):
        fila = self.operar(self.sis.guis[0], "SUM", 0.1, 0.2)
        self.assertEqual(fila["resultado"], 0.30000000000000004, "SUM 1.0: punto flotante")
        asentar()
        banco = microservicios.leer(config.DIR_MICROSERVICIOS / "SUM" / "2.0")
        for m in self.servidores("SUM"):
            self.assertEqual(m.instalar(banco, "prueba").sustituyo, "SUM@1.0")
        fila = self.operar(self.sis.guis[0], "SUM", 0.1, 0.2)
        self.assertEqual(fila["resultado"], 0.3, "SUM 2.0: decimal exacta")
        self.assertEqual(fila["gen"], "SUM@2.0")
        asentar()
        self.assertEqual(self.afirmar_un_res(fila["folio"])["cuerpo"]["gen"], "SUM@2.0")


class TestReglasInterfaz(unittest.TestCase):
    """Las reglas de la GUI sin red: se le entregan mensajes con ``procesar``."""

    def setUp(self):
        self.registro = Registro("GUI-T")
        self.gui = Interfaz("GUI-T", "127.0.0.1:1", bitacora=self.registro.bitacora)
        self.celulas = {n: hashes.de_entidad(mensajes.MADRE, n) for n in "ABC"}

    def msg(self, quien: str, tipo: str, cuerpo: dict, servicio: str = "SUM") -> dict:
        return mensajes.nuevo(codigos.codigo(servicio, tipo), self.celulas[quien],
                              mensajes.MADRE, f"SUM-{quien}", cuerpo)

    def ack(self, quien, op, intento, huella=None, servicio="SUM"):
        self.gui.procesar(self.msg(quien, codigos.ACK, {
            "folio": op.folio, "intento": intento, "huella": huella or op.huella}, servicio))

    def res(self, quien, op, intento, resultado, huella=None):
        self.gui.procesar(self.msg(quien, codigos.RES, {
            "folio": op.folio, "intento": intento, "resultado": resultado, "error": None,
            "rol": "titular", "id_solicitud": "x", "gen": "SUM@1.0",
            "huella": huella or foliado.con_paso(op.huella, self.celulas[quien], f"SUM-{quien}",
                                                 foliado.RES)}))

    def en_vuelo(self, servicio="SUM") -> Operacion:
        """Una operación registrada como si se hubiera publicado (sin red)."""
        with self.gui._lock_ops:
            return self.gui._registrar(servicio, 1, 2)

    def vencer(self, op):
        with self.gui._lock_ops:
            self.gui._vencer(op, "prueba")

    def cerrar_ventana(self, op):
        """Como si hubiera pasado ``VENTANA_ACUSES``: lo revisa el reloj de la GUI."""
        op.enviado_en -= config.VENTANA_ACUSES
        self.gui._revisar()

    def test_folios_propios_y_consecutivos(self):
        a, b = self.en_vuelo(), self.en_vuelo("MUL")
        corto = hashes.corto(self.gui.hash)
        self.assertEqual((a.folio, b.folio), (f"F-{corto}-0001", f"F-{corto}-0002"))
        self.assertEqual(a.huella["origen"], self.gui.hash)
        self.assertEqual(a.sello, foliado.sello(self.gui.hash, a.folio, "SUM", 1, 2))
        self.assertEqual(sorted(self.gui.en_vuelo()), [a.folio, b.folio], "dos en vuelo a la vez")

    def test_quorum_por_intento_y_res_retenido(self):
        op = self.en_vuelo()
        self.ack("A", op, 1)
        self.vencer(op)  # reintento: intento 2 (sin red, el REQ se pierde y se registra)
        self.assertEqual(op.intento, 2)
        self.assertEqual(self.registro.contar("PERDIDO"), 1)
        self.ack("B", op, 1)  # acuse viejo (B murió después de acusar el intento 1)
        self.assertEqual(op.acuses(), 0)
        self.ack("A", op, 2)
        self.assertEqual(op.acuses(), 1)
        self.assertIsNone(op.t_confirmado, "un acuse viejo no confirma el evento")
        self.res("A", op, 2, 3)
        self.assertEqual(op.estado, EN_VUELO, "RES antes de confirmar: se retiene")
        self.assertEqual(self.registro.contar("RETENIDA"), 1)
        self.ack("C", op, 2)
        self.assertIsNotNone(op.t_confirmado)
        self.assertEqual((op.estado, op.resultado), (RESUELTA, 3),
                         "confirmado, se acepta el retenido")
        self.assertEqual(self.gui.en_vuelo(), [])
        self.res("B", op, 2, 3)
        self.assertEqual(self.registro.contar("DUPLICADA"), 1)
        self.assertEqual(op.respondio, "SUM-A")

    def test_fallida_y_tardia(self):
        op = self.en_vuelo()
        for _ in range(config.MAX_INTENTOS):
            self.vencer(op)
        self.assertEqual(op.estado, FALLIDA)
        self.assertEqual(op.intento, config.MAX_INTENTOS)
        self.assertEqual(self.gui.en_vuelo(), [])
        self.assertTrue(op.finalizado)
        self.assertEqual(self.registro.contar("FIN", "fallida"), 1)
        self.ack("A", op, 3)
        self.res("A", op, 3, 3)
        self.assertEqual(self.registro.contar("TARDÍA"), 1)
        self.assertEqual(op.estado, FALLIDA)

    def test_res_sin_resultado_valido_es_error(self):
        op = self.en_vuelo()
        self.ack("A", op, 1)
        self.ack("B", op, 1)
        self.res("A", op, 1, "NaN")
        self.assertEqual(op.estado, RESUELTA)
        self.assertIsNone(op.resultado)
        self.assertIn("sin resultado válido", op.error)

    def test_ajenos_se_ignoran(self):
        op = self.en_vuelo()
        otra = Operacion(foliado.folio(hashes.de_entidad("INTERFAZ", "otra"), 1), "SUM", 1, 2,
                         op.huella)
        self.gui.procesar(self.msg("A", codigos.REQ, {"folio": otra.folio, "intento": 1}))
        self.gui.procesar(self.msg("A", codigos.FIN, {"folio": otra.folio, "intento": 1}))
        self.ack("A", otra, 1)
        self.res("A", otra, 1, 3)
        self.ack("A", op, 1, servicio="MUL")  # mi folio, pero otro servicio
        self.assertEqual(self.gui.ajenas, 5)
        self.assertEqual(op.acuses(), 0)
        self.assertNotIn(otra.folio, self.gui.operaciones)
        self.assertEqual(self.registro.contar("IGNORA", "folio ajeno"), 3)

    def test_sello_alterado_u_origen_ajeno_se_ignoran(self):
        op = self.en_vuelo()
        alterada = {**op.huella, "sello": "0" * 64}
        de_otro = {**op.huella, "origen": self.celulas["C"]}
        self.ack("A", op, 1, huella=alterada)
        self.ack("B", op, 1, huella=de_otro)
        self.res("A", op, 1, 3, huella=alterada)
        self.gui.procesar(self.msg("B", codigos.ACK, {"folio": op.folio, "intento": 1}))
        self.assertEqual(op.acuses(), 0)
        self.assertEqual(op.estado, EN_VUELO)
        self.assertEqual(self.gui.ajenas, 4)
        self.assertEqual(self.registro.contar("SELLO"), 4)
        self.assertEqual(self.registro.contar("SELLO", "alterado"), 2)
        self.assertEqual(self.registro.contar("SELLO", "otro origen"), 1)

    def test_esperados_ausentes_y_fases(self):
        for quien in "ABC":
            self.latido(quien, "SUM")
        op = self.en_vuelo()
        self.assertEqual(sorted(op.esperados.values()), ["M-A", "M-B", "M-C"])
        self.assertEqual(op.fase, foliado.INICIO)
        self.ack("A", op, 1)
        self.ack("B", op, 1)
        self.assertEqual(op.fase, foliado.CONFIRMADO)
        self.res("A", op, 1, 3)
        self.assertEqual(op.fase, foliado.PROCESADO)
        self.assertFalse(op.finalizado, "el FIN espera a que cierre la ventana de confirmación")
        self.cerrar_ventana(op)
        self.assertEqual(op.ausentes, ["M-C"])
        self.assertEqual(op.fase, foliado.FINALIZADO)
        self.assertEqual(self.registro.contar("AUSENTES", "M-C no acusaron"), 1)
        self.assertEqual(self.registro.contar("AUSENTES", "tolerancia"), 1)
        fila = self.gui.operacion(op.folio)
        self.assertEqual([p[2] for p in fila["rastro"]], ["REQ", "RES", "FIN"])
        self.assertEqual(fila["ausentes"], ["M-C"])

    def test_si_acusan_todas_la_ventana_cierra_antes(self):
        for quien in "AB":
            self.latido(quien, "SUM")
        op = self.en_vuelo()
        self.ack("A", op, 1)
        self.assertFalse(op.ventana_cerrada)
        self.ack("B", op, 1)
        self.assertTrue(op.ventana_cerrada)
        self.assertEqual(op.ausentes, [])
        self.res("B", op, 1, 3)
        self.assertTrue(op.finalizado, "sin ausentes posibles, el FIN sale con la respuesta")
        self.assertEqual(self.registro.contar("AUSENTES"), 0)

    def conectada(self):
        parche = mock.patch.object(Interfaz, "conectado", new_callable=mock.PropertyMock,
                                   return_value=True)
        parche.start()
        self.addCleanup(parche.stop)

    def test_sin_minimo_al_cerrar_la_ventana_reintenta(self):
        self.conectada()
        for quien in "ABC":
            self.latido(quien, "SUM")
        op = self.en_vuelo()
        self.ack("A", op, 1)
        self.cerrar_ventana(op)
        self.assertEqual(op.intento, 2)
        self.assertEqual(self.registro.contar("AUSENTES", "sin el mínimo"), 1)
        self.assertEqual(self.registro.contar("REINTENTO", op.folio), 1)
        self.assertFalse(op.ventana_cerrada, "el intento nuevo abre su propia ventana")

    def test_sin_enlace_no_se_gastan_intentos(self):
        op = self.en_vuelo()
        self.gui.al_desconectar("prueba")           # se cayó el nodo: failover en curso
        for _ in range(config.MAX_INTENTOS + 1):
            self.cerrar_ventana(op)
        self.assertEqual((op.intento, op.estado), (1, EN_VUELO), "no se perdió ningún intento")
        self.conectada()
        with mock.patch.object(self.gui, "publicar", return_value={"id": "x" * 64}):
            self.gui.al_conectar({"nombre": "Nodo 2", "endpoint": "127.0.0.1:2"}, "failover")
            self.gui._revisar()
        self.assertEqual(op.intento, 2, "al reconectar se reintenta ya, por el nodo nuevo")

    def test_fin_que_no_salio_se_publica_al_reconectar(self):
        op = self.en_vuelo()
        for _ in range(config.MAX_INTENTOS):
            self.vencer(op)                         # sin red: FALLIDA y su X_FIN no sale
        self.assertEqual(op.estado, FALLIDA)
        with mock.patch.object(self.gui, "publicar", return_value={"id": "x" * 64}) as publicar:
            self.gui.al_conectar({"nombre": "Nodo 1", "endpoint": "127.0.0.1:1"}, "reconexion")
        codigos_publicados = [c.args[0] for c in publicar.call_args_list]
        self.assertEqual(codigos_publicados, ["SUM_FIN"], "las madres sí cierran sus rondas")

    def test_res_retenido_de_otro_intento_no_se_usa(self):
        op = self.en_vuelo()
        self.ack("A", op, 1)
        self.res("A", op, 1, 3)                     # retenida: el intento 1 no llegó al mínimo
        self.vencer(op)                             # intento 2
        self.assertIsNone(op.retenido)
        self.res("B", op, 1, 3)                     # otra del intento viejo: no se retiene
        self.assertIsNone(op.retenido)
        self.ack("A", op, 2)
        self.ack("C", op, 2)
        self.assertEqual(op.estado, EN_VUELO, "espera la respuesta del intento vigente")
        self.res("C", op, 2, 3)
        self.assertEqual((op.estado, op.respondio), (RESUELTA, "SUM-C"))

    def latido(self, quien: str, *genes: str) -> None:
        cuerpo = {"tipo": mensajes.MADRE, "nodo_nombre": "Nodo 1",
                  "genes": [{"codigo": g, "version": "1.0", "sha8": "0" * 8} for g in genes]}
        self.gui.procesar(mensajes.nuevo(codigos.CEL_LAT, self.celulas[quien], mensajes.MADRE,
                                         f"M-{quien}", cuerpo))

    def test_disponibilidad_por_genes_anunciados(self):
        self.latido("A", "SUM", "MUL")
        self.latido("B", "SUM", "MUL")
        self.assertTrue(self.gui.habilitadas["SUM"] and self.gui.habilitadas["MUL"])
        self.latido("B", "SUM")  # B dio de baja MUL: deja de contar al instante
        self.assertTrue(self.gui.habilitadas["SUM"])
        self.assertFalse(self.gui.habilitadas["MUL"])
        self.assertEqual(self.registro.contar("SIN_GEN", "MUL M-B"), 1)
        self.gui.procesar(mensajes.nuevo(codigos.CEL_ADIOS, self.celulas["A"], mensajes.MADRE,
                                         "M-A", {"motivo": "prueba"}))
        self.assertFalse(self.gui.habilitadas["SUM"], "A se despidió: queda 1 < 2")
        self.latido("C")  # madre vacía: no cuenta para nada
        self.assertEqual(self.gui.disponibilidad()["SUM"]["vivas"], 1)

    def test_disponibilidad_por_latidos(self):
        def latido(quien):
            self.latido(quien, "SUM")

        self.assertFalse(self.gui.habilitadas["SUM"])
        latido("A")
        self.assertFalse(self.gui.habilitadas["SUM"], "1 viva < mínimo 2")
        latido("B")
        self.assertTrue(self.gui.habilitadas["SUM"])
        self.assertEqual(self.gui.ajustar_minimo("SUM", 3), 3)
        self.assertFalse(self.gui.habilitadas["SUM"])
        latido("C")
        self.assertTrue(self.gui.habilitadas["SUM"])
        self.assertEqual(self.gui.ajustar_minimo("SUM", 99), 16, "el mínimo se acota")
        self.assertEqual(self.gui.ajustar_minimo("SUM", 0), 1)
        self.assertFalse(any(self.gui.habilitadas[s] for s in ("SUB", "MUL", "DIV")))


if __name__ == "__main__":
    unittest.main()
