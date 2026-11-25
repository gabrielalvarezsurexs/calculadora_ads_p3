"""La calculadora: lo único que ve el usuario final.

    ┌ GUI-1 ─────────────── ● Nodo 1 ┐
    │            7 + 5               │   display
    │ [7][8][9][÷]  …  [C][⌫][  =  ] │   teclado (operadores del color de su gen)
    │ Disponibilidad (latidos)       │   vivas · mín. ACK editable · ✓/✗
    │ [Evento | Mis eventos | Proto] │   tarjeta del evento con sus 4 fases
    │ ajenas ignoradas: 3   [Ráfaga] │
    └────────────────────────────────┘

Adaptado del primer parcial (teclado, display, atajos y el patrón cola +
``after(100)``). Lo que hace visible el protocolo: la conexión al Campo de
Datos, la disponibilidad por latidos con su mínimo de acuses editable en vivo y,
sobre todo, la **tarjeta del evento** (PLAN §5.4): folio, fase actual
(INICIO → CONFIRMADO → PROCESADO → FINALIZADO), sello, ACK k/mín con nombres,
esperados, ausentes, quién respondió con qué gen, y el rastro de la huella.

La red corre en hilos del núcleo y NO toca widgets: el núcleo empuja eventos a
una ``queue.Queue`` y esta ventana la vacía desde el hilo de Tkinter.
"""

import queue
import tkinter as tk
from tkinter import scrolledtext, ttk

from comun import codigos, estilo, foliado, formato, tema
from interfaz.nucleo import EN_VUELO, FALLIDA, MINIMO_RANGO

TECLA_SERVICIO = {"+": "SUM", "-": "SUB", "*": "MUL", "/": "DIV"}
COLORES_LOG = {
    "EVENTO_INICIO": tema.ACENTO, "ACUSE": tema.TEXTO_SUAVE, "CONFIRMADO": tema.OK,
    "AUSENTES": tema.AVISO, "RESULTADO": tema.OK, "FIN": tema.ACENTO,
    "REINTENTO": tema.AVISO, "RETENIDA": tema.AVISO, "FALLIDA": tema.ERROR, "SELLO": tema.ERROR,
    "DESHABILITADA": tema.ERROR, "HABILITADA": tema.OK, "FAILOVER": tema.AVISO,
    "DESCONEXION": tema.ERROR, "DUPLICADA": tema.AVISO, "TARDÍA": tema.AVISO,
    "NO_DISPONIBLE": tema.ERROR, "CONEXION": tema.OK,
}
NOMBRE_FASE = {foliado.INICIO: "inicio", foliado.CONFIRMADO: "confirmado",
               foliado.PROCESADO: "procesado", foliado.FINALIZADO: "finalizado"}
MAX_LINEAS_LOG = 400
MAX_OPERACIONES = 60
DISPLAY = "#111827"


class VentanaInterfaz:
    def __init__(self, interfaz, geometria: str | None = None):
        self.interfaz = interfaz
        self.raiz = tk.Tk()
        self.raiz.title(f"{interfaz.nombre} · Calculadora ADS")
        self.raiz.geometry(geometria or "460x800")
        self.raiz.minsize(420, 680)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)
        estilo.aplicar(self.raiz)

        # Captura "a op b", como una calculadora de verdad.
        self._acumulado = ""
        self._servicio: str | None = None
        self._entrada = "0"
        self._resultado_en_display = False  # el display muestra un resultado (para encadenar)
        self._mi_op: str | None = None      # folio cuyo resultado irá al display
        self._enviada = False               # el display muestra una operación ya enviada
        self._tecleo = False                # se empezó otra mientras _mi_op estaba en vuelo
        self._operaciones: dict[str, dict] = {}  # folio -> fila (en orden de llegada)
        self._evento: str | None = None     # folio que muestra la tarjeta
        self._seguir = True                 # la tarjeta sigue a la operación más nueva
        self._ajenas_mostradas = -1

        self._botones_op: dict[str, tk.Button] = {}
        self._disp_widgets: dict[str, tuple] = {}
        self._construir()
        self._pintar_disponibilidad(self.interfaz.disponibilidad())
        self._pintar_evento()

    # ------------------------------------------------------------ construcción

    def _construir(self) -> None:
        r = self.raiz
        m = tema.MARGEN
        cabeza = tk.Frame(r, bg=tema.FONDO)
        cabeza.pack(fill="x", padx=m, pady=(m, 4))
        tk.Label(cabeza, text=self.interfaz.nombre, font=tema.FUENTE_TITULO, bg=tema.FONDO,
                 fg=tema.TEXTO).pack(side="left")
        self._pil_conexion = estilo.pildora(cabeza, f"conectando a {self.interfaz.nodo_inicial}…",
                                            tema.AVISO)
        self._pil_conexion.pack(side="right")

        self._lbl_display = tk.Label(r, text="0", anchor="e", font=(tema.MONO, 22),
                                     bg=DISPLAY, fg="#F9FAFB", padx=12, pady=4)
        self._lbl_display.pack(fill="x", padx=m)
        self._lbl_estado = tk.Label(r, text="listo", anchor="e", bg=tema.FONDO,
                                    fg=tema.TEXTO_SUAVE, font=tema.FUENTE_CHICA)
        self._lbl_estado.pack(fill="x", padx=m, pady=(2, 2))

        self._teclado(r).pack(fill="x", padx=m - 2)
        self._disponibilidad_ui(r).pack(fill="x", padx=m, pady=(6, 0))
        pie = tk.Frame(r, bg=tema.FONDO)   # abajo primero: nunca queda fuera de la ventana
        pie.pack(side="bottom", fill="x", padx=m, pady=(4, m))
        self._libro_ui(r).pack(fill="both", expand=True, padx=m, pady=(6, 0))
        self._lbl_ajenas = tk.Label(pie, text="", bg=tema.FONDO, fg=tema.TEXTO_SUAVE,
                                    font=tema.FUENTE_CHICA)
        self._lbl_ajenas.pack(side="left")
        estilo.boton(pie, "Ráfaga ×8", self._rafaga, padx=10, pady=3).pack(side="right")

        # El teclado físico también funciona.
        for tecla in "0123456789.+-*/":
            r.bind(tecla, lambda e: self._tecla_fisica(e))
        r.bind("<Return>", lambda e: self._resolver() if not self._en_spinbox(e) else None)
        r.bind("=", lambda e: self._resolver())
        r.bind("<Escape>", lambda e: self._tecla("C"))
        r.bind("<BackSpace>", lambda e: None if self._en_spinbox(e) else self._borrar_digito())

    def _teclado(self, padre) -> tk.Frame:
        teclado = tk.Frame(padre, bg=tema.FONDO)
        filas = [["7", "8", "9", "/"], ["4", "5", "6", "*"], ["1", "2", "3", "-"],
                 ["0", ".", "±", "+"]]
        for j in range(4):
            teclado.columnconfigure(j, weight=1, uniform="tecla")
        for i, fila in enumerate(filas):
            for j, tecla in enumerate(fila):
                servicio = TECLA_SERVICIO.get(tecla)
                if servicio:
                    color = tema.color_gen(servicio)
                    b = self._tecla_btn(teclado, codigos.SIMBOLOS[servicio], color,
                                        tema.TEXTO_INVERSO, lambda t=tecla: self._tecla(t))
                    self._botones_op[servicio] = b
                else:
                    b = self._tecla_btn(teclado, tecla, tema.SUPERFICIE, tema.TEXTO,
                                        lambda t=tecla: self._tecla(t))
                b.grid(row=i, column=j, sticky="nsew", padx=2, pady=2)
        self._tecla_btn(teclado, "C", tema.SUPERFICIE_2, tema.TEXTO,
                        lambda: self._tecla("C")).grid(row=4, column=0, sticky="nsew", padx=2,
                                                       pady=2)
        self._tecla_btn(teclado, "⌫", tema.SUPERFICIE_2, tema.TEXTO,
                        self._borrar_digito).grid(row=4, column=1, sticky="nsew", padx=2, pady=2)
        self._tecla_btn(teclado, "=", tema.ACENTO, tema.TEXTO_INVERSO, self._resolver).grid(
            row=4, column=2, columnspan=2, sticky="nsew", padx=2, pady=2)
        return teclado

    @staticmethod
    def _tecla_btn(padre, texto: str, fondo: str, frente: str, comando) -> tk.Button:
        return tk.Button(padre, text=texto, command=comando, bg=fondo, fg=frente,
                         activebackground=tema.color_suave(fondo, 0.25) if fondo != tema.SUPERFICIE
                         else tema.SUPERFICIE_2, activeforeground=frente, relief="flat",
                         borderwidth=0, font=(tema.FAMILIA, 12), pady=1, cursor="hand2",
                         highlightthickness=1, highlightbackground=tema.BORDE,
                         disabledforeground=tema.color_suave(frente, 0.4))

    def _disponibilidad_ui(self, padre) -> tk.Frame:
        marco, dentro = estilo.tarjeta(padre, "Disponibilidad", derecha="por latidos (CEL_LAT)")
        dentro.columnconfigure(1, weight=1)
        for i, s in enumerate(codigos.SERVICIOS):
            nombre = tk.Frame(dentro, bg=tema.SUPERFICIE)
            nombre.grid(row=i, column=0, sticky="w", pady=1)
            tk.Label(nombre, text="●", fg=tema.color_gen(s), bg=tema.SUPERFICIE,
                     font=tema.FUENTE).pack(side="left")
            tk.Label(nombre, text=f"{codigos.SIMBOLOS[s]} {codigos.NOMBRES[s]}", anchor="w",
                     bg=tema.SUPERFICIE, fg=tema.TEXTO, width=16).pack(side="left")
            vivas = tk.Label(dentro, text="vivas 0", anchor="w", bg=tema.SUPERFICIE,
                             fg=tema.TEXTO_SUAVE, font=tema.FUENTE_CHICA)
            vivas.grid(row=i, column=1, sticky="w")
            tk.Label(dentro, text="mín. ACK", bg=tema.SUPERFICIE, fg=tema.TEXTO_SUAVE,
                     font=tema.FUENTE_CHICA).grid(row=i, column=2, sticky="e", padx=(0, 4))
            var = tk.StringVar(self.raiz, value=str(self.interfaz.acuses_min[s]))
            caja = tk.Spinbox(dentro, from_=MINIMO_RANGO[0], to=MINIMO_RANGO[1], width=3,
                              textvariable=var, font=tema.FUENTE_CHICA, relief="flat",
                              bg=tema.SUPERFICIE_2, buttonbackground=tema.SUPERFICIE_2,
                              command=lambda s=s: self._ajustar_minimo(s))
            caja.grid(row=i, column=3, padx=(0, 6), pady=1)
            caja.bind("<Return>", lambda e, s=s: self._ajustar_minimo(s))
            caja.bind("<FocusOut>", lambda e, s=s: self._ajustar_minimo(s))
            marca = estilo.pildora(dentro, "✗", tema.ERROR, width=2)
            marca.grid(row=i, column=4)
            self._disp_widgets[s] = (vivas, var, marca)
        return marco

    def _libro_ui(self, padre) -> ttk.Notebook:
        libro = ttk.Notebook(padre)
        self._libro = libro

        # --- Evento -------------------------------------------------------------
        ev = tk.Frame(libro, bg=tema.SUPERFICIE, padx=10, pady=6)
        cabeza = tk.Frame(ev, bg=tema.SUPERFICIE)
        cabeza.pack(fill="x")
        self._lbl_folio = tk.Label(cabeza, bg=tema.SUPERFICIE, fg=tema.TEXTO,
                                   font=(tema.MONO, 11, "bold"), anchor="w")
        self._lbl_folio.pack(side="left")
        self._pil_estado = estilo.pildora(cabeza, "", tema.TEXTO_SUAVE)
        self._pil_estado.pack(side="right")
        self._lbl_operacion = tk.Label(ev, bg=tema.SUPERFICIE, fg=tema.TEXTO,
                                       font=tema.FUENTE_SUBTITULO, anchor="w")
        self._lbl_operacion.pack(fill="x", pady=(0, 4))
        fases = tk.Frame(ev, bg=tema.SUPERFICIE)
        fases.pack(fill="x")
        self._fases = []
        for i, fase in enumerate(foliado.FASES):
            fases.columnconfigure(i, weight=1, uniform="fase")
            etiqueta = tk.Label(fases, text=f"{i + 1}. {NOMBRE_FASE[fase]}", pady=3,
                                font=(tema.FAMILIA, 8, "bold"))
            etiqueta.grid(row=0, column=i, sticky="ew", padx=1)
            self._fases.append(etiqueta)
        datos = tk.Frame(ev, bg=tema.SUPERFICIE)
        datos.pack(fill="both", expand=True, pady=(6, 0))
        datos.columnconfigure(1, weight=1)
        self._campos = {}
        for i, clave in enumerate(("sello", "ACK", "esperados", "ausentes", "respondió",
                                   "rastro")):
            tk.Label(datos, text=clave, bg=tema.SUPERFICIE, fg=tema.TEXTO_SUAVE,
                     font=tema.FUENTE_CHICA, anchor="nw").grid(row=i, column=0, sticky="nw",
                                                               padx=(0, 8), pady=1)
            valor = tk.Label(datos, bg=tema.SUPERFICIE, fg=tema.TEXTO, anchor="w",
                             justify="left", wraplength=330,
                             font=tema.FUENTE_MONO if clave in ("sello", "rastro")
                             else tema.FUENTE_CHICA)
            valor.grid(row=i, column=1, sticky="w", pady=1)
            self._campos[clave] = valor
        libro.add(ev, text="Evento")

        # --- Mis eventos ----------------------------------------------------------
        lista = tk.Frame(libro, bg=tema.SUPERFICIE)
        columnas = (("folio", 120), ("operación", 150), ("ACK", 44), ("estado", 80))
        self._tabla = ttk.Treeview(lista, columns=[c for c, _ in columnas], show="headings",
                                   selectmode="browse")
        for c, ancho in columnas:
            self._tabla.heading(c, text=c, anchor="w")
            self._tabla.column(c, width=ancho, minwidth=36, anchor="w", stretch=c == "operación")
        self._tabla.tag_configure(EN_VUELO, foreground=tema.AVISO)
        self._tabla.tag_configure(FALLIDA, foreground=tema.ERROR)
        barra = ttk.Scrollbar(lista, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=barra.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self._tabla.bind("<<TreeviewSelect>>", self._evento_elegido)
        libro.add(lista, text="Mis eventos")

        # --- Protocolo (mini log) --------------------------------------------------
        self._txt_log = scrolledtext.ScrolledText(libro, wrap="word", state="disabled",
                                                  font=tema.FUENTE_MONO, bg=tema.SUPERFICIE,
                                                  fg=tema.TEXTO, relief="flat", borderwidth=0,
                                                  padx=6, pady=4)
        for evento, color in COLORES_LOG.items():
            self._txt_log.tag_config(evento, foreground=color, font=(tema.MONO, 9, "bold"))
        libro.add(self._txt_log, text="Protocolo")
        return libro

    @staticmethod
    def _en_spinbox(evento) -> bool:
        return isinstance(evento.widget, tk.Spinbox)

    def _editando_minimo(self) -> bool:
        try:
            return isinstance(self.raiz.focus_get(), tk.Spinbox)
        except (KeyError, tk.TclError):
            return False

    # ------------------------------------------------------------- captura

    def _tecla_fisica(self, evento) -> None:
        if not self._en_spinbox(evento):
            self._tecla(evento.char)

    def _tecla(self, tecla: str) -> None:
        if self._enviada and tecla in TECLA_SERVICIO:
            self._decir("espera el resultado (o escribe otro número)", tema.AVISO)
            return
        nuevo_numero = ((self._resultado_en_display or self._enviada)
                        and (tecla.isdigit() or tecla == "."))
        if self._enviada:   # se empieza otra operación: la enviada ya no va al display
            self._tecleo = self._mi_op is not None
            self._enviada = False
            if nuevo_numero or tecla == "±":
                self._acumulado, self._servicio = "", None
        self._resultado_en_display = False
        if nuevo_numero:  # tras un resultado, un dígito empieza otro número
            self._entrada = "0"
        if tecla == "C":
            self._acumulado, self._servicio, self._entrada = "", None, "0"
        elif tecla in TECLA_SERVICIO:
            servicio = TECLA_SERVICIO[tecla]
            if not self.interfaz.habilitadas[servicio]:
                self._decir(f"{servicio} no disponible", tema.ERROR)
                return
            if self._servicio and self._entrada == "0":
                self._servicio = servicio   # corrige el operador: el primer número se queda
            elif self._servicio:
                self._decir("presiona = para resolver la operación actual", tema.AVISO)
                return
            else:
                self._acumulado, self._servicio, self._entrada = self._entrada, servicio, "0"
        elif tecla == ".":
            if "." not in self._entrada:
                self._entrada += "."
        elif tecla == "±":
            if self._entrada not in ("0", "0."):
                self._entrada = (self._entrada[1:] if self._entrada.startswith("-")
                                 else "-" + self._entrada)
        elif tecla.isdigit():
            self._entrada = tecla if self._entrada in ("0", "ERROR") else self._entrada + tecla
        else:
            return
        self._refrescar_display()

    def _borrar_digito(self) -> None:
        if self._enviada or self._resultado_en_display or "e" in self._entrada.lower():
            # Lo enviado o un resultado (o notación científica) no se edita dígito a
            # dígito: "1e+20" sin su último carácter sería 100. Se empieza de cero.
            self._tecleo = self._enviada and self._mi_op is not None
            self._enviada = self._resultado_en_display = False
            self._acumulado, self._servicio, self._entrada = "", None, "0"
            self._refrescar_display()
            return
        self._entrada = self._entrada[:-1]
        if self._entrada in ("", "-"):
            self._entrada = "0"
        self._refrescar_display()

    def _refrescar_display(self) -> None:
        if self._servicio:
            texto = f"{self._acumulado} {codigos.SIMBOLOS[self._servicio]} {self._entrada}"
        else:
            texto = self._entrada
        self._lbl_display.config(text=texto)

    def _resolver(self) -> None:
        if self._enviada:   # un = repetido no manda otro evento con otro folio
            self._decir(f"{self._mi_op}: ya va en camino; espera su resultado", tema.AVISO)
            return
        if self._servicio is None:
            self._decir("escoge una operación primero", tema.AVISO)
            return
        try:
            a, b = float(self._acumulado), float(self._entrada)
        except ValueError:
            self._decir("números inválidos", tema.ERROR)
            return
        folio, texto = self.interfaz.solicitar(self._servicio, a, b)
        if folio is None:
            self._decir(texto, tema.ERROR)
            return
        self._mi_op = folio
        self._enviada, self._tecleo = True, False
        self._seguir = True
        self._decir(f"{folio}: esperando acuses…", tema.AVISO)

    def _rafaga(self) -> None:
        folios = self.interfaz.rafaga(8)
        if folios:
            self._seguir = True
            self._libro.select(1)   # "Mis eventos": se ven todas en vuelo a la vez
            self._decir(f"ráfaga: {len(folios)} en vuelo ({folios[0]} … {folios[-1]})",
                        tema.AVISO)
        else:
            self._decir("ráfaga: no hay operadores disponibles", tema.ERROR)

    def _decir(self, texto: str, color: str = tema.TEXTO_SUAVE) -> None:
        self._lbl_estado.config(text=texto, fg=color)

    def _ajustar_minimo(self, servicio: str) -> None:
        _, var, _ = self._disp_widgets[servicio]
        try:
            pedido = int(var.get())
        except ValueError:
            pedido = self.interfaz.acuses_min[servicio]
        var.set(str(self.interfaz.ajustar_minimo(servicio, pedido)))

    def _evento_elegido(self, _evento=None) -> None:
        sel = self._tabla.selection()
        if sel and sel[0] in self._operaciones:
            self._evento = sel[0]
            self._seguir = sel[0] == next(reversed(self._operaciones))
            self._pintar_evento()

    # ------------------------------------------------------------- eventos

    def ejecutar(self) -> None:
        self.raiz.after(100, self._vaciar_cola)
        self.raiz.mainloop()

    def _vaciar_cola(self) -> None:
        lineas = []
        try:
            for _ in range(1000):
                tipo, datos = self.interfaz.eventos.get_nowait()
                if tipo == "log":
                    lineas.append(datos)
                elif tipo == "operacion":
                    self._pintar_operacion(datos)
                elif tipo == "disponibilidad":
                    self._pintar_disponibilidad(datos)
                elif tipo == "conexion":
                    self._pintar_conexion(datos)
        except queue.Empty:
            pass
        if lineas:
            self._agregar_log(lineas)
        if self.interfaz.ajenas != self._ajenas_mostradas:
            self._ajenas_mostradas = self.interfaz.ajenas
            self._lbl_ajenas.config(text=f"ajenas ignoradas: {self._ajenas_mostradas}  "
                                         f"(ACK/RES de folios que no son míos)")
        if self.interfaz.activo:
            self.raiz.after(100, self._vaciar_cola)

    def _pintar_conexion(self, datos: dict) -> None:
        estado = datos.get("estado")
        if estado in ("conexion", "reconexion"):
            texto, color = f"● {datos['nodo']} ({datos['endpoint']})", tema.OK
        elif estado == "failover":
            texto, color = f"● failover → {datos['nodo']}", tema.OK
        elif estado == "caida":
            texto, color = f"● se perdió {datos.get('nodo')}; buscando…", tema.AVISO
        else:
            texto, color = "● sin Campo de Datos", tema.ERROR
        estilo.pintar_pildora(self._pil_conexion, texto, color)

    def _pintar_disponibilidad(self, disp: dict) -> None:
        for s, d in disp.items():
            vivas, var, marca = self._disp_widgets[s]
            vivas.config(text=f"vivas {d['vivas']}",
                         fg=tema.TEXTO if d["vivas"] else tema.ERROR)
            if not self._editando_minimo():
                var.set(str(d["minimo"]))
            estilo.pintar_pildora(marca, "✓" if d["habilitada"] else "✗",
                                  tema.OK if d["habilitada"] else tema.ERROR)
            self._botones_op[s].config(state="normal" if d["habilitada"] else "disabled",
                                       bg=tema.color_gen(s) if d["habilitada"]
                                       else tema.SUPERFICIE_2)

    def _pintar_operacion(self, fila: dict) -> None:
        folio = fila["folio"]
        nueva = folio not in self._operaciones
        self._operaciones[folio] = fila
        while len(self._operaciones) > MAX_OPERACIONES:
            viejo = next(iter(self._operaciones))
            del self._operaciones[viejo]
            if self._tabla.exists(viejo):
                self._tabla.delete(viejo)
        valores = (folio, _operacion(fila), f"{fila['acuses']}/{fila['minimo']}", fila["estado"])
        if self._tabla.exists(folio):
            self._tabla.item(folio, values=valores, tags=(fila["estado"],))
        else:
            self._tabla.insert("", 0, iid=folio, values=valores, tags=(fila["estado"],))
        if self._seguir and nueva:
            self._evento = folio
        if folio == self._evento:
            self._pintar_evento()
        self._al_display(fila)

    def _al_display(self, fila: dict) -> None:
        if fila["folio"] != self._mi_op:
            return
        if fila["estado"] == EN_VUELO:
            self._decir(f"{fila['folio']} · {NOMBRE_FASE[fila['fase']]} · intento "
                        f"{fila['intento']} · ACK {fila['acuses']}/{fila['minimo']}", tema.AVISO)
            return
        # Terminó la última operación pedida con "=": el resultado pasa al display,
        # salvo que ya se esté escribiendo otra (entonces solo va a la línea de estado).
        self._mi_op = None
        if self._tecleo:
            self._tecleo = False
            fallo = fila["estado"] == FALLIDA or fila["error"]
            texto = (f"FALLIDA: {fila['motivo']}" if fila["estado"] == FALLIDA
                     else fila["error"] or f"{fila['folio']}: "
                                           f"{formato.numero(fila['resultado'])}")
            self._decir(texto, tema.ERROR if fallo else tema.OK)
            return
        self._enviada = False
        self._acumulado, self._servicio = "", None
        if fila["estado"] == FALLIDA or fila["error"]:
            self._entrada = "0"
            self._lbl_display.config(text="ERROR")
            self._decir(f"FALLIDA: {fila['motivo']}" if fila["estado"] == FALLIDA
                        else fila["error"], tema.ERROR)
        else:
            self._entrada = formato.numero(fila["resultado"])
            self._refrescar_display()
            self._resultado_en_display = True
            self._decir(f"{fila['folio']} · {fila['rol']} {fila['respondio']} · {fila['gen']} · "
                        f"{fila['ms']} ms", tema.OK)

    def _pintar_evento(self) -> None:
        """La tarjeta del evento (PLAN §5.4)."""
        fila = self._operaciones.get(self._evento) if self._evento else None
        if fila is None:
            self._lbl_folio.config(text="sin eventos")
            self._lbl_operacion.config(text="Haz una operación: aquí se ve su evento.",
                                       fg=tema.TEXTO_SUAVE)
            estilo.pintar_pildora(self._pil_estado, "—", tema.TEXTO_SUAVE)
            for etiqueta in self._fases:
                etiqueta.config(bg=tema.SUPERFICIE_2, fg=tema.APAGADO)
            for valor in self._campos.values():
                valor.config(text="")
            return
        self._lbl_folio.config(text=fila["folio"])
        self._lbl_operacion.config(text=_operacion(fila), fg=tema.TEXTO)
        color = {EN_VUELO: tema.AVISO, FALLIDA: tema.ERROR}.get(fila["estado"], tema.OK)
        estilo.pintar_pildora(self._pil_estado, fila["estado"], color)
        for etiqueta, (bg, fg) in zip(self._fases, _colores_fases(fila), strict=True):
            etiqueta.config(bg=bg, fg=fg)
        acusaron = ", ".join(fila["acusaron"]) or "—"
        self._campos["sello"].config(text=fila["sello"][:16] + "…")
        self._campos["ACK"].config(
            text=f"{fila['acuses']}/{fila['minimo']} (intento {fila['intento']}): {acusaron}",
            fg=tema.OK if fila["acuses"] >= fila["minimo"] else tema.AVISO)
        self._campos["esperados"].config(text=", ".join(fila["esperados"]) or "—")
        self._campos["ausentes"].config(text=", ".join(fila["ausentes"]) or "ninguno",
                                        fg=tema.AVISO if fila["ausentes"] else tema.TEXTO)
        if fila["respondio"]:
            respondio = f"{fila['respondio']} ({fila['rol']}) · {fila['gen']} · {fila['ms']} ms"
        elif fila["estado"] == FALLIDA:
            respondio = fila["motivo"] or "—"
        else:
            respondio = "esperando…"
        self._campos["respondió"].config(text=respondio)
        self._campos["rastro"].config(text=_rastro(fila["rastro"]))

    def _agregar_log(self, lineas) -> None:
        t = self._txt_log
        t.config(state="normal")
        for hora, evento, texto in lineas:
            t.insert("end", f"{hora[:8]} ")
            t.insert("end", evento, (evento,))
            t.insert("end", f" {texto}\n")
        total = int(t.index("end-1c").split(".")[0])
        if total > MAX_LINEAS_LOG:
            t.delete("1.0", f"{total - MAX_LINEAS_LOG}.0")
        t.see("end")
        t.config(state="disabled")

    def _cerrar(self) -> None:
        self.interfaz.detener()
        estilo.cerrar(self.raiz)


def _rastro(rastro: list) -> str:
    """Trayectoria lógica compacta: 'GUI-1 REQ → 4×ACK → SUM-N1 RES → GUI-1 FIN'
    (los nombres de quienes acusaron ya están en la fila ACK)."""
    grupos: list[list] = []
    for _, nombre, paso in rastro:
        if grupos and grupos[-1][0] == paso:
            grupos[-1][1].append(nombre)
        else:
            grupos.append([paso, [nombre]])
    return " → ".join(f"{nombres[0]} {paso}" if len(nombres) == 1 else f"{len(nombres)}×{paso}"
                      for paso, nombres in grupos) or "—"


_HECHA = (tema.OK_SUAVE, tema.OK)
_EN_CURSO = (tema.ACENTO, tema.TEXTO_INVERSO)
_FALLO = (tema.ERROR, tema.TEXTO_INVERSO)
_PENDIENTE = (tema.SUPERFICIE_2, tema.APAGADO)


def _colores_fases(fila: dict) -> list[tuple[str, str]]:
    """(fondo, letra) de cada fase de la tarjeta del evento."""
    n = len(foliado.FASES)
    if fila["estado"] == FALLIDA:
        # Inicio sí; confirmado solo si llegó el mínimo; la primera que no llegó, en
        # rojo (ahí falló); finalizado sí, porque se publicó X_FIN.
        fallo = 2 if fila["acuses"] >= fila["minimo"] else 1
        return [_HECHA if i < fallo or i == n - 1 else _FALLO if i == fallo else _PENDIENTE
                for i in range(n)]
    actual = foliado.FASES.index(fila["fase"])
    return [_HECHA if i < actual or (i == actual and fila["finalizado"])
            else _EN_CURSO if i == actual else _PENDIENTE for i in range(n)]


def _operacion(fila: dict) -> str:
    """'7 + 5 = 12' (o '= …' si aún no hay resultado)."""
    texto = formato.operacion(fila["a"], fila["servicio"], fila["b"], fila["resultado"],
                              fila["error"])
    return texto if fila["estado"] != EN_VUELO else texto.split(" = ")[0] + " = …"
