"""Agenda de tareas a una hora monotónica, en un solo hilo.

Lo usan los respaldos ("si a esta hora nadie respondió, hago el relevo"), la
verificación de que un gen descargado se liberó y, en la regeneración, los
plazos del clonador. Una tarea que lanza no mata al hilo: se entrega a
``al_error`` y la agenda sigue.
"""

import heapq
import itertools
import threading
import time
from collections.abc import Callable


class Programador:
    def __init__(self, al_error: Callable[[Exception], None], nombre: str = "programador"):
        self._heap: list = []
        self._cond = threading.Condition()
        self._seq = itertools.count()
        self._activo = True
        self._al_error = al_error
        threading.Thread(target=self._correr, name=nombre, daemon=True).start()

    def agendar(self, cuando: float, funcion: Callable[[], None]) -> None:
        """Corre ``funcion`` cuando ``time.monotonic()`` llegue a ``cuando``."""
        with self._cond:
            heapq.heappush(self._heap, (cuando, next(self._seq), funcion))
            self._cond.notify()

    def en(self, segundos: float, funcion: Callable[[], None]) -> None:
        self.agendar(time.monotonic() + segundos, funcion)

    def detener(self) -> None:
        with self._cond:
            self._activo = False
            self._cond.notify()

    def _correr(self) -> None:
        while True:
            with self._cond:
                while self._activo:
                    if self._heap and self._heap[0][0] <= time.monotonic():
                        break
                    espera = self._heap[0][0] - time.monotonic() if self._heap else None
                    self._cond.wait(espera)
                if not self._activo:
                    return
                _, _, funcion = heapq.heappop(self._heap)
            try:
                funcion()
            except Exception as e:
                self._al_error(e)
