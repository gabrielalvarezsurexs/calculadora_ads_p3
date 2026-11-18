"""Piezas de Tkinter con la línea visual del sistema (``comun/tema.py``).

Lo usan las ventanas (nunca un ``nucleo.py``): aplicar el tema a ttk, botones
planos, tarjetas blancas con título y "píldoras" de estado. Así todas las
ventanas se ven de la misma familia: simple pero limpio (PLAN §15.1).
"""

import tkinter as tk
from tkinter import ttk

from comun import tema


def aplicar(raiz: tk.Misc) -> ttk.Style:
    """Fondo, tipografía y colores de ttk (tablas, pestañas, barras)."""
    raiz.configure(bg=tema.FONDO)
    raiz.option_add("*Font", tema.FUENTE)
    estilo = ttk.Style(raiz)
    try:
        estilo.theme_use("clam")  # el único tema de Tk que respeta todos los colores
    except tk.TclError:
        pass
    estilo.configure(".", background=tema.FONDO, foreground=tema.TEXTO, font=tema.FUENTE,
                     bordercolor=tema.BORDE, lightcolor=tema.SUPERFICIE,
                     darkcolor=tema.BORDE, troughcolor=tema.SUPERFICIE_2)
    estilo.configure("Treeview", background=tema.SUPERFICIE, fieldbackground=tema.SUPERFICIE,
                     foreground=tema.TEXTO, rowheight=22, font=tema.FUENTE_CHICA,
                     bordercolor=tema.BORDE, borderwidth=0)
    estilo.configure("Treeview.Heading", background=tema.SUPERFICIE_2, foreground=tema.TEXTO,
                     font=(tema.FAMILIA, 9, "bold"), relief="flat", borderwidth=0)
    estilo.map("Treeview", background=[("selected", tema.ACENTO_SUAVE)],
               foreground=[("selected", tema.TEXTO)])
    estilo.map("Treeview.Heading", background=[("active", tema.BORDE)])
    estilo.configure("TNotebook", background=tema.FONDO, borderwidth=0, tabmargins=(0, 4, 0, 0))
    estilo.configure("TNotebook.Tab", background=tema.SUPERFICIE_2, foreground=tema.TEXTO_SUAVE,
                     padding=(14, 5), font=tema.FUENTE_NEGRITA, borderwidth=0)
    estilo.map("TNotebook.Tab", background=[("selected", tema.SUPERFICIE)],
               foreground=[("selected", tema.ACENTO)])
    estilo.configure("Vertical.TScrollbar", background=tema.SUPERFICIE_2, arrowsize=12,
                     bordercolor=tema.SUPERFICIE_2, troughcolor=tema.SUPERFICIE)
    return estilo


def boton(padre: tk.Misc, texto: str, comando, *, tipo: str = "normal", **opciones) -> tk.Button:
    """``tipo``: ``"primario"`` (acento), ``"peligro"`` (rojo) o ``"normal"``."""
    fondo, frente, activo = {
        "primario": (tema.ACENTO, tema.TEXTO_INVERSO, "#1D4ED8"),
        "peligro": (tema.ERROR_SUAVE, tema.ERROR, "#FECACA"),
    }.get(tipo, (tema.SUPERFICIE_2, tema.TEXTO, tema.BORDE))
    base = {"padx": 10, "pady": 5,
            "font": tema.FUENTE_NEGRITA if tipo == "primario" else tema.FUENTE}
    return tk.Button(padre, text=texto, command=comando, bg=fondo, fg=frente,
                     activebackground=activo, activeforeground=frente, relief="flat",
                     borderwidth=0, cursor="hand2", disabledforeground=tema.APAGADO,
                     **{**base, **opciones})


def tarjeta(padre: tk.Misc, titulo: str | None = None, *, derecha: str | None = None
            ) -> tuple[tk.Frame, tk.Frame]:
    """Una superficie blanca con borde fino y título. Devuelve (marco, cuerpo).
    ``marco.titulo`` es la etiqueta del título (para cambiarla después)."""
    marco = tk.Frame(padre, bg=tema.SUPERFICIE, highlightthickness=1,
                     highlightbackground=tema.BORDE)
    marco.titulo = None
    if titulo:
        cabeza = tk.Frame(marco, bg=tema.SUPERFICIE)
        cabeza.pack(fill="x", padx=tema.MARGEN, pady=(tema.SEPARACION + 2, 0))
        marco.titulo = tk.Label(cabeza, text=titulo, bg=tema.SUPERFICIE, fg=tema.TEXTO,
                                font=tema.FUENTE_SUBTITULO, anchor="w")
        marco.titulo.pack(side="left")
        if derecha:
            tk.Label(cabeza, text=derecha, bg=tema.SUPERFICIE, fg=tema.TEXTO_SUAVE,
                     font=tema.FUENTE_CHICA).pack(side="right")
    cuerpo = tk.Frame(marco, bg=tema.SUPERFICIE)
    cuerpo.pack(fill="both", expand=True, padx=tema.MARGEN, pady=tema.SEPARACION)
    return marco, cuerpo


def pildora(padre: tk.Misc, texto: str = "", color: str = tema.TEXTO_SUAVE, **opciones
            ) -> tk.Label:
    """Etiqueta de estado: texto del color sobre su versión suave."""
    return tk.Label(padre, text=texto, fg=color, bg=tema.color_suave(color), padx=8, pady=2,
                    font=(tema.FAMILIA, 9, "bold"), **opciones)


def pintar_pildora(etiqueta: tk.Label, texto: str, color: str) -> None:
    etiqueta.config(text=texto, fg=color, bg=tema.color_suave(color))


def cerrar(raiz: tk.Tk) -> None:
    """Cancela los refrescos ya agendados (``after``) y destruye la ventana: sin esto,
    un refresco pendiente avisa ``invalid command name`` al cerrar."""
    for pendiente in raiz.tk.call("after", "info"):
        raiz.after_cancel(pendiente)
    raiz.destroy()
