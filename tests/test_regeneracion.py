"""Autorrecuperación (PLAN §6): regenerar sin orquestador, gradual y sin cáncer.

* ``TestRegla``: la regla de decisión, sin red ni hilos. Una ``Red`` de madres
  simuladas (cada una con su propia ``Regeneracion``) que se pasan los mismos
  mensajes que en el sistema real, con un reloj que se adelanta a mano. Así se
  prueban los ocho límites de forma determinista.
* ``TestRegeneracionEnVivo``: nodos y madres de verdad (en proceso). El
  lanzador levanta el reemplazo como otra madre del mismo proceso, y el
  reemplazo copia sus genes por el Campo de Datos.
"""

import unittest
from unittest import mock

from comun import codigos, config, hashes, mensajes
from madre import copia
from madre import regeneracion as rg
from tests.apoyo import TIEMPOS, Sistema, acortar, esperar

# --------------------------------------------------------------------------- simulación

class _Genoma:
    def __init__(self, genes):
        self.genes = list(genes)

    def resumen(self):
        return list(self.genes)


class MadreSimulada:
    """Lo que ``Regeneracion`` usa de una madre, sin red."""

    def __init__(self, red, nombre, genes, generacion, mudo, nodo):
        self.red = red
        self.nombre = nombre
        self.hash = hashes.de_entidad(mensajes.MADRE, nombre)
        self.genoma = _Genoma({"codigo": c, "version": "1.0", "sha8": "abcd1234"} for c in genes)
        self.generacion, self.mudo, self.reemplaza = generacion, mudo, None
        self.nodo_actual = {"hash": nodo, "nombre": red.nombres_nodo[nodo],
                            "endpoint": red.endpoints[nodo]}
        self.nodo_inicial = self.nodo_actual["endpoint"]
        self.viva = True
        self.listo_en = None          # si es un reemplazo: cuándo termina de copiar
        self.lineas = []
        self.regeneracion = rg.Regeneracion(self, red.lanzar, reloj=red.reloj)

    def publicar(self, codigo, cuerpo):
        self.red.difundir(self, codigo, cuerpo)
        return {}

    def log(self, evento, texto, consola=True):
        self.lineas.append((round(self.red.t, 2), evento, texto))

    def eventos(self, evento):
        return [linea for linea in self.lineas if linea[1] == evento]

    def latido(self):
        return {"tipo": mensajes.MADRE, "genes": self.genoma.resumen(), "mudo": self.mudo,
                "generacion": self.generacion, "reemplaza": self.reemplaza,
                "nodo": self.nodo_actual["hash"], "nodo_nombre": self.nodo_actual["nombre"]}


class Red:
    """Varias madres simuladas que se oyen entre sí, con un reloj manual."""

    COPIA_S = 1.0   # lo que tarda un reemplazo en copiar sus genes

    def __init__(self, nodos=2):
        self.t = 1000.0
        self.nombres_nodo = {f"{k:064x}": f"Nodo {k}" for k in range(1, nodos + 1)}
        self.endpoints = {h: f"127.0.0.1:{5000 + k}" for k, h in
                          enumerate(self.nombres_nodo, 1)}
        self.madres: list[MadreSimulada] = []
        self.encargos: list[tuple[float, rg.Encargo]] = []
        self.listos: list[float] = []
        self._proximo_latido = self.t

    def reloj(self):
        return self.t

    def madre(self, nombre, genes=(), *, generacion=0, mudo=False, nodo=1):
        m = MadreSimulada(self, nombre, genes, generacion, mudo, list(self.nombres_nodo)[nodo - 1])
        m.regeneracion.conectada()
        self.madres.append(m)
        return m

    def vivas(self):
        return [m for m in self.madres if m.viva]

    def por_nombre(self, nombre):
        return next(m for m in self.madres if m.nombre == nombre)

    # --- mensajes -----------------------------------------------------------------

    def difundir(self, origen, codigo, cuerpo):
        m = {"origen": origen.hash, "nombre_origen": origen.nombre, "codigo": codigo,
             "cuerpo": cuerpo}
        for otra in self.vivas():
            if otra is origen:
                continue
            r = otra.regeneracion
            {codigos.CEL_LAT: r.rx_latido, codigos.NODO_LAT: r.rx_nodo,
             codigos.CEL_ADIOS: r.rx_adios, codigos.CLON_AVISO: r.rx_aviso,
             codigos.CLON_LISTO: r.rx_listo}[codigo](m)

    def lanzar(self, encargo: rg.Encargo):
        self.encargos.append((self.t, encargo))
        nodo = next(h for h, ep in self.endpoints.items() if ep == encargo.nodo)
        hijo = MadreSimulada(self, encargo.nombre, (), encargo.generacion, False, nodo)
        hijo.reemplaza = encargo.reemplaza
        hijo.copiar = [g.partition("@")[0] for g in encargo.genes]
        hijo.listo_en = self.t + self.COPIA_S
        hijo.regeneracion.conectada()
        self.madres.append(hijo)

    # --- tiempo -------------------------------------------------------------------

    def avanzar(self, segundos, paso=0.25):
        fin = self.t + segundos
        while self.t < fin:
            self.t += paso
            if self.t >= self._proximo_latido:
                self._proximo_latido = self.t + config.LATIDO
                for h, nombre in self.nombres_nodo.items():
                    m = {"origen": h, "nombre_origen": nombre, "codigo": codigos.NODO_LAT,
                         "cuerpo": {"nombre": nombre, "endpoint": self.endpoints[h]}}
                    for madre in self.vivas():
                        madre.regeneracion.rx_nodo(m)
                for madre in self.vivas():
                    madre.publicar(codigos.CEL_LAT, madre.latido())
            for madre in self.vivas():
                if madre.listo_en is not None and self.t >= madre.listo_en:
                    madre.listo_en = None
                    madre.genoma = _Genoma({"codigo": c, "version": "1.0", "sha8": "abcd1234"}
                                           for c in madre.copiar)
                    madre.publicar(codigos.CEL_LAT, madre.latido())
                    madre.publicar(codigos.CLON_LISTO, {"reemplaza": madre.reemplaza,
                                                        "fuentes": {}, "faltan": []})
                    self.listos.append(self.t)
            for madre in list(self.vivas()):
                madre.regeneracion.revisar()

    def tumbar(self, *nombres):
        for nombre in nombres:
            self.por_nombre(nombre).viva = False

    def retirar(self, nombre):
        m = self.por_nombre(nombre)
        m.publicar(codigos.CEL_ADIOS, {"motivo": "retiro"})
        m.viva = False

    def configuracion(self, nodos=2):
        """Una madre de cada operación por nodo (el modo "con servicios")."""
        for k in range(1, nodos + 1):
            for s in codigos.SERVICIOS:
                self.madre(f"{s}-N{k}", [s], nodo=k)
        self.avanzar(config.LATIDO_CADUCIDAD + 1)   # todas se conocen y dejan de ser nuevas


class TestRegla(unittest.TestCase):
    def setUp(self):
        self.red = Red()
        self.red.configuracion()

    def nombres_encargos(self):
        return [e.nombre for _, e in self.red.encargos]

    def test_una_perdida_un_reemplazo_con_sus_genes_y_alto(self):
        perdida = self.red.por_nombre("SUM-N2")
        self.red.tumbar("SUM-N2")
        self.red.avanzar(30)
        self.assertEqual(self.nombres_encargos(), ["SUM-N2·r1"])
        _, encargo = self.red.encargos[0]
        self.assertEqual(encargo.genes, ("SUM@1.0:abcd1234",), "copia los genes de la perdida")
        self.assertEqual((encargo.reemplaza, encargo.generacion), (perdida.hash, 1))
        self.assertEqual(encargo.nodo_nombre, "Nodo 2", "su nodo sigue vivo: ahí nace")
        # El que lanzó es el rango 0 del ranking HRW de las aptas (todas lo calculan igual).
        aptas = [m.hash for m in self.red.madres[:8] if m.nombre != "SUM-N2"]
        rango0 = hashes.ranking(aptas, f"clon:{perdida.hash}", 1)[0]
        self.assertEqual(encargo.clonador, next(m.nombre for m in self.red.madres
                                                if m.hash == rango0))
        # Todas llegaron a la misma decisión (las que la calcularon antes de oír el
        # CLON_AVISO la anotan; las demás anotan el aviso) y todas dicen NIVEL_OK.
        vivas = [m for m in self.red.vivas() if m.nombre != "SUM-N2·r1"]
        for m in vivas:
            self.assertEqual(len(m.eventos("CAIDA")), 1, m.nombre)
            self.assertEqual(len(m.eventos("NIVEL_OK")), 1, m.nombre)
            self.assertEqual(len(m.eventos("CLON_AVISO")), 1, m.nombre)
            for _, _, texto in m.eventos("CLONADOR"):
                self.assertIn(f"rango 0 = {encargo.clonador}", texto)
        self.red.avanzar(60)
        self.assertEqual(len(self.red.encargos), 1, "con el nivel recuperado no se clona nada más")

    def test_tres_perdidas_uno_por_uno(self):
        self.red.tumbar("SUM-N1", "SUB-N1", "MUL-N2")
        self.red.avanzar(60)
        self.assertEqual(sorted(self.nombres_encargos()), ["MUL-N2·r1", "SUB-N1·r1", "SUM-N1·r1"])
        avisos = [t for t, _ in self.red.encargos]
        for listo, siguiente in zip(self.red.listos, avisos[1:], strict=False):
            self.assertGreaterEqual(siguiente, listo + config.PAUSA_REGENERACION,
                                    "gradual: el siguiente espera a que el anterior termine")
        self.red.avanzar(60)
        self.assertEqual(len(self.red.encargos), 3, "uno por pérdida, nada más")

    def test_retiro_no_es_perdida(self):
        self.red.retirar("DIV-N1")
        self.red.avanzar(40)
        self.assertEqual(self.red.encargos, [])
        self.assertTrue(all(not m.eventos("CAIDA") for m in self.red.vivas()))

    def test_una_sola_madre_con_el_gen_se_reemplaza_por_una(self):
        red = Red(nodos=1)
        red.madre("SUM-N1", ["SUM"])
        for k in range(3):
            red.madre(f"M{k + 2}-N1")
        red.avanzar(config.LATIDO_CADUCIDAD + 1)
        red.tumbar("SUM-N1")
        red.avanzar(40)
        self.assertEqual([e.nombre for _, e in red.encargos], ["SUM-N1·r1"])
        self.assertEqual(len([m for m in red.vivas() if "SUM" in
                              {g["codigo"] for g in m.genoma.resumen()}]), 1,
                         "el nivel requerido era 1: queda 1")

    def test_si_el_clonador_no_actua_lo_releva_el_rango_1(self):
        perdida = self.red.por_nombre("DIV-N2")
        aptas = [m.hash for m in self.red.madres if m is not perdida]
        rango0, rango1 = hashes.ranking(aptas, f"clon:{perdida.hash}", 1)[:2]
        quieto = next(m for m in self.red.madres if m.hash == rango0)
        quieto.regeneracion.activa = False      # como si se hubiera trabado o caído
        self.red.tumbar("DIV-N2")
        self.red.avanzar(40)
        self.assertEqual(len(self.red.encargos), 1)
        _, encargo = self.red.encargos[0]
        self.assertEqual(encargo.clonador, next(m.nombre for m in self.red.madres
                                                if m.hash == rango1))
        detectada = quieto.eventos("CAIDA")[0][0]
        self.assertGreaterEqual(self.red.encargos[0][0] - detectada, config.RELEVO_CLON,
                                "el rango 1 espera RELEVO_CLON antes de actuar")

    def test_tope_duro_no_clona(self):
        with mock.patch.object(config, "MAX_POR_GEN", 1):
            self.red.tumbar("SUM-N1")
            self.red.avanzar(40)
        self.assertEqual(self.red.encargos, [], "ya hay 1 SUM (la de N2): el tope es 1")
        for m in self.red.vivas():
            self.assertIn("tope duro", m.eventos("NO_CLONA")[0][2])

    def test_telomeros(self):
        red = Red(nodos=1)
        red.madre("SUM-N1", ["SUM"])
        red.madre("VIEJA-1", generacion=config.MAX_GENERACION)
        red.madre("VIEJA-2", generacion=config.MAX_GENERACION)
        red.madre("JOVEN", generacion=0)
        red.avanzar(config.LATIDO_CADUCIDAD + 1)
        red.tumbar("SUM-N1")
        red.avanzar(30)
        self.assertEqual([e.clonador for _, e in red.encargos], ["JOVEN"],
                         "las de generación ≥ MAX_GENERACION no clonan")
        self.assertIn("telómeros", red.por_nombre("VIEJA-1").eventos("CLONADOR")[0][2])
        # Sin nadie apto, nadie clona.
        red = Red(nodos=1)
        red.madre("SUM-N1", ["SUM"])
        red.madre("VIEJA-1", generacion=config.MAX_GENERACION)
        red.avanzar(config.LATIDO_CADUCIDAD + 1)
        red.tumbar("SUM-N1")
        red.avanzar(40)
        self.assertEqual(red.encargos, [])
        self.assertIn("de 0 aptas", red.por_nombre("VIEJA-1").eventos("CLONADOR")[0][2])

    def test_cupo_por_madre(self):
        red = Red(nodos=1)
        red.madre("SUM-N1", ["SUM"])
        red.madre("SUB-N1", ["SUB"])
        red.madre("VIEJA", generacion=config.MAX_GENERACION)
        red.madre("UNICA", generacion=0)
        red.avanzar(config.LATIDO_CADUCIDAD + 1)
        with mock.patch.object(config, "MAX_CLONES_MINUTO", 1):
            red.tumbar("SUM-N1", "SUB-N1")
            red.avanzar(30)
            self.assertEqual(len(red.encargos), 1, "UNICA ya gastó su cupo del minuto")
            red.avanzar(rg.VENTANA_CUPO)
        self.assertEqual(len(red.encargos), 2)
        (t1, _), (t2, _) = red.encargos
        self.assertGreaterEqual(t2 - t1, rg.VENTANA_CUPO)

    def test_si_el_reemplazo_muere_antes_de_estar_listo_se_reintenta(self):
        self.red.COPIA_S = 1000   # nunca termina de copiar
        self.red.tumbar("MUL-N1")
        self.red.avanzar(12)
        self.assertEqual(self.nombres_encargos(), ["MUL-N1·r1"])
        self.red.tumbar("MUL-N1·r1")
        self.red.COPIA_S = 1.0
        self.red.avanzar(30)
        self.assertEqual(self.nombres_encargos(), ["MUL-N1·r1", "MUL-N1·r1"])
        intentos = [m.eventos("CLON_AVISO") for m in self.red.vivas()]
        self.assertTrue(any(any("intento 2" in e[2] for e in lista) for lista in intentos))
        self.red.avanzar(60)
        self.assertEqual(len(self.red.encargos), 2, "una sola pérdida: no se clona de más")

    def test_la_lenta_que_vuelve_no_se_regenera(self):
        lenta = self.red.por_nombre("SUB-N2")
        lenta.viva = False
        self.red.avanzar(config.LATIDO_CADUCIDAD + 0.6)   # detectada, aún sin turno
        lenta.viva = True
        self.red.avanzar(30)
        self.assertEqual(self.red.encargos, [])
        self.assertTrue(any(m.eventos("REVIVIO") for m in self.red.vivas()))


class TestCopiarLista(unittest.TestCase):
    def test_leer_lista(self):
        self.assertEqual(copia.leer_lista("SUM@1.0:1A2B3C4D, MUL@1.0"),
                         [("SUM", "1.0", "1a2b3c4d"), ("MUL", "1.0", None)])
        self.assertEqual(copia.leer_lista(""), [])
        for malo in ("SUM", "CLON@1.0", "SUM@x"):
            with self.assertRaises(ValueError):
                copia.leer_lista(malo)

    def test_encargo_argumentos(self):
        e = rg.Encargo("SUM-N2·r1", "127.0.0.1:5002", "Nodo 2", "a" * 64, "SUM-N2",
                       ("SUM@1.0:1a2b3c4d",), 1, "DIV-N4")
        self.assertEqual(e.argumentos(), ["--nodo", "127.0.0.1:5002", "--nombre", "SUM-N2·r1",
                                          "--reemplaza", "a" * 64, "--perdida", "SUM-N2",
                                          "--generacion", "1", "--copiar", "SUM@1.0:1a2b3c4d"])


# --------------------------------------------------------------------------- en vivo

# LATIDO_CADUCIDAD un poco más holgada que en el resto de la suite: aquí TODAS las
# madres viven en un proceso, y un gc.collect() (verificar que un gen se liberó)
# las pausa a la vez; con 2 s, una pausa así bajo carga parece una pérdida falsa.
TIEMPOS_REGENERACION = {**TIEMPOS, "LATIDO_CADUCIDAD": 3.0, "REVISION_REGENERACION": 0.2,
                        "RELEVO_CLON": 1.0,
                        "PLAZO_CLON": 8.0, "PAUSA_REGENERACION": 0.5, "PLAZO_PEDIDO": 0.8,
                        "REINTENTOS_PEDIDO": 2}


class TestRegeneracionEnVivo(unittest.TestCase):
    """3 nodos con una madre de cada operación + una GUI por nodo."""

    @classmethod
    def setUpClass(cls):
        acortar(cls, **TIEMPOS_REGENERACION)

    def setUp(self):
        self.s = Sistema(regenerar=True)
        self.addCleanup(self.s.apagar)
        self.s.completo(3)
        # Que todas se conozcan y dejen de ser "recién llegadas".
        esperar(lambda: False, config.LATIDO_CADUCIDAD + 0.5)

    def madre(self, nombre):
        return next(m for m in self.s.madres if m.nombre == nombre)

    def contar(self, evento, contiene=""):
        return sum(r.contar(evento, contiene) for r in self.s.registros.values())

    def test_tumbar_una_regenera_un_clon_que_copia_sus_genes(self):
        gestor = self.s.gestor(self.s.nodos[2])   # solo mira: la línea de tiempo
        perdida = self.madre("SUM-N2")
        self.assertTrue(esperar(lambda: gestor.celula(perdida.hash) is not None))
        perdida.tumbar()
        self.assertTrue(esperar(lambda: self.s.clones and self.s.clones[0].copia.terminada.is_set(),
                                15), "no nació el reemplazo")
        clon = self.s.clones[0]
        self.assertEqual(clon.nombre, "SUM-N2·r1")
        self.assertEqual((clon.reemplaza, clon.generacion), (perdida.hash, 1))
        self.assertEqual(clon.genoma.ids(), ["SUM@1.0"])
        self.assertEqual(clon.nodo_actual["nombre"], "Nodo 2")
        de = clon.copia.fuentes["SUM@1.0"]
        self.assertIn(de, ("SUM-N1", "SUM-N3", "G-1"), "por el Campo de Datos, no del banco")
        reg = self.s.registros[clon.nombre]
        self.assertEqual(reg.contar("GEN_ESCRITO"), 1, "escrito en SU disco")
        self.assertEqual(reg.contar("GEN_COPIADO"), 1)
        # Las GUIs lo ven: SUM vuelve a 3.
        self.assertTrue(self.s.esperar_disponible(3))
        # Exactamente un aviso y un reemplazo; NIVEL_OK en todas; nada más después.
        esperar(lambda: False, 3 * config.LATIDO_CADUCIDAD)
        self.assertEqual(len(self.s.encargos), 1)
        originales = [m for m in self.s.madres if m.activo and m not in self.s.clones]
        for m in originales:
            self.assertEqual(self.s.registros[m.nombre].contar("NIVEL_OK"), 1, m.nombre)
        # El gestor no hizo nada, pero lo contó completo, en orden.
        linea = [evento for _, evento, _ in gestor.linea_tiempo]
        self.assertEqual(linea, ["CAIDA", "CLON_AVISO", "CONECTADA", "CLON_LISTO", "NIVEL_OK"]
                         if "ENTREGA" not in linea else
                         ["CAIDA", "CLON_AVISO", "CONECTADA", "ENTREGA", "CLON_LISTO", "NIVEL_OK"])
        self.assertEqual(gestor.foto().naciendo, {})
        # Y opera: la GUI resuelve una suma (con el clon entre las candidatas).
        folio, _ = self.s.guis[1].solicitar("SUM", 2, 3)
        self.assertTrue(esperar(lambda: self.s.guis[1].operacion(folio)["estado"] == "resuelta"))

    def test_tres_sum_vuelven_uno_por_uno(self):
        for k in (1, 2, 3):
            self.madre(f"SUM-N{k}").tumbar()
        self.assertTrue(esperar(lambda: len(self.s.clones) == 3 and all(
            c.copia.terminada.is_set() for c in self.s.clones), 40), "no volvieron las tres")
        nombres = sorted(c.nombre for c in self.s.clones)
        self.assertEqual(nombres, ["SUM-N1·r1", "SUM-N2·r1", "SUM-N3·r1"])
        # Nadie tenía SUM: los copiaron del banco… salvo los que lo copiaron de un
        # reemplazo anterior (que ya lo tenía): los dos caminos son válidos.
        fuentes = [c.copia.fuentes["SUM@1.0"] for c in self.s.clones]
        self.assertEqual(fuentes[0], "banco local", "el primero no tenía a quién pedírselo")
        self.assertTrue(self.s.esperar_disponible(3))
        esperar(lambda: False, 3 * config.LATIDO_CADUCIDAD)
        self.assertEqual(len(self.s.encargos), 3, "tres pérdidas, tres reemplazos")
        # Gradual: en la bitácora de una madre, cada CLON_AVISO va después del CLON_LISTO
        # anterior.
        testigo = self.s.registros["DIV-N1"]
        orden = [e for e, _ in testigo.lineas if e in ("CLON_AVISO", "CLON_LISTO")]
        self.assertEqual(orden, ["CLON_AVISO", "CLON_LISTO"] * 3)

    def test_retiro_y_baja_no_regeneran(self):
        g = self.s.gestor(self.s.nodos[0])
        self.assertTrue(esperar(lambda: g.celula(self.madre("MUL-N3").hash) is not None))
        g.retirar(self.madre("MUL-N3").hash)
        g.baja(self.madre("DIV-N3").hash, "DIV")
        esperar(lambda: False, 2 * config.LATIDO_CADUCIDAD + 1)
        self.assertEqual(self.s.encargos, [])
        self.assertEqual(self.contar("CAIDA"), 0)
        self.assertEqual(self.contar("CLON_AVISO"), 0)


if __name__ == "__main__":
    unittest.main()
