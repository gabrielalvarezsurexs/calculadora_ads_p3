"""uv run python -m madre --nodo 127.0.0.1:5001 [--nombre M1-N1] [--genes SUM@1.0,MUL]
                        [--retardo-ms N] [--mudo] [--sin-regenerar]

Célula madre sin ventana: su bitácora va a consola y a ``logs/``. Sin
``--genes`` arranca VACÍA y espera a que el gestor le inyecte genes. Con
``--genes`` copia esos genes del banco ``microservicios/`` a su disco y los
carga (``SUM`` sin versión = la versión íntegra más alta).

Toda madre participa en la regeneración: si detecta una pérdida y le toca,
lanza el reemplazo como un proceso nuevo de este mismo programa, con
``--reemplaza <hash> --perdida <nombre> --copiar SUM@1.0:<sha8> --generacion 1``
(así nace un reemplazo: vacío, y copia esos genes por el Campo de Datos).

Ctrl+C la cierra ordenadamente (publica ``CEL_ADIOS``: no se regenera).
"""

import argparse
import sys
import time
from pathlib import Path

from comun import config, mensajes
from comun.bitacora import preparar_consola
from madre import lanzador
from madre.copia import leer_lista
from madre.nucleo import Madre


def main(argv=None) -> int:
    preparar_consola()
    p = argparse.ArgumentParser(prog="python -m madre", description="Célula madre (ADS)")
    p.add_argument("--nodo", required=True, help="endpoint host:puerto del nodo inicial")
    p.add_argument("--nombre", help="etiqueta para mostrar (por defecto M-<puerto>)")
    p.add_argument("--genes", default="",
                   help="genes del banco local separados por coma: SUM@1.0,MUL,DIV@1.0")
    p.add_argument("--retardo-ms", type=int, default=0,
                   help="retardo artificial al calcular, para demostrar el relevo")
    p.add_argument("--mudo", action="store_true",
                   help="inyección de falla: late, pero no acusa ni responde")
    p.add_argument("--banco", type=Path, default=config.DIR_MICROSERVICIOS,
                   help="carpeta del banco local de microservicios")
    p.add_argument("--sin-regenerar", action="store_true",
                   help="no lanza reemplazos (sigue la cuenta de pérdidas, pero no clona)")
    reemplazo = p.add_argument_group("reemplazo (lo usa el clonador al regenerar)")
    reemplazo.add_argument("--reemplaza", help="hash de la madre perdida que sustituye")
    reemplazo.add_argument("--perdida", help="nombre de la madre perdida (para mostrar)")
    reemplazo.add_argument("--copiar", default="",
                           help="genes de la perdida: SUM@1.0:1a2b3c4d,MUL@1.0:…")
    reemplazo.add_argument("--generacion", type=int, default=0,
                           help="1 para el reemplazo de una original, 2 para el de un "
                                "reemplazo… (telómeros)")
    args = p.parse_args(argv)

    nombre = args.nombre or f"M-{args.nodo.rsplit(':', 1)[-1]}"
    genes = [g for g in (x.strip() for x in args.genes.split(",")) if g]
    try:
        if args.reemplaza is not None and not mensajes.es_hash(args.reemplaza):
            raise ValueError("--reemplaza debe ser el hash (64 hex) de la madre perdida")
        madre = Madre(nombre, args.nodo, genes_iniciales=genes, banco=args.banco,
                      retardo_ms=args.retardo_ms, mudo=args.mudo,
                      generacion=max(0, args.generacion), reemplaza=args.reemplaza,
                      reemplaza_nombre=args.perdida, copiar=leer_lista(args.copiar),
                      lanzador=None if args.sin_regenerar else lanzador.lanzar_proceso)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    madre.iniciar()
    try:
        while madre.activo:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        madre.detener()
        time.sleep(0.3)  # que el hilo escritor alcance a enviar el CEL_ADIOS
        madre.bitacora.cerrar()
        if args.reemplaza:
            lanzador.olvidar(nombre)  # su registro en run/ (lo dejó quien la lanzó)
    return 0


if __name__ == "__main__":
    sys.exit(main())
