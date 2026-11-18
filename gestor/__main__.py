"""uv run python -m gestor --nodo 127.0.0.1:5001 [--nombre G-N1] [--bd ruta.sqlite3]
                         [--banco microservicios] [--geometria WxH+X+Y]

Gestor de microservicios con ventana: diagrama vivo de la topología, catálogo
(SQLite) y órdenes por el Campo de Datos. Uno por nodo, y lo levanta el
usuario cuando quiere (el panel no lo abre solo). Cerrarlo no cambia nada del
funcionamiento del sistema.
"""

import argparse
import queue
import sys
from pathlib import Path

from comun import config
from comun.bitacora import preparar_consola
from gestor.nucleo import Gestor


def main(argv=None) -> int:
    preparar_consola()
    p = argparse.ArgumentParser(prog="python -m gestor",
                                description="Gestor de microservicios (ADS)")
    p.add_argument("--nodo", required=True, help="endpoint host:puerto del nodo inicial")
    p.add_argument("--nombre", help="etiqueta para mostrar (por defecto G-<puerto>)")
    p.add_argument("--bd", type=Path,
                   help="archivo SQLite (por defecto datos/gestor/<nombre>.sqlite3)")
    p.add_argument("--banco", type=Path, default=config.DIR_MICROSERVICIOS,
                   help="carpeta de microservicios que se importa a la BD")
    p.add_argument("--geometria", help="geometría Tk de la ventana, p. ej. 1400x860+0+0")
    args = p.parse_args(argv)

    nombre = args.nombre or f"G-{args.nodo.rsplit(':', 1)[-1]}"
    try:
        gestor = Gestor(nombre, args.nodo, bd=args.bd, banco=args.banco, eventos=queue.Queue())
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    gestor.iniciar()
    try:
        from gestor.gui import VentanaGestor
        VentanaGestor(gestor, geometria=args.geometria).ejecutar()
    except KeyboardInterrupt:
        pass
    finally:
        gestor.detener()
        gestor.bd.cerrar()
        gestor.bitacora.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
