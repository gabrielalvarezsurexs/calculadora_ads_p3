# Roadmap — Calculadora ADS, Tercer Parcial

Documentos: [docs/PLAN.md](docs/PLAN.md) (diseño) · [docs/REQUISITOS.md](docs/REQUISITOS.md)
(lista de verificación) · [docs/INSTRUCCIONES_USUARIO.md](docs/INSTRUCCIONES_USUARIO.md) (lo que
pidió el usuario, literal) · [docs/ENUNCIADO.md](docs/ENUNCIADO.md) (PDF literal) ·
[CLAUDE.md](CLAUDE.md) (notas internas).

**Protocolo de cada sesión**
- Al iniciar: leer este archivo, `CLAUDE.md`, la sección del plan que toque y las instrucciones
  del usuario; retomar en "Siguiente paso".
- Al cerrar: marcar casillas aquí y en `docs/REQUISITOS.md`, actualizar "Estado actual" y anotar la
  sesión en el registro. Ninguna sesión cierra con código a medias sin anotarlo.
- Orden de fases estricto: 0 → A → B → C → D → E. Si una sesión rinde de más, se adelanta la
  siguiente sin saltarse el orden.
- **No se implementa nada sin que el usuario apruebe el plan.** Instrucciones nuevas del usuario
  se anexan literal a `docs/INSTRUCCIONES_USUARIO.md` y se reflejan en plan y requisitos.

---

## Estado actual / siguiente paso

**Estado:** **S1–S7 cerradas** (fases A–E). S7: `GUION_VIDEO.md` (11 escenas, ~15 min: los 8
escenarios + arranque + "sin unidad central", con clics exactos, qué se ve, qué decir, qué hacer
si algo falla, limpieza, tablas de minutos con las 45 filas de la matriz) y
`docs/llenar_minutos.py` (matriz por ID; probado en copias). Quedan abiertos E2 y E3, que hace
el usuario (grabar el video y publicar el repo). S6: `REPORTE_TECNICO.md` → `.docx` de **30 páginas**
(contadas en Word), con bitácoras reales y 8 figuras; `README.md` completo; `ENTREGA.md` (hoja de
control para el usuario); `docs/REQUISITOS.md` marcado (quedan U1, U20, U21, U32, E2, E3: guion,
video y publicación). S5: los 8 escenarios + "sin unidad
central" verificados en vivo con procesos reales (30/30 revisiones, 0 `ERROR`/`Traceback`/
`DUPLICADA`), 21 capturas en `docs/capturas/`, fixes (ver registro), suite de **201 pruebas en
verde 3 veces seguidas**, ruff limpio, `docs/REQUISITOS.md` marcado (quedan abiertos solo los
del reporte, el guion y la entrega final).

Antes, S1–S4 (fase A): Madres con genes (S1), foliado (S2; PLAN
§5.5), gestor (S3; PLAN §4.6) y **regeneración** (S4; PLAN §6.7): `madre/regeneracion.py` (ocho
límites, cada uno en un método), `madre/lanzador.py` (proceso desacoplado + `run/`),
`madre/copia.py` (el reemplazo copia sus genes por `GEN_PIDE`, banco si nadie entrega); gestor
con animación naciendo/recién nacida y pestaña **Regeneración**; GUI con tarjeta de evento; panel
con los dos modos, botón **Gestor** por nodo y "Tumbar"; repaso visual de las cinco ventanas.
Suite: 200 pruebas en verde; ruff limpio; humo real OK (1 pérdida → 1 reemplazo; 3 SUM → 3
reemplazos uno por uno; retiro no regenera; 0 ERROR).

**Siguiente paso:** ninguna sesión de código pendiente. Lo que falta es del usuario
(`ENTREGA.md`): portada, grabar con `GUION_VIDEO.md`, minutos con `docs/llenar_minutos.py`,
regenerar el `.docx`, commit y publicar el repo. Si pide el commit: el trabajo del tercer parcial
aún no está en commits (la historia llega a la etiqueta `parcial-2`). **Cuidar el límite:** el
`.docx` está en 30 páginas exactas; llenar los minutos no agrega renglones, pero cualquier texto
nuevo en el reporte hay que compensarlo.

---

## S1 — Fase 0 + A1 (células madre y genes)

- [x] Carpeta `calculadora_ads_p3/` (clon local con historia, etiqueta `parcial-2`)
- [x] Entregables del segundo parcial a `docs/parcial2/`
- [x] uv: `pyproject.toml`, `.python-version`, `uv.lock`, ruff en `dev`
- [x] `docs/PLAN.md`, `docs/REQUISITOS.md`, `docs/INSTRUCCIONES_USUARIO.md`, `docs/ENUNCIADO.md`
- [x] `CLAUDE.md` para el tercer parcial; `.gitignore` con `datos/` y `run/`
- [x] **Plan aprobado por el usuario** (mensaje 7: gestor por nodo levantado por él, definiciones
      del PDF, entrega súper completa y visualmente clean)
- [x] `comun/tema.py` (paleta, tipografía, colores por gen; PLAN §15.1)
- [x] `README.md` del tercer parcial (versión mínima; la completa en S6). README y ENTREGA del
      segundo parcial → `docs/parcial2/`
- [x] Renombre `comun/huella.py` → `comun/hashes.py` y sus referencias
- [x] Entidades `MADRE` y `GESTOR`; códigos nuevos (con prefijos reservados) en
      `comun/codigos.py`; constantes del §8 en `config`
- [x] `microservicios/` (SUM 1.0, SUM 2.0, SUB 1.0, MUL 1.0, DIV 1.0, SUM 9.9 manipulado) +
      `comun/microservicios.py` + `.gitattributes` (bytes intactos)
- [x] `herramientas/firmar.py` (firma y `--verificar`)
- [x] `madre/almacen.py` (disco propio) y `madre/genes.py` (localizar, validar, cargar,
      autoprueba, activar, descargar, liberar)
- [x] `madre/rondas.py` (motor del segundo parcial por código) y `madre/nucleo.py`; `--genes`,
      `--mudo`, `CEL_LAT`, `CEL_ADIOS`; se borró `servidor/`; `comun/programador.py`
- [x] GUI: disponibilidad por `CEL_LAT` (genes); `CEL_ADIOS` la quita al instante
- [x] Humo: 4 nodos + 16 madres con genes resuelven las 4 operaciones con un RES; madre vacía no
      acusa; `SUM 9.9` rechazado; descarga confirmada por `weakref` (procesos reales +
      `test_genes`, `test_microservicios`, `TestGenesEnVivo`)

## S2 — A2 (foliado)

- [x] `comun/foliado.py` (folio, sello, huella, rastro, validación)
- [x] Madre: clave `(código, folio, intento)`, validación de huella, rastro en ACK/RES, `X_FIN`
- [x] GUI (núcleo): folios propios, varias operaciones en vuelo, fases del evento,
      esperados/ausentes, `X_FIN`, contador de ajenas, `rafaga()`; ventana adaptada (varias en
      vuelo, ajenas, botón Ráfaga provisional)
- [x] Humo: un RES por folio, FIN cierra rondas, ausentes con madre muda, sello alterado, ráfaga
      (procesos reales + `test_foliado` y las pruebas nuevas de `test_flujo`)

## S3 — A3 (gestor de microservicios y topología)

- [x] Nodo: entidad `GESTOR`, `NODO_LAT`
- [x] Madre: `GEN_INYECTA`, `GEN_BAJA`, `CEL_RETIRO` → `GEN_ACK`/`GEN_RES` (`madre/ordenes.py`);
      `GEN_PIDE` / `GEN_ENTREGA` (`comun/pedidos.py`, `madre/pedidos.py`); `TOPO_REQ`/`TOPO_RES`
      (en la célula base, para toda célula que late)
- [x] `gestor/bd.py` (SQLite: importar carpeta, manipulado, historial de órdenes)
- [x] `gestor/topologia.py` (modelo desde latidos) y `gestor/nucleo.py` (órdenes con folio,
      "Distribuir una de cada operación por nodo", "Sustituir en todas")
- [x] `gestor/diagrama.py` (Canvas vivo: malla, células por gen, clic = destino, destellos) y
      `gestor/gui.py`; `comun/estilo.py`
- [x] Humo: modo vacío + "Distribuir" deja la configuración del PDF; inyectar, sustituir
      (1.0 → 2.0), rechazar 9.9, baja, retiro; topología con Nodo 5 (procesos reales con la
      ventana + `test_gestor`)

## S4 — A4 (regeneración, ventanas y panel)

- [x] `madre/regeneracion.py` (detección, turno gradual, HRW del clonador, `CLON_AVISO`, ocho
      límites, `CLON_LISTO`, `NIVEL_OK`) y `madre/lanzador.py` (proceso desacoplado + PID en `run/`)
- [x] Copia de genes del hijo (`GEN_PIDE` → disco → memoria; banco local de respaldo)
- [x] Gestor: animación de caída y nacimiento; línea de tiempo de regeneración
- [x] `interfaz/gui.py`: tarjeta de evento, "Mis eventos", ajenas ignoradas, botón Ráfaga
- [x] Panel: modos vacía / con servicios (sin gestores), botón **Gestor** por nodo, + Madre,
      + Madre muda, Tumbar SUM-N2, Tumbar 3 SUM, Detener todo (con clones)
- [x] Repaso visual de las ventanas heredadas (nodo, GUI, panel) con `comun/tema.py`
- [x] Humo: tumbar una → un clon con genes copiados y alto; tres → uno por uno y alto; una sola
      `SUM` → solo una; retiro → no regenera; configuración mínima con ventanas
      (procesos reales + `test_regeneracion` + `test_panel`; capturas de las cinco ventanas)

## S5 — B + C (pruebas y fixes)

- [x] Suite heredada adaptada (folio, madres, genes)
- [x] `test_foliado`, `test_genes`, `test_microservicios`, `test_gestor`, `test_regeneracion`
- [x] Verificación en vivo de los 8 escenarios + "sin unidad central" (30/30 revisiones) +
      21 capturas a 1463×914 en `docs/capturas/`
- [x] Fixes hasta 3 corridas seguidas en verde; ruff limpio; bitácoras sin `ERROR`/`Traceback`
- [x] Marcar `docs/REQUISITOS.md`

## S6 — D (reporte)

- [x] README.md, ENTREGA.md, CLAUDE.md completos
- [x] REPORTE_TECNICO.md con bitácoras reales (**30 páginas** en Word), matriz desde
      `docs/REQUISITOS.md`
- [x] `.docx` generado y revisado (Word → PDF → páginas renderizadas)

## S7 — E (guion)

- [x] GUION_VIDEO.md con los 8 escenarios (clics exactos, qué se ve, qué decir) y comandos probados
- [x] `docs/llenar_minutos.py` adaptado a la matriz nueva
- [x] Checklist final (en `GUION_VIDEO.md` y `ENTREGA.md`)

---

## Notas heredadas útiles

- **Revisar el `.docx` (S6):** Word por COM (`Documents.Open(ruta, $false, $true)`,
  `ComputeStatistics(2)` = páginas, `SaveAs2(pdf, 17)`) y el PDF a PNG con `Windows.Data.Pdf`
  desde **Windows PowerShell 5.1** (`scratchpad/pdf_a_png.ps1`; en pwsh 7 no hay WinRT). Un
  `---` justo antes de un `# PARTE` puede quedar solo en una página y dejarla en blanco.
  `md_a_docx.py` solo abre página nueva en los `# PARTE …`.
- **Figuras del reporte:** `fig_guis_*.png` son tres capturas de GUI lado a lado
  (System.Drawing); `fig_e8_topologia.png` es el recorte del diagrama de `e8_gestor_nodo5.png`,
  cuya pestaña Órdenes salió vacía porque el guion la seleccionó justo antes de capturar (Tk no
  la había dibujado; no es bug: las filas nunca se borran).

- **Capturas (S5, la técnica buena; reemplaza a las de abajo):** el usuario **minimiza** toda
  ventana que asome, aunque sea <1 s con `-topmost` (así salieron capturas negras). Ahora nada se
  asoma: la ventana nace fuera de pantalla y se manda a (0,0) **al fondo** del orden Z
  (`SetWindowPos(HWND_BOTTOM=1, …, NOSIZE|NOACTIVATE|SHOWWINDOW)`, con `argtypes`), y se copia con
  `PrintWindow(hwnd, dc, 2)` (PW_RENDERFULLCONTENT, lee DWM aunque esté tapada) desde código
  **sin** conciencia de DPI → sale a 1463×914 lógicos, nítida. Ventanas **del mismo proceso**: se
  capturan **desde su propio hilo de Tk** (10 ms); hacerlo desde otro proceso congeló los
  `after()` de Tk varios minutos. Ventanas de **otro proceso** (nodos): subproceso con `Popen` +
  sondeo por `after`. Guiones: `scratchpad/humo_s5.py`, `capturar_fondo.py` (temporales).
- Pantalla del usuario: 2560×1600 al 175 % (1463×914 lógicos). Operar ventanas sin quitarle el
  foco: `PostMessage` (`WM_SETFOCUS` y luego solo `WM_KEYDOWN`/`WM_KEYUP`; `*` y `/` por teclado
  numérico) o, mejor, llamar los métodos de la ventana en proceso.
- **Tk con varias raíces en un proceso** (humo S5): las variables sin `master` se pegan a la
  primera raíz; dar siempre el dueño (`tk.StringVar(self.raiz, …)`).
- **Capturas del gestor (S3):** `PrintWindow` **traba el hilo de Tk si la ventana está
  minimizada** (el usuario la minimiza si le tapa el trabajo) y, con la ventana fuera de pantalla,
  entrega un `Canvas` viejo. Lo que funcionó: ventana fuera de pantalla (`+-1450+0`); para cada
  captura, `-topmost` + `geometry("+0+0")` + `update()`, copia de **pantalla** (`StretchBlt`
  HALFTONE a /1.75 desde un proceso DPI-aware) y de vuelta fuera. Guion de humo en
  `scratchpad/humo_s3.py` (temporal).
- En Windows `connect()` a un puerto cerrado tarda ~2 s (por eso existe `REINTENTO_TIMEOUT`).
- En Windows `terminate()` deja código de salida 1 (el panel lo muestra como `tumbado`).
- Los clones no los lanza el panel: los lanza su clonador y quedan en `run/` (el panel los muestra
  y "Detener todo" los termina; en un humo propio: `madre.lanzador.registrados()` + `terminar`).
- **Capturas de ventanas de OTRO proceso (S4):** lanzarlas fuera de pantalla (`--geometria
  …+-3000+0`) y, para capturar, `SetWindowPos(HWND_TOPMOST, 0, 0, SWP_NOSIZE|NOACTIVATE|
  SHOWWINDOW)` → copia de pantalla → regresarla. **Declarar `argtypes`** (HWND de 64 bits): sin
  ellos `HWND_TOPMOST = -1` llega mal y la ventana no se mueve (captura negra). Guiones en
  `scratchpad/humo_s4*.py` y `capturar_externa.py` (temporales).
- Un `venv` de Windows arranca Python con un lanzador: el PID de `Popen` no es el del intérprete.
  Por eso `madre/lanzador.py` usa `sys._base_executable` (solo librería estándar).

---

## Registro de sesiones

| Fecha | Sesión | Qué se hizo | Pendiente | Problemas abiertos |
|---|---|---|---|---|
| 2026-11-13 | S1 (Fase 0) | Repo nuevo por clon local, archivo del segundo parcial, uv. Plan v1 → el usuario aclaró el modelo (células madre, gestor con BD que inyecta por el Campo de Datos y dibuja la topología, regeneración gradual sin orquestador que copia genes, dos modos de arranque, reemplazo 1 a 1, video fácil, código deslumbrante) → plan v2, requisitos, transcripciones literales, `CLAUDE.md`. Sin código. | Aprobación del plan; preguntas del §16. | — |
| 2026-11-17 | S1 (A1) | Mensaje 7: plan aprobado; gestor uno por nodo levantado por el usuario; definiciones del PDF; entrega visualmente clean (`comun/tema.py`, PLAN §15.1). Código: `hashes`, catálogo con prefijos reservados, banco de 6 genes firmado, `madre/` (almacén, genes, rondas, núcleo, CLI), latido genérico `CEL_LAT` en la célula base, `CEL_ADIOS`, GUI por genes, panel lanza madres, `formato` con flotantes exactos. Pruebas nuevas: `test_genes`, `test_microservicios`, `TestGenesEnVivo`; 134 en verde. Humo con procesos reales OK. | S2 (foliado). | Ninguno. Nota: en humo con procesos, no dejar stdout en un pipe sin leer (se bloquean). |
| 2026-11-17 | S2 (A2) | `comun/foliado.py`; rondas por folio con huella validada (`DROP huella inválida`), rastro en ACK/RES y `X_FIN` que cierra rondas (estado `cerrada`); GUI con folios propios, varias en vuelo, cuatro fases, esperados/ausentes, FIN tras la ventana de confirmación, `ajenas`, `rafaga()`; ventana adaptada. `hashes.de_operacion` eliminado. Eventos de cierre `FIN` → `DETENIDA`/`DETENIDO`. Pruebas: `test_foliado` + 9 nuevas en `test_flujo`; 158 en verde. Humo real: 17 folios, 1 RES y 1 FIN c/u, muda en AUSENTES, 4 DROP, 0 ERROR. | S3 (gestor). | Ninguno. |
| 2026-11-17 | S3 (A3) | Mensaje 9 ("Procede con la sección 5.5": §5.5 ya estaba; se toma como visto bueno para S3). Nodo origina `NODO_LAT`; célula base contesta `TOPO_REQ`; madre: órdenes (`GEN_ACK` inmediato, trabajo en su programador, solo de un `GESTOR`, repetidas no se re-ejecutan) y pedidos (`Madre.pedir_gen`, proveedor con retardo HRW y silencio). `gestor/`: BD SQLite, topología con caída/olvido, órdenes con folio `O-…` y estados, "Distribuir" (versión base), "Sustituir en todas", entrega de genes desde la BD, diagrama vivo con destellos, ventana con `comun/estilo.py`. GUI: los mensajes de sistema no cuentan como ajenas. Pruebas: `test_gestor` (22); 180 en verde. Humo real con ventana: 16 altas ok, 2.0 ok, 9.9 rechazado, caída roja, retiro con salida 0; 0 ERROR. | S4 (regeneración, panel, repaso visual). | Ninguno. Capturas: ver nota del gestor arriba. |
| 2026-11-17 | S4 (A4) | Mensaje 10 ("Procede con la sesión 4, checa que quede chido (y que lo que lleves vaya bien)"). `madre/regeneracion.py` (detección, turno gradual con hora común, HRW sobre aptas no recién llegadas, topes antes del ranking, `CLON_AVISO`, reintentos, `NIVEL_OK`, `REVIVIO`), `madre/copia.py`, `madre/lanzador.py` (intérprete base, desacoplado, `run/` con hora de creación). Madre: `--reemplaza/--perdida/--copiar/--generacion/--sin-regenerar`, atiende `NODO_LAT`, `CEL_ADIOS`, `CLON_*`. Gestor: caídas de madre hasta su reemplazo, naciendo/recién nacida, pestaña Regeneración, píldora de estado. GUI rehecha (tarjeta de evento, 4 fases, rastro compacto). Panel rehecho (`Procesos`, dos modos, Gestor por nodo, pastillas por gen, reemplazos de `run/`, Tumbar SUM N2 / 3 SUM). Nodo restilizado. Pruebas: `test_regeneracion` (15), `test_panel` (4), topología (+1); 200 en verde. Humo real: 4 reemplazos, 4 avisos, 0 ERROR; retiro sin regenerar; Detener todo deja 0 procesos. | S5 (escenarios en vivo, fixes, 3 corridas). | Tiempos de `test_flujo` bajo carga (ver Siguiente paso). |
| 2026-11-17 | S5 (B + C) | Mensajes 11–12. Humo en vivo de E0–E8 + final con procesos reales (`Procesos` del panel, 4→5 nodos, 16 madres vacías, GUIs y gestor en proceso): 30/30, 10 avisos = 10 reemplazos, 0 `ERROR`/`Traceback`/`DUPLICADA`/`NO_CLONA`; 21 capturas → `docs/capturas/`. Fixes: (1) dos titulares por ACK tardío bajo carga → `VENTANA_ELECCION` de pruebas = la de producción (0.5 s); (2) `ENTREGA` repetida en la línea de tiempo cuando dos madres entregan el mismo gen → `Gestor._rx_entrega` (solo la primera; la otra a la bitácora) + prueba; (3) el diagrama dejaba de repintarse para siempre si su primer dibujo llegaba sin tamaño (`ValueError '10c'`) → `winfo_req*`; (4) `invalid command name` al cerrar → `estilo.cerrar` en las cinco ventanas; (5) `StringVar`/`BooleanVar` sin dueño (mín. ACK mal con varias raíces) → `master` explícito; (6) fichas de madres cortadas en el panel con 5+ por nodo → renglones según el ancho libre. Técnica nueva de capturas (notas). Suite 201 en verde ×3; ruff limpio; `REQUISITOS.md` marcado. | S6 (reporte). | Ninguno. |
| 2026-11-18 | S6 (D) | Mensaje 13 ("Sigue con S6"). `REPORTE_TECNICO.md` (Partes I–III, matriz con ID → archivo/función → sección → `<mm:ss>`, tablas de escenarios/evidencias y de contenido D1–D14, bitácoras reales de la corrida S5 de madres, nodos, GUIs y gestor, 8 figuras, APA) → `.docx` de 30 páginas revisado página por página. `md_a_docx.py`: solo los `# PARTE` abren página (portada sola). `README.md` completo, `ENTREGA.md` nuevo, `REQUISITOS.md` marcado (U2, E1, O1, M5, P7, D1–D14). | S7 (guion, `llenar_minutos.py`, checklist). | Ninguno. Reporte en el límite de 30 páginas. |
| 2026-11-18 | S7 (E) | Mensaje 14 ("Dale a S7"). `GUION_VIDEO.md`: 11 escenas con lo que se ve cotejado contra el código y la corrida S5 (etiquetas de botones, fichas del panel `SUMm · muda`/`M1·r1 · SUM`, mensajes del gestor; `VIVA`/`CADUCA` de la GUI solo van al archivo, no a "Protocolo"); antes de grabar (procesos, `logs\anteriores`, suite), comandos probados (conteo de RES por folio en `logs\*.log`: 148 folios, 1 RES c/u; listado del gen en disco), tabla de fallas en vivo, limpieza, minutos (45 filas generadas desde el reporte). `docs/llenar_minutos.py` por ID (probado en copias: escribe las 45, respeta minuto propio, rechaza faltantes y requisitos distintos). `REQUISITOS.md`: U1, U20, U21, U32. | Lo del usuario (`ENTREGA.md`). | Ninguno. |
