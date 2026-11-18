"""Ventana del gestor de microservicios (PLAN §4.5).

    ┌ Gestor de microservicios · G-N2 ───────────────── ● Nodo 2 · BD 6 genes ┐
    │ ┌ Topología (diagrama vivo) ──────────────┐ ┌ Catálogo · BD SQLite ───┐ │
    │ │  nodos, enlaces reales, células por gen │ │ SUM 1.0 ✔ …  SUM 9.9 ✘  │ │
    │ │  clic en una madre = destino            │ ├ Célula destino ─────────┤ │
    │ └─────────────────────────────────────────┘ │                         │ │
    │ [Órdenes|Bitácora|Regeneración] historial   │ ├ Órdenes ────────────────┤ │
    │                                             │ └─────────────────────────┘ │
    └─────────────────────────────────────────────────────────────────────────┘

La red corre en los hilos del núcleo; esta ventana solo lee ``gestor.foto()`` y
vacía la cola de eventos cada 100 ms desde el hilo de Tkinter.
"""

import queue
import tkinter as tk
from tkinter import scrolledtext, ttk

from comun import estilo, hashes, tema
from gestor import nucleo as gn
from gestor.diagrama import Diagrama
from gestor.topologia import CAIDA

COLOR_ESTADO = {gn.ENVIADA: tema.TEXTO_SUAVE, gn.RECIBIDA: tema.AVISO, gn.OK: tema.OK,
                gn.RECHAZADA: tema.ERROR, gn.SIN_RESPUESTA: tema.ERROR,
                gn.SIN_RESULTADO: tema.ERROR, gn.NO_SALIO: tema.ERROR}
COLOR_LOG = {"ORDEN": tema.ACENTO, "GEN_ACK": tema.TEXTO_SUAVE, "ORDEN_OK": tema.OK,
             "RECHAZADA": tema.ERROR, "SIN_RESPUESTA": tema.ERROR, "CAIDA": tema.ERROR,
             "ADIOS": tema.AVISO, "DISTRIBUIR": tema.ACENTO, "BD": tema.OK,
             "CONEXION": tema.OK, "GEN_PIDE": tema.AVISO, "ENTREGA": tema.OK,
             "OTRO_GESTOR": tema.TEXTO_SUAVE, "CONSULTA": tema.TEXTO_SUAVE,
             "DESCONEXION": tema.ERROR, "FAILOVER": tema.AVISO}
MAX_LINEAS_LOG = 500
# Línea de tiempo de regeneración: color y rótulo corto de cada paso.
PASOS_REGEN = {"CAIDA": (tema.ERROR, "✕ caída"), "CLON_AVISO": (tema.ACENTO, "◎ clonador"),
               "CONECTADA": (tema.ACENTO, "● conectada"), "ENTREGA": (tema.OK, "⇢ gen"),
               "CLON_LISTO": (tema.OK, "✔ listo"), "EN_ESPERA": (tema.AVISO, "… en espera"),
               "NIVEL_OK": (tema.OK, "■ nivel ok")}


class VentanaGestor:
    def __init__(self, gestor: gn.Gestor, geometria: str | None = None):
        self.gestor = gestor
        self.raiz = tk.Tk()
        self.raiz.title(f"{gestor.nombre} · Gestor de microservicios")
        self.raiz.geometry(geometria or "1420x820")   # cabe en 1463×914 con la barra de tareas
        self.raiz.minsize(1100, 660)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)
        estilo.aplicar(self.raiz)

        self._destino: str | None = None
        self._gen: tuple[str, str] | None = None        # (código, versión) del catálogo
        self._ultima: str | None = None                 # folio de la última orden de un botón
        self._version_topo = -1
        self._hubo_regeneracion = False
        self._construir()
        self._pintar_catalogo(gestor.catalogo())
        self._pintar_destino()

    # ------------------------------------------------------------ construcción

    def _construir(self) -> None:
        r = self.raiz
        r.columnconfigure(0, weight=1)
        r.rowconfigure(1, weight=1)
        self._cabecera(r).grid(row=0, column=0, sticky="ew", padx=tema.MARGEN,
                               pady=(tema.MARGEN, tema.SEPARACION))

        cuerpo = tk.Frame(r, bg=tema.FONDO)
        cuerpo.grid(row=1, column=0, sticky="nsew", padx=tema.MARGEN, pady=(0, tema.MARGEN))
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        izquierda = tk.Frame(cuerpo, bg=tema.FONDO)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, tema.SEPARACION))
        izquierda.columnconfigure(0, weight=1)
        izquierda.rowconfigure(0, weight=1)
        marco, dentro = estilo.tarjeta(izquierda, "Topología",
                                       derecha="armada solo con latidos (NODO_LAT, CEL_LAT)")
        marco.grid(row=0, column=0, sticky="nsew")
        self._diagrama = Diagrama(dentro, al_elegir=self._elegir)
        self._diagrama.pack(fill="both", expand=True)
        self._historial_ui(izquierda).grid(row=1, column=0, sticky="nsew",
                                           pady=(tema.SEPARACION, 0))

        lateral = tk.Frame(cuerpo, bg=tema.FONDO, width=400)
        lateral.grid(row=0, column=1, sticky="ns")
        lateral.grid_propagate(False)
        lateral.columnconfigure(0, weight=1)
        lateral.rowconfigure(0, weight=1)
        self._catalogo_ui(lateral).grid(row=0, column=0, sticky="nsew")
        self._destino_ui(lateral).grid(row=1, column=0, sticky="ew", pady=tema.SEPARACION)
        self._ordenes_ui(lateral).grid(row=2, column=0, sticky="ew")

    def _cabecera(self, padre) -> tk.Frame:
        f = tk.Frame(padre, bg=tema.FONDO)
        izquierda = tk.Frame(f, bg=tema.FONDO)
        izquierda.pack(side="left")
        tk.Label(izquierda, text=f"Gestor de microservicios · {self.gestor.nombre}",
                 font=tema.FUENTE_TITULO, bg=tema.FONDO, fg=tema.TEXTO).pack(anchor="w")
        tk.Label(izquierda, bg=tema.FONDO, fg=tema.TEXTO_SUAVE, font=tema.FUENTE_CHICA,
                 text="Herramienta administrativa, no orquestador: publica órdenes por el "
                      "Campo de Datos y cada madre decide si las acepta.").pack(anchor="w")
        derecha = tk.Frame(f, bg=tema.FONDO)
        derecha.pack(side="right")
        self._pil_bd = estilo.pildora(derecha, "BD …", tema.OK)
        self._pil_bd.pack(side="right", padx=(6, 0))
        self._pil_regen = estilo.pildora(derecha, "regeneración: en reposo", tema.TEXTO_SUAVE)
        self._pil_regen.pack(side="right", padx=(6, 0))
        self._pil_conexion = estilo.pildora(derecha, f"conectando a {self.gestor.nodo_inicial}…",
                                            tema.AVISO)
        self._pil_conexion.pack(side="right")
        return f

    def _catalogo_ui(self, padre) -> tk.Frame:
        marco, dentro = estilo.tarjeta(padre, "Catálogo", derecha="BD SQLite")
        columnas = (("gen", 70), ("nombre", 170), ("sha", 72), ("ok", 34))
        self._tabla_cat = ttk.Treeview(dentro, columns=[c for c, _ in columnas],
                                       show="headings", height=6, selectmode="browse")
        for c, ancho in columnas:
            self._tabla_cat.heading(c, text={"ok": "", "sha": "sha256"}.get(c, c), anchor="w")
            self._tabla_cat.column(c, width=ancho, minwidth=30, anchor="w",
                                   stretch=c == "nombre")
        self._tabla_cat.tag_configure("manipulado", foreground=tema.ERROR)
        self._tabla_cat.tag_configure("par", background=tema.SUPERFICIE_2)
        self._tabla_cat.pack(fill="both", expand=True)
        self._tabla_cat.bind("<<TreeviewSelect>>", self._gen_elegido)
        pie = tk.Frame(dentro, bg=tema.SUPERFICIE)
        pie.pack(fill="x", pady=(tema.SEPARACION, 0))
        self._lbl_cat = tk.Label(pie, bg=tema.SUPERFICIE, fg=tema.TEXTO_SUAVE,
                                 font=tema.FUENTE_CHICA, anchor="w")
        self._lbl_cat.pack(side="left", fill="x", expand=True)
        estilo.boton(pie, "Importar carpeta", self._importar).pack(side="right")
        return marco

    def _destino_ui(self, padre) -> tk.Frame:
        marco, dentro = estilo.tarjeta(padre, "Célula destino")
        self._lbl_destino = tk.Label(dentro, bg=tema.SUPERFICIE, fg=tema.TEXTO,
                                     font=(tema.FAMILIA, 13, "bold"), anchor="w")
        self._lbl_destino.pack(fill="x")
        self._lbl_destino_det = tk.Label(dentro, bg=tema.SUPERFICIE, fg=tema.TEXTO_SUAVE,
                                         font=tema.FUENTE_CHICA, anchor="w", justify="left")
        self._lbl_destino_det.pack(fill="x")
        self._genes_destino = tk.Frame(dentro, bg=tema.SUPERFICIE)
        self._genes_destino.pack(fill="x", pady=(4, 0))
        return marco

    def _ordenes_ui(self, padre) -> tk.Frame:
        marco, dentro = estilo.tarjeta(padre, "Órdenes por el Campo de Datos")
        rejilla = tk.Frame(dentro, bg=tema.SUPERFICIE)
        rejilla.pack(fill="x")
        rejilla.columnconfigure((0, 1), weight=1, uniform="b")
        botones = [("Inyectar (alta)", self._inyectar, "primario"),
                   ("Sustituir versión", self._sustituir, "normal"),
                   ("Baja del gen", self._baja, "normal"),
                   ("Retirar célula", self._retirar, "peligro")]
        for i, (texto, comando, tipo) in enumerate(botones):
            estilo.boton(rejilla, texto, comando, tipo=tipo).grid(
                row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        estilo.boton(rejilla, "Sustituir en todas las que lo tengan",
                     self._sustituir_todas).grid(row=2, column=0, columnspan=2, sticky="ew",
                                                 padx=2, pady=2)
        tk.Frame(dentro, bg=tema.BORDE, height=1).pack(fill="x", pady=tema.SEPARACION)
        estilo.boton(dentro, "Distribuir una de cada operación por nodo", self._distribuir,
                     tipo="primario").pack(fill="x", padx=2)
        estilo.boton(dentro, "Consultar topología (TOPO_REQ)", self._consultar).pack(
            fill="x", padx=2, pady=(4, 0))
        self._lbl_estado = tk.Label(dentro, bg=tema.SUPERFICIE, fg=tema.TEXTO_SUAVE,
                                    font=tema.FUENTE_CHICA, anchor="w", justify="left",
                                    wraplength=360, text="Elige una madre en el diagrama y un "
                                                         "gen en el catálogo.")
        self._lbl_estado.pack(fill="x", pady=(tema.SEPARACION, 0))
        return marco

    def _historial_ui(self, padre) -> ttk.Notebook:
        libro = ttk.Notebook(padre, height=170)
        pestana = tk.Frame(libro, bg=tema.SUPERFICIE)
        columnas = (("hora", 64), ("folio", 118), ("acción", 58), ("destino", 70),
                    ("gen", 70), ("estado", 92), ("ms", 40), ("detalle", 420))
        self._tabla_ord = ttk.Treeview(pestana, columns=[c for c, _ in columnas],
                                       show="headings", selectmode="browse")
        for c, ancho in columnas:
            self._tabla_ord.heading(c, text=c, anchor="w")
            self._tabla_ord.column(c, width=ancho, minwidth=40, anchor="w",
                                   stretch=c == "detalle")
        for estado, color in COLOR_ESTADO.items():
            self._tabla_ord.tag_configure(estado, foreground=color)
        barra = ttk.Scrollbar(pestana, orient="vertical", command=self._tabla_ord.yview)
        self._tabla_ord.configure(yscrollcommand=barra.set)
        self._tabla_ord.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        libro.add(pestana, text="Órdenes")

        self._txt_log = scrolledtext.ScrolledText(libro, wrap="word", state="disabled",
                                                  font=tema.FUENTE_MONO, bg=tema.SUPERFICIE,
                                                  fg=tema.TEXTO, relief="flat", borderwidth=0)
        for evento, color in COLOR_LOG.items():
            self._txt_log.tag_config(evento, foreground=color, font=(tema.MONO, 9, "bold"))
        libro.add(self._txt_log, text="Bitácora")

        self._txt_regen = scrolledtext.ScrolledText(libro, wrap="word", state="disabled",
                                                    font=tema.FUENTE, bg=tema.SUPERFICIE,
                                                    fg=tema.TEXTO, relief="flat", borderwidth=0,
                                                    padx=8, pady=6, spacing1=3)
        self._txt_regen.tag_config("hora", foreground=tema.TEXTO_SUAVE, font=tema.FUENTE_MONO)
        for evento, (color, _) in PASOS_REGEN.items():
            self._txt_regen.tag_config(evento, foreground=color, font=tema.FUENTE_NEGRITA)
        self._txt_regen.insert("1.0", "Sin fallas todavía. Si una madre muere, aquí se ve sola "
                                      "su regeneración: nadie tiene que tocar nada.\n", ("hora",))
        self._txt_regen.config(state="disabled")
        libro.add(self._txt_regen, text="Regeneración")
        self._libro = libro
        return libro

    # ---------------------------------------------------------- selección

    def _elegir(self, h: str) -> None:
        self._destino = h
        self._pintar_destino()
        self._diagrama.dibujar(self.gestor.foto(), self._destino, self.gestor.hash)

    def _gen_elegido(self, _evento=None) -> None:
        sel = self._tabla_cat.selection()
        if sel:
            codigo, _, version = sel[0].partition("@")
            self._gen = (codigo, version)

    def _pintar_destino(self) -> None:
        for hijo in self._genes_destino.winfo_children():
            hijo.destroy()
        c = self.gestor.celula(self._destino) if self._destino else None
        if c is None:
            self._lbl_destino.config(text="—", fg=tema.TEXTO_SUAVE)
            self._lbl_destino_det.config(text="Clic en una madre del diagrama para elegirla.")
            return
        caida = c.estado == CAIDA
        self._lbl_destino.config(text=c.nombre, fg=tema.ERROR if caida else tema.TEXTO)
        partes = [f"en {c.nodo_nombre or '?'}", f"hash {hashes.corto(c.hash)}",
                  f"atendidas {c.atendidas}"]
        if c.generacion:
            partes.append(f"generación {c.generacion}")
        if caida:
            partes.append("SIN LATIDO")
        self._lbl_destino_det.config(text=" · ".join(partes))
        if c.genes:
            for g in c.genes:
                estilo.pildora(self._genes_destino, f"{g['codigo']} {g['version']} · {g['sha8']}",
                               tema.color_gen(g["codigo"])).pack(side="left", padx=(0, 4))
        else:
            estilo.pildora(self._genes_destino, "vacía: sin genes", tema.APAGADO).pack(
                side="left")
        if c.mudo:
            estilo.pildora(self._genes_destino, "muda", tema.ERROR).pack(side="left", padx=4)

    # -------------------------------------------------------------- acciones

    def _decir(self, texto: str, color: str = tema.TEXTO_SUAVE) -> None:
        self._lbl_estado.config(text=texto, fg=color)

    def _requiere(self, *, gen: bool) -> bool:
        if self._destino is None or self.gestor.celula(self._destino) is None:
            self._decir("Primero elige una madre en el diagrama.", tema.ERROR)
            return False
        if gen and self._gen is None:
            self._decir("Elige un gen en el catálogo.", tema.ERROR)
            return False
        return True

    def _resultado(self, r, que: str) -> None:
        if isinstance(r, gn.Orden):
            self._ultima = r.folio
            self._decir(f"{r.folio}: {que} {r.gen} → {r.destino_nombre}. Esperando GEN_ACK…",
                        tema.ACENTO)
        else:
            self._decir(r, tema.ERROR)

    def _inyectar(self) -> None:
        if self._requiere(gen=True):
            self._resultado(self.gestor.inyectar(self._destino, *self._gen), "alta de")

    def _sustituir(self) -> None:
        if self._requiere(gen=True):
            self._resultado(self.gestor.sustituir(self._destino, *self._gen), "cambio a")

    def _baja(self) -> None:
        if not self._requiere(gen=False):
            return
        c = self.gestor.celula(self._destino)
        if self._gen and self._gen[0] in c.codigos:
            codigo = self._gen[0]
        elif len(c.codigos) == 1:
            codigo = c.codigos[0]
        else:
            self._decir(f"{c.nombre} no tiene un gen claro que dar de baja: elige uno en el "
                        f"catálogo.", tema.ERROR)
            return
        self._resultado(self.gestor.baja(self._destino, codigo), "baja de")

    def _retirar(self) -> None:
        if self._requiere(gen=False):
            self._resultado(self.gestor.retirar(self._destino), "retiro")

    def _sustituir_todas(self) -> None:
        if self._gen is None:
            self._decir("Elige en el catálogo la versión nueva.", tema.ERROR)
            return
        ordenes = self.gestor.sustituir_en_todas(*self._gen)
        gen = "@".join(self._gen)
        self._decir(f"{len(ordenes)} orden(es) de cambio a {gen}" if ordenes
                    else f"Ninguna madre tiene {self._gen[0]} con otra versión.",
                    tema.ACENTO if ordenes else tema.TEXTO_SUAVE)

    def _distribuir(self) -> None:
        ordenes, notas = self.gestor.distribuir()
        texto = f"Distribuir: {len(ordenes)} orden(es) de alta."
        if notas:
            texto += " " + "; ".join(notas)
        elif not ordenes:
            texto = "Cada nodo ya tiene una madre por operación: nada que distribuir."
        self._decir(texto, tema.ACENTO if ordenes else tema.TEXTO_SUAVE)

    def _consultar(self) -> None:
        self.gestor.consultar()
        self._decir("TOPO_REQ publicado: todas las células contestan con su estado.")

    def _importar(self) -> None:
        ids = self.gestor.importar()
        self._decir(f"Importé {len(ids)} gen(es) de {self.gestor.banco.name}/ a la BD.", tema.OK)

    # ---------------------------------------------------------- refresco

    def ejecutar(self) -> None:
        self.raiz.after(100, self._vaciar_cola)
        self.raiz.after(250, self._refrescar_topologia)
        self.raiz.mainloop()

    def _refrescar_topologia(self) -> None:
        version = self.gestor.topologia.version
        if version != self._version_topo:
            self._version_topo = version
            self._diagrama.dibujar(self.gestor.foto(), self._destino, self.gestor.hash)
            self._pintar_destino()
        if self.gestor.activo:
            self.raiz.after(250, self._refrescar_topologia)

    def _vaciar_cola(self) -> None:
        lineas = []
        try:
            for _ in range(1000):
                tipo, datos = self.gestor.eventos.get_nowait()
                if tipo == "log":
                    lineas.append(datos)
                elif tipo == "orden":
                    self._pintar_orden(datos)
                elif tipo == "regeneracion":
                    self._pintar_regeneracion(datos)
                elif tipo == "destello":
                    self._diagrama.destello(*datos)
                elif tipo == "catalogo":
                    self._pintar_catalogo(datos)
                elif tipo == "conexion":
                    self._pintar_conexion(datos)
        except queue.Empty:
            pass
        if lineas:
            self._agregar_log(lineas)
        if self.gestor.activo:
            self.raiz.after(100, self._vaciar_cola)

    def _pintar_catalogo(self, catalogo: list[dict]) -> None:
        t = self._tabla_cat
        t.delete(*t.get_children())
        for i, g in enumerate(catalogo):
            etiquetas = ["manipulado"] if not g["integro"] else []
            if i % 2:
                etiquetas.append("par")
            t.insert("", "end", iid=g["id"], tags=etiquetas,
                     values=(f"{g['codigo']} {g['version']}", g["nombre"], g["sha8"],
                             "✔" if g["integro"] else "✘"))
        if self._gen and "@".join(self._gen) in t.get_children():
            t.selection_set("@".join(self._gen))
        manipulados = sum(1 for g in catalogo if not g["integro"])
        self._lbl_cat.config(text=f"{len(catalogo)} genes · ✘ = sha256 no coincide "
                                  f"({manipulados})")
        estilo.pintar_pildora(self._pil_bd, f"BD · {len(catalogo)} genes", tema.OK)

    def _pintar_orden(self, fila: dict) -> None:
        t = self._tabla_ord
        valores = (fila["hora"], fila["folio"], fila["accion"], fila["destino_nombre"],
                   fila["gen"], fila["estado"], fila["ms"] if fila["ms"] is not None else "",
                   fila["detalle"])
        if t.exists(fila["folio"]):
            t.item(fila["folio"], values=valores, tags=(fila["estado"],))
        else:
            t.insert("", 0, iid=fila["folio"], values=valores, tags=(fila["estado"],))
        if fila["destino"] == self._destino:
            self._pintar_destino()
        if fila["folio"] == self._ultima and fila["estado"] != gn.ENVIADA:
            texto = f"{fila['folio']} · {fila['destino_nombre']}: {fila['estado']}"
            if fila["estado"] != gn.RECIBIDA:
                texto += f" — {fila['detalle']}"
            self._decir(texto, COLOR_ESTADO.get(fila["estado"], tema.TEXTO_SUAVE))

    def _pintar_conexion(self, datos: dict) -> None:
        estado = datos.get("estado")
        if estado in ("conexion", "reconexion", "failover"):
            flecha = "failover → " if estado == "failover" else ""
            estilo.pintar_pildora(self._pil_conexion, f"● {flecha}{datos['nodo']} "
                                                      f"({datos['endpoint']})", tema.OK)
        elif estado == "caida":
            estilo.pintar_pildora(self._pil_conexion, f"● se perdió {datos.get('nodo')}; "
                                                      f"buscando otro…", tema.AVISO)
        else:
            estilo.pintar_pildora(self._pil_conexion, "● sin Campo de Datos", tema.ERROR)

    def _pintar_regeneracion(self, linea) -> None:
        hora_, evento, texto = linea
        t = self._txt_regen
        t.config(state="normal")
        if not self._hubo_regeneracion:
            self._hubo_regeneracion = True
            t.delete("1.0", "end")
        _, titulo = PASOS_REGEN.get(evento, (tema.TEXTO, evento))
        t.insert("end", f"{hora_[:8]}  ", ("hora",))
        t.insert("end", f"{titulo:<12}", (evento,))
        t.insert("end", f" {texto}\n")
        t.see("end")
        t.config(state="disabled")
        if evento == "CAIDA":   # lo automático se ve solo: la pestaña se abre sola
            self._libro.select(self._txt_regen)
        pildora = {"CAIDA": ("pérdida detectada", tema.ERROR),
                   "CLON_AVISO": ("regenerando…", tema.ACENTO),
                   "EN_ESPERA": ("regenerando (gradual)…", tema.AVISO),
                   "NIVEL_OK": ("nivel ok · sin clonar", tema.OK)}.get(evento)
        if pildora:
            estilo.pintar_pildora(self._pil_regen, f"regeneración: {pildora[0]}", pildora[1])

    def _agregar_log(self, lineas) -> None:
        t = self._txt_log
        t.config(state="normal")
        for hora_, evento, texto in lineas:
            t.insert("end", f"{hora_[:8]} ")
            t.insert("end", f"{evento:<13}", (evento,))
            t.insert("end", f" {texto}\n")
        total = int(t.index("end-1c").split(".")[0])
        if total > MAX_LINEAS_LOG:
            t.delete("1.0", f"{total - MAX_LINEAS_LOG}.0")
        t.see("end")
        t.config(state="disabled")

    def _cerrar(self) -> None:
        self.gestor.detener()
        estilo.cerrar(self.raiz)
