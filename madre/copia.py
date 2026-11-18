"""El reemplazo al nacer: copia los genes de la célula que sustituye (PLAN §6.3, paso 6).

El clonador NO le pasa programas: solo la lista de lo que tenía la perdida
(``--copiar SUM@1.0:1a2b3c4d``). El reemplazo nace **vacío** y copia cada gen
como lo haría cualquier madre: lo pide por el Campo de Datos (``GEN_PIDE``),
quien lo tenga se lo entrega (otra madre desde su disco, o un gestor desde su
BD), lo escribe en **su** disco, lo valida y lo carga. Pide todos a la vez.

Si nadie lo entrega (por ejemplo, murió la única ``SUM`` y no hay gestor), la
última fuente es el **banco local** ``microservicios/``, y solo si el sha256
coincide con el de la perdida: un reemplazo nunca cambia de versión por su
cuenta. Al terminar publica ``CLON_LISTO`` con de dónde salió cada gen; con eso
todas las madres dan la pérdida por resuelta.
"""

import threading

from comun import codigos, config, microservicios
from comun.pedidos import coincide
from madre.almacen import BANCO
from madre.pedidos import LISTO

Gen = tuple[str, str, str | None]   # (código, versión, sha o prefijo)


def leer_lista(texto: str) -> list[Gen]:
    """``"SUM@1.0:1a2b3c4d,MUL@1.0"`` → ``[("SUM", "1.0", "1a2b3c4d"), ("MUL", "1.0", None)]``."""
    genes = []
    for parte in (p.strip() for p in (texto or "").split(",")):
        if not parte:
            continue
        gen, _, sha = parte.partition(":")
        codigo, _, version = gen.partition("@")
        if not codigos.es_gen(codigo) or not microservicios.es_version(version):
            raise ValueError(f"gen a copiar inválido: {parte!r} (se espera SUM@1.0[:sha8])")
        genes.append((codigo, version, sha.lower() or None))
    return genes


class Copia:
    def __init__(self, madre, genes: list[Gen]):
        self.madre = madre
        self.genes = list(genes)
        self.fuentes: dict[str, str] = {}   # 'SUM@1.0' -> de quién
        self.faltan: list[str] = []
        self.terminada = threading.Event()
        self._iniciada = False

    def iniciar(self) -> None:
        """Una sola vez (en la primera conexión): una reconexión no vuelve a copiar."""
        if self._iniciada:
            return
        self._iniciada = True
        threading.Thread(target=self._correr, name=f"{self.madre.nombre}-copia",
                         daemon=True).start()

    def _correr(self) -> None:
        try:
            self._copiar()
        except Exception as e:  # el reemplazo sigue vivo aunque no haya podido copiar
            self.madre.log("ERROR", f"copia de genes: {e!r}")
        finally:
            self.terminada.set()

    def _copiar(self) -> None:
        m = self.madre
        lista = ", ".join(microservicios.gen_id(c, v) for c, v, _ in self.genes) or "nada"
        m.log("REEMPLAZO", f"nací vacía para reemplazar a {m.reemplaza_nombre or '?'} "
                           f"(generación {m.generacion}); copio: {lista}")
        pedidos = [(gen, m.pedir_gen(*gen)) for gen in self.genes]
        plazo = config.PLAZO_PEDIDO * config.REINTENTOS_PEDIDO + 1.0
        for (codigo, version, sha), pedido in pedidos:
            gen_id = microservicios.gen_id(codigo, version)
            pedido.esperar(plazo)
            if pedido.estado == LISTO:
                self.fuentes[gen_id] = pedido.de
            elif self._del_banco(codigo, version, sha):
                self.fuentes[gen_id] = "banco local"
            else:
                self.faltan.append(gen_id)
        if not m.activo:
            return
        m.publicar(codigos.CLON_LISTO, {"reemplaza": m.reemplaza, "genes": m.genoma.ids(),
                                        "fuentes": self.fuentes, "faltan": self.faltan,
                                        "generacion": m.generacion})
        copiados = ", ".join(f"{g} de {de}" for g, de in self.fuentes.items()) or "ninguno"
        m.log("CLON_LISTO", f"reemplazo listo: {copiados}"
                            + (f" · NO pude copiar {', '.join(self.faltan)}" if self.faltan else ""))

    def _del_banco(self, codigo: str, version: str, sha: str | None) -> bool:
        """Última fuente: el banco local, solo si es el MISMO gen (sha)."""
        m = self.madre
        try:
            paquete = microservicios.leer(microservicios.resolver(m.banco, f"{codigo}@{version}"))
        except (LookupError, OSError, ValueError) as e:
            m.log("GEN_RECHAZADO", f"{codigo}@{version}: nadie lo entregó y no está en el banco "
                                   f"({e})")
            return False
        if not coincide(sha, paquete.sha_real):
            m.log("GEN_RECHAZADO", f"{paquete.id}: el del banco no es el que tenía la perdida "
                                   f"(sha {paquete.sha_real[:8]} ≠ {sha})")
            return False
        m.log("GEN_PIDE", f"{paquete.id}: nadie lo entregó por el Campo de Datos; lo copio del "
                          f"banco local (mismo sha {paquete.sha_real[:8]})")
        return m.instalar(paquete, f"{BANCO} (respaldo)").ok
