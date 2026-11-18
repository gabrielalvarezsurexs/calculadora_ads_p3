"""Línea visual del sistema: una sola paleta y tipografía para todas las ventanas.

Simple pero limpio (PLAN §15.1): fondo claro, superficies blancas, un acento,
texto gris oscuro y un color por gen que es el MISMO en la GUI, el nodo, el
panel y el diagrama del gestor. Aquí solo hay constantes (nada de Tkinter), así
que cualquier módulo puede importarlo.
"""

# --- Superficies y texto -----------------------------------------------------
FONDO = "#F4F6FA"         # fondo de ventana
SUPERFICIE = "#FFFFFF"    # tarjetas, tablas, lienzo
SUPERFICIE_2 = "#EEF1F6"  # filas alternas, encabezados de tabla
BORDE = "#D9DEE7"
TEXTO = "#1F2937"
TEXTO_SUAVE = "#6B7280"
TEXTO_INVERSO = "#FFFFFF"

ACENTO = "#2563EB"        # acciones principales, selección
ACENTO_SUAVE = "#DBEAFE"

# --- Estados ------------------------------------------------------------------
OK = "#16A34A"
OK_SUAVE = "#DCFCE7"
AVISO = "#D97706"
AVISO_SUAVE = "#FEF3C7"
ERROR = "#DC2626"
ERROR_SUAVE = "#FEE2E2"
APAGADO = "#9CA3AF"       # madre vacía, célula sin conexión

# --- Color por gen (igual en todo el sistema) ---------------------------------
GENES = {
    "SUM": "#2563EB",     # azul
    "SUB": "#9333EA",     # violeta
    "MUL": "#EA580C",     # naranja
    "DIV": "#0D9488",     # verde azulado
}
GEN_OTRO = "#64748B"      # cualquier otro gen que se cargue
GEN_VACIA = APAGADO


def color_gen(codigo: str | None) -> str:
    if not codigo:
        return GEN_VACIA
    return GENES.get(codigo, GEN_OTRO)


def color_suave(color: str, mezcla: float = 0.85) -> str:
    """El color mezclado con blanco (para fondos de píldoras y tarjetas)."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(c + (255 - c) * mezcla) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


# --- Tipografía -----------------------------------------------------------------
FAMILIA = "Segoe UI"
MONO = "Cascadia Mono"     # Windows 11; Tk cae a otra monoespaciada si no existe
FUENTE = (FAMILIA, 10)
FUENTE_CHICA = (FAMILIA, 9)
FUENTE_NEGRITA = (FAMILIA, 10, "bold")
FUENTE_TITULO = (FAMILIA, 14, "bold")
FUENTE_SUBTITULO = (FAMILIA, 11, "bold")
FUENTE_GRANDE = (FAMILIA, 22, "bold")
FUENTE_MONO = (MONO, 9)

# --- Espaciado ------------------------------------------------------------------
MARGEN = 12
SEPARACION = 8
