# Resumen técnico del proyecto Calculadora ADS

Documento de referencia con todo lo técnico del proyecto en un solo lugar. Sirve para pulir el
reporte o para preparar la exposición. El reporte (`REPORTE_TECNICO.md`) sigue siendo la versión
oficial, con las bitácoras reales y las figuras.

---

## 1. Qué es

Es la calculadora del primer parcial pasada a una **arquitectura ADS** (Autonomous Decentralized
System). En el primer parcial había N calculadoras, N servidores y un middleware central por el que
pasaba todo. Si el middleware se caía, se caía el sistema. Ahora no hay nada central.

- Hay un **Campo de Datos** formado por nodos en malla completa.
- Las **células** (GUIs y servidores) se conectan a un nodo y publican mensajes sin destinatario.
- Cada mensaje lleva un **Código de Contenido** (`SUM_REQ`, `SUM_RES`, …) y cada célula toma solo
  los que le interesan.
- Ninguna pieza es indispensable. Se puede caer un nodo, un servidor o el panel y el sistema sigue.

Configuración mínima del enunciado: 4 nodos en malla completa y 5 células por nodo (1 GUI y 4
servidores, uno por operación), 20 células en total.

---

## 2. Lo que se usó

### 2.1 Lenguaje y entorno

| Cosa | Detalle |
|---|---|
| Lenguaje | Python 3.14 (funciona desde 3.12, según `pyproject.toml`) |
| Dependencias | Ninguna. Solo librería estándar |
| Sistema operativo | Windows 11, todo corre en `127.0.0.1` por defecto |
| Cómo se ejecuta | `py -m <paquete>` desde la carpeta del proyecto |
| Lint | `ruff` (configurado en `pyproject.toml`, línea de 100 columnas). Solo para desarrollo |
| Control de versiones | Git, repositorio público en GitHub |
| Base de datos | Ninguna. El enunciado no pide persistencia |

Se renunció a propósito a los puntos extra de Java.

### 2.2 Módulos de la librería estándar y para qué se usó cada uno

| Módulo | Para qué |
|---|---|
| `socket` | Conexiones TCP entre nodos y entre células y nodos |
| `threading` | Hilos (lector y escritor por enlace, aceptador, supervisor, trabajador, reloj), `Lock`, `RLock` y `Condition` |
| `queue` | Cola de escritura de cada enlace, cola de trabajo del servidor y puente red → ventana |
| `json` | Serializar los mensajes (NDJSON, con `allow_nan=False`) |
| `hashlib` | SHA-256 para todos los identificadores y para el ranking de la elección |
| `secrets` | 128 bits aleatorios que entran a cada hash |
| `os`, `time`, `itertools` | PID, reloj en nanosegundos y contador por proceso para los hashes |
| `collections` | `OrderedDict` del registro de vistos y de las operaciones de la GUI, `deque` para la bitácora de cada proceso en el panel |
| `heapq` | El programador de revisiones de los respaldos |
| `dataclasses` | `Ronda` (servidor), `Operacion` (GUI), `Proceso` (panel) |
| `math` | Detectar resultados no finitos (`isfinite`) |
| `tkinter` | Las ventanas del nodo, de la GUI y del panel |
| `subprocess` | El panel lanza y tumba procesos (`Popen`, `terminate()`) |
| `argparse` | Opciones de línea de comandos de nodo, servidor, interfaz y sonda |
| `re`, `pathlib`, `traceback` | Validación de campos, rutas de bitácoras y registro de errores |
| `random` | El panel elige una semilla al azar para cada nodo |
| `unittest` (+ `tempfile`, `io`, `contextlib`) | Las 106 pruebas |
| `zipfile`, `xml`, `struct` | Solo en `docs/md_a_docx.py`, para generar el `.docx` sin pandoc |

### 2.3 Conceptos y técnicas de sistemas distribuidos

| Técnica | Dónde se aplica | Referencia |
|---|---|---|
| Arquitectura ADS (Campo de Datos, células, Código de Contenido) | Todo el diseño | Mori (1993) |
| Inundación (*flooding*) con supresión de duplicados | `Nodo._difundir()` | Tanenbaum y Van Steen (2023) |
| Descubrimiento por gossip (epidémico) | Formación de la malla | Demers et al. (1987) |
| *Rendezvous hashing* (HRW) | Elección de la célula que responde | Thaler y Ravishankar (1998) |
| TTL y horizonte dividido | Prevención de ciclos | Tanenbaum y Van Steen (2023) |
| Acuses y quórum | Confirmar que la solicitud llegó a suficientes servidores | Modelo visto en clase |
| Latidos (*heartbeats*) | Disponibilidad de los servidores | |
| Failover | Las células cambian de nodo si el suyo cae | |
| Backoff exponencial | Reintentos de conexión (1 a 8 s) | |
| Framing NDJSON sobre TCP | Separar mensajes en el flujo de bytes | RFC 8259 (JSON), RFC 9293 (TCP) |
| SHA-256 | Identificadores | NIST FIPS 180-4 |

---

## 3. Estructura del repositorio

| Carpeta | Líneas | Qué contiene |
|---|---|---|
| `comun/` | ~790 | Transporte NDJSON y `Enlace`, mensajes, códigos, hashes, constantes, registro de vistos, bitácora y formato de números |
| `nodo/` | ~805 | El nodo del Campo de Datos (`nucleo.py` sin Tkinter, `gui.py` la ventana) |
| `celula/` | ~325 | La célula base, con lo común a toda célula (conexión, failover, deduplicación, publicar) |
| `servidor/` | ~505 | La célula servidor (`calculo.py` la lógica de negocio, `nucleo.py` acuses, elección y relevo) |
| `interfaz/` | ~805 | La célula GUI (`nucleo.py` sin Tkinter, `gui.py` la calculadora) |
| `panel/` | ~460 | Herramienta de despliegue para la demo, fuera del sistema |
| `sonda/` | ~95 | Herramienta para inyectar mensajes de prueba, fuera del sistema |
| `tests/` | ~1,760 | 106 pruebas unitarias y de integración |
| `docs/` | ~610 | `md_a_docx.py` (reporte a Word), `llenar_minutos.py` (minutos del video a la matriz) y las capturas |

El sistema (sin pruebas, herramientas ni docs) son unas 3,200 líneas.

**Regla del proyecto.** Ningún `nucleo.py` importa Tkinter. Los núcleos ponen sus eventos en una
`queue.Queue` y la ventana la vacía cada 100 ms con `after(100)`. Tkinter no es seguro entre hilos,
y además así las pruebas levantan el sistema completo sin abrir ventanas.

---

## 4. Los tres programas del sistema

### 4.1 Nodo (`py -m nodo`)

- Acepta conexiones de nodos y de células, y sabe qué es cada una por su `HOLA`.
- Forma la malla solo, por gossip, con una semilla cualquiera.
- Difunde cada mensaje de datos por inundación.
- **No lee el `cuerpo` ni conoce el catálogo de códigos.** Solo usa `id`, `ttl` y `ruta`. Lee
  `codigo` y `origen` solo para su bitácora. Si aparece un servicio nuevo, el nodo no cambia.
- Su ventana muestra vecinos, células, contadores (recibidos, reenviados, `DUP`, `TTL`, descartados,
  ids en el registro) y el tráfico en vivo con ruta y destinos.

### 4.2 Célula servidor (`py -m servidor --servicio SUM|SUB|MUL|DIV`)

- Atiende **un solo servicio** por instancia.
- Al recibir un `X_REQ` de su servicio, acusa de inmediato (`X_ACK`) y lo encola.
- Participa en la elección por hash. Si es titular responde, si es respaldo espera su turno.
- Emite un latido (`SRV_LAT`) al conectarse y cada 2 s.
- `--retardo-ms` simula una célula lenta (solo atrasa el cálculo, nunca el acuse).
- No tiene ventana. Su bitácora se ve en el panel.

### 4.3 Célula GUI (`py -m interfaz`)

- La calculadora con teclado y display (adaptada del primer parcial).
- Publica la solicitud, cuenta acuses por intento, reintenta y muestra el resultado.
- Ignora las solicitudes de otras GUIs y las respuestas de operaciones ajenas.
- Habilita o deshabilita cada operador según cuántos servidores vivos hay (por latidos).
- Muestra "Mis operaciones", la disponibilidad por servicio y un mini log de protocolo
  (`SOLICITUD`, `ACUSE`, `QUÓRUM`, `RESULTADO`).
- `--acuses-min` (2 por defecto) se puede cambiar también en vivo desde la ventana.

### 4.4 Herramientas fuera del sistema

- **Panel** (`py -m panel`). Matriz de nodos por tipo de célula con ▶ y ■, "Levantar configuración
  mínima", "+ Nodo", campo "retardo ms" y la lista de procesos con su comando exacto y su bitácora.
  Lanza con `subprocess.Popen` y tumba con `terminate()`, que simula una caída real. Si se cierra sin
  detener los procesos, el sistema sigue funcionando.
- **Sonda** (`py -m sonda`). Se presenta como entidad `SONDA`, inyecta un `SONDA_PRUEBA` que ninguna
  célula procesa e imprime su id. Con `--ttl`, `--repetir` e `--id` se prueba cada defensa contra
  ciclos por separado.

---

## 5. Topología y descubrimiento

- Ningún nodo tiene la lista de los demás. Arranca con cero o más semillas (`host:puerto`).
- Al conectarse, el nodo recibe `BIENVENIDA` con todos los nodos que conoce el otro.
- Cada vez que crece su lista de nodos conocidos, manda `PARES` a todos sus enlaces.
- Un **supervisor** corre cada 2 s y marca a cada nodo conocido con el que no tenga enlace. Si falla,
  reintenta con backoff de 1 a 8 s.
- La lista solo crece y es finita, así que el gossip se detiene solo. El resultado es una malla
  completa con cualquier número de nodos.
- En la corrida real, el Nodo 2 tenía a sus 3 vecinos en 130 ms. Un 5º nodo con una sola semilla
  quedó conectado con los otros 4 en menos de 100 ms.

**Regla de enlace duplicado.** Si dos nodos se marcan al mismo tiempo quedan dos conexiones TCP
entre ellos. Los dos lados deben quedarse con la misma sin hablarlo. Sea `preferido = min(mi_hash,
hash_del_par)`. Se queda el enlace nuevo solo si lo inició el preferido y el existente no. En otro
caso se queda el existente y el nuevo recibe `RECHAZO(duplicado)`.

---

## 6. Protocolos

### 6.1 Transporte

- **NDJSON sobre TCP.** Un objeto JSON por línea, terminado en `\n`.
- **Lector tolerante.** Una línea inválida se reporta como `DROP` y la lectura sigue. Una línea de
  más de 64 KiB se descarta.
- **Sin NaN ni Infinity** (`allow_nan=False` al escribir y se rechazan al leer).
- **`Enlace` con hilo escritor propio.** Quien difunde solo encola bytes, así que un par lento no
  frena a nadie. Si la cola pasa de 5,000 mensajes, el enlace se da por muerto (`LENTO`).

### 6.2 Protocolo de conexión (mensajes de control)

Viajan por un solo enlace, nunca se retransmiten y llevan `ctrl` en vez de `codigo`.

| `ctrl` | Dirección | Campos | Propósito |
|---|---|---|---|
| `HOLA` | entidad → nodo | `entidad` (`NODO`, `INTERFAZ`, `SERVIDOR`, `SONDA`), `hash`, `nombre`, `servicio`, `escucha`, `version` | Presentarse e identificar el tipo de entidad |
| `BIENVENIDA` | nodo → entidad | `hash`, `nombre`, `nodos` | Confirmar el registro y pasar la lista de nodos |
| `PARES` | nodo → sus enlaces | `nodos` | Gossip |
| `RECHAZO` | nodo → entidad | `motivo` (`duplicado`, `autoconexion`, `version`, `invalido`), `hash` | Se manda y se cierra el enlace |

Reglas del nodo:

- Una conexión que no manda `HOLA` válido en 5 s se cierra. Sus datos previos se descartan.
- Los nodos van a la tabla `vecinos` y las células a la tabla `celulas` (control de conexiones
  activas del §10.1).
- Si una célula se reconecta con el mismo hash, gana el enlace nuevo.
- El endpoint de un nodo se arma con la IP real del socket y su puerto `escucha`.
- Si un nodo se marca a sí mismo, recibe `RECHAZO(autoconexion)`.
- Puerto ocupado termina con un mensaje claro y código de salida 1.
- Bind a `127.0.0.1` por defecto para que el firewall de Windows no interrumpa la demo. Con
  `--host 0.0.0.0` funciona en red local.

Regla de la célula. Manda `HOLA`, espera la `BIENVENIDA` hasta 3 s y no publica nada antes. Guarda la
lista de nodos para el failover.

### 6.3 Protocolo de comunicación (sobre de datos)

```json
{
  "id": "b8a83064…",
  "codigo": "SUM_REQ",
  "origen": "dedbdb88…",
  "tipo_origen": "INTERFAZ",
  "nombre_origen": "GUI-1",
  "ts": 1791767405.852,
  "ttl": 8,
  "ruta": [],
  "cuerpo": {"id_operacion": "adced3c6…", "intento": 1, "a": 7, "b": 5}
}
```

---

## 7. Códigos de Contenido y mensajes

| Servicio | Solicitud | Acuse | Respuesta |
|---|---|---|---|
| Suma | `SUM_REQ` | `SUM_ACK` | `SUM_RES` |
| Resta | `SUB_REQ` | `SUB_ACK` | `SUB_RES` |
| Multiplicación | `MUL_REQ` | `MUL_ACK` | `MUL_RES` |
| División | `DIV_REQ` | `DIV_ACK` | `DIV_RES` |

Otros dos códigos: `SRV_LAT` (latido de cualquier servidor) y `SONDA_PRUEBA` (solo la sonda).

| Código | Campos del `cuerpo` |
|---|---|
| `X_REQ` | `id_operacion`, `intento`, `a`, `b` |
| `X_ACK` | `id_operacion`, `id_solicitud`, `intento`, `en_cola` |
| `X_RES` | `id_operacion`, `id_solicitud`, `intento`, `resultado`, `error`, `rol` (`titular` o `relevo k`), `ms` |
| `SRV_LAT` | `servicio`, `en_cola`, `atendidas`, `nodo`, `nodo_nombre` |
| `SONDA_PRUEBA` | `nota` |

**Tres identificadores con propósitos distintos.**

| Id | Identifica | Para qué |
|---|---|---|
| `id` (sobre) | Este mensaje | Detectar duplicados en la malla. La respuesta tiene su propio `id` |
| `id_solicitud` | El `X_REQ` exacto que se atendió | La referencia a la solicitud original que piden el §7 y el §11 |
| `id_operacion` | La operación del usuario, igual en todos los reintentos | Que la GUI reconozca como suya la respuesta a cualquier intento |

Valores válidos. `a`, `b` y `resultado` son números finitos. Un operando que no es número (o es
`bool`) o un resultado no finito se responde con `error`. La división entre cero se responde con
`error: "división entre cero"` y cuenta como respuesta válida.

---

## 8. Broadcast

Algoritmo de `Nodo._difundir()` al recibir un mensaje de datos por el enlace `L`:

```
validar el sobre                      → si falla: DROP (el enlace sigue vivo)
si el id ya está en vistos            → DUP: no se procesa ni se retransmite
ttl = min(ttl, 16)
si ttl <= 0                           → TTL: no se procesa
ttl -= 1 ; ruta.append(mi_hash)
serializar una sola vez
entregar a todas mis células, excepto L
si ttl > 0: entregar a cada nodo vecino, excepto L y los que están en la ruta
bitácora FWD
```

En la malla de 4 nodos, cada mensaje se procesa una vez en cada nodo y cada nodo distinto del de
entrada descarta 2 copias duplicadas (1 `FWD` y 2 `DUP`). El nodo de entrada no registra `DUP`. Cada
una de las otras 19 células recibe el mensaje exactamente una vez.

Las células filtran por código. Un servidor X procesa `X_REQ`, `X_ACK` y `X_RES`, e ignora lo demás.
Una GUI procesa `*_ACK` y `*_RES` solo si el `id_operacion` es suyo, y `SRV_LAT`. Ignora siempre los
`*_REQ`.

---

## 9. Prevención de ciclos y duplicados (cuatro defensas)

1. **Id único y registro temporal** (`comun/vistos.py`). `OrderedDict` de `id → expiración`,
   vigencia de 60 s, tope de 100,000 ids. `marcar_si_nuevo()` es atómico con un `Lock`, así que dos
   copias simultáneas por dos enlaces dan un solo reenvío.
2. **TTL.** Las células publican con 8, cada nodo resta 1 y se recorta a 16 si llega mayor. Cubre el
   caso de un duplicado que llegue después de los 60 s.
3. **Horizonte dividido y ruta.** Nunca se devuelve un mensaje por donde llegó ni a un nodo que ya
   está en `ruta`. Evita tráfico inútil.
4. **Deduplicación en la célula.** Cada célula tiene su propio registro de vistos. Cubre las copias
   repetidas tras un failover y los ecos de lo que ella misma publicó.

Evidencia con la sonda:

| Comando | Resultado |
|---|---|
| `py -m sonda --nodo 127.0.0.1:5002 --ttl 1` | Solo lo procesa el Nodo 2 (`FWD` a 0 nodos y `TTL`) |
| `py -m sonda --nodo 127.0.0.1:5002 --repetir 3` | 1 `FWD` y 2 `DUP` en el Nodo 2; las copias no salen |
| `py -m sonda --nodo 127.0.0.1:5003 --id <id>` | `DUP` en el Nodo 3 con un id que circuló antes |

---

## 10. Flujo de una operación (los 10 pasos del §12)

Ejemplo real, `7 + 5` desde la GUI-1 con los 20 procesos vivos.

1. El usuario teclea `7 + 5 =`. La GUI revisa que está conectada y que `SUM` está habilitado.
2. La GUI crea el `id_operacion`, **registra la operación antes de publicar** (un acuse rápido podría
   llegar antes) y publica el `SUM_REQ`.
3. El mensaje sale por su único enlace al Nodo 1.
4. El Nodo 1 lo entrega a sus otras 4 células y a los 3 nodos.
5. Los Nodos 2, 3 y 4 hacen 1 `FWD` y 2 `DUP` cada uno.
6. Las 16 células servidor y las otras 3 GUIs lo reciben. Solo las 4 `SUM` lo procesan.
7. Las 4 `SUM` acusan y encolan. A los 0.5 s calculan el mismo ranking y la titular es `SUM-N4`.
8. `SUM-N4` publica el `SUM_RES` con `id` nuevo, `id_solicitud` de la original y `resultado: 12`.
9. La respuesta se inunda igual que la solicitud. Los otros 3 `SUM` la ven y quedan `LIBERADO`.
10. Solo la GUI-1 reconoce el `id_operacion` y muestra `7 + 5 = 12 · titular SUM-N4 · solicitud
    b8a83064… ↔ respuesta 06164ef7… · 513 ms`.

Patrón por operación en las bitácoras: 4 `ACUSE`, 1 `TITULAR`, 3 `LIBERADO` y **1 `RES`**.

Latencia de ~510 ms. Casi todo es la ventana de elección de 0.5 s. El viaje y el cálculo son unos
milisegundos.

---

## 11. Acuses y mínimo de acuses

- El servidor **acusa al recibir, no al terminar**. El acuse sale en el hilo lector, antes de
  encolar. El retardo artificial nunca atrasa el acuse.
- Los acuses sirven a la GUI (cuenta cuántos tienen su operación) y a los otros servidores (saben
  quiénes participan en la elección).
- **Quórum por intento.** Mínimo de 2 por defecto. Los acusadores se cuentan en un conjunto por
  intento y no se acumulan entre intentos.
- **Respuesta solo con quórum.** Si llega antes que el quórum, se retiene y se acepta al completarse.
- Con mínimo 2 siempre hay al menos un respaldo que puede relevar a la titular.

Plazos (un reloj de 100 ms los revisa):

| Situación | Plazo | Al vencer |
|---|---|---|
| Sin quórum | 1.5 s desde el envío del intento | Reintento |
| Con quórum, sin respuesta | `t_quorum + 0.5 + 1.5 · n_acusadores + 2` s | Reintento |
| Tercer intento vencido | El que aplique | `FALLIDA` con motivo |

Un reintento lleva el mismo `id_operacion`, `intento + 1` y un `id` de mensaje nuevo (si no, la malla
lo descartaría). Una respuesta a una operación ya resuelta se registra `DUPLICADA descartada`, y a
una fallida, `TARDÍA descartada`.

---

## 12. Respuesta única (elección HRW)

Cada servidor que recibió el `X_REQ`:

1. Acusa y encola.
2. Junta los `X_ACK` de los demás para esa ronda (`id_operacion`, `intento`).
3. Espera la ventana de elección (0.5 s).
4. Ordena a los acusadores por `SHA-256(hash_célula | id_operacion | intento)` y ve su posición `r`.

| Posición | Rol | Qué hace |
|---|---|---|
| `r = 0` | Titular | Calcula y responde con `rol = "titular"` |
| `r ≥ 1` | Respaldo r | Revisa a los `r · 1.5 s`. Si nadie respondió, toma el relevo (`rol = "relevo r"`). Si ya hubo respuesta, queda liberado |

Todas calculan el mismo orden sobre el mismo conjunto, así que coinciden sin mensajes extra y sin
coordinador. El hash reparte la titularidad de forma uniforme (en `test_huella`, 4,000 operaciones
entre 4 células dan 1,000 ± 150 cada una). Como el `intento` entra al hash, un reintento puede tocarle
a otra titular.

**Las seis capas contra respuestas duplicadas.**

| Capa | Dónde | Qué evita |
|---|---|---|
| 1. Elección HRW | `Servidor._elegir()` | Que respondan todas |
| 2. Respaldos escalonados | `_revisar_respaldo()` | Que un respaldo responda si la titular ya lo hizo |
| 3. Doble revisión antes de publicar | `_ejecutar()` | Que una titular lenta responda después del relevo (`SUPRIMIDA`) |
| 4. Regla ≤ k | `_marcar_resueltas()` | Un `RES` del intento k resuelve las rondas ≤ k, nunca las posteriores |
| 5. Ronda superada | `_rx_req()` | Que respondan rondas viejas, incluso si el REQ viejo llega después del nuevo |
| 6. Deduplicación en la GUI | `Interfaz._rx_res()` | Si aun así llega una segunda respuesta, se descarta |

Casos demostrados:

- **Normal.** Responde la titular en ~510 ms y los 3 respaldos quedan liberados.
- **Titular lenta** (`SUM-N3b` con `--retardo-ms 4000`). El respaldo 1 (`SUM-N2`) toma el relevo a
  los 2.0 s y la titular suprime su respuesta a los 4.5 s. Una sola respuesta.
- **Titular que muere tras acusar** (prueba automatizada). El respaldo 1 responde a los ~2 s sin que
  la GUI reintente.

---

## 13. Disponibilidad por latidos

- Cada servidor publica `SRV_LAT` al conectarse y cada 2 s. Un acuse también cuenta como señal de
  vida.
- Una célula caduca tras 6 s sin noticias (tres latidos).
- Si las vivas de un servicio son menos que su mínimo de acuses, la GUI deshabilita ese operador.
  Se rehabilita en cuanto llega el latido de una célula nueva.
- Al arrancar, todo está "esperando latidos…" y se habilita en menos de 2 s.
- La GUI no caduca a nadie mientras ella misma está sin enlace.
- Demo real. Se tumbaron 3 de 4 `DIV`, las 4 GUIs deshabilitaron `÷`, se levantó `DIV-N2b` y se
  rehabilitó. Después `8 ÷ 2 = 4` con 2 acuses y 1 respuesta.

---

## 14. Identificadores

- Todo tiene un SHA-256 de 64 caracteres hex (nodos, células, mensajes y operaciones).
- Cada entidad genera el suyo con `sha256("tipo|datos|hostname|pid|time_ns|contador|128 bits
  aleatorios")`. Nadie asigna identidades.
- Colisión del orden de 2⁻¹²⁸. El contador garantiza unicidad dentro del proceso. La prueba genera
  50,000 hashes sin repetir.
- Los nombres ("Nodo 1", "SUM-N3", "GUI-2") son solo etiquetas. Si un proceso se reinicia, es una
  entidad nueva.

---

## 15. Failover

Si muere el nodo de una célula (`Celula._recuperar()`):

1. Reintenta 2 veces con su nodo, 1 s entre intentos y espera corta de 0.5 s.
2. Rota por los demás nodos que recibió en `BIENVENIDA` y `PARES`.
3. Si nadie responde en una vuelta, espera con backoff (hasta 8 s) y repite.
4. Conserva su hash, así que sigue siendo la misma célula.
5. No regresa a su nodo original si revive, para no oscilar.

Demo real. Se tumbó el Nodo 1 y sus 5 células pasaron al Nodo 2 en ~3.0 s. Ninguna GUI dio por
muerto a ningún servidor (el failover es más rápido que la caducidad de 6 s). Luego `9 × 9` se
resolvió en 512 ms.

Detalle de Windows. Un `connect()` a un puerto cerrado tarda ~2 s en fallar. Con el tiempo normal el
failover tardaba ~6 s y las GUIs caducaban a todos. Se agregó `REINTENTO_TIMEOUT` de 0.5 s.

---

## 16. Concurrencia

| Mecanismo | Dónde | Qué resuelve |
|---|---|---|
| Hilo lector + hilo escritor por enlace | `Enlace` | Un par lento no frena a nadie |
| Cola de salida con tope de 5,000 | `Enlace.enviar_bytes()` | Un par colgado se detecta (`LENTO`) |
| Hilos aceptador, supervisor y marcadores | `Nodo` | Conexiones, descubrimiento y marcado en paralelo |
| `RLock` del nodo | `Nodo._lock` | Tablas de vecinos y células, conocidos y contadores |
| `Lock` del registro de vistos | `RegistroVistos` | Reenvío único con copias simultáneas |
| Hilo conector | `Celula._mantener()` | Conexión y failover sin bloquear a la célula |
| Hilo trabajador + `queue.Queue` | `Servidor._trabajar()` | Cola FIFO; el cálculo nunca corre en el hilo lector |
| Programador (heap + `Condition`) | `Programador` | Revisiones de los respaldos a la hora exacta, en un solo hilo |
| `RLock` de las rondas | `Servidor._lock_rondas` | Estado de cada ronda, que tocan tres hilos |
| Hilo de reloj (100 ms) + `RLock` | `Interfaz._vigilar()` | Plazos, reintentos y caducidad |
| `queue.Queue` + `after(100)` | Las tres ventanas | Tkinter solo se toca desde su hilo |

Carreras consideradas:

- Acuse que llega antes que la solicitud. El servidor crea una ronda "esqueleto" y el REQ la completa.
- Acuse antes de que exista la operación. La GUI registra la operación antes de publicar.
- Datos antes de la bienvenida. El nodo encola la `BIENVENIDA` antes de registrar el enlace.
- Solicitud vieja que llega después de la nueva. Se marca superada (bug 1).

---

## 17. Tolerancia a fallas

| Escenario | Qué pasa |
|---|---|
| Cae un nodo | Sus células hacen failover en ~3 s y el servicio sigue |
| El nodo vuelve en el mismo puerto | Reingresa a la malla solo |
| Cae la titular después de acusar | El respaldo 1 responde a los ~2 s |
| Titular lenta | Relevo y `SUPRIMIDA`, una sola respuesta |
| Quedan menos servidores que el mínimo | Se deshabilita el operador; una célula nueva lo rehabilita |
| Se pierde una respuesta | La GUI reintenta y la ronda nueva se atiende (regla ≤ k) |
| Basura o mensaje mal formado | `DROP` y el enlace sigue vivo |
| Datos antes del `HOLA` | Se descartan; sin `HOLA` en 5 s se cierra |
| Dos nodos se marcan a la vez | Regla de enlace duplicado |
| Un nodo recibe su propio endpoint | `RECHAZO(autoconexion)` |
| Par lento o colgado | `LENTO` y se cierra sin bloquear a nadie |
| ÷0, operando inválido o resultado no finito | `X_RES` con `error` |
| Se cierra el panel sin detener | Los 24 procesos siguen y `2 + 2` se resuelve |
| Caen todos los nodos | Las células ciclan con backoff y la GUI muestra "sin Campo de Datos" (por diseño, no se ejercitó) |

No hay puntos únicos de falla. Cualquier nodo sirve de semilla, la elección no tiene coordinador,
nadie asigna identidades y el panel está fuera del sistema.

---

## 18. Pruebas

### 18.1 Suite automatizada

`py -m unittest discover -s tests -t .` corre **106 pruebas** en ~85 s, sin ventanas. Las de
integración levantan nodos y células reales en el mismo proceso, con puertos efímeros y tiempos
acortados con `mock.patch` (por eso las constantes se leen como `config.X` al usarlas).

| Archivo | Pruebas | Qué cubre |
|---|---|---|
| `test_protocolo.py` | 17 | Framing, línea inválida que no rompe el lector, tope de longitud, NaN |
| `test_enlace.py` | 7 | Cola de escritura, desborde (`LENTO`), orden, cierre |
| `test_huella.py` | 10 | 64 hex, 50,000 únicos, ranking determinista, reparto uniforme |
| `test_mensajes.py` | 14 | Sobre, validación, `HOLA`, endpoints, catálogo |
| `test_vistos.py` | 4 | Nuevo, repetido, caducidad, tope, atomicidad con 16 hilos |
| `test_calculo.py` | 11 | Las 4 operaciones, ÷0, no finitos, `bool` y `str` |
| `test_formato.py` | 6 | Números y operaciones legibles |
| `test_bitacora.py` | 5 | La bitácora nunca lanza |
| `test_malla.py` | 7 | Malla completa sin enlaces duplicados, marcado simultáneo, autoconexión, 5º nodo, nodo caído y que vuelve |
| `test_broadcast.py` | 8 | Con la sonda real, exactamente una vez por célula, ruta, TTL, `--repetir`, `--id`, basura |
| `test_flujo.py` | 17 | Sistema completo con célula espía. Exactamente un `RES`, ÷0, titular lenta y tumbada, deshabilitar y rehabilitar, failover, regla ≤ k, ronda superada, REQ desordenado, ACK antes del REQ, reglas de quórum |

`tests/apoyo.py` tiene los ayudantes de integración (`Sistema`, `Registro`, `Receptor`, `Espia`).

### 18.2 Verificación en vivo

Con el panel real (24 procesos al final), el 11 de octubre de 2026. Un script revisó las bitácoras
de los 24 procesos.

| Escenario | Resultado |
|---|---|
| Una operación desde cada GUI y ÷0 | 4 `ACUSE`, 1 `TITULAR`, 3 `LIBERADO`, 1 `RES` por operación |
| Tumbar el Nodo 1 | Failover en ~3.0 s sin `CADUCA` |
| Tumbar 3 `DIV` y levantar una | `DESHABILITADA` y `HABILITADA`, luego `8 ÷ 2 = 4` |
| `SUM-N3b` lenta | Relevo a 2.0 s, `SUPRIMIDA` a 4.5 s, 1 `RES` |
| Sondas | Como en la sección 9 |
| "+ Nodo" | Nodo 5 con 4 vecinos, 1 `FWD` y 3 `DUP` por nodo |
| Cerrar el panel | 24 de 24 procesos vivos y `2 + 2 = 4` |
| Errores | Ningún `ERROR`, `Traceback`, `PERDIDO`, `DROP` ni `LENTO` |

### 18.3 Bugs que encontraron las pruebas

1. **Doble respuesta por desorden.** Un intento 2 que llegaba antes que el intento 1 hacía que el 1
   se atendiera como nuevo y saliera un segundo `RES` (1 de 6 operaciones en un diagnóstico).
   Corrección: la ronda se marca superada al llegar si ya se conoce un intento posterior.
2. **Caída falsa al formarse la malla.** 1 de cada ~25 veces el enlace sobrante se cerraba sin
   avisar y el otro lado veía una `DESCONEXION` falsa. Corrección: siempre se manda
   `RECHAZO(duplicado)` antes de cerrar (0 casos en 60 formaciones).
3. **Reemplazo de enlace sin rastro.** La ventana mostraba dos `CONEXION` seguidas sin explicación.
   Corrección: se registra un evento `DUPLICADO`.

Antes de la suite, las corridas manuales dejaron otras dos correcciones: el `REINTENTO_TIMEOUT` del
failover y que la GUI no caduque células mientras está sin enlace.

---

## 19. Decisiones de diseño

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Solo librería estándar | Java, bibliotecas de red | Cero instalación |
| Nodos que no leen el contenido | Nodos que enrutan por servicio | El nodo no cambia con servicios nuevos |
| Todo por broadcast | Mensajes dirigidos | Lo pide el §9 |
| Malla por gossip | Lista fija de nodos | Cualquier número de nodos, ninguno especial |
| NDJSON | Encabezado binario | Legible y ya probado en el primer parcial |
| SHA-256 generado por cada entidad | Ids asignados por un nodo | Sin autoridad central |
| Elección HRW | Que respondan todas | El §9 pide evitar las respuestas no deseadas |
| Acuse inmediato | Acusar al terminar | Una célula lenta no parece muerta |
| Latidos | Disponibilidad solo por acuses | La GUI sabe antes de pedir |
| Failover | Que la célula muera con su nodo | Si no, cada nodo sería punto único de falla |
| Bind a 127.0.0.1 | 0.0.0.0 | Evita el diálogo del firewall en la demo |
| `config.X` al usarlas | `from config import X` | Las pruebas acortan tiempos con `mock.patch` |

Lo que no se hizo, a propósito: foliado (entrega final), células que levantan células y
persistencia.

---

## 20. Diferencias con lo visto en clase

1. **Latidos además de acuses.** En clase la disponibilidad se conocía solo por los acuses. Los
   latidos permiten deshabilitar un operador antes de mandar la solicitud. Los acuses se conservan.
2. **Una sola respuesta por elección.** En clase respondían todas y la GUI tomaba la primera. El
   enunciado (§9 y §11) pide evitar las respuestas duplicadas, así que responde una sola. La
   redundancia se conserva con los respaldos, y la deduplicación en la GUI queda como última capa.

---

## 21. Reutilización y originalidad

Del primer parcial (mismo autor) se adaptaron:

| Archivo | Cambio |
|---|---|
| `comun/protocolo.py` | Lector tolerante, tope de longitud, `allow_nan=False`, `Enlace` con cola |
| `servidor/calculo.py` | Un servicio por llamada, control de tipos y de no finitos |
| `comun/formato.py` | Formato `.12g` y flotantes enteros como enteros |
| `interfaz/gui.py` (de `cliente/gui.py`) | Teclado, display, atajos y el patrón cola + `after(100)` |
| `tests/test_protocolo.py` | Base de la fuente falsa |

De la Práctica 3 del curso se tomaron ideas, no código (gossip, validación de mensajes, ACP/ASM).

---

## 22. Limitaciones y trabajo futuro

Limitaciones:

1. Enlaces medio abiertos (un par que no responde sin cerrar la conexión) no se detectan pronto.
2. Durante un marcado simultáneo se puede perder un mensaje (solo al formarse la malla).
3. Un duplicado que llegue después de 60 s volvería a circular, acotado por el TTL.
4. Un acuse tardío puede producir dos titulares; las capas 3 y 6 lo absorben.
5. Sin autenticación.
6. El failover no regresa al nodo original.
7. Latencia mínima de ~0.5 s por la ventana de elección.

Trabajo futuro: foliado, células que levantan células, latidos entre nodos y autenticación.

---

## 23. Constantes (`comun/config.py`, tiempos en segundos)

| Constante | Valor | Uso |
|---|---|---|
| `TTL_INICIAL` / `TTL_MAX` | 8 / 16 | TTL al publicar y tope |
| `VISTOS_VIGENCIA` / `VISTOS_MAX` | 60 / 100,000 | Registro de vistos |
| `LATIDO` / `LATIDO_CADUCIDAD` | 2 / 6 | Latidos |
| `VENTANA_ACUSES` | 1.5 | Plazo para juntar quórum |
| `VENTANA_ELECCION` | 0.5 | Espera antes de elegir |
| `RELEVO` | 1.5 | Separación entre respaldos |
| `MARGEN_RESULTADO` | 2 | Holgura del plazo de resultado |
| `MAX_INTENTOS` / `ACUSES_MIN_DEFECTO` | 3 / 2 | Reintentos y quórum |
| `HOLA_TIMEOUT` / `BIENVENIDA_TIMEOUT` | 5 / 3 | Presentación |
| `CONECTAR_TIMEOUT` | 3 | `connect()` TCP |
| `BACKOFF_MIN` / `BACKOFF_MAX` | 1 / 8 | Reintentos de conexión |
| `SUPERVISOR` | 2 | Revisión de enlaces faltantes |
| `REINTENTOS_MISMO_NODO` / `REINTENTO_TIMEOUT` | 2 / 0.5 | Failover |
| `MAX_LINEA` / `COLA_ENLACE_MAX` | 64 KiB / 5,000 | Transporte |
| `RONDAS_VIGENCIA` | 120 | Purga de rondas viejas en el servidor |

---

## 24. Comandos

```powershell
py -m panel                                     # panel de despliegue
py -m nodo --puerto 5001 --nombre "Nodo 1"
py -m nodo --puerto 5002 --nombre "Nodo 2" --semillas 127.0.0.1:5001
py -m servidor --servicio SUM --nodo 127.0.0.1:5001 --nombre SUM-N1
py -m servidor --servicio DIV --nodo 127.0.0.1:5003 --nombre DIV-N3 --retardo-ms 4000
py -m interfaz --nodo 127.0.0.1:5002 --nombre GUI-2 --acuses-min 2
py -m sonda --nodo 127.0.0.1:5002 --ttl 1
py -m unittest discover -s tests -t .           # 106 pruebas
py docs/llenar_minutos.py                       # minutos del guion a la matriz del reporte
py docs/md_a_docx.py                            # REPORTE_TECNICO.md → .docx
```

Bitácoras de cada proceso en `logs/<nombre>-<hash8>.log`.

---

## 25. Datos para citar

| Dato | Valor |
|---|---|
| Procesos en la configuración mínima | 4 nodos + 20 células = 24 |
| Enlaces TCP entre nodos | 6 |
| Latencia típica | ~510 ms (500 de ventana de elección) |
| Formación de la malla | ~130 ms; Nodo 5 en menos de 100 ms |
| Failover | ~3.0 s, sin caducar a nadie |
| Relevo con titular lenta | 2.0 s (titular suprimida a 4.5 s) |
| Copias por mensaje en cada nodo no de entrada | 1 `FWD` + 2 `DUP` (con 5 nodos, 1 + 3) |
| Respuestas por operación | Exactamente 1 en todas las pruebas y corridas |
| Pruebas | 106, ~85 s |
| Bugs reales encontrados | 3, más 2 correcciones de las corridas manuales |
