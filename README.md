# Calculadora ADS — Tercer Parcial

Entrega final de **Cómputo Distribuido**. Es la calculadora distribuida del segundo parcial
(Campo de Datos en malla, células que solo se hablan por **broadcast con Códigos de Contenido**,
sin servidor central), con cuatro cosas nuevas:

| | Qué es | Dónde |
|---|---|---|
| **Células madre** | Servidores genéricos que no saben sumar ni dividir: cargan **microservicios (genes)** desde disco con `importlib`, los validan por sha256 y los cambian en caliente | [madre/](madre/), [microservicios/](microservicios/) |
| **Gestor de microservicios** | Interfaz con base de datos (SQLite) que dibuja la topología e **inyecta genes por el Campo de Datos**. Uno por nodo; **no es un orquestador** | [gestor/](gestor/) |
| **Foliado** | Cada operación lleva folio y huella (sello + rastro); su evento pasa por cuatro fases y cierra con `X_FIN`. Varias operaciones en vuelo por GUI | [comun/foliado.py](comun/foliado.py) |
| **Autorrecuperación** | Si una célula muere, las demás la regeneran solas, una a la vez, sin "cáncer", y la nueva copia los genes que hacían falta | [madre/regeneracion.py](madre/regeneracion.py), [madre/copia.py](madre/copia.py), [madre/lanzador.py](madre/lanzador.py) |

**Python 3.14 con librería estándar únicamente** (sockets, hilos, Tkinter, `importlib`,
`sqlite3`). Entorno con [uv](https://docs.astral.sh/uv/).

| Entregable | Dónde |
|---|---|
| Reporte técnico (30 páginas) | [REPORTE_TECNICO.md](REPORTE_TECNICO.md) → `Reporte_Tecnico_Calculadora_ADS.docx` (`uv run python docs/md_a_docx.py`) |
| Guion del video (11 escenas, ~12 min) | [GUION_VIDEO.md](GUION_VIDEO.md) (la matriz del reporte remite a sus escenas) |
| Hoja de control de la entrega | [ENTREGA.md](ENTREGA.md) |
| Resumen técnico (para auditar el reporte o preparar la exposición) | [RESUMEN_PROYECTO.md](RESUMEN_PROYECTO.md) |

Verificado: 217 pruebas en verde tres veces seguidas, `ruff` limpio y los ocho escenarios del
enunciado en vivo (30/30 revisiones; bitácora y capturas en [docs/capturas/](docs/capturas/)). Lo
entregado en el segundo parcial está archivado en [docs/parcial2/](docs/parcial2/).

## Cómo correrlo

```
uv sync                                              # una vez
uv run python -m panel                               # panel de la demo
uv run python -m unittest discover -s tests -t .     # pruebas
uv run ruff check .                                  # estilo
uv run python -m herramientas.firmar --verificar     # integridad del banco de genes
```

Programas sueltos:

```
uv run python -m nodo   --puerto 5001 --nombre "Nodo 1" [--semillas 127.0.0.1:5002]
uv run python -m madre  --nodo 127.0.0.1:5001 --nombre M1-N1 [--genes SUM@1.0,MUL] [--mudo]
uv run python -m interfaz --nodo 127.0.0.1:5001 --nombre GUI-1
uv run python -m gestor --nodo 127.0.0.1:5001 --nombre G-N1      # uno por nodo, cuando quieras
```

**Panel** (`python -m panel`): "Configuración mínima — vacía" (16 madres sin genes) o "— con
servicios" (cada madre con su gen); botón **Gestor** en cada nodo (no se abren solos); **+ Madre**,
**+ Muda (SUM)**, **+ Nodo**; **Tumbar SUM de Nodo 2**, **Tumbar 3 SUM**, **Tumbar
seleccionado** y **Detener todo** (también los reemplazos). Las madres se pintan del color de su gen.

**Regeneración**: tumba una madre y no toques nada. A los ~8 s las madres, sin hablarse, eligen
quién la regenera (HRW), éste publica `CLON_AVISO` y lanza `python -m madre --reemplaza …
--copiar SUM@1.0:<sha8>`; el reemplazo (`SUM-N2·r1`) nace vacío, pide sus genes por el Campo de
Datos y publica `CLON_LISTO`. Varias pérdidas se reponen una por una; al recuperar el nivel todas
anotan `NIVEL_OK`. Un retiro o una baja hechos con el gestor no se regeneran. En el gestor, la
pestaña **Regeneración** lo cuenta paso a paso. Los reemplazos dejan su PID en `run/`.

El gestor importa `microservicios/` a su BD (`datos/gestor/<nombre>.sqlite3`) al abrir. En su
ventana: clic en una madre del diagrama = destino; un gen del catálogo; **Inyectar**,
**Sustituir**, **Baja**, **Retirar célula**, **Sustituir en todas** y **Distribuir una de cada
operación por nodo** (modo vacío → configuración del PDF en un clic). Cada orden lleva folio
`O-…`; la madre contesta `GEN_ACK` y `GEN_RES`, y puede rechazarla (`SUM 9.9`).

## Microservicios (genes)

Cada gen es una carpeta `microservicios/<CÓDIGO>/<versión>/` con `manifiesto.json` (código,
versión, sha256 del programa, pruebas) y `servicio.py` (`SERVICIO`, `VERSION` y
`calcular(a, b) -> (resultado, error)`).

| Gen | Qué hace |
|---|---|
| `SUM 1.0` | Suma en punto flotante: `0.1 + 0.2 = 0.30000000000000004` |
| `SUM 2.0` | Suma decimal exacta: `0.1 + 0.2 = 0.3` |
| `SUB 1.0`, `MUL 1.0`, `DIV 1.0` | Resta, multiplicación, división (entre cero responde con error) |
| `SUM 9.9` | **Manipulado a propósito**: su programa cambió después de firmarse; toda célula lo rechaza |

Cada madre copia sus genes a su propio disco (`datos/celulas/<nombre>-<hash8>/genes/`) y los
carga desde ahí.

## Estructura

| Carpeta | Qué hay |
|---|---|
| [nodo/](nodo/) | Nodo del Campo de Datos (malla por gossip, broadcast, `NODO_LAT`) |
| [celula/](celula/) | Célula base: conexión, failover, latido, `TOPO_REQ` |
| [interfaz/](interfaz/) | GUI de la calculadora con foliado |
| [madre/](madre/) | Célula madre: almacén, genes, rondas, órdenes, pedidos, regeneración, lanzador, copia |
| [gestor/](gestor/) | Gestor de microservicios: BD SQLite, topología, diagrama, ventana |
| [microservicios/](microservicios/) | Banco de genes en disco |
| [comun/](comun/) | Protocolo, mensajes, códigos, foliado, hashes, config, tema y piezas visuales |
| [panel/](panel/), [sonda/](sonda/) | Herramientas de demostración, fuera del sistema |
| [herramientas/](herramientas/) | `firmar.py`: firma y verifica los manifiestos |
| [tests/](tests/) | 217 pruebas (unitarias y de integración en proceso) |
| [docs/](docs/) | Enunciado, requisitos, plan, capturas, convertidor a Word |

`datos/`, `logs/` y `run/` se generan al correr y no se versionan.
