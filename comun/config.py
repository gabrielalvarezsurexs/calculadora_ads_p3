"""Todas las constantes de tiempo, TTL y tamaños del sistema, en un solo lugar.

Regla del proyecto: el resto del código las lee como ``config.X`` en el momento
de usarlas, NUNCA con ``from comun.config import X``. Así las pruebas pueden
acortar los tiempos con ``mock.patch.object(config, "LATIDO", 0.2)`` y el cambio
se ve en todos los módulos sin reiniciar nada.

Los tiempos están en segundos.
"""

from pathlib import Path

# --- Carpetas ---------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
DIR_MICROSERVICIOS = RAIZ / "microservicios"   # banco local de genes (programas en disco)
DIR_DATOS = RAIZ / "datos"                     # almacén de cada madre y BD de los gestores
DIR_RUN = RAIZ / "run"                         # PIDs de los clones (para detenerlos)

# --- Broadcast y prevención de ciclos (§9, §11) -----------------------------
TTL_INICIAL = 8           # con lo que publica una célula; debe ser >= diámetro de la red
TTL_MAX = 16              # tope: un TTL mayor que llegue por la red se recorta
VISTOS_VIGENCIA = 60.0    # cuánto recuerda el registro temporal un id ya procesado
VISTOS_MAX = 100_000      # tope de ids en el registro (se olvidan los más viejos)

# --- Latidos y disponibilidad -----------------------------------------------
LATIDO = 2.0              # cada cuánto emite CEL_LAT una célula
LATIDO_CADUCIDAD = 6.0    # sin latido ni acuse en este tiempo, la célula se da por muerta

# --- Acuses, elección y plazos de la GUI -----------------------------------
VENTANA_ACUSES = 1.5      # sin quórum en este tiempo, la GUI reintenta
VENTANA_ELECCION = 0.5    # lo que espera una madre para juntar acuses antes de elegir
RELEVO = 1.5              # separación entre respaldos escalonados (rank r espera r·RELEVO)
MARGEN_RESULTADO = 2.0    # holgura extra del plazo de resultado en la GUI
MAX_INTENTOS = 3
ACUSES_MIN_DEFECTO = 2

# --- Conexión ---------------------------------------------------------------
HOLA_TIMEOUT = 5.0        # una conexión entrante que no se presenta en este tiempo se cierra
BIENVENIDA_TIMEOUT = 3.0  # lo que espera quien marca a que el nodo lo acepte
CONECTAR_TIMEOUT = 3.0    # connect() TCP
BACKOFF_MIN = 1.0
BACKOFF_MAX = 8.0
SUPERVISOR = 2.0          # cada cuánto el nodo revisa qué endpoints conocidos le faltan
REINTENTOS_MISMO_NODO = 2 # failover: intentos con el nodo original antes de rotar
# connect() de esos reintentos. En Windows, marcar a un puerto cerrado tarda ~2 s
# en devolver el rechazo; sin este tope, el failover tardaría ~6 s en vez de ~3.
REINTENTO_TIMEOUT = 0.5

# --- Transporte -------------------------------------------------------------
MAX_LINEA = 64 * 1024     # una línea NDJSON más larga se descarta
COLA_ENLACE_MAX = 5_000   # mensajes pendientes por enlace antes de darlo por LENTO

# --- Célula madre: rondas ---------------------------------------------------
RONDAS_VIGENCIA = 120.0   # rondas más viejas que esto se purgan

# --- Genes (microservicios cargables) ----------------------------------------
GEN_MAX_BYTES = 32 * 1024     # tope de un servicio.py: viaja dentro de una línea NDJSON
GEN_LIBERACION = (0.2, 1.0, 3.0)  # cuándo se revisa (s) que un gen descargado se liberó
GEN_ACK_TIMEOUT = 2.0         # gestor: sin GEN_ACK en este tiempo, "sin respuesta"
GEN_RES_TIMEOUT = 10.0        # gestor: con GEN_ACK pero sin GEN_RES en este tiempo, "sin resultado"
PLAZO_PEDIDO = 2.0            # GEN_PIDE: espera de una GEN_ENTREGA
REINTENTOS_PEDIDO = 3
ENTREGA_RETARDO_MAX = 0.4     # quien puede entregar espera un retardo propio (≤ esto) y se
                              # calla si otro ya entregó: normalmente sale UNA sola entrega

# --- Gestor: topología ---------------------------------------------------------
CAIDA_VISIBLE = 8.0           # una célula o nodo caído se sigue dibujando (en rojo) este tiempo
ESPERA_REEMPLAZO = 60.0       # una MADRE caída sigue en rojo hasta que aparece su reemplazo
                              # (o hasta esto, si nadie la regenera)

# --- Regeneración (anti-cáncer, PLAN §6.4) ----------------------------------
REVISION_REGENERACION = 0.5   # cada cuánto revisa cada madre si hay que regenerar
RELEVO_CLON = 3.0             # el rango r del ranking espera r·RELEVO_CLON para regenerar
PLAZO_CLON = 15.0             # lo que se espera a que el reemplazo esté listo
MAX_REINTENTOS_CLON = 2       # por pérdida
PAUSA_REGENERACION = 2.0      # gradual: entre una regeneración y la siguiente
MAX_MADRES = 40               # tope duro de madres en el sistema
MAX_POR_GEN = 8               # tope duro de madres con un mismo código
MAX_GENERACION = 3            # telómeros: una madre de esta generación ya no clona
MAX_CLONES_MINUTO = 2         # cupo de lanzamientos por madre

# --- Presentación -----------------------------------------------------------
# Códigos que NO se escriben en consola (sí en archivo). El nodo no interpreta
# el catálogo: esto es solo un filtro de ruido para la bitácora.
CODIGOS_SILENCIOSOS = ("CEL_LAT", "NODO_LAT", "TOPO_REQ", "TOPO_RES")
