"""Diagrama vivo de la topología (PLAN §4.4): un ``tk.Canvas`` que dibuja una
``Foto`` de ``gestor/topologia.py``.

* **Nodos** en círculo, unidos por los **enlaces reales** que cada uno anuncia
  en su ``NODO_LAT`` (línea continua si los dos extremos lo anuncian; punteada
  si solo uno, p. ej. mientras se forma la malla).
* Alrededor de cada nodo, **sus células**, en abanico hacia afuera: la GUI
  (rectángulo), los gestores (rombo) y las madres (círculo) **coloreadas por
  gen** con los mismos colores de todo el sistema. Varios genes = rebanadas.
  Madre vacía: gris punteada. Muda: tachada. Clon: insignia ``r1``. Caída: roja
  con ✕ (una madre caída es una pérdida: sigue así hasta que aparece su
  reemplazo). Reemplazo **naciendo** (hubo ``CLON_AVISO``): contorno punteado
  azul que late junto a su nodo hasta su primer latido; luego se llena con el
  color de los genes que copió.
* **Clic en una madre** = célula destino de la orden (evidencia V9).
* **Destellos**: un anillo que se expande sobre la célula cuando sale una orden
  hacia ella (azul), cuando contesta (verde si la aceptó, rojo si no), cuando
  cae (rojo) y cuando nace un reemplazo (verde).

Arriba, la disponibilidad por código; abajo, la leyenda.
"""

import math
import time
import tkinter as tk
from collections.abc import Callable

from comun import codigos, mensajes, tema
from gestor.nucleo import natural
from gestor.topologia import CAIDA, NACIENDO, CelulaVista, Foto, NodoVisto

DESTELLO_S = 0.9
LATIDO_NACIENDO_S = 1.1         # periodo del anillo de un reemplazo naciendo
RECIEN_NACIDA_S = 6.0           # lo que late en verde un reemplazo tras su primer latido
COLOR_DESTELLO = {"orden": tema.ACENTO, "ok": tema.OK, "rechazada": tema.ERROR,
                  "caida": tema.ERROR, "nace": tema.OK}
ARRIBA, ABAJO = 40, 30          # franjas de disponibilidad y leyenda
_ORDEN_TIPO = {mensajes.INTERFAZ: 0, mensajes.MADRE: 1, mensajes.GESTOR: 2}


def _fuente(tam: int, *estilo) -> tuple:
    return (tema.FAMILIA, tam, *estilo)


class Diagrama(tk.Canvas):
    def __init__(self, padre: tk.Misc, al_elegir: Callable[[str], None], **opciones):
        super().__init__(padre, bg=tema.SUPERFICIE, highlightthickness=0, **opciones)
        self._al_elegir = al_elegir
        self._foto: Foto | None = None
        self._seleccion: str | None = None
        self._yo: str | None = None
        self._pos: dict[str, tuple[float, float, float]] = {}   # hash -> (x, y, radio)
        self._destellos: dict[str, tuple[str, float]] = {}      # hash -> (tipo, inicio)
        self._animando = False
        self.bind("<Configure>", lambda e: self._redibujar())
        self.tag_bind("madre", "<Button-1>", self._clic)
        self.tag_bind("madre", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("madre", "<Leave>", lambda e: self.config(cursor=""))

    # ------------------------------------------------------------- API

    def dibujar(self, foto: Foto, seleccion: str | None, yo: str | None) -> None:
        self._foto, self._seleccion, self._yo = foto, seleccion, yo
        self._redibujar()
        if foto.naciendo or self._recien_nacidas(time.monotonic()):
            self._arrancar_animacion()

    def destello(self, h: str, tipo: str) -> None:
        self._destellos[h] = (tipo, time.monotonic())
        self._arrancar_animacion()

    def _arrancar_animacion(self) -> None:
        if not self._animando:
            self._animando = True
            self._animar()  # el primer anillo, ya; los siguientes cada 30 ms

    # ------------------------------------------------------------- dibujo

    def _redibujar(self) -> None:
        self.delete("all")
        self._pos.clear()
        foto = self._foto
        # Antes de mostrarse, winfo_* vale 1: se usa el tamaño pedido (en píxeles; el
        # "width" del Canvas puede venir en otras unidades, como "10c").
        ancho = self.winfo_width() if self.winfo_width() > 1 else self.winfo_reqwidth()
        alto = self.winfo_height() if self.winfo_height() > 1 else self.winfo_reqheight()
        ancho, alto = max(ancho, 200), max(alto, 200)
        if foto is None or not foto.nodos:
            self.create_text(ancho / 2, alto / 2, fill=tema.TEXTO_SUAVE, font=_fuente(11),
                             text="Esperando latidos del Campo de Datos…")
            return
        area = alto - ARRIBA - ABAJO
        cx, cy = ancho / 2, ARRIBA + area / 2
        escala = max(0.7, min(1.25, area / 440, ancho / 760))
        # Elipse ancha: el lienzo es más ancho que alto. Los abanicos se abren hacia
        # arriba (nodos de arriba) y hacia abajo (los de abajo), donde hay lugar.
        ry = area * 0.2
        rx = min(ancho * 0.3, ry * 2.6)
        nodos = sorted(foto.nodos.values(), key=lambda n: natural(n.nombre))
        posiciones = self._posiciones_nodos(nodos, cx, cy, rx, ry)

        self._enlaces(nodos, posiciones)
        por_nodo: dict[str, list[CelulaVista]] = {}
        for c in (*foto.celulas.values(), *foto.naciendo.values()):
            if c.nodo in posiciones:
                por_nodo.setdefault(c.nodo, []).append(c)
        for n in nodos:
            x, y = posiciones[n.hash]
            # Hacia afuera, pero cargado a lo vertical (×3): los vecinos de al lado
            # quedan lejos en x, así que sus abanicos no se tocan.
            angulo = math.atan2(3 * (y - cy), x - cx) if len(nodos) > 1 else -math.pi / 2
            celulas = sorted(por_nodo.get(n.hash, []),
                             key=lambda c: (_ORDEN_TIPO.get(c.tipo, 9), natural(c.nombre)))
            self._celulas(celulas, x, y, angulo, escala, abanico=len(nodos) > 1)
            self._nodo(n, x, y, escala)
        self._disponibilidad(foto, ancho)
        self._leyenda(alto)
        self._pintar_destellos()

    @staticmethod
    def _posiciones_nodos(nodos: list[NodoVisto], cx: float, cy: float, rx: float,
                          ry: float) -> dict:
        if len(nodos) == 1:
            return {nodos[0].hash: (cx, cy)}
        paso = 2 * math.pi / len(nodos)
        inicio = -3 * math.pi / 4  # el primero arriba a la izquierda, en sentido horario
        return {n.hash: (cx + rx * math.cos(inicio + i * paso),
                         cy + ry * math.sin(inicio + i * paso)) for i, n in enumerate(nodos)}

    def _enlaces(self, nodos: list[NodoVisto], pos: dict) -> None:
        hechos = set()
        for a in nodos:
            for h in a.vecinos:
                if h not in pos or frozenset((a.hash, h)) in hechos:
                    continue
                hechos.add(frozenset((a.hash, h)))
                b = next(n for n in nodos if n.hash == h)
                mutuo = a.hash in b.vecinos
                caido = CAIDA in (a.estado, b.estado)
                self.create_line(*pos[a.hash], *pos[h], width=3 if mutuo else 2,
                                 fill=tema.ERROR if caido else "#B6C2D2",
                                 dash=() if mutuo and not caido else (6, 4))

    def _nodo(self, n: NodoVisto, x: float, y: float, escala: float) -> None:
        r = 31 * escala
        caido = n.estado == CAIDA
        relleno = tema.ERROR if caido else tema.TEXTO
        self.create_oval(x - r, y - r, x + r, y + r, fill=relleno, outline="")
        self.create_text(x, y - 5 * escala, text=n.nombre, fill=tema.TEXTO_INVERSO,
                         font=_fuente(max(8, round(9 * escala)), "bold"))
        detalle = "caído" if caido else (n.endpoint or "…").rsplit(":", 1)[-1]
        self.create_text(x, y + 9 * escala, text=f":{detalle}" if not caido else detalle,
                         fill="#CBD5E1", font=_fuente(max(7, round(8 * escala))))

    def _celulas(self, celulas: list[CelulaVista], nx: float, ny: float, angulo: float,
                 escala: float, abanico: bool) -> None:
        k = len(celulas)
        if not k:
            return
        distancia = 92 * escala
        if abanico:
            paso = min(math.radians(26), math.radians(170) / max(k - 1, 1))
            angulos = [angulo + (i - (k - 1) / 2) * paso for i in range(k)]
        else:
            angulos = [angulo + i * 2 * math.pi / k for i in range(k)]
        r = max(12.0, 16 * escala)
        for c, a in zip(celulas, angulos, strict=True):
            x, y = nx + distancia * math.cos(a), ny + distancia * math.sin(a)
            self.create_line(nx, ny, x, y, fill=tema.BORDE, width=1)
            self._pos[c.hash] = (x, y, r)
            if c.tipo == mensajes.MADRE:
                self._madre(c, x, y, r)
            elif c.tipo == mensajes.INTERFAZ:
                self._gui(c, x, y, r)
            else:
                self._gestor(c, x, y, r)
            # La etiqueta, por fuera del círculo: más lejos cuanto más horizontal es
            # el rayo (el texto es más ancho que alto).
            largo = max(len(c.nombre), 9) * 3.1 * escala
            fuera = distancia + r + 9 * escala + largo * abs(math.cos(a)) + 9 * abs(math.sin(a))
            self._etiqueta(c, nx + fuera * math.cos(a), ny + fuera * math.sin(a), escala)

    def _madre(self, c: CelulaVista, x: float, y: float, r: float) -> None:
        etiqueta = ("madre", f"h:{c.hash}")
        caja = (x - r, y - r, x + r, y + r)
        if c.estado == NACIENDO:   # aún no late: no se puede elegir como destino
            self.create_oval(*caja, fill=tema.ACENTO_SUAVE, outline=tema.ACENTO, width=2,
                             dash=(4, 3))
            self.create_text(x, y, text="…", fill=tema.ACENTO, font=_fuente(11, "bold"))
            return
        if c.hash == self._seleccion:
            s = r + 6
            self.create_oval(x - s, y - s, x + s, y + s, outline=tema.ACENTO, width=3,
                             tags=etiqueta)
        if c.estado == CAIDA:
            self.create_oval(*caja, fill=tema.ERROR_SUAVE, outline=tema.ERROR, width=2,
                             tags=etiqueta)
            self.create_text(x, y, text="✕", fill=tema.ERROR, font=_fuente(13, "bold"),
                             tags=etiqueta)
            return
        if not c.genes:
            self.create_oval(*caja, fill=tema.SUPERFICIE, outline=tema.APAGADO, width=2,
                             dash=(3, 3), tags=etiqueta)
        elif len(c.genes) == 1:
            self.create_oval(*caja, fill=tema.color_gen(c.codigos[0]), outline="", tags=etiqueta)
        else:
            extension = 360 / len(c.genes)
            for i, cod in enumerate(c.codigos):
                self.create_arc(*caja, start=90 - (i + 1) * extension, extent=extension,
                                fill=tema.color_gen(cod), outline=tema.SUPERFICIE, width=1,
                                tags=etiqueta)
        texto = c.codigos[0] if len(c.genes) == 1 else (f"{len(c.genes)}" if c.genes else "")
        self.create_text(x, y, text=texto, fill=tema.TEXTO_INVERSO,
                         font=_fuente(8, "bold"), tags=etiqueta)
        if c.mudo:
            d = r * 0.75
            self.create_line(x - d, y + d, x + d, y - d, fill=tema.ERROR, width=3, tags=etiqueta)
        if c.generacion > 0:
            bx, by, br = x + r * 0.8, y - r * 0.8, 8
            self.create_oval(bx - br, by - br, bx + br, by + br, fill=tema.AVISO, outline=tema.SUPERFICIE,
                             width=2, tags=etiqueta)
            self.create_text(bx, by, text=f"r{c.generacion}", fill=tema.TEXTO_INVERSO,
                             font=_fuente(6, "bold"), tags=etiqueta)

    def _gui(self, c: CelulaVista, x: float, y: float, r: float) -> None:
        caido = c.estado == CAIDA
        self.create_rectangle(x - r * 1.1, y - r * 0.75, x + r * 1.1, y + r * 0.75,
                              fill=tema.ERROR_SUAVE if caido else tema.SUPERFICIE,
                              outline=tema.ERROR if caido else tema.TEXTO, width=2)
        self.create_text(x, y, text="GUI", fill=tema.ERROR if caido else tema.TEXTO,
                         font=_fuente(8, "bold"))

    def _gestor(self, c: CelulaVista, x: float, y: float, r: float) -> None:
        d = r * 1.05
        yo = c.hash == self._yo
        self.create_polygon(x, y - d, x + d, y, x, y + d, x - d, y,
                            fill=tema.ACENTO if yo else tema.ACENTO_SUAVE,
                            outline=tema.ACENTO, width=2)
        self.create_text(x, y, text="G", fill=tema.TEXTO_INVERSO if yo else tema.ACENTO,
                         font=_fuente(9, "bold"))

    def _etiqueta(self, c: CelulaVista, x: float, y: float, escala: float) -> None:
        tam = max(7, round(8 * escala))
        if c.tipo == mensajes.MADRE:
            if c.estado == NACIENDO:
                linea2, color2 = "naciendo…", tema.ACENTO
            elif c.estado == CAIDA:
                linea2 = "reemplazada" if c.reemplazada_en is not None else "pérdida"
                color2 = tema.ERROR
            elif c.genes:
                linea2 = " · ".join(f"{g['codigo']} {g['version']}" for g in c.genes)
                color2 = tema.color_gen(c.codigos[0]) if len(c.genes) == 1 else tema.TEXTO
            else:
                linea2, color2 = "vacía", tema.APAGADO
            if c.mudo:
                linea2 += " · muda"
        elif c.tipo == mensajes.GESTOR:
            linea2, color2 = ("este gestor" if c.hash == self._yo else "gestor"), tema.ACENTO
        else:
            linea2, color2 = "interfaz", tema.TEXTO_SUAVE
        etiqueta = (("madre", f"h:{c.hash}") if c.tipo == mensajes.MADRE and c.estado != NACIENDO
                    else ())
        self.create_text(x, y - 6, text=c.nombre, fill=tema.TEXTO, font=_fuente(tam, "bold"),
                         tags=etiqueta)
        self.create_text(x, y + 7, text=linea2, fill=color2, font=_fuente(tam), tags=etiqueta)

    def _disponibilidad(self, foto: Foto, ancho: float) -> None:
        x, y = 14, ARRIBA / 2
        self.create_text(x, y, text="Disponibilidad", anchor="w", fill=tema.TEXTO_SUAVE,
                         font=_fuente(9, "bold"))
        x += 104
        for cod, n in foto.disponibilidad().items():
            color = tema.color_gen(cod)
            self.create_oval(x, y - 5, x + 10, y + 5, fill=color, outline="")
            self.create_text(x + 15, y, anchor="w", font=_fuente(9, "bold"),
                             fill=color if n else tema.ERROR, text=f"{cod} {n}")
            x += 72
        madres = foto.madres()
        vacias = sum(1 for c in madres if c.vacia)
        guis = sum(1 for c in foto.celulas.values() if c.tipo == mensajes.INTERFAZ)
        gestores = sum(1 for c in foto.celulas.values() if c.tipo == mensajes.GESTOR)
        nodos = sum(1 for n in foto.nodos.values() if n.estado != CAIDA)
        self.create_text(ancho - 14, y, anchor="e", fill=tema.TEXTO_SUAVE, font=_fuente(9),
                         text=f"{nodos} nodos · {len(madres)} madres ({vacias} vacías) · "
                              f"{guis} GUI · {gestores} gestor(es)")

    def _leyenda(self, alto: float) -> None:
        x, y = 14, alto - ABAJO / 2
        for cod in codigos.SERVICIOS:
            self.create_oval(x, y - 5, x + 10, y + 5, fill=tema.color_gen(cod), outline="")
            self.create_text(x + 14, y, anchor="w", text=cod, fill=tema.TEXTO_SUAVE,
                             font=_fuente(8))
            x += 50
        muestras = [("vacía", tema.SUPERFICIE, tema.APAGADO, (3, 2)),
                    ("caída", tema.ERROR_SUAVE, tema.ERROR, ())]
        for texto, relleno, borde, punteado in muestras:
            self.create_oval(x, y - 5, x + 10, y + 5, fill=relleno, outline=borde, dash=punteado)
            self.create_text(x + 14, y, anchor="w", text=texto, fill=tema.TEXTO_SUAVE,
                             font=_fuente(8))
            x += 58
        self.create_text(x + 6, y, anchor="w", fill=tema.TEXTO_SUAVE, font=_fuente(8),
                         text="r1 = clon · tachada = muda · clic en una madre = destino de "
                              "la orden")

    # ---------------------------------------------------------- destellos

    def _pintar_destellos(self) -> None:
        self.delete("destello")
        ahora = time.monotonic()
        for h, (tipo, inicio) in list(self._destellos.items()):
            avance = (ahora - inicio) / DESTELLO_S
            if avance >= 1 or h not in self._pos:
                if avance >= 1:
                    del self._destellos[h]
                continue
            self._anillo(h, avance, COLOR_DESTELLO.get(tipo, tema.ACENTO))
        # Los reemplazos naciendo laten (anillo azul periódico) hasta su primer latido,
        # y en verde unos segundos después de nacer.
        fase = (ahora % LATIDO_NACIENDO_S) / LATIDO_NACIENDO_S
        for c in self._naciendo():
            self._anillo(c.hash, fase, tema.ACENTO)
        for c in self._recien_nacidas(ahora):
            self._anillo(c.hash, fase, tema.OK)

    def _naciendo(self) -> list[CelulaVista]:
        return list(self._foto.naciendo.values()) if self._foto else []

    def _recien_nacidas(self, ahora: float) -> list[CelulaVista]:
        if self._foto is None:
            return []
        return [c for c in self._foto.celulas.values()
                if c.reemplaza and c.estado != CAIDA and ahora - c.desde < RECIEN_NACIDA_S]

    def _anillo(self, h: str, avance: float, color: str) -> None:
        if h not in self._pos:
            return
        x, y, r = self._pos[h]
        radio = r + 3 + 16 * avance
        self.create_oval(x - radio, y - radio, x + radio, y + radio, outline=color,
                         width=max(1, round(4 * (1 - avance))), tags="destello")

    def _animar(self) -> None:
        self._pintar_destellos()
        if self._destellos or self._naciendo() or self._recien_nacidas(time.monotonic()):
            self.after(30, self._animar)
        else:
            self._animando = False

    # --------------------------------------------------------------- clic

    def _clic(self, _evento) -> None:
        for etiqueta in self.gettags("current"):
            if etiqueta.startswith("h:"):
                self._al_elegir(etiqueta[2:])
                return
