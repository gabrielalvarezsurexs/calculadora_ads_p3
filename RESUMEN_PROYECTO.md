# Resumen técnico del proyecto Calculadora ADS (Tercer Parcial)

Documento de referencia con todo lo técnico del proyecto en un solo lugar, **sacado del código**
(no del reporte), para auditar el reporte por tu cuenta o preparar la exposición. Cada dato dice
en qué archivo y función se puede comprobar. La versión oficial del reporte es
`Reporte_Tecnico_Calculadora_ADS.pdf` (29 páginas, editada por ti); `REPORTE_TECNICO.md` es la
versión extendida, con algunas bitácoras y tablas que el PDF resume. Las secciones se numeran igual
en los dos; en el PDF, las constantes son el Anexo A.

La sección 27 es una guía para la auditoría: qué revisar del reporte, contra qué y lo que ya se
corrigió.

---

## 1. Qué es

Es la calculadora ADS del segundo parcial con cuatro cosas nuevas que pide el enunciado del
tercero:

1. **Foliado** (§5.1): cada operación lleva folio y huella; ACK, mínimo de ACK y un evento con
   cuatro fases.
2. **Microservicios dinámicos** (§5.2): las células servidor son **células madre** que no saben
   sumar. Su funcionalidad vive en **genes** (programas en disco) que se cargan con `importlib`
   mientras el sistema corre.
3. **Autorrecuperación** (§5.3): si una madre muere, las demás la **regeneran solas**, una a la
   vez y sin "cáncer". La nueva copia los genes que tenía la perdida.
4. **Gestor de servicios** (§5.4): una ventana con base de datos SQLite que dibuja la topología y
   da de alta, baja o sustituye genes **por el Campo de Datos**.

Lo heredado sigue igual: Campo de Datos de nodos en malla completa, broadcast con Código de
Contenido, sin unidad central. **No hay orquestador**: el gestor y el panel son herramientas;
las decisiones las toman las células con la misma regla determinista.

Configuración mínima del enunciado (Figura 1 del PDF): 4 nodos en malla completa y, en cada nodo,
1 GUI y 4 células servidor (una por operación): 4 GUIs y 16 madres.

---

## 2. Lo que se usó

### 2.1 Lenguaje y entorno

| Cosa | Detalle |
|---|---|
| Lenguaje | Python 3.14 |
| Dependencias del sistema | Ninguna. Solo librería estándar |
| Entorno | **uv** (`uv sync` crea `.venv` con `ruff`, la única dependencia de desarrollo) |
| Sistema operativo | Windows 11, todo en `127.0.0.1` por defecto (`--host 0.0.0.0` para LAN en el nodo) |
| Cómo se ejecuta | `uv run python -m <paquete>` desde la carpeta del proyecto |
| Lint | `ruff check .` (configurado en `pyproject.toml`) |
| Base de datos | SQLite (`sqlite3`), solo en el gestor |
| Control de versiones | Git, repositorio `calculadora_ads_p3` en GitHub; la etiqueta `parcial-2` marca el punto de partida |

Se renunció a propósito a los puntos extra de Java (§1 del enunciado).

### 2.2 Módulos de la librería estándar y para qué se usó cada uno

| Módulo | Para qué |
|---|---|
| `socket` | TCP entre nodos y entre células y nodos |
| `threading` | Hilos (lector y escritor por enlace, aceptador, supervisor, latido, conector, trabajador de rondas, regeneración), `Lock`, `RLock`, `Event` |
| `queue` | Cola de escritura de cada enlace, cola de rondas de la madre y puente red → ventana |
| `json` | Mensajes NDJSON (`allow_nan=False`), manifiestos, registros de `run/` |
| `hashlib` | SHA-256: identidades, ids de mensaje, sello, ranking HRW, integridad de genes |
| `secrets` | 128 bits aleatorios en cada hash de identidad |
| `importlib` (`importlib.util`) | Cargar el `servicio.py` de cada gen en memoria |
| `weakref`, `gc` | Confirmar que un gen descargado salió de memoria |
| `sqlite3` | BD del gestor (`microservicio`, `orden`) |
| `decimal` | Solo dentro del gen `SUM 2.0` (suma decimal exacta) |
| `subprocess` | El panel lanza y tumba procesos; el clonador lanza el reemplazo desacoplado |
| `ctypes` | `madre/lanzador.py`: hora de creación de un PID y `TerminateProcess` (Windows recicla PIDs) |
| `tkinter` | Ventanas del nodo, la GUI, el gestor (diagrama en `Canvas`) y el panel |
| `heapq` | `comun/programador.py`: tareas a tiempo (respaldos, vencimientos de órdenes y pedidos) |
| `dataclasses` | `Ronda`, `Operacion`, `Ficha`, `Perdida`, `Encargo`, `Orden`, `Paquete`… |
| `collections` | `OrderedDict` del registro de vistos, `deque` para el cupo de clones y las bitácoras del panel |
| `math` | `isfinite` en operandos y resultados |
| `argparse` | Opciones de cada programa |
| `re`, `pathlib`, `os`, `sys`, `time`, `itertools`, `traceback`, `shutil`, `typing` | Validación, rutas, PIDs, reloj, contadores, registro de errores |
| `random` | El panel elige una semilla al azar para cada nodo nuevo |
| `unittest` (+ `tempfile`, `io`, `contextlib`, `unittest.mock`) | Las 217 pruebas |
| `zipfile`, `xml`, `struct` | Solo `docs/md_a_docx.py`, que genera el `.docx` sin pandoc |

### 2.3 Conceptos y técnicas de sistemas distribuidos

| Técnica | Dónde se aplica | Referencia del reporte |
|---|---|---|
| Arquitectura ADS (Campo de Datos, células, Código de Contenido) | Todo el diseño | Mori (1993) |
| Inundación con supresión de duplicados, TTL y horizonte dividido | `Nodo._difundir()` | Tanenbaum y Van Steen (2023) |
| Descubrimiento por gossip | Formación de la malla | Demers et al. (1987) |
| *Rendezvous hashing* (HRW) | Titular de cada operación **y** clonador de cada pérdida | Thaler y Ravishankar (1998) |
| Acuses, quórum (mínimo de ACK) y reintentos con el mismo folio | Foliado | Enunciado / clase |
| Latidos y detección de fallas por caducidad | Disponibilidad, topología, pérdidas | Coulouris et al. (2011) |
| Failover del cliente | Las células cambian de nodo si el suyo cae | — |
| Backoff exponencial | Reconexión (1 a 8 s) | — |
| Carga dinámica de código con verificación de integridad | Genes: sha256 antes de ejecutar | FIPS 180-4, docs de `importlib` |
| Replicación 1 a 1 con límites (Hayflick) | Regeneración sin cáncer | Hayflick (1965) |
| NDJSON sobre TCP | Framing | RFC 8259, RFC 9293 |

---

## 3. Estructura del repositorio

| Carpeta | Líneas (.py) | Qué contiene |
|---|---|---|
| `comun/` | ~1,600 | Transporte NDJSON y `Enlace`, mensajes, Códigos de Contenido, hashes y HRW, foliado, microservicios (manifiesto y paquete), pedidos, programador, constantes, vistos, bitácora, formato, tema y estilo Tk |
| `nodo/` | ~890 | Nodo del Campo de Datos (`nucleo.py` sin Tkinter, `gui.py` la ventana) |
| `celula/` | ~390 | Célula base: conexión, failover, deduplicación, publicar, latido, `TOPO_REQ` |
| `madre/` | ~2,300 | Célula madre: núcleo, almacén, genes, rondas, órdenes, pedidos, copia, regeneración, lanzador |
| `interfaz/` | ~1,245 | GUI: núcleo del foliado y la calculadora con tarjeta de evento |
| `gestor/` | ~1,830 | Gestor: BD, topología, núcleo de órdenes, diagrama vivo y ventana |
| `panel/` | ~790 | Panel de despliegue de la demo (fuera del sistema) |
| `sonda/` | ~95 | Inyecta mensajes de prueba (fuera del sistema) |
| `herramientas/` | ~70 | `firmar.py`: calcula y verifica el sha256 de cada gen |
| `microservicios/` | 6 genes | `SUM 1.0`, `SUM 2.0`, `SUB 1.0`, `MUL 1.0`, `DIV 1.0`, `SUM 9.9` (manipulado) |
| `tests/` | ~3,820 | 217 pruebas unitarias y de integración |
| `docs/` | ~620 | `md_a_docx.py`, `ENUNCIADO.md`, `PLAN.md`, `REQUISITOS.md`, capturas y lo del parcial 2 |
| `datos/`, `run/`, `logs/` | — | Almacenes de las madres y BD de los gestores / PIDs de los reemplazos / bitácoras (ignorados por git) |

El sistema (`comun`, `nodo`, `celula`, `madre`, `interfaz`, `gestor`) son unas 8,250 líneas.

**Reglas de código** (se cumplen en todo el proyecto):
1. Ningún `nucleo.py` importa Tkinter. Los núcleos publican eventos en una `queue.Queue` que la
   ventana vacía con `after(100)`. Así las pruebas levantan el sistema entero sin ventanas.
2. Las constantes se leen como `config.X` al usarlas (las pruebas las acortan con `mock.patch`).
3. Estado compartido entre hilos, protegido por el lock de su dueño.
4. Ningún hilo de red muere por una excepción: se registra `ERROR` y sigue.
5. Los nodos no leen el `cuerpo`; cada célula filtra por código.

---

## 4. Los programas

### 4.1 Nodo (`uv run python -m nodo --puerto 5001 --nombre "Nodo 1" --semillas 127.0.0.1:5002`)

- Acepta conexiones de nodos y de células; sabe qué es cada una por su `HOLA`.
- Forma la malla solo, por gossip, con **una semilla cualquiera**.
- Inunda cada mensaje de datos. **No lee el `cuerpo`**: usa `id`, `ttl` y `ruta`; `codigo` y
  `origen` solo para su bitácora.
- **Nuevo:** acepta la entidad `GESTOR` y origina cada `LATIDO` (2 s), y al cambiar sus enlaces,
  un `NODO_LAT` con su nombre, endpoint, vecinos reales y células conectadas.
- Opciones: `--host`, `--sin-ventana`, `--geometria`.
- Ventana: vecinos, células, contadores (recibidos, reenviados, duplicados, TTL agotado,
  descartados) y tráfico en vivo (`FWD`, `DUP`, `TTL`, `DROP`) con casilla "pausar".

### 4.2 Célula madre (`uv run python -m madre --nodo 127.0.0.1:5001 [--genes SUM@1.0] …`)

- **Programa base genérico sin aritmética.** Sin `--genes` arranca **vacía**: se conecta, late
  con `genes: []` y espera órdenes.
- Opciones: `--nombre`, `--genes SUM@1.0,MUL,DIV@1.0` (del banco local), `--retardo-ms` (atrasa
  el cálculo, nunca el acuse), `--mudo` (late pero no acusa ni responde: falla inyectada),
  `--banco`, `--sin-regenerar`.
- Solo para reemplazos (lo usa el clonador): `--reemplaza <hash> --perdida <nombre>
  --copiar SUM@2.0:765cbef9,… --generacion 1`.
- Por dentro: `almacen.py` (su disco), `genes.py` (cargar/ejecutar), `rondas.py` (atender
  operaciones), `ordenes.py` (órdenes del gestor), `pedidos.py` (pedir genes), `copia.py` (el
  reemplazo copia sus genes), `regeneracion.py` (detectar y clonar), `lanzador.py` (procesos).
- Sin ventana; su bitácora se ve en el panel y en `logs/`.

### 4.3 GUI (`uv run python -m interfaz --nodo 127.0.0.1:5001 [--acuses-min 2]`)

- Calculadora con teclado y display. Hasta 32 operaciones en vuelo; **"Ráfaga ×8"** lanza 8 de
  las cuatro operaciones a la vez.
- Folia cada solicitud, cuenta ACK por intento, reintenta con el mismo folio y publica `X_FIN`.
- Pestañas **Evento** (tarjeta con folio, 4 fases, sello, ACK k/mín., esperadas, ausentes, quién
  respondió con qué gen y el rastro), **Mis eventos** y **Protocolo** (mini bitácora).
- **Disponibilidad** por operación: "vivas N" por latidos y el campo **"mín. ACK"** editable en
  vivo; un operador se deshabilita si hay menos vivas que el mínimo.
- Pie: contador **"ajenas ignoradas"**.

### 4.4 Gestor (`uv run python -m gestor --nodo 127.0.0.1:5001 [--nombre G-N1]`)

- Es una **célula más** (entidad `GESTOR`), uno por nodo, cada uno con su BD
  (`datos/gestor/<nombre>.sqlite3`, `--bd` para otra ruta). Al abrir importa `microservicios/`.
- Diagrama vivo (Tk `Canvas`), catálogo de la BD, pestañas **Órdenes**, **Regeneración** y
  **Bitácora**. Clic en una madre = destino de la orden.
- Botones: "Inyectar (alta)", "Sustituir versión", "Baja del gen", "Retirar célula",
  "Distribuir una de cada operación por nodo", "Sustituir en todas las que lo tengan",
  "Consultar topología (TOPO_REQ)".

### 4.5 Herramientas fuera del sistema

- **Panel** (`uv run python -m panel`): dos modos, **"Configuración mínima — vacía"** (16 madres
  sin genes) y **"con servicios"** (cada madre con `--genes`). Fila por nodo con fichas de sus
  madres, botón **Gestor** por nodo (los gestores no se abren solos), "+ Nodo", "+ Madre",
  "+ Muda (SUM)", "Tumbar SUM de Nodo 2", "Tumbar 3 SUM", "Tumbar seleccionado", "Detener todo"
  (incluye los reemplazos registrados en `run/`), tabla **Procesos** con el comando exacto y la
  bitácora en vivo. Si se cierra sin detener, el sistema sigue.
- **Sonda** (`uv run python -m sonda --nodo … [--ttl] [--repetir] [--id]`): inyecta un
  `SONDA_PRUEBA` para probar cada defensa contra ciclos.
- **Firmar** (`uv run python -m herramientas.firmar [--verificar]`): escribe o comprueba el
  sha256 de cada `servicio.py` en su manifiesto.

---

## 5. Topología y descubrimiento (heredado)

- Ningún nodo tiene la lista de los demás. Arranca con cero o más semillas.
- `BIENVENIDA` trae los nodos que conoce el otro; cada vez que crece su lista, manda `PARES` a
  todos sus enlaces. La lista solo crece y es finita: el gossip se detiene solo.
- Un **supervisor** cada `SUPERVISOR` (2 s) marca a cada endpoint conocido sin enlace; si falla,
  backoff de 1 a 8 s (`BACKOFF_MIN`, `BACKOFF_MAX`).
- **Regla de enlace duplicado** (`Nodo._registrar_vecino()`): sea `preferido = min(mi_hash,
  hash_par)`; se queda el enlace nuevo solo si lo inició el preferido y el existente no. Los dos
  lados deciden lo mismo sin hablarlo. **Nuevo tras la auditoría:** el sobrante se cierra con
  `Enlace.cerrar(drenar=True)`: deja de escribir pero sigue leyendo hasta que el par cierra
  (máx. `DRENAJE` = 2 s), para no perder lo que venía en camino.

---

## 6. Protocolos

### 6.1 Transporte (`comun/protocolo.py`)

- NDJSON: un objeto JSON por línea, UTF-8. Línea máxima `MAX_LINEA` = 64 KiB (más larga se
  descarta completa).
- Lector tolerante: una línea inválida se reporta y la lectura sigue. Se rechazan `NaN`,
  `Infinity`, números que desbordan (`1e999`) y anidamiento extremo.
- `Enlace`: hilo lector + hilo escritor con cola; quien difunde solo encola. Más de
  `COLA_ENLACE_MAX` (5,000) mensajes pendientes = par lento, se cierra (`LENTO`).

### 6.2 Protocolo de conexión (control, un solo enlace, nunca se reenvía)

| `ctrl` | Dirección | Campos |
|---|---|---|
| `HOLA` | entidad → nodo | `entidad` (`NODO`, `INTERFAZ`, `MADRE`, `GESTOR`, `SONDA`), `hash`, `nombre`, `servicio`, `escucha` (solo nodos), `version` (1) |
| `BIENVENIDA` | nodo → entidad | `hash`, `nombre`, `nodos` (endpoints conocidos) |
| `PARES` | nodo → sus enlaces | `nodos` |
| `RECHAZO` | nodo → entidad | `motivo`: `duplicado`, `autoconexion`, `version`, `invalido`; `hash` |

Una entrante que no manda `HOLA` en `HOLA_TIMEOUT` (5 s) se cierra; quien marca espera la
`BIENVENIDA` `BIENVENIDA_TIMEOUT` (3 s). **Nuevo tras la auditoría:** si la `BIENVENIDA` llega
justo después de ese plazo, ya no se registra (antes salía una `DESCONEXION` falsa).

### 6.3 Sobre de datos (`comun/mensajes.py` → `nuevo()`)

```json
{"id": "<sha256 propio>", "codigo": "SUM_REQ", "origen": "<hash de la célula>",
 "tipo_origen": "INTERFAZ", "nombre_origen": "GUI-1", "ts": 1763420934.885,
 "ttl": 8, "ruta": ["<hash nodo>", …], "cuerpo": {…}}
```

---

## 7. Códigos de Contenido (`comun/codigos.py`)

**Operación**: `<GEN>_<TIPO>`, con `<GEN>` = 3 o 4 mayúsculas que no sean un prefijo reservado
(`es_gen()`), y `TIPO` ∈ `REQ`, `ACK`, `RES`, `FIN`. La GUI pide `SUM`, `SUB`, `MUL`, `DIV`; una
madre atiende el código de cualquier gen que tenga activo.

**Sistema** (prefijos reservados `CEL`, `NODO`, `GEN`, `CLON`, `TOPO`, `SONDA`):

| Código | Lo publica | Lo atiende | Cuerpo |
|---|---|---|---|
| `X_REQ` | GUI | Madres con `X` activo | `folio, intento, a, b, huella` |
| `X_ACK` | Madre | GUI dueña; madres con `X` (ranking) | `folio, intento, id_solicitud, en_cola, gen, huella` |
| `X_RES` | Titular o relevo | GUI dueña; madres (marcan resuelta) | `folio, intento, id_solicitud, resultado, error, rol, ms, gen, huella` |
| `X_FIN` | GUI | Madres (cierran las rondas del folio) | `folio, intento, estado, id_respuesta, acuses, ausentes, huella` |
| `CEL_LAT` | Toda célula, cada 2 s | GUIs, madres, gestores | tipo, nodo, nodo_nombre; madre: `genes [{codigo, version, sha8}]`, generación, reemplaza, mudo, en_cola, atendidas |
| `CEL_ADIOS` | Célula que se cierra ordenadamente | Todos (**no** es pérdida) | `motivo, genes, generacion` |
| `NODO_LAT` | Nodo | Gestores y madres | `nombre, endpoint, vecinos, celulas, contadores` |
| `TOPO_REQ` / `TOPO_RES` | Gestor / toda célula que late | Células / gestor | `consulta` / latido + `consulta`, `para` |
| `GEN_INYECTA` | Gestor | Solo la madre `destino`, y solo si el origen es `GESTOR` | `orden, destino, accion (alta\|cambio), manifiesto, fuente` |
| `GEN_BAJA` | Gestor | Ídem | `orden, destino, accion: baja, codigo` |
| `CEL_RETIRO` | Gestor | Ídem (publica `CEL_ADIOS` y termina) | `orden, destino, accion: retiro` |
| `GEN_ACK` | Madre destino | Gestor | `orden, destino, accion` |
| `GEN_RES` | Madre destino | Gestor | `orden, destino, accion, ok, detalle, gen, ms, ruta, sustituyo, genes` |
| `GEN_PIDE` | Madre que necesita un gen | Madres con el gen activo; gestores con el gen íntegro | `pedido, intento, codigo, version, sha` |
| `GEN_ENTREGA` | Quien lo tenga | La que pidió | el paquete (manifiesto + fuente) |
| `CLON_AVISO` | Clonador | Madres y gestores | `reemplaza, perdida, nodo_perdida, genes, hijo, nodo, nodo_nombre, generacion, intento, rango` |
| `CLON_LISTO` | Reemplazo | Madres y gestores | `reemplaza, genes, fuentes, faltan, generacion` |
| `SONDA_PRUEBA` | Sonda | Nadie | — |

Los códigos `CEL_LAT`, `NODO_LAT`, `TOPO_REQ` y `TOPO_RES` no se escriben en consola (sí en el
archivo de bitácora): `config.CODIGOS_SILENCIOSOS`.

---

## 8. Broadcast y prevención de ciclos (cuatro defensas, heredado)

1. **Id único + registro temporal** (`comun/vistos.py`, `VISTOS_VIGENCIA` 60 s, hasta 100,000
   ids): un id ya visto es `DUP` y no se reenvía.
2. **TTL**: `TTL_INICIAL` 8, se descuenta en cada nodo; uno mayor que `TTL_MAX` (16) se recorta.
   Con TTL 0 se entrega a las células del nodo pero no se reenvía.
3. **Horizonte dividido + ruta**: nunca de vuelta al enlace de llegada ni a un nodo que ya está
   en `ruta`.
4. **Deduplicación en la célula** (su propio `RegistroVistos`), útil tras un failover.

El nodo **no cambió** para soportar genes, órdenes ni regeneración: todo lo nuevo son códigos que
solo entienden las células.

---

## 9. Foliado (`comun/foliado.py`, `interfaz/nucleo.py`, `madre/rondas.py`)

### 9.1 Definiciones (las del PDF)

| Concepto | En el código |
|---|---|
| **Folio** | `F-<hash8 de la GUI>-<n:04d>` (`foliado.folio()`). Lo genera la GUI con su contador. El mismo en todos los reintentos y en `REQ`, `ACK`, `RES`, `FIN` |
| **Huella** | `{origen, nodo, sello, rastro}` (`foliado.huella()`). `nodo` = nodo de entrada |
| **Sello** | `sha256(origen \| folio \| código del gen \| repr(float(a)) \| repr(float(b)))`. Usa el código del gen (`SUM`), así vale para todo el evento. `7` y `7.0` sellan igual |
| **Rastro** | Lista de pasos `[hash8, nombre, paso]`, paso ∈ `REQ`, `ACK`, `RES`, `FIN`; máx. 32 (`MAX_RASTRO`). La `ruta` del sobre es la trayectoria física |
| **ACK** | `X_ACK`, publicado al recibir, **antes de encolar**, con su paso en el rastro |
| **Mínimo de ACK** | Por operación, `ACUSES_MIN_DEFECTO` 2, editable en vivo en la GUI |
| **Evento** | Fases `INICIO` → `CONFIRMADO` → `PROCESADO` → `FINALIZADO` |
| **Esperadas / ausentes** | Esperadas = madres vivas con el gen al iniciar (por latidos). La ventana de confirmación cierra a los `VENTANA_ACUSES` (1.5 s) **o antes si acusaron todas**; entonces se anotan las ausentes |

Además, los folios administrativos: `O-<hash8 del gestor>-<n>` (órdenes) y
`P-<hash8 de la madre>-<n>` (pedidos de genes).

### 9.2 Reglas de atención

**Madre** (`Rondas.rx_req()`, `rx_fin()`): atiende solo si (1) el código es de un gen activo
(si no, `IGNORA`); (2) en el `REQ`, `huella.origen` = origen del sobre y el sello recalculado
coincide (si no, `DROP huella inválida` y no acusa; cuenta en `rondas.invalidas`); (3) la ronda
`(código, folio, intento)` no está terminada; (4) tras un `X_FIN`, un `REQ` tardío de ese folio
ya no se acusa.

**GUI** (`Interfaz.procesar()`, `_huella_ajena()`): muestra un `ACK`/`RES` solo si el folio es
suyo, `huella.origen` es su hash y el sello es el que ella generó. Lo demás suma a "ajenas
ignoradas".

### 9.3 Ciclo de vida en la GUI

1. `solicitar()` → `_publicar_req()`: `X_REQ` (fase INICIO).
2. Cada `X_ACK` del intento vigente suma; al llegar al mínimo, `_confirmar()` (CONFIRMADO). Un
   `RES` que llega antes de confirmar se **retiene** y se usa al confirmar (solo si es del mismo
   intento).
3. Primer `X_RES` válido → `_aceptar()` (PROCESADO). Uno repetido es `DUPLICADA`; uno de un
   intento viejo, `TARDÍA`.
4. `_finalizar()` publica `X_FIN` (FINALIZADO) con `estado` resuelta o fallida, acuses y
   ausentes. Si no sale (sin enlace), se reenvía al reconectar.
5. Sin mínimo en la ventana, o sin resultado a tiempo: reintento con el **mismo folio** e
   `intento + 1`, hasta `MAX_INTENTOS` (3); luego `FALLIDA`. Durante un failover no se gastan
   intentos.

---

## 10. Respuesta única: rondas, elección HRW y relevo (`madre/rondas.py`)

- Una ronda por `(código, folio, intento)`. Estados: `esqueleto` (llegó un ACK antes que el REQ),
  `en_cola`, `titular`, `respaldo`, `resuelta`, `superada` (llegó un intento posterior), `cerrada`
  (llegó `X_FIN`).
- La ronda **fija el gen con el que acusó** (`SUM@1.0`) y lo usa hasta el final: una sustitución
  a media ronda no mezcla versiones. Al terminar, suelta la referencia (para que el gen viejo
  pueda liberarse).
- **Trabajador**: espera `VENTANA_ELECCION` (0.5 s) para juntar acuses y ordena a los acusadores
  con `hashes.ranking(acusadores, folio, intento)` (HRW: `sha256(célula|folio|intento)`). Rango 0
  = **titular**: calcula y responde. Rango r = **respaldo**: si a los `r · RELEVO` (1.5 s) nadie
  respondió, toma el relevo. Antes de publicar vuelve a revisar: si ya hubo respuesta, la suya se
  **suprime** (`LIBERADO`).
- Si el `X_ACK` propio no sale (sin enlace), la madre se retira de esa ronda (`RETIRADA`): si se
  contara sola podrían quedar dos titulares.
- Rondas más viejas que `RONDAS_VIGENCIA` (120 s) se purgan en cada latido.

---

## 11. Genes y carga dinámica (`madre/genes.py`, `madre/almacen.py`, `comun/microservicios.py`)

### 11.1 El gen en disco

`microservicios/<CÓDIGO>/<versión>/` con `manifiesto.json` (`codigo`, `version` `\d.\d`,
`nombre`, `archivo: servicio.py`, `sha256`, `interfaz: 1`, `pruebas: [[a, b, esperado], …]`,
`descripcion`) y `servicio.py` (`SERVICIO`, `VERSION`, `calcular(a, b) → (resultado, error)`).

| Gen | Qué hace |
|---|---|
| `SUM 1.0`, `SUB 1.0`, `MUL 1.0`, `DIV 1.0` | Las cuatro operaciones en punto flotante (`DIV` devuelve error si `b = 0`) |
| `SUM 2.0` | Suma decimal exacta (`Decimal(repr(a)) + Decimal(repr(b))`): `0.1 + 0.2 = 0.3` |
| `SUM 9.9` | **Manipulado a propósito**: su programa se cambió después de firmarlo; nadie lo carga |

### 11.2 Almacén propio y tres vías de llegada

Cada madre: `datos/celulas/<nombre>-<hash8>/genes/<CÓDIGO>/<versión>/`. **Todo** gen pasa por
ahí antes de cargarse (requisito M1). Vías: **banco local** (`--genes`), **inyección**
(`GEN_INYECTA`, el programa viaja dentro del mensaje), **entrega** (`GEN_ENTREGA` a un
reemplazo). Bitácora: `GEN_ESCRITO` con la vía y la ruta.

### 11.3 Ciclo de vida (requisito M5)

| Paso | Qué hace | Si falla |
|---|---|---|
| Localizar | `almacén/CÓDIGO/versión/`, ruta confinada al almacén (`FueraDelAlmacen`) | no existe |
| Validar | Esquema del manifiesto, `servicio.py` ≤ `GEN_MAX_BYTES` (32 KiB), `sha256` real = declarado. Sin ejecutar nada | `validar: sha256 no coincide` |
| Cargar | `spec_from_file_location` + `module_from_spec`, y se ejecutan **los mismos bytes validados** (`compile` + `exec`, no se relee el archivo). Módulo `gen_<COD>_<ver>_<sha8>_<n>`, **no** se registra en `sys.modules`. Exige `SERVICIO`, `VERSION`, `calcular` | interfaz inválida |
| Autoprueba | Corre los vectores `pruebas` del manifiesto | autoprueba falló |
| Activar | Bajo el lock del genoma, `activos[código] = gen`; `CEL_LAT` inmediato | — |
| Descargar | Lo saca de `activos` (deja de acusar), **borra su copia del disco** y vigila con `weakref` + `gc.collect()` que salga de memoria (`GEN_LIBERADO`) a los 0.2, 1 y 3 s; si una ronda aún lo retiene, sigue cada 3 s hasta `GEN_VIGILANCIA` (130 s) con un solo `GEN_EN_USO` | — |

`genes.ejecutar()` exige operandos numéricos finitos (no `bool`), un resultado finito, y
convierte cualquier excepción del gen (incluso `sys.exit()`) en una respuesta con error.

### 11.4 Sustituir con reversión

La versión nueva se escribe, valida, carga y autoprueba **antes** de tocar la vieja. Si falla, la
vieja sigue activa (`GEN_RECHAZADO … sigue activo SUM@2.0`); si pasa, el cambio es atómico
(`GEN_SUSTITUIDO`) y la vieja se descarga.

---

## 12. Gestor (`gestor/`)

### 12.1 No es un orquestador

Solo actúa cuando el administrador pulsa un botón; no guarda topología (la reconstruye de
latidos); la madre destino decide si instala; nunca ve un `X_REQ`; la regeneración es de las
madres; hay uno por nodo y ninguno manda sobre otro.

### 12.2 Base de datos (`gestor/bd.py`)

- `microservicio(codigo, version, nombre, descripcion, manifiesto, fuente, sha256_declarado,
  sha256_real, importado)`.
- `orden(folio, accion, destino, destino_nombre, codigo, version, estado, detalle, ms, creada,
  cerrada)`.
- Un gen con sha256 real ≠ declarado se marca ✘ y no se ofrece como fuente.

### 12.3 Órdenes

Folio `O-…`, broadcast, solo la madre `destino` las atiende y solo de un `GESTOR`. Contesta
`GEN_ACK` antes de trabajar y `GEN_RES` al terminar; una orden repetida no se ejecuta dos veces
(se reenvía el `GEN_RES` anterior). Estados: `enviada → recibida → ok | rechazada | sin respuesta
| sin resultado`, o `no salió` si el gestor no tenía enlace. Plazos: `GEN_ACK_TIMEOUT` 2 s,
`GEN_RES_TIMEOUT` 10 s.

- **Distribuir** (`Gestor.distribuir()`): en cada nodo vivo, a cada operación que le falte se le
  asigna una madre vacía (en orden de nombre: M1 → SUM, M2 → SUB…) con la versión base (`SUM
  1.0`). Cuenta como presentes las caídas que esperan reemplazo y los reemplazos naciendo; no
  cuenta a las mudas.
- **Sustituir en todas**: el cambio de versión a cada madre viva con ese código y otra versión.

### 12.4 Topología (`gestor/topologia.py`)

Fuentes: `NODO_LAT` (nodos y enlaces reales), `CEL_LAT` (células, tipo, nodo, genes, generación,
reemplaza, mudo), `CEL_ADIOS` (se quita al instante), `CLON_AVISO`/`CLON_LISTO` (regeneración en
curso), `TOPO_REQ` → `TOPO_RES` (consulta inmediata). Lo que no late en 6 s se dibuja **caído**
(rojo) `CAIDA_VISIBLE` (8 s); una **madre** caída sigue en rojo hasta que aparece su reemplazo (o
`ESPERA_REEMPLAZO`, 60 s). Al reconectarse el gestor, `tregua()` evita marcar caídas falsas.

Diagrama: nodos en círculo con sus enlaces, células alrededor, madres coloreadas por gen con su
versión, vacías punteadas, mudas tachadas, reemplazos con insignia `r1`, `r2`, "naciendo" con
contorno azul. Arriba, la disponibilidad por código y la píldora de regeneración ("nivel ok · sin
clonar").

### 12.5 Pedidos de genes (`madre/pedidos.py`, `comun/pedidos.py`)

`GEN_PIDE` con folio `P-…`. Pueden entregar las madres que lo tienen **activo** (lo leen de su
disco) y los gestores que lo tienen **íntegro** en su BD. Cada proveedor espera un retardo
derivado de su hash (≤ `ENTREGA_RETARDO_MAX`, 0.4 s) y se calla si ya vio una entrega para ese
pedido. La que pidió toma la primera que **valide** (mismo sha); `PLAZO_PEDIDO` 2 s,
`REINTENTOS_PEDIDO` 3.

---

## 13. Autorrecuperación (`madre/regeneracion.py`)

### 13.1 Estado de cada madre (nadie lleva uno central)

- **Directorio** de madres (por `CEL_LAT`): nombre, nodo, genes con sha8, generación, reemplaza,
  mudo, último latido (`visto`) y primer latido oído (`desde`).
- **Nodos** vivos (por `NODO_LAT`).
- **Pérdidas**: `pendiente`, `en curso` (hubo `CLON_AVISO`), `resuelta`, `descartada`.

### 13.2 La regla (`Regeneracion.revisar()`, cada `REVISION_REGENERACION` = 0.5 s)

1. **Detectar** (`_detectar`): madre sin latido en `LATIDO_CADUCIDAD` (6 s) y sin `CEL_ADIOS` →
   pérdida, con sus genes, nodo y generación. Puede tocarle turno 2 s después (6 + `LATIDO`).
   Si el que muere es un reemplazo que aún no estaba listo, **no** es otra pérdida: se reintenta
   la misma.
2. **Vencer** (`_vencer`): un aviso sin `CLON_LISTO` en `PLAZO_CLON` (15 s) → si el reemplazo
   late, se da por resuelta; si no, el clonador **termina a su hijo** y se reintenta (máx.
   `MAX_REINTENTOS_CLON` = 2 reintentos, 3 intentos en total); luego se descarta.
3. **Turno** (`_turno`): si hay una pérdida `en curso` en el sistema, nada; si no, tras
   `PAUSA_REGENERACION` (2 s) desde la última, va la pendiente de **menor hash** (todas eligen la
   misma).
4. **Topes** (`_topes`) antes del ranking: ya hay un reemplazo vivo de esa pérdida; `MAX_MADRES`
   (40); `MAX_POR_GEN` (8). Si alguno falla → `NO_CLONA` y se descarta.
5. **Clonador**: `hashes.ranking(aptas, "clon:<hash de la pérdida>", intento)`. Rango 0 lanza;
   rango r espera `r · RELEVO_CLON` (3 s) y solo lanza si no oyó un `CLON_AVISO`.
6. **Aptas** (`_aptas`): vivas, no mudas, generación < `MAX_GENERACION` (3), con al menos
   `LATIDO_CADUCIDAD` de antigüedad (no recién llegadas: su ranking podría diferir) y con cupo
   (< `MAX_CLONES_MINUTO` = 2 lanzamientos en 60 s).
7. **Avisar y lanzar** (`_lanzar`): publica `CLON_AVISO`; **si no sale, no lanza**. Lanza
   `python -m madre --nodo … --nombre M1-N2·r1 --reemplaza <hash> --perdida M1-N2 --generacion 1
   --copiar SUM@2.0:765cbef9` en el **nodo de la perdida** si sigue vivo, si no en el nodo vivo
   con **menos madres**.
8. **Copiar** (`madre/copia.py`): el reemplazo nace vacío, pide cada gen con `GEN_PIDE`, lo
   escribe en su disco, lo valida y lo carga. Si nadie entrega, usa el **banco local solo si el
   sha coincide**. Publica `CLON_LISTO` con `fuentes` y `faltan`.
9. **Cerrar** (`rx_listo`): con `CLON_LISTO` la pérdida queda resuelta en todas.
10. **Alto** (`_quizas_nivel_ok`): sin pérdidas pendientes ni en curso → `NIVEL_OK` y no se clona
    nada más.

Otros casos: `REVIVIO` (la pérdida pendiente vuelve a latir: solo estaba lenta), `ADIOS` (se
despide después de darla por perdida), retiro del reemplazo en curso por el administrador (se
descarta). Al **reconectarse** una madre, `conectada()` le da a todas un plazo nuevo y reinicia su
propia antigüedad (si no, tras un hueco daría por perdidas a todas).

### 13.3 Nivel requerido: reemplazo 1 a 1

No hay un número de réplicas que se rellene. Cada **pérdida** pide **un** reemplazo con los genes
que tenía. Una baja o un retiro hechos con el gestor no son pérdidas: son el nuevo nivel.

### 13.4 Ocho límites contra el cáncer (cada uno en un método)

| # | Límite | Método |
|---|---|---|
| 1 | Solo por pérdida (no por baja, retiro, carga ni "faltan para N") | `_detectar`, `rx_adios` |
| 2 | Uno a uno: a lo más un reemplazo vivo por pérdida (y el hijo vencido se termina) | `_topes`, `_vencer` |
| 3 | Un clonador por pérdida: HRW + `CLON_AVISO` | `_turno`, `_lanzar` |
| 4 | El reemplazo en curso cuenta hasta que aparece o caduca | inicio de `_turno` |
| 5 | Gradual: una regeneración a la vez + pausa de 2 s | inicio de `_turno` |
| 6 | Topes duros: 40 madres, 8 por código | `_topes` |
| 7 | Telómeros: generación ≥ 3 no clona | `_aptas` |
| 8 | Cupo: 2 lanzamientos por madre por minuto | `_aptas`, `_cupo` |

### 13.5 El lanzador (`madre/lanzador.py`)

Proceso **desacoplado** (`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`): si el clonador muere, el
reemplazo sigue. Usa el intérprete base (no el del `.venv`) para que el PID registrado sea el
real. Cada lanzamiento deja `run/<nombre>-<pid>.json` (pid, hora de inicio, comando, a quién
reemplaza); el panel lo usa para mostrarlos y "Detener todo". Antes de terminar un PID se
comprueba su hora de creación con `ctypes` (Windows recicla PIDs).

---

## 14. Disponibilidad por latidos

- Toda célula que late publica `CEL_LAT` al conectarse y cada `LATIDO` (2 s); la madre, además,
  justo después de activar o dar de baja un gen.
- La GUI cuenta "vivas" por código con los latidos (sin latido ni acuse en 6 s = muerta) y
  deshabilita el operador si hay menos que el mínimo de ACK.
- Las madres usan los mismos latidos para su directorio; el gestor, para la topología.

---

## 15. Identificadores (`comun/hashes.py`)

- Cada entidad genera su hash SHA-256 al arrancar con `tipo | datos | host | pid | time_ns |
  contador | 128 bits aleatorios`: nadie asigna identidades. Los mensajes, igual.
- `corto(h)` = 8 primeros caracteres, solo para mostrar.
- `ranking(celulas, clave, intento)` ordena por `sha256(célula|clave|intento)`: lo usan la
  elección de titular (clave = folio) y la de clonador (clave = `clon:<hash>`).

---

## 16. Failover (`celula/base.py` → `_recuperar()`)

1. Reintenta `REINTENTOS_MISMO_NODO` (2) veces con su nodo, 1 s entre intentos y `connect()` de
   `REINTENTO_TIMEOUT` (0.5 s): en Windows un puerto cerrado tarda ~2 s en rechazar.
2. Rota por los demás candidatos (de `BIENVENIDA` y `PARES`).
3. Si nadie responde en una vuelta, backoff 1 → 8 s y otra vuelta.
4. Conserva su hash: para el sistema es la misma célula. No regresa a su nodo original si
   revive.

---

## 17. Concurrencia

| Proceso | Hilos |
|---|---|
| Nodo | aceptador, supervisor, latido, marcadores, y lector + escritor por enlace |
| Célula base | conector, latido, lector + escritor de su enlace |
| Madre | + trabajador de rondas, programador de respaldos, programador de la madre (regeneración, vigilancia de genes, pedidos), hilo de copia (reemplazo) |
| GUI | + revisión de operaciones; Tk en el hilo principal (cola + `after(100)`) |
| Gestor | + programador de órdenes; Tk en el hilo principal |

Locks: `Nodo._lock` (RLock, tablas), `Celula._lock`, `Rondas._lock`, `Regeneracion._lock`,
`Ordenes._lock`, `Gestor._lock_ordenes`, `Interfaz._lock_ops`, el lock del genoma y
`Madre._lock_instalar` (instalaciones en serie). Las llamadas lentas (publicar, lanzar, cancelar)
se hacen **fuera** del lock.

---

## 18. Tolerancia a fallas

| Falla | Mecanismo |
|---|---|
| Madre muda o lenta | Esperadas/ausentes; basta el mínimo de ACK |
| No se alcanza el mínimo | Reintento con el mismo folio hasta 3 intentos; luego `X_FIN` fallida |
| La titular calla después de acusar | Respaldos escalonados (`r · 1.5 s`); sigue siendo una respuesta |
| Mensaje alterado | El sello no coincide: la madre no acusa; la GUI lo ignora |
| Cae un nodo | Failover de sus células; la malla sigue; sin gastar reintentos |
| Mueren una o varias madres | Regeneración 1 a 1, una a la vez, con copia de genes |
| Muere el clonador antes de avisar | El rango 1 regenera a los 3 s |
| Muere el reemplazo antes de estar listo | Se reintenta la misma pérdida |
| El reemplazo tarda más de 15 s | El clonador lo termina y se reintenta (nunca quedan dos) |
| Muere el nodo de la perdida | El reemplazo va al nodo vivo con menos madres |
| Nadie tiene el gen | Banco local si el sha coincide; si no, `CLON_LISTO` con `faltan` |
| Gen manipulado | sha256 antes de ejecutar; la versión vieja sigue |
| Gen que lanza excepción o `sys.exit()` | Respuesta con error; la madre sigue |
| Se cierra el gestor o el panel | Nada depende de ellos |

---

## 19. Pruebas

### 19.1 Suite automatizada

`uv run python -m unittest discover -s tests -t .` levanta el sistema completo **en el mismo
proceso** (nodos, madres, GUIs y gestor sin ventanas), con tiempos acortados por `mock.patch`. La
regeneración usa un lanzador inyectable que crea los reemplazos en proceso
(`Sistema(regenerar=True)` en `tests/apoyo.py`).

| Archivo | Pruebas | Qué cubre |
|---|---|---|
| `test_protocolo` | 19 | Framing, líneas inválidas, tope de línea, `NaN`, `1e999`, anidamiento, drenaje |
| `test_mensajes` | 15 | Sobre, `HOLA`, validaciones |
| `test_hashes` | 10 | Unicidad y ranking HRW |
| `test_enlace` | 7 | Cola de escritura, cierre, `LENTO` |
| `test_formato` | 6 | Formato de números en la GUI |
| `test_bitacora` | 5 | Bitácora |
| `test_vistos` | 4 | Registro de vistos |
| `test_malla` | 9 | Gossip, 5.º nodo, marcado simultáneo, autoconexión, nodo que vuelve, nodo detenido al marcar, BIENVENIDA tardía |
| `test_broadcast` | 8 | Inundación, TTL, duplicados, horizonte dividido |
| `test_flujo` | 33 | Cuatro operaciones con un RES por folio, ráfagas, relevo, reintentos, huella inválida, `X_FIN`, muda en ausentes, failover, baja y sustitución en vivo, ajenas, sello alterado, sin enlace |
| `test_foliado` | 15 | Folio, sello, rastro, validación |
| `test_genes` | 21 | Almacén, validar, cargar, autoprueba, activar, sustituir con reversión, `weakref`, gen retenido |
| `test_microservicios` | 14 | Cada gen real pasa sus pruebas; `SUM 9.9` se rechaza; `SUM 2.0` da `0.3` |
| `test_gestor` | 28 | BD, topología, distribuir, alta, baja, sustituir, retiro, orden a célula muerta, pedidos y entregas, sistema sin gestor |
| `test_regeneracion` | 19 | Una pérdida → un reemplazo; tres en secuencia; retiro y baja no regeneran; relevo del clonador; topes, telómeros, cupo; reconexión; hijo vencido; aviso que no sale |
| `test_panel` | 4 | Los dos modos y que el panel no abre gestores |
| **Total** | **217** | |

Resultado final: **217 en verde tres veces seguidas** (190.4 s, 192.7 s y 193.8 s); `ruff check
.` limpio.

### 19.2 Verificación en vivo (17 de noviembre de 2026)

Procesos reales (4 nodos con ventana → 5, 16 madres vacías, 4 GUIs, gestor G-N1), operados como
lo haría el usuario: **30 de 30 revisiones**; en todas las bitácoras **0 `ERROR`, 0 `Traceback`,
0 respuestas duplicadas**; **10 `CLON_AVISO` = 10 reemplazos listos**. Las bitácoras y las
figuras del reporte son de esa corrida (`docs/capturas/`).

Tras la auditoría se hizo además un humo real sin ventanas (2 nodos, madres reales): 1 aviso = 1
reemplazo que copió `SUM@1.0` de otra madre, `NIVEL_OK`, 0 `ERROR`, y la cancelación real de un
hijo vencido.

### 19.3 Bugs encontrados en la verificación en vivo (§13 del reporte)

| # | Síntoma | Corrección |
|---|---|---|
| 1 | Bajo carga, dos titulares | Las pruebas usan la `VENTANA_ELECCION` real (0.5 s); la carrera sigue posible (limitación 3) |
| 2 | `ENTREGA` repetida en la línea de tiempo | El gestor muestra solo la primera |
| 3 | El diagrama dejaba de redibujarse | Tamaño pedido mientras no hay real |
| 4 | `invalid command name` al cerrar | `estilo.cerrar(raiz)` cancela los `after` |
| 5 | El mínimo de ACK de una GUI cambiaba otra | `StringVar`/`BooleanVar` con dueño explícito |
| 6 | La quinta madre de un nodo se cortaba en el panel | Fichas en varios renglones |

### 19.4 Auditoría final (29 defectos + 4 menores, todos corregidos)

Ninguno daba un resultado aritmético incorrecto ni lo provoca la demo. Por área:

- **Regeneración**: madre que tras más de ~8 s sin enlace clonaba sanas; hijo vencido que
  quedaba vivo junto al del reintento; lanzaba sin `CLON_AVISO` publicado; `CEL_ADIOS` después de
  darla por perdida; pausa gradual mal contada; `nodo_perdida` sin validar.
- **Madre**: temporizador de pedido perdido; `Ordenes` sin lock; gen con `sys.exit()` o error
  raro; ACK que no salió y aun así competía; nombre no-texto en la ronda; `GEN_LIBERADO` que
  dejaba de vigilarse.
- **GUI**: reintentos gastados sin enlace; `X_FIN` perdido sin enlace; `RES` retenido de otro
  intento; fases de un evento fallido; resultado que pisaba lo tecleado; `=` repetido; cambio de
  operador; retroceso en notación científica.
- **Gestor**: reemplazo muerto antes de listo bloqueaba `NIVEL_OK`; entrega propia ausente de la
  línea de tiempo; caídas falsas sin enlace; "Distribuir" duplicaba durante una regeneración y
  contaba mudas; carrera de vencimientos; revivida marcada como reemplazada.
- **Nodo, protocolo y panel**: anidamiento extremo y `1e999`; reemplazos por (PID, inicio);
  contadores de la célula con lock; enlace duplicado que perdía mensajes en vuelo; `BIENVENIDA`
  tardía con `DESCONEXION` falsa; nodo detenido con un enlace a medio abrir.

---

## 20. Decisiones de diseño

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Madre genérica que carga genes con `importlib` | Un programa por servicio | Es lo que pide §5.2 |
| Todo gen pasa por el disco propio de la madre | Cargar directo del mensaje | Cumple M1 y deja evidencia física |
| sha256 antes de ejecutar y cargar los bytes validados | Confiar en el archivo | `SUM 9.9` nunca corre |
| El programa dentro de `GEN_INYECTA` | Ruta compartida | Todo viaja por el Campo de Datos |
| Regeneración 1 a 1 | N réplicas por servicio | Lo pidió el usuario |
| Clonador por HRW + aviso | Votación | Acuerdo sin rondas de mensajes |
| El reemplazo copia genes por la red | Que el clonador le pase los suyos | El clonador puede no tener ese gen |
| Un gestor por nodo, que el usuario levanta | Gestor único automático | No es un orquestador ni punto único |
| Dos modos de arranque (vacía / con servicios) | Solo uno | Lo pidió el usuario; mismo funcionamiento después |

---

## 21. Diferencias con lo visto en clase

Para el foliado se usaron las definiciones del enunciado (huella, evento, mínimo de ACK). Se
conservan las dos diferencias del segundo parcial: **latidos además de los acuses** (ahora
indispensables: de ellos salen la topología y la detección de pérdidas) y **una sola respuesta
por elección** en vez de que todas respondan (la deduplicación en la GUI queda como última capa).

---

## 22. Reutilización y originalidad

Código propio. Lo reutilizado es el **segundo parcial del mismo autor** (base obligatoria del §4
del enunciado): nodo, célula base, GUI, protocolo, mensajes, hashes, vistos y bitácora,
adaptados. `servidor/` y su `calculo.py` desaparecieron: la aritmética vive en los genes. La
etiqueta `parcial-2` del repositorio marca el punto de partida.

---

## 23. Limitaciones y trabajo futuro

1. Una "pérdida" que solo estaba lenta y vuelve después de lanzado su reemplazo deja una de más
   (los topes lo acotan).
2. Partición de red: cada lado podría regenerar las del otro (los topes acotan, no evitan).
3. Carrera en la elección (heredada): un ACK que llega después de 0.5 s puede dar dos titulares;
   la GUI acepta una sola respuesta por folio.
4. Sin autenticación: un proceso podría presentarse como `GESTOR` o usar el folio de otra GUI. El
   sha256 protege la integridad del gen, no su origen.
5. Un gen bien firmado pero malicioso se ejecuta (faltaría aislarlo en otro proceso).
6. Colisión de folios entre dos GUIs: mismo prefijo de 8 hex (~1 en 4×10⁹ por par), y el sello
   seguiría siendo distinto.
7. Detección en ~6 s: compromiso entre reaccionar rápido y no confundir una pausa con una muerte.
8. Enlace duplicado: queda una ventana de microsegundos en que lo que un nodo difunde hacia ese
   vecino se pierde por ese enlace (con ≥ 3 nodos llega por otro camino). *No está en el
   reporte.*

Trabajo futuro: firma de genes con llave y autenticación de gestores; gen en proceso aislado;
detectar particiones antes de regenerar.

---

## 24. Constantes (`comun/config.py`, tiempos en segundos)

| Constante | Valor | Para qué |
|---|---|---|
| `TTL_INICIAL` / `TTL_MAX` | 8 / 16 | Saltos de un mensaje / tope |
| `VISTOS_VIGENCIA` / `VISTOS_MAX` | 60 / 100,000 | Registro de vistos |
| `LATIDO` / `LATIDO_CADUCIDAD` | 2 / 6 | Latidos y muerte por silencio |
| `VENTANA_ACUSES` | 1.5 | Ventana de confirmación en la GUI |
| `VENTANA_ELECCION` | 0.5 | Espera de la madre antes de ordenar acusadores |
| `RELEVO` | 1.5 | Separación entre respaldos |
| `MARGEN_RESULTADO` | 2 | Holgura del plazo de resultado en la GUI |
| `MAX_INTENTOS` / `ACUSES_MIN_DEFECTO` | 3 / 2 | Foliado |
| `HOLA_TIMEOUT` / `BIENVENIDA_TIMEOUT` / `CONECTAR_TIMEOUT` | 5 / 3 / 3 | Conexión |
| `BACKOFF_MIN` / `BACKOFF_MAX` / `SUPERVISOR` | 1 / 8 / 2 | Reconexión de nodos |
| `REINTENTOS_MISMO_NODO` / `REINTENTO_TIMEOUT` | 2 / 0.5 | Failover |
| `MAX_LINEA` / `COLA_ENLACE_MAX` / `DRENAJE` | 64 KiB / 5,000 / 2 | Transporte |
| `RONDAS_VIGENCIA` | 120 | Purga de rondas |
| `GEN_MAX_BYTES` | 32 KiB | Tope de `servicio.py` |
| `GEN_LIBERACION` / `GEN_VIGILANCIA` | (0.2, 1, 3) / 130 | Vigilancia de un gen descargado |
| `GEN_ACK_TIMEOUT` / `GEN_RES_TIMEOUT` | 2 / 10 | Órdenes del gestor |
| `PLAZO_PEDIDO` / `REINTENTOS_PEDIDO` / `ENTREGA_RETARDO_MAX` | 2 / 3 / 0.4 | Pedidos de genes |
| `CAIDA_VISIBLE` / `ESPERA_REEMPLAZO` | 8 / 60 | Dibujo de caídas en el gestor |
| `REVISION_REGENERACION` | 0.5 | Revisión de cada madre |
| `RELEVO_CLON` / `PLAZO_CLON` / `MAX_REINTENTOS_CLON` | 3 / 15 / 2 | Clonador |
| `PAUSA_REGENERACION` | 2 | Gradual |
| `MAX_MADRES` / `MAX_POR_GEN` / `MAX_GENERACION` / `MAX_CLONES_MINUTO` | 40 / 8 / 3 / 2 | Anti-cáncer |

El anexo de constantes del reporte (A en el PDF, B en el `.md`) lista las heredadas y las nuevas principales; `DRENAJE`, `GEN_LIBERACION`,
`GEN_VIGILANCIA`, `CAIDA_VISIBLE`, `ESPERA_REEMPLAZO` y las de conexión no están ahí (no son
necesarias para entender el diseño).

---

## 25. Comandos

```
uv sync                                            # una vez
uv run python -m panel                             # demo
uv run python -m unittest discover -s tests -t .   # pruebas (~3 min)
uv run ruff check .                                # lint
uv run python -m herramientas.firmar --verificar   # integridad del banco de genes
uv run python docs/md_a_docx.py                    # REPORTE_TECNICO.md → .docx
```

A mano (lo mismo que lanza el panel):

```
uv run python -m nodo --puerto 5001 --nombre "Nodo 1" --semillas 127.0.0.1:5002
uv run python -m madre --nodo 127.0.0.1:5001 --nombre M1-N1 [--genes SUM@1.0] [--mudo]
uv run python -m interfaz --nodo 127.0.0.1:5001 --nombre GUI-1
uv run python -m gestor --nodo 127.0.0.1:5001 --nombre G-N1
```

---

## 26. Datos para citar

| Dato | Valor | Fuente |
|---|---|---|
| Configuración de la demo | 4 nodos (luego 5), 4 GUIs, 16 madres, 1 gestor | §3.2, §12 del reporte |
| "Distribuir" | 16 altas `ok` en 270 ms | §12 |
| Alta de `MUL 1.0` en madre vacía | disco → activo en ~10 ms (carga 0.4 ms) | §6.6 |
| Duración de un evento | ~0.5 s (la ventana de elección); el recorrido, milisegundos | §5.4 |
| De la caída al nivel recuperado | ~8 s: 6 de detección, 2 de turno, 0.3 de copia | §8.6 |
| Verificación en vivo | 30/30; 0 `ERROR`, 0 `Traceback`, 0 duplicadas; 10 avisos = 10 reemplazos | §12 |
| Pruebas | 217 ×3 (190.4, 192.7, 193.8 s) | §11 |
| Reporte | 29 páginas (PDF entregado) | `Reporte_Tecnico_Calculadora_ADS.pdf` |
| Video | 11 escenas, ~12 min | `GUION_VIDEO.md` |

---

## 27. Guía para auditar el reporte

### 27.1 Qué revisar y contra qué

| Sección del reporte | Contra qué compararla aquí | En el código |
|---|---|---|
| §2 Matriz | §4 a §13 de este resumen | Cada función nombrada en la columna "Implementación" existe |
| §4.1–4.5 Heredado | §5, §6, §8, §10, §16 | `nodo/nucleo.py`, `celula/base.py`, `madre/rondas.py` |
| §4.4 Códigos | §7 | `comun/codigos.py` |
| §5 Foliado | §9 | `comun/foliado.py`, `interfaz/nucleo.py` |
| §6 Genes | §11 | `madre/genes.py`, `madre/nucleo.py` (`_instalar`, `_descargar`) |
| §7 Gestor | §12 | `gestor/nucleo.py`, `gestor/bd.py`, `gestor/topologia.py` |
| §8 Autorrecuperación | §13 | `madre/regeneracion.py`, `madre/copia.py`, `madre/lanzador.py` |
| §9 Tolerancia | §18 | — |
| §11 Pruebas | §19.1 | `tests/` (contar `def test_` por archivo) |
| §13 Bugs | §19.3, §19.4 | `ROADMAP.md` (registro) |
| §14.2 Limitaciones | §23 | — |
| Anexo A (PDF) / B (`.md`) | §24 | `comun/config.py` |

Preguntas útiles al leer cada sección: ¿el número coincide con `config.py`? ¿El nombre de la
función existe? ¿El orden de los pasos es el del código? ¿La bitácora citada usa etiquetas que el
código de verdad escribe (`GEN_ACTIVO`, `CLON_AVISO`, `NIVEL_OK`…)?

### 27.2 Ya revisado y corregido (25 de noviembre)

Se cotejó el reporte completo contra el código. Coinciden las constantes, los códigos, los
cuerpos de los mensajes, el sello, el algoritmo de regeneración, los ocho límites, los conteos de
pruebas por archivo y el comando del reemplazo. Se corrigieron tres detalles, sin cambiar la
extensión:

1. §6.4 "Descargar": decía que el gen se borra del disco **después** de confirmar la liberación;
   el código lo borra antes y luego vigila la memoria.
2. §8.3 paso 2: `EN_ESPERA` lo escribe el **gestor** (línea de tiempo), no las madres.
3. §7.3: faltaba el estado `no salió` de una orden.

### 27.3 Lo que queda a tu criterio

- En la portada del PDF solo falta la liga del video.
- La matriz (§2) ya no lleva minutos: su columna "Escena" remite a las escenas de
  `GUION_VIDEO.md`. Conviene revisar que cada requisito se vea de verdad en esa escena.
- §1.4 y §12 dicen que las bitácoras y figuras son de la corrida del 17 de noviembre, anterior a
  la auditoría. Los cambios de la auditoría no alteran lo que se ve en esas bitácoras, pero si
  quieres que coincidan al 100 % con el código final, el video sirve como evidencia nueva.
- §16 menciona la etiqueta `parcial-2`: existe en tu repositorio local, pero aún no está en
  GitHub (`git push origin parcial-2`).
- El límite 8 de §23 (ventana de microsegundos del enlace duplicado) no está en el reporte; es
  muy menor.
