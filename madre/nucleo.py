"""Célula madre: un servidor genérico que no sabe sumar ni dividir.

Arranca **vacía** (o con los genes que se le indiquen), se conecta al Campo de
Datos y late. Lo que sabe hacer depende de los **genes** que cargue: programas
que llegan a su disco (banco local, inyección del gestor o entrega de otra
célula) y que ella misma valida y carga a memoria. Con un gen activo atiende
las operaciones de ese código como cualquier servidor del segundo parcial.

Este módulo solo compone las piezas:

* ``almacen.Almacen`` — su carpeta en disco;
* ``genes`` — ciclo de vida (validar, cargar, autoprueba, activar, descargar);
* ``rondas.Rondas`` — foliado (huella, ``X_FIN``), acuse, elección HRW,
  relevo, respuesta única;
* ``ordenes.Ordenes`` — órdenes del gestor dirigidas a ella (alta, cambio,
  baja, retiro → ``GEN_ACK`` / ``GEN_RES``);
* ``pedidos.Pedidos`` + ``comun.pedidos.Proveedor`` — pedir un gen por el
  Campo de Datos (``GEN_PIDE``) y entregar los suyos a quien los pida
  (``GEN_ENTREGA``), leyéndolos de su disco;
* ``regeneracion.Regeneracion`` — la autorrecuperación: detectar pérdidas,
  decidir con las demás (sin hablarse) quién regenera, y lanzar el reemplazo;
* ``copia.Copia`` — si ella ES un reemplazo: copiar los genes de la perdida.

Al cerrarse **ordenadamente** publica ``CEL_ADIOS``: así las demás saben que
no fue una falla y no la regeneran. Una caída (proceso terminado, ``tumbar``)
no avisa a nadie: eso es lo que la regeneración detecta como pérdida.
"""

import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from celula.base import CONEXION, Celula
from comun import codigos, config, hashes, mensajes, microservicios
from comun.bitacora import Bitacora
from comun.microservicios import Paquete
from comun.pedidos import Proveedor, coincide
from comun.programador import Programador
from madre import genes
from madre.almacen import BANCO, ENTREGA, INYECCION, Almacen
from madre.copia import Copia, Gen
from madre.ordenes import Ordenes
from madre.pedidos import Pedido, Pedidos
from madre.regeneracion import Lanzador, Regeneracion
from madre.rondas import Rondas

__all__ = ["BANCO", "ENTREGA", "INYECCION", "Instalacion", "Madre"]

# Órdenes y pedidos que atiende una madre (lo demás de sistema se ignora).
_ORDENES = (codigos.GEN_INYECTA, codigos.GEN_BAJA, codigos.CEL_RETIRO)
_SOLO_TOPOLOGIA = (codigos.TOPO_REQ, codigos.TOPO_RES)


@dataclass(frozen=True)
class Instalacion:
    """Resultado de instalar un gen: lo que se reporta al gestor en ``GEN_RES``."""

    ok: bool
    gen: str                      # 'SUM@2.0'
    detalle: str
    ms: int
    ruta: str | None = None       # dónde quedó en disco
    sustituyo: str | None = None  # 'SUM@1.0' si fue un cambio de versión

    def a_cuerpo(self) -> dict:
        return {"ok": self.ok, "gen": self.gen, "detalle": self.detalle, "ms": self.ms,
                "ruta": self.ruta, "sustituyo": self.sustituyo}


class Madre(Celula):
    def __init__(self, nombre: str, nodo: str, *, genes_iniciales: Sequence[str] = (),
                 banco: Path | None = None, datos: Path | None = None, retardo_ms: int = 0,
                 mudo: bool = False, generacion: int = 0, reemplaza: str | None = None,
                 reemplaza_nombre: str | None = None, copiar: Sequence[Gen] = (),
                 lanzador: Lanzador | None = None, bitacora: Bitacora | None = None,
                 eventos=None):
        """``lanzador``: cómo levantar un reemplazo (``madre.lanzador.lanzar_proceso``
        en producción; en las pruebas, una madre en el mismo proceso). Sin él, la
        madre lleva la cuenta de las pérdidas pero no clona.
        ``reemplaza`` + ``copiar``: esta madre ES el reemplazo de una perdida."""
        super().__init__(mensajes.MADRE, nombre, nodo, None, bitacora=bitacora, eventos=eventos)
        self.banco = banco or config.DIR_MICROSERVICIOS
        carpeta = (datos or config.DIR_DATOS) / "celulas" / f"{nombre}-{hashes.corto(self.hash)}"
        self.almacen = Almacen(carpeta / "genes")
        self.genoma = genes.Genoma()
        self.rondas = Rondas(self)
        self.retardo_ms = max(0, int(retardo_ms))
        self.mudo = mudo
        self.generacion = generacion
        self.reemplaza = reemplaza
        self.reemplaza_nombre = reemplaza_nombre
        self.ignorados = 0
        self.latidos_vistos = 0
        self._genes_iniciales = list(genes_iniciales)
        self._lock_instalar = threading.Lock()   # un ciclo de vida a la vez
        # Órdenes, entregas, instalaciones de pedidos y verificación de liberación:
        # todo en este hilo, uno a la vez y fuera del hilo de red.
        self.programador = Programador(lambda e: self.log("ERROR", f"programador: {e!r}"),
                                       f"{nombre}-genes")
        self.ordenes = Ordenes(self)
        self.pedidos = Pedidos(self)
        self.proveedor = Proveedor(self, self._buscar_gen, self.programador)
        self.regeneracion = Regeneracion(self, lanzador)
        self.copia = Copia(self, list(copiar)) if reemplaza else None

    # ------------------------------------------------------------------ vida

    def iniciar(self) -> None:
        self.rondas.iniciar()
        super().iniciar()
        self.programador.en(config.REVISION_REGENERACION, self._revisar_regeneracion)
        if self.mudo:
            self.log("INICIO", "MUDA (inyección de falla): late pero no acusa ni responde")
        if self.retardo_ms:
            self.log("INICIO", f"retardo artificial de {self.retardo_ms} ms al calcular "
                               f"(el acuse no se retrasa)")
        if not self._genes_iniciales:
            self.log("VACIA", "célula madre vacía: esperando genes (inyección o pedido)")
        for texto in self._genes_iniciales:
            self.instalar_del_banco(texto)

    def detener(self, *, adios: bool = True, motivo: str = "cierre ordenado") -> None:
        """Cierre ordenado: avisa con ``CEL_ADIOS`` (no es una pérdida) y termina."""
        avisa = adios and self.activo and self.conectado
        if avisa:
            self.publicar(codigos.CEL_ADIOS, {"motivo": motivo, "genes": self.genoma.resumen(),
                                              "generacion": self.generacion})
            self.log("ADIOS", f"{motivo}: aviso a todos que no es una falla")
        super().detener(vaciar=avisa)
        self.rondas.detener()
        self.programador.detener()

    def tumbar(self) -> None:
        """Simula una caída: se cierra SIN avisar (como un proceso terminado)."""
        self.detener(adios=False)

    def cuerpo_latido(self) -> dict:
        return {"tipo": mensajes.MADRE, "genes": self.genoma.resumen(),
                "en_cola": self.rondas.en_cola(), "atendidas": self.rondas.atendidas,
                "mudo": self.mudo, "generacion": self.generacion, "reemplaza": self.reemplaza}

    def al_latir(self) -> None:
        self.rondas.purgar()

    def al_conectar(self, nodo: dict, como: str) -> None:
        if como == CONEXION:
            self.regeneracion.conectada()
            if self.copia is not None:
                self.copia.iniciar()

    def _revisar_regeneracion(self) -> None:
        if not self.activo:
            return
        try:
            if self.conectado:
                self.regeneracion.revisar()
        finally:
            self.programador.en(config.REVISION_REGENERACION, self._revisar_regeneracion)

    @property
    def atendidas(self) -> int:
        return self.rondas.atendidas

    # ---------------------------------------------------------- ciclo de vida

    def instalar_del_banco(self, texto: str) -> Instalacion:
        """``--genes SUM@1.0``: copia el gen del banco local a su disco y lo carga."""
        try:
            origen = microservicios.resolver(self.banco, texto)
            paquete = microservicios.leer(origen)
        except (LookupError, OSError, ValueError) as e:
            self.log("GEN_RECHAZADO", f"{texto}: {e}")
            return Instalacion(False, texto, str(e), 0)
        return self.instalar(paquete, BANCO)

    def instalar(self, paquete: Paquete, via: str) -> Instalacion:
        """Escribe el gen en SU disco, lo carga desde ahí y lo activa.

        Si ya había otra versión del mismo código es una **sustitución con
        reversión**: la nueva se valida, carga y autoprueba ANTES de tocar la
        vieja; si algo falla, la vieja sigue activa como si nada.
        """
        with self._lock_instalar:
            return self._instalar(paquete, via)

    def _instalar(self, paquete: Paquete, via: str) -> Instalacion:
        t0 = time.perf_counter()
        etiqueta = _etiqueta(paquete)

        def ms() -> int:
            return round((time.perf_counter() - t0) * 1000)

        def rechazo(motivo: str, ruta: str | None = None) -> Instalacion:
            vieja = self.genoma.activo(etiqueta.partition("@")[0])
            sigue = f"; sigue activo {vieja.id}" if vieja else ""
            del vieja
            self.log("GEN_RECHAZADO", f"{etiqueta} ({via}): {motivo}{sigue}")
            return Instalacion(False, etiqueta, f"{motivo}{sigue}", ms(), ruta)

        # Forma mínima antes de tocar el disco (la ruta sale del código y la versión).
        problema = microservicios.validar_manifiesto(paquete.manifiesto)
        if problema:
            return rechazo(f"manifiesto inválido: {problema}")
        actual = self.genoma.activo(paquete.codigo)
        if actual is not None and actual.version == paquete.version:
            if actual.sha256 == paquete.sha_real:
                self.log("GEN_ACTIVO", f"{actual.id} ya estaba activo (mismo sha256); sin cambios")
                return Instalacion(True, actual.id, "ya estaba activo", ms(),
                                   self.almacen.relativa(actual.carpeta))
            return rechazo(f"{actual.id} ya está activo con otro contenido")

        # 1. Disco (requisito M1: el gen existe físicamente)
        try:
            carpeta = self.almacen.guardar(paquete)
        except (OSError, ValueError) as e:
            return rechazo(f"no se pudo escribir en disco: {e}")
        ruta = self.almacen.relativa(carpeta)
        self.log("GEN_ESCRITO", f"{paquete.id} ({via}) → {ruta}/")

        # 2-4. Validar, cargar y autoprobar desde la copia en disco
        try:
            gen = genes.cargar(carpeta, informar=self.log)
        except genes.GenRechazado as e:
            self.almacen.borrar(paquete.codigo, paquete.version)
            return rechazo(f"{e.paso}: {e.motivo}", ruta)

        # 5. Activar (atómico); si había otra versión, se descarga después
        anterior = self.genoma.activar(gen)
        if anterior is None:
            self.log("GEN_ACTIVO", f"{gen.id} activo: ahora atiendo {gen.codigo}_REQ · "
                                   f"genes: {', '.join(self.genoma.ids())}")
            sustituyo = None
        else:
            sustituyo = anterior.id
            self.log("GEN_SUSTITUIDO", f"{anterior.id} → {gen.id} (cambio atómico; las rondas "
                                       f"en curso terminan con {anterior.id})")
            self._descargar(anterior)
            del anterior
        self.latir()
        self._emitir("genes", self.genoma.ids())
        return Instalacion(True, gen.id, "activo", ms(), ruta, sustituyo)

    def dar_de_baja(self, codigo: str) -> Instalacion:
        """Descarga el gen activo de ``codigo``: deja de acusarlo al instante."""
        with self._lock_instalar:
            gen = self.genoma.quitar(codigo)
            if gen is None:
                self.log("GEN_RECHAZADO", f"baja de {codigo}: no lo tengo activo")
                return Instalacion(False, codigo, f"{codigo} no está activo", 0)
            gen_id = gen.id
            self.log("GEN_BAJA", f"{gen_id} dado de baja: ya no acuso {codigo}_REQ · genes: "
                                 f"{', '.join(self.genoma.ids()) or 'ninguno (vacía)'}")
            self._descargar(gen)
            del gen
        self.latir()
        self._emitir("genes", self.genoma.ids())
        return Instalacion(True, gen_id, "dado de baja", 0)

    def _descargar(self, gen: genes.Gen) -> None:
        """Borra la copia en disco y vigila que el módulo salga de memoria."""
        ref, gen_id = genes.referencia(gen), gen.id
        self.almacen.borrar(gen.codigo, gen.version)
        intentos = list(config.GEN_LIBERACION)

        def revisar() -> None:
            if genes.liberado(ref):
                self.log("GEN_LIBERADO", f"{gen_id}: módulo eliminado de memoria "
                                         f"(weakref confirmado) y borrado del disco")
            elif intentos:
                self.programador.en(intentos.pop(0), revisar)
            else:
                self.log("GEN_EN_USO", f"{gen_id}: aún lo retiene una ronda en curso; se "
                                       f"liberará al terminar")
        self.programador.en(intentos.pop(0), revisar)

    # ------------------------------------------------------- pedir y entregar

    def pedir_gen(self, codigo: str, version: str, sha: str | None = None) -> Pedido:
        """Pide un gen por el Campo de Datos (``GEN_PIDE``); se instala al llegar."""
        return self.pedidos.pedir(codigo, version, sha)

    def _buscar_gen(self, codigo: str, version: str, sha: str | None) -> Paquete | None:
        """¿Tengo ACTIVO ese gen exacto? Se entrega la copia de MI disco."""
        gen = self.genoma.activo(codigo)
        if gen is None or gen.version != version or not coincide(sha, gen.sha256):
            return None
        try:
            paquete = self.almacen.leer(codigo, version)
        except (OSError, ValueError):
            return None
        return paquete if paquete.sha_real == gen.sha256 else None

    # ------------------------------------------------------------ recepción

    def procesar(self, m: dict) -> None:
        codigo = m["codigo"]
        partes = codigos.separar(codigo)
        if partes is not None:
            self._operacion(m, *partes)
        elif codigo == codigos.CEL_LAT:
            self.latidos_vistos += 1
            self.regeneracion.rx_latido(m)
        elif codigo == codigos.NODO_LAT:
            self.regeneracion.rx_nodo(m)
        elif codigo == codigos.CEL_ADIOS:
            self.regeneracion.rx_adios(m)
        elif codigo == codigos.CLON_AVISO:
            self.regeneracion.rx_aviso(m)
        elif codigo == codigos.CLON_LISTO:
            self.regeneracion.rx_listo(m)
        elif codigo in _ORDENES:
            self.ordenes.rx(m)
        elif codigo == codigos.GEN_PIDE:
            self.proveedor.rx_pide(m)
        elif codigo == codigos.GEN_ENTREGA:
            self.proveedor.rx_entrega(m)
            self.pedidos.rx_entrega(m)
        elif codigo in _SOLO_TOPOLOGIA:
            pass  # respuestas de topología: son para el gestor
        else:
            self._ignorar(m, "no es para una madre")

    def _operacion(self, m: dict, codigo: str, tipo: str) -> None:
        gen = self.genoma.activo(codigo)
        if self.mudo:
            self._ignorar(m, "muda: no participa")
        elif tipo == codigos.REQ:
            if gen is None:
                self._ignorar(m, f"no tengo el gen {codigo}")
            else:
                self.rondas.rx_req(m, codigo, gen)
        elif tipo == codigos.ACK and (gen is not None or self.rondas.conoce(codigo)):
            self.rondas.rx_ack(m, codigo, crear=gen is not None)
        elif tipo == codigos.RES and (gen is not None or self.rondas.conoce(codigo)):
            self.rondas.rx_res(m, codigo)
        elif tipo == codigos.FIN and (gen is not None or self.rondas.conoce(codigo)):
            self.rondas.rx_fin(m, codigo)
        else:
            self._ignorar(m, f"no tengo el gen {codigo}")

    def _ignorar(self, m: dict, por: str) -> None:
        self.ignorados += 1
        self.log("IGNORA", f"{m['codigo']} de {m.get('nombre_origen')} "
                           f"({hashes.corto(m['id'])}): {por}", consola=False)


def _etiqueta(paquete: Paquete) -> str:
    m = paquete.manifiesto
    if isinstance(m, dict) and isinstance(m.get("codigo"), str) and isinstance(m.get("version"),
                                                                                str):
        return microservicios.gen_id(m["codigo"], m["version"])
    return "gen sin nombre"
