"""Ventana del nodo: el control de conexiones activas y el tráfico en vivo.

Muestra lo que pide el §10.1 (qué entidades están conectadas y de qué tipo) y lo
que pide el §11 (qué se reenvió, qué se descartó como duplicado y dónde se agotó
el TTL). El núcleo corre en sus hilos y solo empuja eventos a una cola; esta
ventana la vacía cada 100 ms desde el hilo de Tkinter.
"""

import queue
import time
import tkinter as tk
from tkinter import ttk

from comun import config, estilo, hashes, tema

MAX_FILAS = 500
COLORES = {
    "FWD": tema.ACENTO, "DUP": tema.AVISO, "TTL": tema.AVISO, "DROP": tema.ERROR,
    "CONEXION": tema.OK, "DESCONEXION": tema.ERROR, "LENTO": tema.ERROR,
    "DUPLICADO": tema.APAGADO,
}
_TIPOS = {"INTERFAZ": "GUI", "MADRE": "madre", "GESTOR": "gestor", "SONDA": "sonda"}


def _hora(t: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(t))


class VentanaNodo:
    def __init__(self, nodo, geometria: str | None = None):
        self.nodo = nodo
        self.raiz = tk.Tk()
        self.raiz.title(f"{nodo.nombre} · Campo de Datos")
        self.raiz.geometry(geometria or "720x450")
        self.raiz.minsize(600, 380)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)
        estilo.aplicar(self.raiz)
        ttk.Style(self.raiz).configure("Treeview", rowheight=19)
        self._ocultar_latidos = tk.BooleanVar(self.raiz, value=True)
        self._pausar = tk.BooleanVar(self.raiz, value=False)
        self._construir()
        self._refrescar_tablas()

    # ------------------------------------------------------------ construcción

    def _construir(self) -> None:
        raiz = self.raiz
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(2, weight=1)

        cabeza = tk.Frame(raiz, bg=tema.FONDO)
        cabeza.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))
        tk.Label(cabeza, text=self.nodo.nombre, font=tema.FUENTE_TITULO, bg=tema.FONDO,
                 fg=tema.TEXTO).pack(side="left")
        tk.Label(cabeza, text=f"  nodo del Campo de Datos · {hashes.corto(self.nodo.hash)}",
                 font=tema.FUENTE_CHICA, bg=tema.FONDO, fg=tema.TEXTO_SUAVE).pack(side="left",
                                                                                   pady=(4, 0))
        estilo.pildora(cabeza, f"escucha {self.nodo.endpoint}", tema.OK).pack(side="right")
        self._lbl_contadores = tk.Label(raiz, anchor="w", font=tema.FUENTE_CHICA, bg=tema.FONDO,
                                        fg=tema.TEXTO_SUAVE)
        self._lbl_contadores.grid(row=1, column=0, sticky="ew", padx=10)

        cuerpo = tk.Frame(raiz, bg=tema.FONDO)
        cuerpo.grid(row=2, column=0, sticky="nsew", padx=8, pady=(4, 8))
        cuerpo.columnconfigure((0, 1), weight=1, uniform="tabla")
        cuerpo.rowconfigure(1, weight=1)

        marco, dentro = estilo.tarjeta(cuerpo, "Vecinos")
        marco.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self._lbl_vecinos = marco.titulo
        self._vecinos = self._tabla(dentro, [("nombre", 56), ("hash", 62), ("endpoint", 96),
                                             ("sentido", 54), ("desde", 54)], alto=4)
        self._vecinos.pack(fill="both", expand=True)
        marco, dentro = estilo.tarjeta(cuerpo, "Células")
        marco.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self._lbl_celulas = marco.titulo
        self._celulas = self._tabla(dentro, [("tipo", 56), ("nombre", 92), ("hash", 66),
                                             ("desde", 58)], alto=4)
        barra_c = ttk.Scrollbar(dentro, orient="vertical", command=self._celulas.yview)
        barra_c.pack(side="right", fill="y")
        self._celulas.pack(fill="both", expand=True)
        self._celulas.configure(yscrollcommand=barra_c.set)

        marco, dentro = estilo.tarjeta(cuerpo, "Tráfico",
                                       derecha="lo que reenvié (FWD), descarté (DUP) y el TTL")
        marco.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        barra = tk.Frame(dentro, bg=tema.SUPERFICIE)
        barra.pack(fill="x", pady=(0, 4))
        for texto, var in (("pausar", self._pausar), ("ocultar latidos", self._ocultar_latidos)):
            tk.Checkbutton(barra, text=texto, variable=var, bg=tema.SUPERFICIE, fg=tema.TEXTO,
                           activebackground=tema.SUPERFICIE, selectcolor=tema.SUPERFICIE,
                           font=tema.FUENTE_CHICA, relief="flat").pack(side="right", padx=4)
        # Anchos para que quepan "DESCONEXION" y "SONDA_PRUEBA" a 720 px.
        self._trafico = self._tabla(dentro, [("hora", 58), ("evento", 92), ("código", 100),
                                             ("id", 62), ("origen", 66), ("de", 62),
                                             ("ruta", 92), ("destinos", 140)], alto=8)
        barra_v = ttk.Scrollbar(dentro, orient="vertical", command=self._trafico.yview)
        barra_v.pack(side="right", fill="y")
        self._trafico.pack(fill="both", expand=True)
        self._trafico.configure(yscrollcommand=barra_v.set)
        for evento, color in COLORES.items():
            self._trafico.tag_configure(evento, foreground=color)

    def _tabla(self, padre, columnas, alto: int) -> ttk.Treeview:
        tabla = ttk.Treeview(padre, columns=[c for c, _ in columnas], show="headings",
                             height=alto, selectmode="browse")
        for nombre, ancho in columnas:
            tabla.heading(nombre, text=nombre, anchor="w")
            tabla.column(nombre, width=ancho, minwidth=40, anchor="w", stretch=True)
        return tabla

    # ------------------------------------------------------------- eventos

    def ejecutar(self) -> None:
        self.raiz.after(100, self._vaciar_cola)
        self.raiz.after(500, self._refrescar_contadores)
        self.raiz.mainloop()

    def _vaciar_cola(self) -> None:
        filas, tablas = [], False
        cola = self.nodo.eventos
        if cola is not None:
            try:
                for _ in range(2000):  # tope por tick: la ventana nunca se congela
                    tipo, datos = cola.get_nowait()
                    if tipo == "tablas":
                        tablas = True
                    elif tipo == "trafico":
                        filas.append(datos)
            except queue.Empty:
                pass
        if tablas:
            self._refrescar_tablas()
        if filas and not self._pausar.get():
            self._agregar_trafico(filas)
        if self.nodo.activo:
            self.raiz.after(100, self._vaciar_cola)

    def _agregar_trafico(self, filas: list[dict]) -> None:
        ocultar = self._ocultar_latidos.get()
        insertadas = 0
        for f in filas:
            if ocultar and f.get("codigo") in config.CODIGOS_SILENCIOSOS:
                continue
            evento = f.get("evento", "?")
            valores = (f.get("hora", ""), evento, f.get("codigo", ""), f.get("id8", ""),
                       f.get("origen", ""), f.get("de", "") or "", f.get("ruta", ""),
                       f.get("destinos") or f.get("detalle", ""))
            self._trafico.insert("", "end", values=valores, tags=(evento,))
            insertadas += 1
        if not insertadas:
            return
        hijos = self._trafico.get_children()
        if len(hijos) > MAX_FILAS:
            self._trafico.delete(*hijos[:len(hijos) - MAX_FILAS])
        self._trafico.yview_moveto(1.0)

    def _refrescar_tablas(self) -> None:
        foto = self.nodo.instantanea()
        self._llenar(self._vecinos, [
            (v["nombre"], hashes.corto(v["hash"]), v["endpoint"], v["sentido"], _hora(v["desde"]))
            for v in sorted(foto["vecinos"], key=lambda v: v["nombre"] or "")])
        celulas = sorted(foto["celulas"], key=lambda c: (c["entidad"] != "INTERFAZ",
                                                          c["servicio"] or "", c["nombre"] or ""))
        self._llenar(self._celulas, [
            (_TIPOS.get(c["entidad"], c["entidad"]), c["nombre"], hashes.corto(c["hash"]),
             _hora(c["desde"])) for c in celulas])
        guis = sum(1 for c in celulas if c["entidad"] == "INTERFAZ")
        madres = sum(1 for c in celulas if c["entidad"] == "MADRE")
        otras = len(celulas) - guis - madres
        detalle = f"{guis} GUI + {madres} madres" + (f" + {otras} otra(s)" if otras else "")
        self._lbl_vecinos.config(text=f"Vecinos · {len(foto['vecinos'])}")
        self._lbl_celulas.config(text=f"Células · {len(celulas)} ({detalle})")

    @staticmethod
    def _llenar(tabla: ttk.Treeview, filas) -> None:
        tabla.delete(*tabla.get_children())
        for fila in filas:
            tabla.insert("", "end", values=fila)

    def _refrescar_contadores(self) -> None:
        foto = self.nodo.instantanea()
        c = foto["contadores"]
        self._lbl_contadores.config(
            text=f"recibidos {c['recibidos']} · reenviados {c['reenviados']} · "
                 f"duplicados descartados {c['duplicados']} · TTL agotado {c['ttl_agotado']} · "
                 f"descartados {c['descartados']} · ids en el registro temporal "
                 f"{foto['vistos']} ({config.VISTOS_VIGENCIA:g} s)")
        if self.nodo.activo:
            self.raiz.after(500, self._refrescar_contadores)

    def _cerrar(self) -> None:
        self.nodo.detener()  # cierra los sockets: los pares lo detectan
        estilo.cerrar(self.raiz)
