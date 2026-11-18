"""Ventana del panel de despliegue. NO forma parte del sistema ADS.

    ┌ Panel de despliegue ──────────────────────────────────────────────────┐
    │ Arranque: [Configuración mínima — vacía] [— con servicios] [+ Nodo] … │
    │ Nodos:  Nodo 1 ●  GUI ●  (M1·SUM) (M2·SUB) (M3·MUL) (M4·DIV)  [Gestor] │
    │ Fallas: [Tumbar SUM de Nodo 2] [Tumbar 3 SUM] [Tumbar seleccionado]    │
    │ Procesos (comando exacto) + bitácora en vivo del seleccionado          │
    └────────────────────────────────────────────────────────────────────────┘

Cada madre se dibuja como una pastilla del color de su gen (el mismo de todo el
sistema), con lo que dice su propia bitácora; los reemplazos que lanzan las
madres aparecen solos (``run/``). Un clic en una pastilla la selecciona.
La configuración mínima NO abre gestores: el botón **Gestor** de cada nodo lo
levanta cuando el usuario quiera (uno por nodo).
"""

import re
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from comun import codigos, estilo, tema
from panel.procesos import CLON, CON_SERVICIOS, GESTOR, GUI, MADRE, NODO, VACIA, Proceso, Procesos

FILAS_MINIMAS = 4
ANCHO_MADRES = 320      # px para las fichas de madres si la ventana aún no tiene tamaño


class VentanaPanel:
    def __init__(self, procesos: Procesos):
        self.procesos = procesos
        self.raiz = tk.Tk()
        self.raiz.title("Panel de despliegue · Calculadora ADS")
        self.ancho_pantalla = self.raiz.winfo_screenwidth()
        self.alto_pantalla = self.raiz.winfo_screenheight()
        ancho, alto = 940, min(800, self.alto_pantalla - 80)
        self.raiz.geometry(f"{ancho}x{alto}+{max(0, (self.ancho_pantalla - ancho) // 2)}+20")
        self.raiz.minsize(860, 640)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)
        estilo.aplicar(self.raiz)

        self._n_filas = FILAS_MINIMAS
        self._filas: dict[int, dict] = {}         # k -> widgets de la fila del nodo
        self._firma: dict[int, tuple] = {}        # k -> lo pintado (para no repintar igual)
        self._iids: dict[int, str] = {}           # id(proceso) -> iid del Treeview
        self._por_iid: dict[str, Proceso] = {}
        self._visto: tuple[str | None, int] = (None, 0)  # (iid mostrado, líneas ya pintadas)
        self._construir()

    # ------------------------------------------------------------ construcción

    def _construir(self) -> None:
        r = self.raiz
        r.columnconfigure(0, weight=1)
        r.rowconfigure(4, weight=1)
        cabeza = tk.Frame(r, bg=tema.FONDO)
        cabeza.grid(row=0, column=0, sticky="ew", padx=tema.MARGEN, pady=(tema.MARGEN, 4))
        tk.Label(cabeza, text="Panel de despliegue", font=tema.FUENTE_TITULO, bg=tema.FONDO,
                 fg=tema.TEXTO).pack(anchor="w")
        tk.Label(cabeza, bg=tema.FONDO, fg=tema.TEXTO_SUAVE, font=tema.FUENTE_CHICA,
                 text="Herramienta de demo, fuera del sistema ADS: solo lanza procesos con el "
                      "mismo comando que se escribiría a mano. Nada depende de ella.").pack(
            anchor="w")

        self._arranque_ui(r).grid(row=1, column=0, sticky="ew", padx=tema.MARGEN, pady=4)
        self._nodos_ui(r).grid(row=2, column=0, sticky="ew", padx=tema.MARGEN, pady=4)
        self._fallas_ui(r).grid(row=3, column=0, sticky="ew", padx=tema.MARGEN, pady=4)
        self._procesos_ui(r).grid(row=4, column=0, sticky="nsew", padx=tema.MARGEN,
                                  pady=(4, tema.MARGEN))

    def _arranque_ui(self, padre) -> tk.Frame:
        marco, dentro = estilo.tarjeta(padre, "Arranque",
                                       derecha="4 nodos · 1 GUI y 4 madres por nodo · sin gestor")
        estilo.boton(dentro, "Configuración mínima — vacía", lambda: self._configuracion(VACIA),
                     tipo="primario").pack(side="left")
        estilo.boton(dentro, "Configuración mínima — con servicios",
                     lambda: self._configuracion(CON_SERVICIOS), tipo="primario").pack(
            side="left", padx=6)
        estilo.boton(dentro, "+ Nodo", self._agregar_nodo).pack(side="left")
        estilo.boton(dentro, "Detener todo", self._detener_todo, tipo="peligro").pack(
            side="right")
        return marco

    def _nodos_ui(self, padre) -> tk.Frame:
        marco, dentro = estilo.tarjeta(padre, "Nodos",
                                       derecha="madres del color de su gen · ·r1 = reemplazo · clic = seleccionar")
        self._rejilla = dentro
        dentro.columnconfigure(2, weight=1)
        self._asegurar_filas()
        return marco

    def _fallas_ui(self, padre) -> tk.Frame:
        marco, dentro = estilo.tarjeta(padre, "Fallas", derecha="un clic; lo demás pasa solo")
        fila = tk.Frame(dentro, bg=tema.SUPERFICIE)
        fila.pack(fill="x")
        for texto, comando in (("Tumbar SUM de Nodo 2", self._tumbar_sum_n2),
                               ("Tumbar 3 SUM", self._tumbar_3_sum),
                               ("Tumbar seleccionado", self._tumbar_seleccionado)):
            estilo.boton(fila, texto, comando, tipo="peligro").pack(side="left", padx=(0, 6))
        self._lbl_aviso = tk.Label(dentro, bg=tema.SUPERFICIE, fg=tema.TEXTO_SUAVE,
                                   font=tema.FUENTE_CHICA, anchor="w", justify="left",
                                   wraplength=860,
                                   text="Tumbar = terminar el proceso sin avisar (como una "
                                        "falla). La regeneración es automática: no toques nada "
                                        "después.")
        self._lbl_aviso.pack(fill="x", pady=(6, 0))
        return marco

    def _procesos_ui(self, padre) -> tk.Frame:
        marco, dentro = estilo.tarjeta(padre, "Procesos",
                                       derecha="comando exacto · bitácora en vivo")
        dentro.columnconfigure(0, weight=1)
        dentro.rowconfigure(0, weight=1)
        dentro.rowconfigure(2, weight=1)
        columnas = [("nombre", 92), ("tipo", 70), ("nodo", 40), ("PID", 56), ("estado", 84),
                    ("genes", 110), ("comando", 380)]
        self._arbol = ttk.Treeview(dentro, columns=[c for c, _ in columnas], show="headings",
                                   height=6, selectmode="browse")
        for nombre, ancho in columnas:
            self._arbol.heading(nombre, text=nombre, anchor="w")
            self._arbol.column(nombre, width=ancho, minwidth=36, anchor="w",
                               stretch=nombre == "comando")
        self._arbol.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(dentro, orient="vertical", command=self._arbol.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self._arbol.configure(yscrollcommand=barra.set)
        self._arbol.tag_configure("muerto", foreground=tema.APAGADO)
        self._arbol.tag_configure(CLON, foreground=tema.AVISO)
        self._arbol.bind("<<TreeviewSelect>>", lambda e: self._pintar_bitacora(reiniciar=True))

        self._lbl_bitacora = tk.Label(dentro, text="Bitácora en vivo: selecciona un proceso",
                                      anchor="w", bg=tema.SUPERFICIE, fg=tema.TEXTO_SUAVE,
                                      font=tema.FUENTE_CHICA)
        self._lbl_bitacora.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        self._txt = scrolledtext.ScrolledText(dentro, height=8, wrap="none", state="disabled",
                                              font=tema.FUENTE_MONO, bg=tema.SUPERFICIE_2,
                                              fg=tema.TEXTO, relief="flat", borderwidth=0)
        self._txt.grid(row=2, column=0, columnspan=2, sticky="nsew")
        return marco

    def _asegurar_filas(self) -> None:
        objetivo = max(self._n_filas, *(self.procesos.filas() or [0]))
        while len(self._filas) < objetivo:
            k = len(self._filas) + 1
            self._filas[k] = self._fila_nodo(k)

    def _fila_nodo(self, k: int) -> dict:
        g = self._rejilla
        fila = {}
        cab = tk.Frame(g, bg=tema.SUPERFICIE)
        cab.grid(row=k, column=0, sticky="w", pady=3)
        tk.Label(cab, text=f"Nodo {k}", font=tema.FUENTE_NEGRITA, bg=tema.SUPERFICIE,
                 fg=tema.TEXTO, width=7, anchor="w").pack(side="left")
        fila["nodo"] = estilo.pildora(cab, "apagado", tema.APAGADO, width=7)
        fila["nodo"].pack(side="left")
        self._mini(cab, "▶", lambda: self._levantar_nodo(k)).pack(side="left", padx=(4, 0))
        self._mini(cab, "■", lambda: self._tumbar_tipo(k, NODO), peligro=True).pack(side="left")

        gui = tk.Frame(g, bg=tema.SUPERFICIE)
        gui.grid(row=k, column=1, sticky="w", padx=(14, 0))
        fila["gui"] = estilo.pildora(gui, "GUI 0", tema.APAGADO, width=6)
        fila["gui"].pack(side="left")
        self._mini(gui, "▶", lambda: self._levantar_gui(k)).pack(side="left", padx=(4, 0))
        self._mini(gui, "■", lambda: self._tumbar_tipo(k, GUI), peligro=True).pack(side="left")

        fila["madres"] = tk.Frame(g, bg=tema.SUPERFICIE)
        fila["madres"].grid(row=k, column=2, sticky="w", padx=(14, 0))

        mas = tk.Frame(g, bg=tema.SUPERFICIE)
        mas.grid(row=k, column=3, sticky="e", padx=(8, 0))
        estilo.boton(mas, "+ Madre", lambda: self._mas_madre(k), padx=6, pady=2).pack(
            side="left")
        estilo.boton(mas, "+ Muda (SUM)", lambda: self._mas_madre(k, muda=True), padx=6,
                     pady=2).pack(side="left", padx=4)
        fila["gestor"] = estilo.boton(mas, "Gestor", lambda: self._gestor(k), padx=8, pady=2)
        fila["gestor"].pack(side="left")
        fila["fijos"] = (cab, gui, mas)     # lo que queda libre entre ellos es para las madres
        return fila

    @staticmethod
    def _mini(padre, texto: str, comando, *, peligro: bool = False) -> tk.Button:
        color = tema.ERROR if peligro else tema.OK
        return tk.Button(padre, text=texto, command=comando, relief="flat", borderwidth=0,
                         bg=tema.SUPERFICIE, fg=color, activebackground=tema.SUPERFICIE_2,
                         activeforeground=color, cursor="hand2", padx=4,
                         font=(tema.FAMILIA, 9))

    # ------------------------------------------------------------- geometría

    def _geometria_nodo(self, k: int) -> str:
        w = min(720, (self.ancho_pantalla - 20) // 2)
        h = min(450, (self.alto_pantalla - 90) // 2)
        i = (k - 1) % 4
        extra = 30 * ((k - 1) // 4)
        return f"{w}x{h}+{(i % 2) * (w + 8) + extra}+{(i // 2) * (h + 36) + extra}"

    def _geometria_gui(self, k: int) -> str:
        w, h = 460, min(800, self.alto_pantalla - 100)
        i = (k - 1) % 4
        x = max(0, self.ancho_pantalla - w - 20 - 45 * (3 - i))
        return f"{w}x{h}+{x}+{10 + 30 * i}"

    def _geometria_gestor(self, k: int) -> str:
        w, h = min(1420, self.ancho_pantalla - 30), min(820, self.alto_pantalla - 90)
        return f"{w}x{h}+{10 + 24 * (k - 1)}+{10 + 24 * (k - 1)}"

    # --------------------------------------------------------------- acciones

    def _decir(self, texto: str, color: str = tema.TEXTO_SUAVE) -> None:
        self._lbl_aviso.config(text=texto, fg=color)

    def _levantar_nodo(self, k: int) -> None:
        if self.procesos.vivos(k, NODO):
            self._decir(f"El Nodo {k} ya está vivo (su puerto está ocupado).", tema.AVISO)
            return
        self.procesos.lanzar_nodo(k, geometria=self._geometria_nodo(k))
        self._refrescar()

    def _levantar_gui(self, k: int) -> None:
        self.procesos.lanzar_gui(k, geometria=self._geometria_gui(k))
        self._refrescar()

    def _mas_madre(self, k: int, *, muda: bool = False) -> None:
        p = self.procesos.lanzar_madre(k, gen="SUM" if muda else None, muda=muda)
        self._decir(f"{p.nombre}: {'muda (late, no acusa)' if muda else 'vacía'} en Nodo {k}.")
        self._refrescar()

    def _gestor(self, k: int) -> None:
        if self.procesos.vivos(k, GESTOR):
            self._decir(f"G-N{k} ya está abierto: búscalo en la barra de tareas.", tema.AVISO)
            return
        self.procesos.lanzar_gestor(k, geometria=self._geometria_gestor(k))
        self._decir(f"G-N{k}: gestor de microservicios conectado al Nodo {k}.", tema.ACENTO)
        self._refrescar()

    def _tumbar_tipo(self, k: int, tipo: str) -> None:
        vivos = self.procesos.vivos(k, tipo)
        if vivos:
            p = max(vivos, key=lambda p: p.inicio)
            self.procesos.tumbar(p)
            self._decir(f"Tumbé {p.nombre} (PID {p.pid}).", tema.ERROR)
        self._refrescar()

    def _configuracion(self, modo: str) -> None:
        """Primero los nodos que falten y ~1 s después las células (nunca gestores)."""
        for k in range(1, FILAS_MINIMAS + 1):
            if not self.procesos.vivos(k, NODO):
                self.procesos.lanzar_nodo(k, geometria=self._geometria_nodo(k))
        self.raiz.after(1200, lambda: self._celulas_minimas(modo))
        self._decir(f"Configuración mínima — {modo}: nodos primero, luego GUIs y madres. Los "
                    f"gestores los abres tú (botón Gestor).", tema.ACENTO)
        self._refrescar()

    def _celulas_minimas(self, modo: str) -> None:
        for k in range(1, FILAS_MINIMAS + 1):
            if not self.procesos.vivos(k, GUI):
                self.procesos.lanzar_gui(k, geometria=self._geometria_gui(k))
            self.procesos.configuracion(k, modo)
        self._refrescar()

    def _agregar_nodo(self) -> None:
        self._n_filas = max(self._n_filas, len(self._filas)) + 1
        self._asegurar_filas()
        self._levantar_nodo(self._n_filas)

    def _detener_todo(self) -> None:
        self.procesos.detener_todo()
        self._decir("Todo detenido (también los reemplazos que lanzaron las madres).")
        self._refrescar()

    def _tumbar_sum_n2(self) -> None:
        candidatas = self.procesos.con_gen("SUM", 2)
        if not candidatas:
            self._decir("Nodo 2 no tiene una madre viva con SUM.", tema.AVISO)
            return
        self._tumbar([candidatas[0]])

    def _tumbar_3_sum(self) -> None:
        """Una SUM de cada uno de los nodos 1, 2 y 3 (o las que haya)."""
        elegidas = []
        for k in (1, 2, 3, *range(4, len(self._filas) + 1)):
            elegidas += self.procesos.con_gen("SUM", k)[:1]
        if len(elegidas) < 3:
            resto = [p for p in self.procesos.con_gen("SUM") if p not in elegidas]
            elegidas += resto[:3 - len(elegidas)]
        if not elegidas:
            self._decir("No hay madres vivas con SUM.", tema.AVISO)
            return
        self._tumbar(elegidas[:3])

    def _tumbar(self, procesos: list[Proceso]) -> None:
        for p in procesos:
            self.procesos.tumbar(p)
        nombres = ", ".join(p.nombre for p in procesos)
        self._decir(f"Tumbé {nombres}. Ahora no toques nada: las madres lo detectan en "
                    f"~6 s y regeneran una por una.", tema.ERROR)
        self._refrescar()

    def _tumbar_seleccionado(self) -> None:
        sel = self._arbol.selection()
        if sel and sel[0] in self._por_iid:
            self._tumbar([self._por_iid[sel[0]]])

    def _seleccionar(self, p: Proceso) -> None:
        iid = self._iids.get(id(p))
        if iid:
            self._arbol.selection_set(iid)
            self._arbol.see(iid)

    # ------------------------------------------------------------- refresco

    def ejecutar(self) -> None:
        self.raiz.after(500, self._ciclo)
        self.raiz.mainloop()

    def _ciclo(self) -> None:
        try:
            self.procesos.buscar_reemplazos()
        finally:
            self._refrescar()
            self.raiz.after(700, self._ciclo)

    def _refrescar(self) -> None:
        self._asegurar_filas()
        for k, fila in self._filas.items():
            self._pintar_fila(k, fila)
        for p in list(self.procesos.procesos):
            valores = (p.nombre, p.tipo, p.fila, p.pid, p.estado, ", ".join(p.genes) or
                       ("vacía" if p.tipo in (MADRE, CLON) else ""), p.comando_legible())
            etiqueta = (CLON,) if p.tipo == CLON and p.vivo else (() if p.vivo else ("muerto",))
            iid = self._iids.get(id(p))
            if iid is None:
                iid = self._arbol.insert("", "end", values=valores, tags=etiqueta)
                self._iids[id(p)] = iid
                self._por_iid[iid] = p
            else:
                self._arbol.item(iid, values=valores, tags=etiqueta)
        self._pintar_bitacora()

    def _pintar_fila(self, k: int, fila: dict) -> None:
        nodo = bool(self.procesos.vivos(k, NODO))
        guis = len(self.procesos.vivos(k, GUI))
        gestor = bool(self.procesos.vivos(k, GESTOR))
        madres = self.procesos.madres(k)
        firma = (nodo, guis, gestor, tuple((p.nombre, tuple(p.genes), p.muda) for p in madres))
        if self._firma.get(k) == firma:
            return
        self._firma[k] = firma
        estilo.pintar_pildora(fila["nodo"], "vivo" if nodo else "apagado",
                              tema.OK if nodo else tema.APAGADO)
        estilo.pintar_pildora(fila["gui"], f"GUI {guis}", tema.OK if guis else tema.APAGADO)
        fila["gestor"].config(text="Gestor ●" if gestor else "Gestor",
                              fg=tema.ACENTO if gestor else tema.TEXTO)
        for hijo in fila["madres"].winfo_children():
            hijo.destroy()
        if not madres:
            tk.Label(fila["madres"], text="sin madres", bg=tema.SUPERFICIE, fg=tema.APAGADO,
                     font=tema.FUENTE_CHICA).grid(row=0, column=0, sticky="w")
        orden = {s: i for i, s in enumerate(codigos.SERVICIOS)}
        madres = sorted(madres, key=lambda p: (orden.get((p.codigos or ["~"])[0], 9), p.nombre))
        # Renglones según el ancho libre de la columna: con muchas madres no se cortan.
        libre = self._rejilla.winfo_width() - sum(
            w.winfo_reqwidth() + 14 for w in fila["fijos"])
        libre = libre if libre > 120 else ANCHO_MADRES
        renglon, usado = None, 0
        for p in madres:
            if renglon is None:
                renglon = tk.Frame(fila["madres"], bg=tema.SUPERFICIE)
                renglon.grid(sticky="w", pady=1)
            ficha = self._pastilla(renglon, p)
            ancho = ficha.winfo_reqwidth() + 4
            if usado and usado + ancho > libre:
                ficha.destroy()
                renglon = tk.Frame(fila["madres"], bg=tema.SUPERFICIE)
                renglon.grid(sticky="w", pady=1)
                ficha, usado = self._pastilla(renglon, p), 0
            ficha.pack(side="left", padx=(0, 4))
            usado += ancho

    def _pastilla(self, padre, p: Proceso) -> tk.Label:
        """Una madre, del color de su gen: ``SUM`` · ``M3 · MUL`` · ``M2 · vacía`` ·
        ``SUM·r1`` (reemplazo) · ``SUM · muda``."""
        color = tema.color_gen(p.codigos[0]) if len(p.codigos) == 1 else (
            tema.TEXTO if p.codigos else tema.APAGADO)
        corto = re.sub(r"-N\d+", "", p.nombre)          # 'M3-N2' → 'M3', 'SUM-N2·r1' → 'SUM·r1'
        genes = "+".join(p.codigos) or "vacía"
        texto = corto if corto.startswith(genes) and p.codigos else f"{corto} · {genes}"
        if p.muda:
            texto += " · muda"
        etiqueta = estilo.pildora(padre, texto, tema.ERROR if p.muda else color, cursor="hand2")
        etiqueta.bind("<Button-1>", lambda e, p=p: self._seleccionar(p))
        return etiqueta

    def _pintar_bitacora(self, reiniciar: bool = False) -> None:
        sel = self._arbol.selection()
        if not sel or sel[0] not in self._por_iid:
            return
        iid = sel[0]
        p = self._por_iid[iid]
        mostrado, vistas = self._visto
        if reiniciar or mostrado != iid:
            vistas = None
        nuevas, total_lineas = p.lineas_desde(vistas)
        t = self._txt
        t.config(state="normal")
        if vistas is None:
            t.delete("1.0", "end")
            self._lbl_bitacora.config(text=f"Bitácora en vivo: {p.nombre} (PID {p.pid}) · "
                                           f"{p.comando_legible()}", fg=tema.TEXTO)
        if nuevas:
            abajo = t.yview()[1] > 0.98
            t.insert("end", "\n".join(nuevas) + "\n")
            total = int(t.index("end-1c").split(".")[0])
            if total > 2000:
                t.delete("1.0", f"{total - 2000}.0")
            if abajo or vistas is None:
                t.see("end")
        t.config(state="disabled")
        self._visto = (iid, total_lineas)

    def _cerrar(self) -> None:
        if self.procesos.vivos():
            r = messagebox.askyesnocancel(
                "Cerrar el panel",
                "¿Detener también todos los procesos (y los reemplazos)?\n\n"
                "Sí: se detienen.\nNo: siguen vivos; su bitácora sigue en logs/.")
            if r is None:
                return
            if r:
                self.procesos.detener_todo()
        estilo.cerrar(self.raiz)

