# Plan — Calculadora ADS, Tercer Parcial (Cómputo Distribuido)

> Plan **autocontenido**: con este documento, una sesión nueva puede seguir el proyecto sin la
> conversación previa. Documentos hermanos (leerlos también):
> - `docs/INSTRUCCIONES_USUARIO.md`: lo que pidió el usuario, **literal**. Manda sobre este plan.
> - `docs/ENUNCIADO.md`: el PDF, literal, con identificadores por requisito.
> - `docs/REQUISITOS.md`: lista de verificación con cada requisito → sección del plan → sesión.
> - `ROADMAP.md`: avance por sesiones y siguiente paso.
>
> **Regla del usuario: no se implementa nada sin que apruebe el plan.**

---

## 0. Contexto

**Antecedente.** El segundo parcial (`c:\SCHOOL\COMPUTO_DISTRIBUIDO\calculadora_ads\`, entregado,
**no se toca**) ya cumple toda la base del §4 del enunciado: 4 nodos en malla completa por gossip;
célula GUI, célula servidor y nodo; broadcast con Códigos de Contenido; prevención de ciclos
(vistos, TTL, horizonte dividido, dedup en célula); acuses con mínimo configurable; elección HRW
con una sola respuesta; latidos; failover; sin unidad central. Su plan, reporte, guion y capturas
están archivados en `docs/parcial2/`.

**Este repo** (`calculadora_ads_p3/`) es un clon local de aquel (conserva la historia; la etiqueta
`parcial-2` marca el punto de partida; sin remoto). El usuario creará un repo nuevo en GitHub.

**La idea del usuario, en una frase:** el Campo de Datos y las GUIs siguen igual, pero las células
servidor ahora son **células madre vacías** (4 por nodo) que pueden hacer cualquier operación
porque **jalan programas**; una interfaz nueva, el **gestor de microservicios**, tiene una **base
de datos** con todos los servicios, dibuja la **topología** y puede **inyectar** microservicios a
las madres **por el Campo de Datos**. Si una célula muere, las demás la **regeneran solas**, de
forma **gradual**, **sin orquestador** y **sin cáncer**, y la nueva **copia los genes** que hacían
falta. Fácil de grabar; código deslumbrante.

### 0.1 Decisiones (no reabrir sin el usuario)

| Tema | Decisión |
|---|---|
| Lenguaje | **Python 3.14, solo librería estándar** en el sistema (incluye `sqlite3`, `importlib`, `tkinter`). Sin Java. |
| Entorno | **uv**: `pyproject.toml` + `uv.lock` + `.python-version`; `ruff` en `dev`. Se corre con `uv run python -m <paquete>`. |
| Repo | `calculadora_ads_p3/`, clon local del segundo parcial. El del segundo parcial no se toca. |
| Orden de trabajo | Fases estrictas: 0 → A código → B pruebas → C fixes → D reporte → E guion. En A solo humo. |
| Herencia | Se conserva el diseño del segundo parcial: nodos "bobos" (no leen `cuerpo`), todo por broadcast, hashes SHA-256 propios de cada entidad, acuse inmediato, elección HRW, respaldos escalonados, latidos, failover. |
| Célula servidor = **célula madre** | Paquete `madre/` (sustituye a `servidor/`). Un solo programa base genérico **sin** lógica de +, −, ×, ÷. Arranca vacía o con genes; puede tener varios genes activos. |
| Configuración de demo | 4 nodos; por nodo **1 GUI + 4 células madre** + **un gestor por nodo**, que el usuario **levanta cuando quiere** (no arrancan solos). |
| Visual | "Súper completo y bonito, simple pero clean": línea visual única para todas las ventanas (§15.1). |
| Dos modos de arranque | **Vacía**: las 16 madres sin genes; se llenan desde el gestor. **Con servicios**: cada madre arranca con un gen (una de cada operación por nodo). Después el funcionamiento es idéntico. |
| Genes en disco | Cada madre tiene **su propio almacén en disco** (`datos/celulas/<nombre>-<hash8>/genes/`). Todo gen que recibe (de donde sea) se **escribe ahí** y de ahí se **carga a memoria** con `importlib`. |
| Fuentes de un gen | (1) Banco local `microservicios/` (modo con servicios); (2) **inyección** del gestor por el Campo de Datos; (3) **pedido** por el Campo de Datos a quien lo tenga (otras madres o un gestor). |
| Gestor | `gestor/`: interfaz nueva que se conecta a un nodo (entidad `GESTOR`). Tiene **BD SQLite** con los programas (se llena importando `microservicios/`). Dibuja la topología como **diagrama vivo**. Inyecta, da de baja, sustituye y retira. **No es orquestador** (§4.1). |
| Foliado | Folio `F-<hash8 GUI>-<n>`; huella con origen, sello y rastro; evento con 4 fases; `X_FIN` nuevo; esperados/ausentes (§5). |
| Varias operaciones en vuelo por GUI | Sí: el folio las distingue. Botón **Ráfaga** para el escenario 2. |
| Nivel requerido | **No hay número fijo que el sistema rellene.** Se reemplaza **1 a 1** cada célula perdida, nada más: si solo se levantó una, solo se mantiene una. |
| Autorrecuperación | **100 % automática** (sin input del usuario). La deciden las madres con la misma regla determinista; el reemplazo nace vacío y **copia** los genes de la perdida por el Campo de Datos. **Gradual**: uno a la vez. |
| Anti-cáncer | Ocho límites (§6.4), incluidos topes duros y telómeros. |
| Fácil de grabar | Panel con los dos modos y botones de un clic para provocar fallas; gestor con "Distribuir una de cada operación por nodo"; todo lo automático se ve solo en el diagrama del gestor (§10). |
| Calidad | "Deslumbrante": estándares del §15. |
| PDF vs clase | El PDF manda; las diferencias se mencionan breve y respetuosamente en reporte y video. |
| Reporte | Markdown → `.docx` (`docs/md_a_docx.py`). **≤ 30 páginas.** Lo heredado, resumido. |
| Commits | Solo cuando el usuario lo pida. |

---

## 1. Arquitectura final

```
                         ┌───────────── Gestor de microservicios ─────────────┐
                         │ BD SQLite · diagrama vivo · inyectar/baja/sustituir │
                         └──────────────────────┬─────────────────────────────┘
                                                │ (una interfaz más, en cualquier nodo)
   GUI-1  M1 M2 M3 M4                           │                  GUI-2  M1 M2 M3 M4
       \   \  \ /  /                                                  \   \  \ /  /
        [ NODO 1 :5001 ] ═══════════════════════════════════════ [ NODO 2 :5002 ]
               ║        ╲\                                   /╱        ║
               ║           ═══════════════╳══════════════════          ║   malla completa
        [ NODO 3 :5003 ] ═══════════════════════════════════════ [ NODO 4 :5004 ]
       /   /  / \  \                                                  /   /  / \  \
   GUI-3  M1 M2 M3 M4                                              GUI-4  M1 M2 M3 M4

   M = célula madre: vacía, o con genes (SUM 1.0, SUM 2.0, SUB 1.0, MUL 1.0, DIV 1.0…)
   microservicios/  = carpeta con los programas (banco local; el gestor la importa a su BD)
   datos/celulas/*/genes/ = almacén en disco de cada madre (de ahí carga a memoria)
```

| Componente | Paquete | Papel |
|---|---|---|
| Nodo del Campo de Datos | `nodo/` | Heredado. Nuevo: acepta la entidad `GESTOR` y origina `NODO_LAT` (latido con nombre, endpoint, vecinos y número de células). Sigue sin leer el `cuerpo` de nadie. |
| Célula base (ACP) | `celula/base.py` | Heredada: conexión, `BIENVENIDA`/`PARES`, failover, dedup, `publicar()`. |
| Célula cliente (GUI) | `interfaz/` | Heredada + foliado, eventos, ráfaga, ajenas ignoradas. |
| Célula madre (servidor) | `madre/` | Nueva base genérica: almacén de genes, cargador, rondas por código, órdenes del gestor, pedidos de genes, regeneración. |
| Microservicios | `microservicios/` | Programas en disco (no es paquete importable). |
| Gestor de microservicios | `gestor/` | Nuevo: BD, topología, diagrama, órdenes. |
| Foliado | `comun/foliado.py` | Folio, sello, huella, rastro, validación. |
| Panel / Sonda | `panel/`, `sonda/` | Herramientas de demo fuera del sistema. |

**Principio rector: no hay orquestador.** Ninguna pieza nueva es indispensable ni decide por las
células: cada madre valida y carga sus propios genes; cada madre detecta pérdidas y aplica la misma
regla para decidir quién regenera; el gestor solo actúa cuando el administrador lo usa; el panel
está fuera del sistema.

---

## 2. Estructura del proyecto

```
calculadora_ads_p3/
├─ pyproject.toml  uv.lock  .python-version  .gitignore
├─ CLAUDE.md  ROADMAP.md  README.md  ENTREGA.md
├─ REPORTE_TECNICO.md  GUION_VIDEO.md                 (fases D y E)
├─ Instrucciones_Proyecto_Tercer_Parcial_ADS_v4.pdf
├─ comun/        protocolo, hashes (antes huella.py), foliado (nuevo), codigos, mensajes, config,
│                vistos, bitacora, formato, tema (nuevo: paleta y tipografía de las ventanas),
│                estilo (nuevo: piezas Tk con el tema), pedidos (nuevo: quien entrega un gen),
│                microservicios (nuevo: formato del gen en disco, sha256, banco local),
│                programador (agenda de tareas; antes vivía en servidor/nucleo.py)
├─ nodo/         nucleo.py, gui.py, __main__.py
├─ celula/       base.py
├─ madre/        __main__.py, nucleo.py (une todo), almacen.py (disco), genes.py (cargador),
│                rondas.py (acuse/elección/relevo por código), ordenes.py (gestor),
│                pedidos.py (pedir un gen por el Campo de Datos),
│                regeneracion.py (autorrecuperación), lanzador.py (procesos clon),
│                copia.py (el reemplazo copia los genes de la perdida)
├─ interfaz/     nucleo.py, gui.py, __main__.py
├─ gestor/       __main__.py, nucleo.py, bd.py (SQLite), topologia.py (modelo),
│                diagrama.py (Canvas), gui.py
├─ microservicios/
│   ├─ SUM/1.0/{manifiesto.json, servicio.py}    suma flotante
│   ├─ SUM/2.0/{…}                               suma decimal exacta (0.1 + 0.2 = 0.3)
│   ├─ SUB/1.0/  MUL/1.0/  DIV/1.0/
│   └─ SUM/9.9/{…}                               manipulado a propósito (sha256 no coincide)
├─ herramientas/ firmar.py                       recalcula sha256 de los manifiestos
├─ panel/  sonda/
├─ tests/
├─ docs/         PLAN.md, REQUISITOS.md, ENUNCIADO.md, INSTRUCCIONES_USUARIO.md, md_a_docx.py,
│                capturas/, parcial2/
└─ logs/  datos/  run/                           (ignorados por git)
```

---

## 3. Células madre y genes (§5.2 del enunciado) — `madre/`

### 3.1 El gen en disco

```
microservicios/SUM/2.0/manifiesto.json
{"codigo": "SUM", "version": "2.0", "nombre": "Suma decimal exacta", "archivo": "servicio.py",
 "sha256": "<hex del servicio.py>", "interfaz": 1,
 "pruebas": [[2, 3, 5], [0.1, 0.2, 0.3]], "descripcion": "…"}

microservicios/SUM/2.0/servicio.py
SERVICIO = "SUM"
VERSION = "2.0"
def calcular(a, b):   # -> (resultado, error)
```

El gen contiene **solo** la operación. El programa base valida antes y después (operandos
numéricos finitos y no `bool`, resultado finito): eso es protocolo, no lógica de negocio.

### 3.2 Almacén propio de cada madre — `madre/almacen.py`

`datos/celulas/<nombre>-<hash8>/genes/<CÓDIGO>/<versión>/{manifiesto.json, servicio.py}`.
Todo gen pasa por aquí, venga de donde venga (requisito M1: "existir físicamente en disco"):

| Vía | Cuándo | Qué hace la madre |
|---|---|---|
| Banco local | Modo "con servicios" (`--genes SUM@1.0`) | Copia `microservicios/SUM/1.0/` a su almacén |
| Inyección | El gestor manda `GEN_INYECTA` con el programa dentro | Escribe el manifiesto y el programa en su almacén |
| Pedido | Una madre regenerada necesita copiar genes (`GEN_PIDE`) | Escribe lo que le llega en `GEN_ENTREGA` |

### 3.3 Ciclo de vida de un gen — `madre/genes.py`

| Paso | Qué hace | Si falla |
|---|---|---|
| **Localizar** | Ruta `almacén/CÓDIGO/versión/manifiesto.json`, resuelta y confinada al almacén (sin `..`). | `no existe` |
| **Validar** | Esquema del manifiesto; `servicio.py` ≤ `GEN_MAX_BYTES`; `sha256(servicio.py) == manifiesto.sha256`. | `sha256 no coincide` (caso `SUM 9.9`), `manifiesto inválido` |
| **Cargar** | `importlib.util.spec_from_file_location(nombre_único, ruta)` → `module_from_spec` → `exec_module`. Revisa `SERVICIO`, `VERSION` y `calcular` invocable. | `interfaz inválida` |
| **Autoprueba** | Corre los vectores `pruebas` del manifiesto. | `autoprueba falló` |
| **Activar** | Con el lock de genes lo pone en `activos[codigo]`; publica `CEL_LAT` de inmediato. | — |
| **Descargar** | Lo saca de `activos` (deja de acusar ese código al instante); las rondas en curso terminan con su referencia; `sys.modules.pop`; `weakref` + `gc.collect()` confirman que el módulo se liberó; borra la copia del almacén. | — |
| **Sustituir** | Escribe, valida y carga la versión nueva **antes** de tocar la vieja; si falla, la vieja sigue (reversión); si pasa, cambio atómico y descarga de la vieja. | la vieja queda activa |

Cada ronda guarda el gen con el que acusó (`SUM@1.0`) y lo usa hasta el final: un cambio a mitad
de un evento no mezcla versiones; al terminar la ronda suelta la referencia para que el gen viejo
pueda liberarse.

**Detalles de implementación (S1):** la carga ejecuta **los mismos bytes que se validaron**
(`compile` + `exec` sobre el módulo de `module_from_spec`), no vuelve a leer el archivo: entre
validar y cargar nadie puede cambiarlo. El módulo no se registra en `sys.modules`, así que al
descargarlo solo lo retenía el `Genoma` y el `weakref` confirma la liberación. `ejecutar` convierte
los operandos a `float` y atrapa cualquier excepción del gen (un gen roto no tumba a la célula).
`comun/formato.py` muestra los flotantes exactos (`repr`) para que se vea `0.30000000000000004`
contra `0.3` (escenario 5). Todas las células laten con `CEL_LAT` desde la célula base
(`cuerpo_latido`); la GUI cuenta una madre para un servicio mientras lo anuncie en sus genes, y la
olvida al instante si deja de anunciarlo o publica `CEL_ADIOS`. `Madre.tumbar()` simula una caída
en proceso (sin `CEL_ADIOS`), para las pruebas. Bitácora: `GEN_ESCRITO` (vía, ruta), `GEN_VALIDADO` (sha8),
`GEN_CARGADO` (ms), `GEN_ACTIVO`, `GEN_RECHAZADO` (motivo), `GEN_BAJA`, `GEN_LIBERADO`.

### 3.4 Programa base

```
uv run python -m madre --nodo 127.0.0.1:5001 [--nombre M1-N1] [--genes SUM@1.0,MUL]
                       [--retardo-ms N] [--mudo]
                       [--reemplaza <hash> --copiar SUM@1.0#<sha8>,… --generacion G]   (lo usa el clonador)
```

Sin `--genes` arranca **vacía**: se conecta, late con `genes: []`, aparece en el diagrama como
madre vacía y espera. `--mudo` (inyección de falla para el escenario 3): late pero no acusa ni
participa. Al cerrarse ordenadamente (retiro desde el gestor, Ctrl+C) publica `CEL_ADIOS`: así
las demás saben que **no** fue una falla.

### 3.5 Rondas por código — `madre/rondas.py`

El motor del segundo parcial (acuse inmediato, cola, elección HRW entre las que acusaron, titular,
respaldos escalonados, relevo, doble revisión, regla ≤ k, ronda superada) se conserva, ahora con
clave `(código, folio, intento)` y una cola por madre. Solo atiende códigos de genes **activos**.

---

## 4. Gestor de microservicios (§5.4) — `gestor/`

### 4.1 Por qué NO es un orquestador

| Un orquestador… | Este gestor… |
|---|---|
| Decide solo dónde corre cada servicio | Solo actúa cuando el administrador pulsa un botón; nunca decide automáticamente |
| Lleva el registro oficial de la topología | No guarda la topología: la reconstruye de los latidos que **cualquiera** puede oír |
| Instala el código | Publica una orden por broadcast; la **célula destino** escribe, valida y carga el gen ella misma, y puede rechazarlo |
| Está en el camino de las operaciones | Nunca ve un `X_REQ`, no acusa ni responde |
| Recupera fallas | La regeneración es de las madres (§6); el gestor solo la **muestra** |
| Es único | Hay **uno por nodo** (los levanta el usuario), cada uno con su BD; todos ven todo y ninguno manda sobre los demás |

Cerrar el gestor no cambia nada del funcionamiento normal (requisito G7 / evidencia V13).

### 4.2 Base de datos — `gestor/bd.py` (SQLite, `datos/gestor/<nombre>.sqlite3`)

```sql
CREATE TABLE microservicio (
  codigo TEXT, version TEXT, nombre TEXT, descripcion TEXT,
  manifiesto TEXT,           -- JSON tal cual
  fuente TEXT,               -- el programa servicio.py
  sha256_declarado TEXT, sha256_real TEXT,   -- distintos = manipulado (✘ en la ventana)
  importado TEXT,
  PRIMARY KEY (codigo, version));
CREATE TABLE orden (
  folio TEXT PRIMARY KEY, accion TEXT, destino TEXT, destino_nombre TEXT,
  codigo TEXT, version TEXT, estado TEXT, detalle TEXT, creada TEXT, cerrada TEXT);
```

Se llena con **"Importar carpeta"** (`microservicios/`), al abrir y cuando se pulse. El historial
de órdenes queda en la tabla `orden`.

### 4.3 Órdenes por el Campo de Datos — `madre/ordenes.py`

```
GEN_INYECTA {orden, destino, accion: "alta"|"cambio", manifiesto, fuente}   (gestor → madre)
GEN_BAJA    {orden, destino, accion: "baja", codigo}
CEL_RETIRO  {orden, destino, accion: "retiro"}  (la madre publica CEL_ADIOS y termina)
GEN_ACK     {orden, destino, accion}            (madre → gestor: la recibí)
GEN_RES     {orden, destino, accion, ok, detalle, gen, sustituyo, genes, ms, ruta}
GEN_PIDE    {pedido, intento, codigo, version, sha}           (cualquier madre → todos)
GEN_ENTREGA {pedido, intento, destino, gen, manifiesto, fuente} (quien lo tenga → la que pidió)
```

`orden` es el folio de la orden (`O-<hash8 gestor>-<n>`). Solo la célula con `destino == mi
hash` atiende; las demás registran `IGNORA`. Sin `GEN_ACK` en `GEN_ACK_TIMEOUT` el gestor marca
"sin respuesta". A `GEN_PIDE` contestan las madres que tienen ese gen exacto (mismo sha) y los
gestores que lo tienen en su BD, cada una tras un retardo derivado de su hash; si ya vio una
`GEN_ENTREGA` para ese pedido, se calla. La que pidió toma la primera entrega que valide.

### 4.4 Topología y diagrama vivo — `gestor/topologia.py` + `gestor/diagrama.py`

**Fuentes** (no se le pregunta nada al nodo): `BIENVENIDA`/`PARES` (endpoints), `NODO_LAT` (nodos
vivos y sus vecinos reales), `CEL_LAT` (cada célula: tipo, nodo, genes con versión y sha8,
generación, reemplaza, mudo, cola, atendidas), `CEL_ADIOS`, `CLON_AVISO`/`CLON_LISTO`, y
`TOPO_REQ` → `TOPO_RES` para una consulta inmediata (botón **Consultar**).

**Dibujo** (Tk `Canvas`, se redibuja con los latidos):
- Nodos en círculo con los **enlaces reales** de la malla (de `NODO_LAT`).
- Alrededor de cada nodo, sus células: GUI, gestores y madres; cada madre **coloreada por gen**
  (SUM/SUB/MUL/DIV), gris punteada si está vacía, con su versión (`SUM 2.0`).
- Clones con insignia `r1`, `r2` y puntos de generación; madre muda tachada.
- Caída: la célula se pone **roja** con ✕ y se desvanece; regeneración en curso: contorno
  punteado "naciendo…" junto al nodo destino, que se llena cuando el clon carga sus genes.
- **Clic en una célula la elige como destino** de la orden (evidencia V9).
- Barra de disponibilidad por código: madres vivas con el gen.

### 4.5 Ventana — `gestor/gui.py`

Izquierda: **diagrama**. Derecha: catálogo de la BD (código, versión, sha8, ✔/✘), célula destino
seleccionada con sus genes, botones **Inyectar (alta)**, **Sustituir**, **Baja**, **Retirar
célula**, **Distribuir una de cada operación por nodo** (llena el modo vacío en un clic: 16
órdenes, una por madre), **Importar carpeta**, **Consultar**. Abajo, pestañas: bitácora de órdenes
(`GEN_ACK`/`GEN_RES` con ms y ruta) y **línea de tiempo de regeneración** (§6.6).

### 4.6 Detalles fijados al implementar (S3)

- **`NODO_LAT`** lo origina el nodo cada `LATIDO` s y en cuanto cambian sus enlaces (como mucho uno
  cada 0.25 s): `{nombre, endpoint, vecinos: [{hash, nombre, endpoint}], celulas: [{hash, nombre,
  entidad}], contadores}`. Sale ya marcado como visto, con su hash en la ruta y el TTL descontado.
  El código vive en `comun/mensajes.py` (el nodo no importa el catálogo); `codigos.NODO_LAT` es el
  mismo.
- **`TOPO_REQ`** lo contesta la **célula base** (toda célula que late) con `TOPO_RES` = su latido
  + `{consulta, para}`. Los nodos no contestan: su `NODO_LAT` basta.
- **Órdenes**: solo las acepta la madre `destino` y solo si `tipo_origen == GESTOR` (si no, `DROP
  solo un gestor da órdenes`). Folio `O-<hash8>-<n>` (`foliado.folio_admin`). El `GEN_ACK` sale
  antes de trabajar; el trabajo corre en el programador de la madre (uno a la vez, fuera del hilo
  de red). Una orden repetida no se ejecuta dos veces: se reenvía su `GEN_RES`. Estados en el
  gestor: `enviada → recibida → ok | rechazada | sin respuesta (sin GEN_ACK en GEN_ACK_TIMEOUT) |
  sin resultado (sin GEN_RES en GEN_RES_TIMEOUT) | no salió`. Un `GEN_RES` tardío se acepta.
- **Pedidos**: folio `P-<hash8>-<n>`, con `intento` (el silencio de los proveedores es por
  `(pedido, intento)`, así un reintento vuelve a tener quién conteste). El `sha` puede ser prefijo
  (el `sha8` del latido). Proveedor = madre con ese gen **activo** (lo lee de su disco) o gestor con
  él **íntegro** en su BD; espera `retardo(hash, pedido, intento) ∈ [0, ENTREGA_RETARDO_MAX]` y se
  calla si ya vio una entrega. Quien pide toma la primera que valide; si una llega alterada, la
  rechaza y sigue esperando. Lado proveedor en `comun/pedidos.py`; lado de quien pide en
  `madre/pedidos.py` (`Madre.pedir_gen`).
- **"Distribuir"**: por cada nodo vivo, a cada operación que le falte se le asigna una madre
  **vacía** (no muda), en orden natural de nombre (`M1` → SUM, `M2` → SUB…), con la **versión base**
  (la íntegra más antigua: `SUM 1.0`), para que el escenario 5 muestre el cambio a `2.0`. Lo que ya
  está no se toca. Además, **"Sustituir en todas las que lo tengan"** manda el cambio a cada madre
  viva con ese código en otra versión (escenario 5 en un clic).
- **Topología**: una célula o nodo sin latido en `LATIDO_CADUCIDAD` s queda **caído** (rojo) y se
  olvida a los `CAIDA_VISIBLE` (8) s; si vuelve a latir, revive. `CEL_ADIOS` lo quita al instante.
  Un nodo que aún no manda `NODO_LAT` se dibuja ya con lo que dice su célula. El gestor se dibuja a
  sí mismo (su propio latido no le llega).
- **GUI**: los mensajes de sistema (`NODO_LAT`, `GEN_*`, `TOPO_*`, …) no cuentan como "ajenas".
- **Ventana**: diagrama + historial (órdenes / bitácora) a la izquierda; catálogo, destino y botones
  a la derecha; 1420×820. Nodos en elipse con abanicos de células hacia arriba/abajo; destellos al
  enviar (azul) y al contestar (verde / rojo). Piezas Tk compartidas en `comun/estilo.py` (tema ttk,
  botones planos, tarjetas, píldoras), para el repaso visual de S4.
- `Madre._programador` pasa a ser `Madre.programador` (lo comparten órdenes, pedidos y entregas);
  las vías de un gen (`BANCO`, `INYECCION`, `ENTREGA`) viven en `madre/almacen.py`.

---

## 5. Protocolo de foliado (§5.1) — `comun/foliado.py`

### 5.1 Definiciones

| Concepto | Definición en este sistema |
|---|---|
| **Folio** | `F-<hash8 GUI>-<n:04d>`. Lo genera la GUI con su contador (sin autoridad central). Igual en todos los reintentos y presente en **todos** los mensajes del evento (`REQ`, `ACK`, `RES`, `FIN`). |
| **Huella** | `{"origen": hash GUI, "nodo": hash del nodo de entrada, "sello": sha256(origen|folio|código|a|b), "rastro": [[hash8, nombre, paso], …]}`. El **sello** amarra folio, origen y datos; el **rastro** es la trayectoria lógica: `REQ` (GUI), `ACK` de cada madre, `RES` de quien respondió, `FIN` (GUI). La `ruta` del sobre sigue siendo la trayectoria física (nodos). |
| **Evento** | Ciclo de vida de una solicitud con folio. **INICIO**: la GUI publica `X_REQ`. **CONFIRMACIÓN**: llegan `X_ACK` del intento vigente hasta el mínimo; el evento queda *aceptado*. **PROCESAMIENTO**: la titular (o un relevo) publica `X_RES` con gen y versión. **FINALIZACIÓN**: la GUI acepta la respuesta (o agota intentos) y publica `X_FIN`; las madres cierran sus rondas. |
| **ACK** | `X_ACK`: la madre confirma recepción y participación. Sale de inmediato, antes de encolar. |
| **Min. # de ACK** | ACK del intento vigente para aceptar el evento. Por código, 2 por defecto, editable en vivo en la GUI. |
| **Esperados / ausentes** | Esperados = madres vivas con el gen al iniciar (por latidos). Al cerrar la ventana de confirmación (`VENTANA_ACUSES`, o antes si acusaron todas) la GUI registra `AUSENTES: […]`. Con el mínimo alcanzado el evento sigue (**tolerancia**). Sin mínimo: reintento; tras `MAX_INTENTOS`, `FALLIDA` y `X_FIN` con estado fallida. |

### 5.2 Mensajes

```
X_REQ {folio, intento, a, b, huella}
X_ACK {folio, intento, id_solicitud, en_cola, gen: "SUM@1.0", huella(+ACK)}
X_RES {folio, intento, id_solicitud, resultado, error, rol, ms, gen, huella(+RES)}
X_FIN {folio, intento, estado: "resuelta"|"fallida", id_respuesta, acuses, ausentes, huella(+FIN)}
```

### 5.3 Reglas de atención (folio + Código de Contenido)

**Madre:** atiende si (1) el código es de un gen **activo**; (2) en el `REQ`, `huella.origen ==
sobre.origen` y el sello recalculado coincide (si no, `DROP huella inválida`); (3) la ronda
`(código, folio, intento)` no está terminada; (4) `X_FIN` cierra todas las rondas del folio.

**GUI:** muestra una respuesta solo si el código es `X_ACK`/`X_RES`, el folio es suyo,
`huella.origen == mi hash` y el sello es el que generó. Lo demás suma a **"ajenas ignoradas"**
(contador visible) y va a la bitácora como `IGNORA`.

### 5.4 Lo visible en la GUI

Tarjeta del evento seleccionado: folio, código, sello (8), rastro, ACK `k/min` con nombres,
esperados, ausentes, titular, gen/versión, ms y la fase actual resaltada (INICIO → CONFIRMADO →
PROCESADO → FINALIZADO). Lista "Mis eventos" por folio. Mini log: `EVENTO_INICIO`, `ACUSE`,
`CONFIRMADO`, `AUSENTES`, `RESULTADO`, `FIN`. Botón **Ráfaga** (varias operaciones en vuelo).

### 5.5 Detalles fijados al implementar (S2)

- **Sello**: `sha256(origen|folio|código|repr(float(a))|repr(float(b)))`; `código` es el del gen
  (`SUM`), no el del mensaje, así que el sello vale para todo el evento. `7` y `7.0` sellan igual y
  el valor sobrevive al JSON. Operando no numérico → huella inválida.
- **Rastro**: el `X_ACK` lleva `REQ + ACK propio`; el `X_RES` lleva `REQ + los ACK que vio quien
  respondió + RES`; el `X_FIN` agrega `FIN`. Acotado a 32 pasos. La huella también lleva el `nodo`
  de entrada de la GUI (cambia tras un failover; el sello no).
- **`X_FIN`** sale cuando hay desenlace (respuesta aceptada o FALLIDA) **y** ya cerró la ventana de
  confirmación, para que lleve los ausentes. Si acusaron todas las esperadas, sale con la respuesta.
  En la madre, `X_FIN` deja las rondas del folio en estado `cerrada` (sueltan el gen) y un REQ
  tardío de ese folio ya no se acusa.
- **Madre**: un REQ que llega a una ronda ya terminada (resuelta, superada o cerrada) no se acusa.
  Los descartados por huella cuentan en `rondas.invalidas`.
- **GUI**: hasta 32 operaciones en vuelo; `solicitar()` devuelve el folio; `rafaga(n)` reparte
  `n` solicitudes entre los operadores habilitados. Un `X_ACK`/`X_RES` con mi folio pero huella
  ajena o sello alterado se ignora y deja una línea `SELLO` en el mini log; todo lo ignorado suma a
  `ajenas`. La ventana ya permite varias en vuelo, muestra "ajenas ignoradas" y tiene un botón
  **Ráfaga ×8** provisional (la tarjeta del evento llega en S4).
- Los eventos de bitácora de cierre de célula y nodo pasan de `FIN` a `DETENIDA`/`DETENIDO`, para
  que `FIN` solo signifique fin de evento.
- Colisión de folios entre dos GUIs: requiere el mismo prefijo de 8 hex (≈ 1 en 4×10⁹ por par);
  aun así el sello de cada una sería distinto. Limitación documentada.

---

## 6. Autorrecuperación (§5.3) — `madre/regeneracion.py`

### 6.1 Estado que lleva **cada** madre (distribuido)

Directorio de madres por `CEL_LAT` (hash → nombre, nodo, genes con sha, generación, visto);
nodos vivos por `NODO_LAT`; pérdidas pendientes; regeneración en curso (por `CLON_AVISO`).

### 6.2 Nivel requerido = el que había (reemplazo 1 a 1)

No hay un número de réplicas que el sistema "rellene": si el administrador levantó una sola `SUM`,
el nivel requerido de `SUM` es 1. Cada **pérdida** (madre que dejó de latir **sin** `CEL_ADIOS`)
genera **una** necesidad de reemplazo, con los genes que tenía. Una baja hecha con el gestor o un
retiro (`CEL_ADIOS`) **no** es pérdida: ese es el nuevo nivel que quiso el administrador.

### 6.3 Algoritmo (cada `LATIDO` s, en cada madre; sin input de nadie)

1. **Detectar.** Sin latido en `LATIDO_CADUCIDAD` → `CAIDA` registrada como pérdida P con sus
   genes, su nodo y su nombre. Cada madre lo detecta por su cuenta.
2. **Turno (gradual).** Si hay una regeneración en curso en el sistema, P espera (`EN_ESPERA`).
   Si no, va la pérdida pendiente de menor hash (todas eligen la misma).
3. **Clonador.** Ranking HRW de las madres vivas aptas (telómeros y cupo, §6.4) con la clave
   `hash(P)`. Rango 0 regenera. Rango r > 0 espera `r · RELEVO_CLON` s y regenera si no vio
   `CLON_AVISO` para P (tolerancia a que el clonador también caiga).
4. **Topes** justo antes de lanzar (§6.4). Si alguno falla: `NO_CLONA <motivo>`.
5. **Avisar y lanzar.** `CLON_AVISO {reemplaza, perdida, genes, hijo, nodo, clonador,
   generacion}` y lanza un proceso **madre vacía** con `--reemplaza P --copiar <genes>
   --generacion g+1`, conectado al nodo de P si sigue vivo, o al nodo vivo con menos madres.
6. **Copiar funcionalidad.** El hijo pide cada gen con `GEN_PIDE` (mismo código, versión y sha);
   quien lo tenga se lo entrega; el hijo lo **escribe en su disco**, lo valida y lo carga. Si nadie
   contesta en `PLAZO_PEDIDO` (y reintentos), lo copia del banco local si el sha coincide. Al
   tenerlos todos publica `CLON_LISTO {reemplaza, genes, fuentes}` y su `CEL_LAT` con `reemplaza`.
7. **Cerrar.** Con `CLON_LISTO` la pérdida queda resuelta en todas; tras `PAUSA_REGENERACION` va la
   siguiente. Si el hijo no aparece en `PLAZO_CLON`, el aviso caduca y se reintenta (máx.
   `MAX_REINTENTOS_CLON`).
8. **Alto.** Sin pérdidas pendientes, todas registran `NIVEL_OK` y **no se clona nada más**.

### 6.4 Mecanismo anti-cáncer (ocho límites)

| # | Límite | Evita |
|---|---|---|
| 1 | Solo se regenera por **pérdida** (sin `CEL_ADIOS`); nunca por baja, retiro, carga ni por "faltan para llegar a N" | Clonar por cualquier variación |
| 2 | **Uno a uno**: cada pérdida tiene a lo más un reemplazo vivo; se detiene al recuperar el nivel previo | Pasarse del nivel requerido |
| 3 | **Un clonador por pérdida**: HRW + `CLON_AVISO` que las demás respetan | Que todas clonen a la vez |
| 4 | El **reemplazo en curso cuenta** hasta que aparece o caduca | Clonar dos veces mientras el hijo arranca |
| 5 | **Gradual**: una regeneración en curso en todo el sistema + `PAUSA_REGENERACION` | Ráfagas; da tiempo a que todos actualicen su conteo |
| 6 | **Topes duros**: `MAX_MADRES` en total y `MAX_POR_GEN` por código | Crecimiento ilimitado por un error de conteo |
| 7 | **Telómeros**: una madre de generación ≥ `MAX_GENERACION` no puede clonar | Cadenas de clones de clones |
| 8 | **Cupo por madre**: a lo más `MAX_CLONES_MINUTO` lanzamientos por minuto | Una madre que clone sin parar |

### 6.5 Tolerancia

Cualquier madre puede regenerar a cualquier otra (todas tienen el mismo programa base y los genes
se copian por la red), así que perder todas las `SUM` no pierde el servicio. Si cae el clonador,
actúa el rango 1. Si cae el nodo de la perdida, el hijo va a otro nodo. Si nadie tiene el gen, el
banco local en disco es la última fuente.

### 6.6 Cómo se ve (sin tocar nada después de la falla)

Un clic provoca la falla (panel: **Tumbar**). Lo demás aparece solo:
- **Diagrama del gestor:** la célula se pone roja → contorno "naciendo…" → la nueva aparece y se
  colorea al cargar sus genes, con insignia `r1`.
- **Línea de tiempo de regeneración** (gestor): `CAIDA SUM-N2 (detectada por 15)` →
  `CLONADOR DIV-N4 (rango 0)` → `CLON_AVISO` → `CONECTADA SUM-N2·r1 en Nodo 2` → `GENES COPIADOS
  SUM 1.0 de SUM-N3 (disco → memoria)` → `NIVEL OK — regeneración detenida`.
- **GUIs:** el operador baja a `3/4` y vuelve a `4/4`.
- **Bitácoras** de todas las madres con la misma decisión.

### 6.7 Detalles fijados al implementar (S4)

- **Módulos**: `madre/regeneracion.py` decide (directorio, pérdidas, turno, ranking, topes);
  `madre/lanzador.py` levanta el proceso; `madre/copia.py` es lo que hace el reemplazo al nacer.
  Cada límite anti-cáncer vive en un solo método (docstring del módulo).
- **Revisión** cada `REVISION_REGENERACION` (0.5 s) en el programador de la madre. Una pérdida
  puede tocar turno desde `último latido + LATIDO_CADUCIDAD + LATIDO` (la misma hora para todas,
  porque todas oyeron el mismo último latido), y entre pérdidas listas va la de menor hash.
- **Aptas para clonar**: vivas, no mudas, generación < `MAX_GENERACION`, con cupo, y **no recién
  llegadas** (al menos `LATIDO_CADUCIDAD` s oyéndolas: una recién llegada aún no conoce a todas y
  su ranking podría diferir). Ranking `hashes.ranking(aptas, "clon:<hash perdida>", intento)`.
- **Topes duros y uno a uno** se revisan *antes* del ranking, igual en todas: si fallan, la pérdida
  queda `descartada` en todas a la vez (`NO_CLONA`).
- **`CLON_AVISO`** `{reemplaza, perdida, nodo_perdida, genes, hijo, nodo (endpoint), nodo_nombre,
  generacion, intento, rango}`. Quien lo oye sin haber detectado la pérdida la crea desde el aviso.
- **Reemplazo**: nombre `<perdida sin ·rN>·r<generación>` (`SUM-N2·r1`), generación = la de la
  perdida + 1, nodo = el de la perdida si su `NODO_LAT` sigue llegando; si no, el vivo con menos
  madres. Argumentos: `--reemplaza <hash> --perdida <nombre> --generacion g --copiar
  SUM@1.0:<sha8>,…`. Pide todos sus genes a la vez (`GEN_PIDE` con el `sha8`); si un pedido falla,
  usa el banco local solo si el sha coincide. Publica `CLON_LISTO {reemplaza, genes, fuentes,
  faltan, generacion}` (también si no pudo copiar todo: lo reporta en `faltan`).
- **Cierre**: `CLON_LISTO` resuelve; si no llega en `PLAZO_CLON` pero el reemplazo late, también.
  Si el reemplazo muere antes de estar listo, se reintenta la MISMA pérdida (no se crea otra). Tras
  `MAX_REINTENTOS_CLON` reintentos sin éxito, `descartada`. Un `CEL_ADIOS` del reemplazo en curso
  (el administrador lo retiró) la descarta. Una "pérdida" que vuelve a latir antes de su turno se
  cancela (`REVIVIO`).
- **Proceso**: intérprete base (no el lanzador del `.venv`, para que el PID sea el real),
  `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`, stdout a `DEVNULL` (bitácora en `logs/`). Se
  verificó que sobrevive a la muerte de su clonador. Registro `run/<nombre>-<pid>.json` con la hora
  de arranque; antes de terminar un PID se compara su hora de creación (Windows recicla PIDs). El
  reemplazo borra su registro al cerrarse ordenadamente.
- **Gestor** (solo muestra): la madre caída sigue en rojo hasta que aparece su reemplazo (o
  `ESPERA_REEMPLAZO`); el reemplazo se dibuja "naciendo…" (punteado azul que late) desde el
  `CLON_AVISO` hasta su primer latido y luego late en verde unos segundos. Pestaña
  **Regeneración** (se abre sola con la primera caída): `caída → clonador → conectada → gen →
  listo → en espera / nivel ok`; píldora de estado en la cabecera.
- **Pruebas**: `Sistema(regenerar=True)` lanza los reemplazos en el mismo proceso; por defecto las
  madres de las pruebas no clonan. Las pruebas en vivo usan `LATIDO_CADUCIDAD` 3 s (con todas las
  madres en un proceso, un `gc.collect()` las pausa a la vez).

---

## 7. Catálogo de mensajes y Códigos de Contenido

| Código | Publica | Atiende |
|---|---|---|
| `X_REQ`, `X_FIN` | GUI | Madres con el gen X |
| `X_ACK`, `X_RES` | Madre con el gen X | GUI dueña del folio; madres con el gen X |
| `CEL_LAT` | Madres, GUIs, gestores | GUIs (disponibilidad), madres (regeneración), gestores (topología) |
| `CEL_ADIOS` | Célula que se cierra ordenadamente | Todos (no es pérdida) |
| `NODO_LAT` | Nodos | Gestores, madres (nodo del clon) |
| `TOPO_REQ` / `TOPO_RES` | Gestor / todas las células | Células / gestor |
| `GEN_INYECTA`, `GEN_BAJA`, `CEL_RETIRO` | Gestor | La madre `destino` |
| `GEN_ACK`, `GEN_RES` | Madre destino | Gestor |
| `GEN_PIDE` / `GEN_ENTREGA` | Madre que necesita / quien lo tenga | Madres y gestores / la que pidió |
| `CLON_AVISO`, `CLON_LISTO` | Clonador / hijo | Madres, gestores |
| `SONDA_PRUEBA` | Sonda | Nadie |

Silenciosos en consola (sí en archivo): `CEL_LAT`, `NODO_LAT`, `TOPO_REQ`, `TOPO_RES`.
Entidades en `HOLA`: `NODO`, `INTERFAZ`, `MADRE`, `GESTOR`, `SONDA`.

---

## 8. Constantes nuevas (`comun/config.py`)

| Constante | Valor | Uso |
|---|---|---|
| `DIR_MICROSERVICIOS` | `<raíz>/microservicios` | Banco local |
| `DIR_DATOS` / `DIR_RUN` | `<raíz>/datos`, `<raíz>/run` | Almacenes, BD del gestor / PIDs |
| `GEN_MAX_BYTES` | 32 KiB | Tope de un programa (cabe en una línea NDJSON de 64 KiB) |
| `GEN_ACK_TIMEOUT` / `GEN_RES_TIMEOUT` | 2.0 / 10.0 | Gestor: "sin respuesta" / "sin resultado" |
| `PLAZO_PEDIDO` / `REINTENTOS_PEDIDO` | 2.0 / 3 | Copia de genes |
| `ENTREGA_RETARDO_MAX` | 0.4 | Retardo propio máximo de un proveedor antes de entregar |
| `CAIDA_VISIBLE` | 8.0 | Lo que el diagrama sigue mostrando en rojo algo caído |
| `ESPERA_REEMPLAZO` | 60.0 | Una madre caída sigue en rojo hasta su reemplazo, o hasta esto |
| `REVISION_REGENERACION` | 0.5 | Cada cuánto revisa cada madre si hay que regenerar |
| `RELEVO_CLON` | 3.0 | Espera del rango r para regenerar |
| `PLAZO_CLON` | 15.0 | Lo que se espera a que el hijo esté listo |
| `MAX_REINTENTOS_CLON` | 2 | Por pérdida |
| `PAUSA_REGENERACION` | 2.0 | Entre una regeneración y la siguiente |
| `MAX_MADRES` / `MAX_POR_GEN` | 40 / 8 | Topes duros |
| `MAX_GENERACION` | 3 | Telómeros |
| `MAX_CLONES_MINUTO` | 2 | Cupo por madre |

Heredadas: `LATIDO` 2, `LATIDO_CADUCIDAD` 6, `VENTANA_ACUSES` 1.5, `VENTANA_ELECCION` 0.5,
`RELEVO` 1.5, `MARGEN_RESULTADO` 2, `MAX_INTENTOS` 3, `ACUSES_MIN_DEFECTO` 2, etc.

---

## 9. Casos borde

| Caso | Manejo |
|---|---|
| Baja de un gen con una ronda en curso | La ronda termina con su referencia; el código deja de acusarse de inmediato |
| Sustituir por un programa manipulado (`SUM 9.9`) | Rechazado; la versión vieja sigue activa (`GEN_RES ok=false`) |
| Orden a una célula que murió | Sin `GEN_ACK` → "sin respuesta" en el gestor |
| Dos madres ven la pérdida a la vez | HRW: una sola regenera |
| El clonador muere antes de avisar | El rango 1 regenera a los `RELEVO_CLON` s |
| Nadie tiene el gen que hay que copiar | Banco local si el sha coincide; si no, el clon queda con los que sí pudo copiar y lo reporta |
| La célula "perdida" vuelve (solo estaba lenta) | Puede quedar una de más (≤ topes). Limitación documentada |
| Partición de red | Cada lado podría regenerar; los topes lo acotan. Limitación documentada |
| Célula muda | Late pero no acusa: es esperada y sale en `AUSENTES` |
| Respuesta con folio ajeno o sello alterado | La GUI la ignora ("ajenas ignoradas") |
| REQ con sello que no coincide | La madre lo descarta (`DROP huella inválida`) |
| Gestor cerrado | Nada cambia; la regeneración copia genes de otras madres |
| Retiro desde el gestor | `CEL_ADIOS` → no se regenera |

---

## 10. Panel y facilidad de grabación

### 10.1 Panel (`panel/`, fuera del sistema)
- **Configuración mínima — vacía**: 4 nodos (ventana) + 4 GUIs + 16 madres vacías (`M1-N1` …
  `M4-N4`). **Sin gestores**: los levanta el usuario.
- **Configuración mínima — con servicios**: igual, pero cada madre con su gen (`SUM-N1`, `SUB-N1`,
  … con `--genes`).
- **Gestor** por nodo (botón en la fila de cada nodo; uno por nodo, `G-N1` … `G-N4`), además de
  `uv run python -m gestor --nodo 127.0.0.1:500X` por terminal.
- **+ Nodo**, **+ Madre**, **+ Madre muda (SUM)**, **+ GUI**.
- **Tumbar** (por célula de la matriz) y atajos **Tumbar SUM-N2** y **Tumbar 3 SUM**.
- **Detener todo** (incluye los clones, por los PIDs de `run/`).
- *Implementado (S4)*: cada madre se pinta como pastilla del color de su gen (el panel lee los
  `GEN_ACTIVO`/`GEN_BAJA`/`GEN_SUSTITUIDO` de su propia bitácora); los reemplazos aparecen solos
  (`run/` + su bitácora en `logs/`). "Tumbar SUM de Nodo 2" tumba la madre de Nodo 2 que tenga
  `SUM` (sirve en los dos modos); "Tumbar 3 SUM", una con `SUM` de los nodos 1, 2 y 3. La clase
  del panel que maneja procesos se llama `Procesos` (antes `Gestor`, que se confundía con el
  gestor de microservicios). El botón de retardo del segundo parcial se quitó (ningún escenario
  lo usa).

### 10.2 Atajos para grabar
- Gestor: **Distribuir una de cada operación por nodo** (modo vacío → configuración del PDF en un
  clic, viéndose las 16 inyecciones en el diagrama).
- GUI: **Ráfaga** (varias operaciones en vuelo) para el escenario 2.
- Todo lo automático (regeneración, alto) se ve sin tocar nada (§6.6).

---

## 11. Escenarios del video (§10 del enunciado)

| # | Escenario | Qué se hace (clics) | Evidencia |
|---|---|---|---|
| 0 | Arranque y base heredada | Panel → "vacía"; gestor → "Distribuir" | Malla y células en el diagrama; 16 inyecciones; ventanas de nodo con FWD/DUP |
| 1 | Foliado | `7 + 5` en GUI-1 | Tarjeta del evento: folio, sello, rastro, ACK 4/2, RES, FIN; GUI-2 no lo muestra y su contador de ajenas sube |
| 2 | Simultáneas | Ráfaga en GUI-1 y GUI-2 casi a la vez | Cada una con sus folios; un RES por folio |
| 3 | Min. ACK | Panel → "+ Madre muda (SUM)"; `2 + 2` | ACK 4/2 de 5 esperados, `AUSENTES: SUM-N1m`, evento finalizado |
| 4 | Carga dinámica | Panel → "+ Madre" (vacía); gestor: clic en ella → inyectar `MUL 1.0` | `GEN_ESCRITO/VALIDADO/CARGADO`, ruta en disco; atiende `MUL_REQ` |
| 5 | Baja y cambio | Gestor: baja `SUM` en una madre; sustituir `SUM 1.0 → 2.0` en todas; intentar `9.9` | Deja de acusar `SUM`; `0.1 + 0.2` pasa de `0.30000000000000004` a `0.3`; `9.9` rechazado |
| 6 | Autorrecuperación | Panel → "Tumbar SUM-N2" y **no tocar nada** | Rojo → naciendo → `SUM-N2·r1` con genes copiados de otra madre |
| 7 | Anti-cáncer y gradual | Esperar; luego "Tumbar 3 SUM" | `NIVEL_OK` y nada más; los 3 vuelven **uno por uno** y se detiene |
| 8 | Topología | "+ Nodo" (Nodo 5) y "+ Madre" en él; gestor la usa | El diagrama dibuja el Nodo 5 y sus enlaces; se le inyecta un gen |
| — | Sin unidad central | Cerrar gestor y panel; operar; tumbar una madre | Sigue resolviendo y regenerando |

---

## 12. Pruebas (fase B) — `uv run python -m unittest discover -s tests -t .`

Las 106 del segundo parcial se adaptan (folio, madres, genes). Nuevas:

| Archivo | Cubre |
|---|---|
| `test_foliado.py` | Folio, sello determinista y sensible a cada campo, rastro, validación |
| `test_genes.py` | Localizar (confinado al almacén), validar (sha, tamaño, esquema), cargar (interfaz), autoprueba, activar, descargar (weakref liberado), sustituir con reversión |
| `test_microservicios.py` | Cada gen real pasa sus pruebas; `SUM 9.9` se rechaza; `SUM 2.0` da `0.3` |
| `test_flujo.py` (adaptada) | Un RES por folio, `FIN` cierra rondas, ajenas ignoradas, sello alterado, madre muda → ausentes, varias operaciones en vuelo |
| `test_gestor.py` | BD (importar, manipulado), topología (nodos por `NODO_LAT`, células y genes), inyectar/baja/sustituir/retirar por broadcast con destino, orden a célula muerta, `GEN_PIDE`/`GEN_ENTREGA` |
| `test_regeneracion.py` | Con lanzador inyectable (células en proceso): una pérdida → un clon con sus genes copiados; tres → tres **en secuencia**; retiro y baja no regeneran; una sola `SUM` → solo una; clonador muerto → rango 1; topes; telómeros; cupo |

Verificación en vivo de los 8 escenarios con el panel y el gestor; scripts que revisan bitácoras
(RES por folio, `CLON_AVISO` por pérdida, ningún `ERROR`/`Traceback`).

---

## 13. Sesiones (detalle en `ROADMAP.md`)

| Sesión | Fase | Contenido |
|---|---|---|
| S1 | 0 + A1 | Fase 0 cerrada; `hashes`; `microservicios/` + `firmar`; `madre/` (almacén, genes, rondas por código, `--genes`, `--mudo`, `CEL_LAT`, `CEL_ADIOS`); GUI con `CEL_LAT` |
| S2 | A2 | Foliado en madre y GUI (núcleo); varias operaciones en vuelo |
| S3 | A3 | Nodo (`GESTOR`, `NODO_LAT`); órdenes y pedidos en la madre; `gestor/` (BD, topología, diagrama, ventana) |
| S4 | A4 | Regeneración + lanzador; ventana de la GUI (tarjeta de evento, ráfaga); panel (dos modos, atajos, detener todo) |
| S5 | B + C | Suite adaptada y nueva; verificación en vivo de los 8 escenarios; fixes |
| S6 | D | README, ENTREGA, REPORTE_TECNICO.md (≤ 30 págs.), capturas, `.docx` |
| S7 | E | GUION_VIDEO.md, checklist (sin minutos: mensaje 19) |

---

## 14. Reporte (fase D) — esqueleto para ≤ 30 páginas

| Parte | Secciones | Págs. |
|---|---|---|
| Portada + índice | | 2 |
| I. Requisitos | Matriz de trazabilidad (IDs de `REQUISITOS.md` → archivo/función → escena del video) | 3 |
| II. Diseño | Arquitectura final y topología de demo · Heredado resumido (conexión, comunicación y ciclos, formato y códigos) · Foliado (definiciones, mensajes, reglas, diagrama de tiempo de un evento) · Tolerancia a fallas · Células madre y genes (ciclo de vida) · Gestor, BD y topología (por qué no es orquestador) · Regeneración y anti-cáncer (algoritmo, reglas de clonar y detener) | 15 |
| III. Evidencia | Pruebas automatizadas · Escenarios 1–8 con bitácoras reales y capturas · Bugs encontrados · Limitaciones y decisiones · Diferencias con la clase · Referencias APA | 9 |
| Anexo | Glosario y constantes | 1 |

---

## 15. Calidad del código ("deslumbrante")

- Módulos chicos con **una responsabilidad** (almacén ≠ cargador ≠ rondas ≠ regeneración ≠
  órdenes); `nucleo.py` solo compone.
- Tipos en todas las firmas, `dataclass` para el estado, `enum`/constantes para estados y fases.
- Docstring de módulo que explica el **porqué** y el protocolo que implementa; comentarios solo
  donde la razón no es obvia.
- Reglas heredadas: ningún `nucleo.py` importa Tk; `config.X` al usarlas; estado compartido con el
  lock de su dueño; ningún hilo de red muere por excepción; stdout en UTF-8.
- Dependencias inyectables (lanzador de clones, reloj) para que las pruebas levanten todo en
  proceso.
- Bitácoras con eventos en mayúsculas y consistentes entre módulos (fáciles de contar con scripts).
- `ruff` limpio; suite en verde tres veces seguidas.
- Ventanas cuidadas: diagrama del gestor con colores por gen y animación de caída y nacimiento;
  tarjeta de evento en la GUI.

### 15.1 Línea visual ("súper completo y bonito, simple pero clean")

- **Un solo tema** en `comun/tema.py` (solo constantes, sin Tk: lo importan las ventanas): fondo
  claro, superficies blancas, un color de acento, texto gris oscuro, una tipografía
  (`Segoe UI`) y una monoespaciada (`Cascadia Mono`/`Consolas`) para folios y bitácoras.
- **Color por gen, igual en todas las ventanas**: SUM, SUB, MUL, DIV con un color cada uno; madre
  vacía en gris; caída en rojo; clon con insignia. Lo que se ve en la GUI, el nodo, el panel y el
  diagrama coincide.
- Encabezado de cada ventana con su nombre, su rol y el nodo al que está conectada; estados como
  "píldoras" de color (conectada, vacía, muda, clon).
- Espaciado generoso, sin bordes 3D ni adornos; tablas con filas alternadas; nada se encima a
  1463×914.
- Se aplica a las ventanas nuevas (gestor, madre) y se repasa en las heredadas (nodo, GUI, panel)
  en S4. *Hecho en S4*: las cinco ventanas usan `comun/estilo.py` (tema ttk, tarjetas, píldoras,
  botones planos). GUI 460×800: teclado con los operadores del color de su gen, tarjeta del evento
  con las 4 fases como pasos, rastro compacto (`GUI-1 REQ → 4×ACK → SUM-N3 RES → GUI-1 FIN`),
  pestañas Evento / Mis eventos / Protocolo y pie fijo con "ajenas ignoradas" y Ráfaga ×8.

---

## 16. Preguntas abiertas para el usuario (cerradas, mensaje 7)

1. Huella / evento / Min. ACK → **las del PDF** (§5.1).
2. Gestor → **uno por nodo**, levantados por el usuario (§0.1, §10.1).
