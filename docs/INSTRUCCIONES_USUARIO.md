# Instrucciones del usuario (transcripción literal)

Todo lo que el usuario ha pedido para el tercer parcial, **copiado tal cual** (con su ortografía),
en orden. Debajo de cada mensaje, cómo quedó en el plan. Si algo de aquí choca con `PLAN.md`,
manda esto (y el PDF manda sobre lo visto en clase). Al agregar instrucciones nuevas, se anexan al
final con fecha.

---

## Mensaje 1 — 2026-11-13 (con el PDF adjunto)

> A ver, ahora viene la tercera evolución del proyecto, puede ser el mismo repo u otro de la
> última entrega, tu sabrás. Te comparto las instrucciones, la diea es la misma, tener un
> reporte, un guión, el código y lo necesario para grabar un video. El reporte igual que antes
> que no pase de 30 páginas.
>
> Igual vamos a usar las cosas q ya teniamos como uv para manejar paquetes, buena estructura de
> carpetas, etc.

**Cómo quedó:** repo nuevo `calculadora_ads_p3/` (clon local del segundo parcial, que no se toca).
Entregables: reporte (**≤ 30 páginas**), guion, código y todo lo necesario para grabar. **uv**
para el entorno (`pyproject.toml`, `uv.lock`, `.python-version`, ruff en `dev`), estructura de
carpetas limpia.

## Mensaje 2 — 2026-11-13

> ARMA EL PLAN/ROADMAP PRIMERO EH, NO EMPIECES A IMPLEMENTAR SIN HABLAR CONMIGO

**Cómo quedó:** regla permanente: primero plan y roadmap; **no se implementa nada sin su
aprobación explícita**.

## Mensaje 3 — 2026-11-13

> Tambien para autoregeneracion que no se genere cancer, que los servicios sean programas en una
> carpeta y los jale, etc

**Cómo quedó:** los microservicios son **programas en una carpeta** (`microservicios/`); las
células los **jalan**. La autorregeneración tiene límites contra el **cáncer** (PLAN §6.4).

## Mensaje 4 — 2026-11-13

> regeneraicion de celulas es gradual, tambien hay que tener gestor de microservicios (RECUERDA,
> NO HAY UN ORQUESTADOR)

**Cómo quedó:** regeneración **gradual** (un reemplazo a la vez, con pausa). Hay **gestor de
microservicios**, pero **no hay orquestador**: las células deciden solas; el gestor es una
herramienta administrativa que solo actúa cuando alguien lo usa (PLAN §4.1).

## Mensaje 5 — 2026-11-13 (respuesta a las preguntas del primer borrador)

> Esto del gestor basicamente es que tenemos campo de datos y tenemos interfaces graficas (igual
> que como las hemos tenido) pero ahora vamos a tener celulas vacías, que pueden ahcer culquier
> tipod e operación, 4 de ellas por nodo (estas son las q jalan los programas), son celulas
> madres que estan vidas y generamos una nueva interfaz en los nodos que se llama gestor y que
> tiene una base de datos con todos los servicios (lo que te hbaia dicho) y de aqui las celulas
> lo pueden jalar). desde el gestor muestras como esta la topologia del sistema (similar a lo q
> ya teníamos), si se pudiera ver esa topología desde el gestos q muestre el diagrama/dibujos
> mejor, con este gestor puedes inyectar microservicios por el campo de datos a las celulas
> "madre". En general, al ser la entrega final, no quiero que este tan complicado DE GRABAR EL
> VIDEO, pero el codigo si debe de ser deslumbrante.
>
> Lo que ya teniamos definido pues basate en esto, EN PYTHON SEGUIMOS, lo de los topes me aprece
> pero si solo queremos levantar una celula, solo hay q levantar una, y que hayan las 2 opciones,
> de arrancar todo vacio o todo levantado (el funcionamiento se mantiene).
>
> La idea es primero ARMAR EL ROADMAP Y ANOTAR TODOS LOS REQUISITOS SIN QUE SE VAYA UN SOLO
> DETALLE (haz una transcripcion de lo que te dije y todas las instrucciones del pdf para que no
> se pierdan cuando compacte la conversacion). Tambien actualiza el claude.md para que sepa a
> donde referenciar y que sepas en que vamos a estar trabajando y que requisitos hya, pero que no
> todo quede en el claude.md, por eso te pido que referencies otros mds con la documentación
> necesaria.
>
> Las celulas al rehacerlas deben de copiar la funcionalidad necesaria

**Cómo quedó (cada frase):**

| Lo que dijo | Decisión en el plan |
|---|---|
| Campo de Datos e interfaces gráficas igual que antes | Nodos y GUIs heredados del segundo parcial (con foliado encima). |
| Células vacías que pueden hacer cualquier operación, 4 por nodo | **Células madre** (`madre/`): un solo programa base genérico, sin lógica de operaciones; 4 por nodo en la configuración de demo. |
| Ellas son las que jalan los programas | La célula guarda el programa en **su disco** y de ahí lo carga a memoria (PLAN §3). |
| Células madre que están vivas | Arrancan, se conectan y laten aunque no tengan genes; aparecen en la topología como "vacías". |
| Nueva interfaz en los nodos llamada gestor | **Gestor de microservicios** (`gestor/`): una interfaz más que se conecta a un nodo como las GUIs. Se pueden abrir varios (p. ej. uno por nodo); ninguno es indispensable. |
| Con una base de datos con todos los servicios | **SQLite** (`sqlite3`, librería estándar) con los programas, versiones, sha256 y el historial de órdenes; se llena importando la carpeta `microservicios/` (PLAN §4.2). |
| De aquí las células lo pueden jalar | Una célula puede **pedir** un gen por el Campo de Datos (`GEN_PIDE`) y el gestor (o cualquier célula que lo tenga) se lo **entrega** (`GEN_ENTREGA`). |
| Mostrar la topología, similar a lo que ya teníamos | Árbol/tabla de nodos, células y genes, como las ventanas del nodo. |
| Mejor si muestra el diagrama/dibujos | **Diagrama vivo** en un `Canvas`: nodos en malla con sus enlaces reales, células alrededor de su nodo coloreadas por gen, clones marcados, caídas en rojo (PLAN §4.4). |
| Inyectar microservicios por el Campo de Datos a las células madre | Orden `GEN_INYECTA` con el programa dentro del mensaje, dirigida por contenido a la célula destino (PLAN §4.3). |
| No tan complicado de grabar | Panel con los **dos modos de arranque** y botones de escenario de un clic; gestor con "Distribuir una de cada operación por nodo"; GUI con botón de ráfaga para las solicitudes simultáneas (PLAN §10). |
| El código sí debe ser deslumbrante | Estándares de calidad del §15 del plan (módulos chicos con una responsabilidad, tipos, dataclasses, docstrings, ruff, pruebas, diagrama vivo). |
| Basarse en lo ya definido | Se conserva todo el diseño del segundo parcial y del primer borrador que no contradiga este mensaje. |
| EN PYTHON SEGUIMOS | Python 3.14, librería estándar; sin Java. |
| Los topes le parecen | Se conservan tope duro y telómeros (PLAN §6.4). |
| Si solo queremos levantar una célula, solo hay que levantar una | **No hay un número fijo de réplicas que el sistema "rellene".** El nivel requerido es el que existía antes de la falla: cada célula perdida se reemplaza 1 a 1, y nada más (PLAN §6.2). |
| Dos opciones: arrancar todo vacío o todo levantado | Panel: **"Configuración mínima — vacía"** (16 madres sin genes) y **"— con servicios"** (cada madre arranca con su gen). Después el funcionamiento es idéntico (PLAN §10.1). |
| Anotar todos los requisitos sin perder detalle | `docs/REQUISITOS.md` (lista con identificadores), `docs/ENUNCIADO.md` (PDF literal) y este archivo. |
| Actualizar CLAUDE.md, pero que no todo quede ahí | `CLAUDE.md` corto que referencia `ROADMAP.md`, `docs/PLAN.md`, `docs/REQUISITOS.md`, `docs/ENUNCIADO.md` y este archivo. |
| Las células al rehacerlas deben copiar la funcionalidad necesaria | El reemplazo nace vacío y **copia los genes** que tenía la célula perdida, pidiéndolos por el Campo de Datos a quien los tenga (otras madres o un gestor) (PLAN §6.3). |

## Mensaje 6 — 2026-11-13

> y recuerda, la autorecuperacion debe de no necesitar input del usuario (y debemos de poder
> mostrarlo FACILMENTE para el video)

**Cómo quedó:** la autorrecuperación es **100 % automática**: nadie pulsa nada después de la
falla (ni gestor, ni panel, ni GUI). Para mostrarla fácil: un solo clic en el panel provoca la
falla ("Tumbar una célula" / "Tumbar 3 SUM") y todo lo demás se **ve solo** en el diagrama vivo
del gestor (célula en rojo → aviso de clonación → célula nueva que aparece y se llena con sus
genes), en una línea de tiempo de recuperación y en la disponibilidad de las GUIs (PLAN §6.6).

## Mensaje 7 — 2026-11-17 (respuesta a las preguntas del plan v2 y aprobación)

> 1- Un gestor por nodo pero dame la opcion de yo levantarlo
>
> 2- Usa las definiciones del pdf, genuinamente lo podemos manejar como queramos
>
> Extra- Como dije, al ser la entrega final la idea es q quede super completo y bonito
> visualmente el proyecto (Simple, pero clean) para la ultima entrega.
>
> Considerando esto anotalo y procede con la sesión 1.

**Cómo quedó:**

| Lo que dijo | Decisión en el plan |
|---|---|
| Un gestor por nodo | El diseño de la demo es **un gestor por nodo** (hasta 4, cada uno con su BD). Todos ven la topología completa y pueden mandar órdenes a cualquier madre; ninguno es indispensable (PLAN §4.1). |
| …pero dame la opción de yo levantarlo | La configuración mínima del panel **no** abre gestores: el usuario los levanta cuando quiere, con un botón **Gestor** por nodo en el panel (o por terminal con `uv run python -m gestor --nodo …`) (PLAN §10.1). |
| Usa las definiciones del PDF | Huella, evento y Min. ACK se definen como en el PDF (PLAN §5.1). Pregunta cerrada. |
| Lo podemos manejar como queramos | Libertad de diseño dentro del PDF; se documenta la decisión en el reporte. |
| Súper completo y bonito visualmente, simple pero clean | **Línea visual única** para todas las ventanas (nodo, GUI, madre, gestor, panel): paleta y tipografía compartidas en `comun/tema.py`, colores por gen consistentes en todo el sistema, espaciado generoso, sin adornos. Todos los requisitos cubiertos y nada a medias (PLAN §15.1). |
| Anótalo y procede con la sesión 1 | **Plan aprobado.** Se empieza S1. |

## Mensaje 8 — 2026-11-17

> Dale a la sesión 2, foliado

**Cómo quedó:** se implementa S2 (foliado) según el plan; detalles fijados en PLAN §5.5.

## Mensaje 9 — 2026-11-17

> Procede con la sección 5.5

**Cómo quedó:** el §5.5 del plan es el registro de lo fijado en S2 (ya implementado); se toma como
visto bueno para seguir con la siguiente sesión, **S3 (gestor)**.

## Mensaje 10 — 2026-11-17

> Procede con la sesión 4, checa que quede chido (y que lo que lleves vaya bien)

**Cómo quedó:** se implementa S4 (regeneración, lanzador, ventanas y panel) según el plan, con
repaso visual de todas las ventanas y una revisión de lo ya hecho (S1–S3): suite completa, humo
con procesos reales y capturas.

## Mensaje 11 — 2026-11-17

> Dale a la sesión 5 (y antes de comenzar, cuantas sesiones faltan?)

**Cómo quedó:** faltan tres contando esta (S5 pruebas y fixes, S6 reporte, S7 guion). Se
implementa S5: los 8 escenarios en vivo con capturas, fixes, tres corridas seguidas en verde y
`docs/REQUISITOS.md` marcado.

## Mensaje 12 — 2026-11-17

> sigue?

> Ok, ahora que sigue? Ya el reporte no?

**Cómo quedó:** S5 se termina primero (humo de los 8 escenarios, tres corridas de la suite,
requisitos marcados); el reporte es S6 y empieza cuando el usuario lo indique.

## Mensaje 13 — 2026-11-18

> Sigue con S6

**Cómo quedó:** se implementa S6 (fase D): README, ENTREGA y CLAUDE completos,
`REPORTE_TECNICO.md` (≤ 30 páginas) con bitácoras reales y capturas, `.docx` generado y revisado.

## Mensaje 14 — 2026-11-18

> Dale a S7

**Cómo quedó:** se implementa S7 (fase E): `GUION_VIDEO.md` (escenas con clics exactos, qué se
ve y qué decir, tablas de minutos), `docs/llenar_minutos.py` adaptado a la matriz por ID y
checklist final.

## Mensaje 15 — 2026-11-18

> el proyecto es calculadora_ads, no?

> osea tengo q crear un nuevo repo no?

> Ya quedó

**Cómo quedó:** el tercer parcial vive en `calculadora_ads_p3/` (el segundo, en `calculadora_ads/`,
no se toca). El usuario creó el repo `calculadora_ads_p3` en GitHub e hizo commit y push
("Entrega Final ADS").

## Mensaje 16 — 2026-11-18

> Ahora, hazle una auditoría completa a la implementacion para encontrar bugs ver que este bien
> pero no demasiado largo el guion, y que el reporte tampoco sea exageradamente extenso

**Cómo quedó:** auditoría en 5 áreas con revisores independientes; se corrigieron los defectos
confirmados (casos borde de regeneración, GUI, gestor, protocolo y panel) con 12 pruebas nuevas
(213 en verde) y un humo real. Guion recortado de ~15 a ~12 min. El reporte se mantiene en
≤ 30 páginas: su extensión va en el diseño que pide el enunciado; se recortó §1.4 y la auditoría
va en un párrafo de §13.

## Mensaje 17 — 2026-11-18

> Corrige los issues menores que encontraste

**Cómo quedó:** se corrigieron los cuatro casos menores que la auditoría había dejado anotados
(enlace duplicado que perdía mensajes en vuelo, BIENVENIDA tardía que parecía desconexión, nodo
detenido con un enlace a medio abrir, `GEN_LIBERADO` que dejaba de vigilarse), con 4 pruebas
nuevas (217 en verde).

## Mensaje 18 — 2026-11-25

> Entonces, ya esta al 100 el proyecto? obvio me falta grabar el video pero ya esta el reporte, el
> guion con lo que hay que ejecutar LEGIBLE, etc? tambien armame un archivo como en el parcial 2
> que contenga todos los detalles relevantes del proyecto par que le haga una auditoria al reporte
> tecnico por mi cuenta

**Cómo quedó:** se revisó el estado de la entrega (lo que falta es del usuario) y se armó
`RESUMEN_PROYECTO.md`, con la misma estructura que el del segundo parcial, sacado del código.

## Mensaje 19 — 2026-11-25

> Quita la seccion de minutos

**Cómo quedó:** el enunciado no pide minutos. Se quitó la sección "Minutos" del guion y
`docs/llenar_minutos.py`; la columna "Video" de la matriz del reporte ahora da la **escena** del
video en que se demuestra cada requisito (no hay nada que cronometrar).

## Mensaje 20 — 2026-11-25

> Lo de minutos no lo piden las intrucciones vdd?

**Cómo quedó:** confirmado: el enunciado solo pide un video con audio que demuestre los escenarios
(§2 E2 y §10); los minutos eran una convención propia heredada del segundo parcial.

## Mensaje 21 — 2026-11-25 (con el PDF final del reporte adjunto)

> A ver, así quedó el reporte al final (solo falta lo del video); checa si tienes que ajustarle
> algo al guion, y agrega este al repo, este es el bueno bueno (checa que no haya eliminado algo
> por accidente innecesariamente pero si busque resumirlo)

**Cómo quedó:** el PDF editado por el usuario (29 páginas) quedó en la raíz como
`Reporte_Tecnico_Calculadora_ADS.pdf`, y es **la versión que se entrega**. `REPORTE_TECNICO.md` y el
`.docx` quedan como la versión extendida de trabajo. Se cotejó el PDF contra el `.md`: no falta
ningún requisito de la matriz, ni D1–D14, ni escenarios; los recortes fueron de detalle. El guion
no cambia salvo su checklist final (la liga va en la portada del PDF). ENTREGA, README, RESUMEN,
CLAUDE y ROADMAP apuntan al PDF.

## Mensaje 22 — 2026-11-25

> bueno esque esto es aprcial 3 ya ni aprical 2

**Cómo quedó:** se aclaró que la etiqueta `parcial-2` no entrega nada del segundo parcial: marca
el commit `cc7bdce` (17-oct), el último del segundo parcial dentro de este mismo repo, para que se
vea qué es heredado y qué es nuevo (§16 del reporte). Subirla es opcional; si no se sube, conviene
quitar esa frase del §16.

## Mensaje 23 — 2026-11-25 (con el PDF corregido adjunto)

> Aqui esta corregido el repotre, deja este como el bueno

**Cómo quedó:** el PDF corregido reemplazó a `Reporte_Tecnico_Calculadora_ADS.pdf` (sigue en 29
páginas). Trae `r x RELEVO` y `r x RELEVO_CLON` en los tres lugares, las celdas ya sin palabras
partidas, "puntos suspensivos" en el §1.4, la fila "Cae un nodo" de vuelta en el §9 y fecha de
entrega 25/11/2026. Solo falta la liga del video.

---

## Respuestas a las preguntas del primer borrador

| Pregunta | Respuesta del usuario |
|---|---|
| ¿Definición de huella/evento/Min. ACK de la clase? | "Usa las definiciones del pdf, genuinamente lo podemos manejar como queramos" (mensaje 7) → las del PDF (PLAN §5). |
| ¿Un gestor o uno por nodo? | "Un gestor por nodo pero dame la opcion de yo levantarlo" (mensaje 7) → uno por nodo, los levanta el usuario. |
| ¿Objetivo 4 / máximo 6 por servicio? | "lo de los topes me parece, pero si solo queremos levantar una célula, solo hay que levantar una" → sin objetivo fijo; reemplazo 1 a 1; topes duros sí. |
| ¿Arrancar con servicios o vacío? | Las **dos opciones**. |
| ¿Java? | **Python**. |
