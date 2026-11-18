"""Firma y verifica los genes del banco ``microservicios/``.

    uv run python -m herramientas.firmar               # firma (recalcula sha256)
    uv run python -m herramientas.firmar --verificar   # solo revisa; código 1 si algo falla

"Firmar" aquí es escribir en el manifiesto el sha256 del ``servicio.py``: quien
reciba el gen recalcula el hash y, si no coincide, lo rechaza sin ejecutarlo.
Hay que firmar cada vez que se edita un programa a propósito.

``SUM@9.9`` NO se firma nunca: es el gen manipulado de la demo (su programa se
modificó después de firmar) y debe seguir fallando la verificación.
"""

import argparse
import json
import sys
from pathlib import Path

from comun import config, microservicios
from comun.bitacora import preparar_consola

MANIPULADOS_DE_DEMO = {"SUM@9.9"}


def firmar(carpeta: Path) -> tuple[str, bool]:
    """Escribe el sha256 real en el manifiesto. Devuelve (sha, si cambió)."""
    ruta = carpeta / microservicios.MANIFIESTO
    manifiesto = json.loads(ruta.read_text(encoding="utf-8"))
    sha = microservicios.sha256((carpeta / microservicios.ARCHIVO).read_bytes())
    if manifiesto.get("sha256") == sha:
        return sha, False
    manifiesto["sha256"] = sha
    texto = json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n"
    ruta.write_text(texto, encoding="utf-8", newline="\n")
    return sha, True


def main(argv=None) -> int:
    preparar_consola()
    p = argparse.ArgumentParser(prog="python -m herramientas.firmar", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--verificar", action="store_true", help="solo revisar, sin escribir")
    p.add_argument("--banco", type=Path, default=config.DIR_MICROSERVICIOS)
    args = p.parse_args(argv)

    fallas = 0
    for carpeta in microservicios.carpetas(args.banco):
        nombre = f"{carpeta.parent.name}@{carpeta.name}"
        try:
            if not args.verificar and nombre not in MANIPULADOS_DE_DEMO:
                _, cambio = firmar(carpeta)
                if cambio:
                    print(f"  firmado   {nombre}")
            paquete = microservicios.leer(carpeta)
            problema = paquete.problema(config.GEN_MAX_BYTES)
        except (OSError, ValueError) as e:
            problema = str(e)
        if problema is None:
            print(f"✔ {nombre:<9} sha {paquete.sha_real[:8]}  {paquete.manifiesto['nombre']}")
        else:
            esperado = " (esperado: manipulado de demo)" if nombre in MANIPULADOS_DE_DEMO else ""
            print(f"✘ {nombre:<9} {problema}{esperado}")
            fallas += nombre not in MANIPULADOS_DE_DEMO
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
