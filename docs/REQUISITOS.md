# Requisitos — lista de verificación

Cada requisito del PDF (`docs/ENUNCIADO.md`, texto literal) y de lo que pidió el usuario
(`docs/INSTRUCCIONES_USUARIO.md`, texto literal), con dónde se resuelve en el plan, en qué sesión
y con qué se demuestra. Se marca `[x]` cuando está implementado **y** verificado (fase B/C).
La matriz de trazabilidad del reporte sale de esta tabla.

Columnas: **ID** · **Requisito (resumen)** · **Plan** (sección de `docs/PLAN.md`) · **Sesión** ·
**Evidencia** (escenario del video §11 del plan / prueba).

**Verificación S5 (2026-11-17):** humo en vivo de los 8 escenarios + "sin unidad central" con
procesos reales (4 nodos → 5, 16 madres vacías, 4 GUIs, gestor `G-N1`): **30/30 revisiones OK**,
bitácoras con 0 `ERROR`, 0 `Traceback`, 0 `DUPLICADA`; 21 capturas a 1463×914. "Humo S5 E*n*"
en la evidencia = ese escenario de esa corrida. Suite completa 3 veces seguidas en verde; ruff
limpio.

---

## Usuario (manda sobre el plan)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | U1 | Entregables: reporte, guion, código y lo necesario para grabar el video | §13, §14 | S6–S7 | `REPORTE_TECNICO.md` + `.docx` · `GUION_VIDEO.md` · `ENTREGA.md` · repo (falta publicarlo: E3) |
| [x] | U2 | Reporte de **máximo 30 páginas** | §14 | S6 | Conteo en Word: **30** (S6) |
| [x] | U3 | **uv** para paquetes, buena estructura de carpetas | §0.1, §2 | S1 | `pyproject.toml`, `uv.lock` |
| [x] | U4 | Repo: el mismo u otro, a criterio → repo nuevo por clon local | §0 | S1 | `calculadora_ads_p3/` |
| [x] | U5 | **No implementar sin aprobar** plan/roadmap | §0.1 | Siempre | — |
| [x] | U6 | Los servicios son **programas en una carpeta** y las células los **jalan** | §3 | S1, S3 | Esc. 4 · humo S5 E4 (`microservicios/` → `datos/celulas/M5-N2-…/genes/MUL/1.0/`) |
| [x] | U7 | Autorregeneración **sin cáncer** | §6.4 | S4 | Esc. 7 · `madre/regeneracion.py` (8 límites) · `TestRegla` (topes, telómeros, cupo) · humo S5 E7 (tras el alto, un solo aviso) |
| [x] | U8 | Regeneración **gradual** | §6.3 paso 2, §6.4 #5 | S4 | Esc. 7 (uno por uno) · `test_tres_perdidas_uno_por_uno`, `test_tres_sum_vuelven_uno_por_uno` · humo S5 E7 (`EN_ESPERA` entre reemplazos) |
| [x] | U9 | Hay **gestor de microservicios** | §4 | S3 | Esc. 4, 5, 8 · `gestor/`, `test_gestor` · humo S5 E0–E8 |
| [x] | U10 | **No hay orquestador** | §1, §4.1, §6 | Todas | Esc. "sin unidad central" · humo S5 final (gestor cerrado: 9−4 = 5 y regeneró `M4-N3·r1`) |
| [x] | U11 | Campo de Datos e interfaces gráficas igual que antes | §1 | S1–S2 | Esc. 0 · humo S5 E0 (captura del nodo) |
| [x] | U12 | **Células vacías** (madre) que pueden hacer cualquier operación, **4 por nodo**, vivas | §0.1, §3.4 | S1 | Esc. 0 (modo vacío) · humo S5 E0 (16 madres vacías vistas por el gestor) |
| [x] | U13 | Las madres son las que **jalan** los programas | §3.2 | S1, S3 | Esc. 4 · `GEN_PIDE` (`TestPedidos`) · humo S5 E6 (el reemplazo pide SUM 2.0) |
| [x] | U14 | **Gestor** como nueva interfaz conectada a los nodos | §4 | S3 | Esc. 4 · `python -m gestor` (entidad `GESTOR`) · humo S5 E0 |
| [x] | U15 | Gestor con **base de datos con todos los servicios** | §4.2 | S3 | Ventana del gestor (catálogo de 6 genes, 9.9 marcado) · `TestBaseDatos` |
| [x] | U16 | Las células pueden **jalar** del gestor | §4.3 (`GEN_PIDE`) | S3 | `test_b_el_gestor_entrega_de_su_bd` · humo S5 E6 (SUM 2.0 copiado de G-N1) |
| [x] | U17 | El gestor **muestra la topología** (como antes) | §4.4 | S3 | Esc. 8 · `test_a_topologia…`, `test_j_nodo_nuevo…` · humo S5 E8 |
| [x] | U18 | Topología como **diagrama/dibujo** | §4.4 | S3 | Esc. 0, 6, 8 · `gestor/diagrama.py`, `TestDiagrama` · capturas S5 |
| [x] | U19 | **Inyectar** microservicios **por el Campo de Datos** a las madres | §4.3 (`GEN_INYECTA`) | S3 | Esc. 4 · `test_b_distribuir…`, `test_e_alta…` · humo S5 E0 (16 altas), E4, E8 |
| [x] | U20 | Video **fácil de grabar** | §10, §11 | S4, S7 | `GUION_VIDEO.md` (11 escenas, clics exactos, qué se ve, qué decir) · panel (modos, Gestor por nodo, Tumbar) · gestor (Distribuir, línea de tiempo) |
| [x] | U21 | Código **deslumbrante** | §15 | Todas | Revisión por sesión, ruff limpio, 217 pruebas ×3 en verde (auditoría final incluida), cada límite anti-cáncer en un método |
| [x] | U22 | Seguimos en **Python** | §0.1 | — | — |
| [x] | U23 | Topes sí, pero **si se levanta una, solo se mantiene una** (sin rellenar a N) | §6.2 | S4 | `test_una_sola_madre_con_el_gen_se_reemplaza_por_una` · humo S5 final (DIV de vuelta a 5, no más) |
| [x] | U24 | **Dos modos**: arrancar todo vacío o todo levantado; el funcionamiento se mantiene | §10.1 | S4 | Panel: "Configuración mínima — vacía" / "— con servicios" (`panel/procesos.py`, `test_panel`) · humo S4 (con servicios) y S5 (vacía) |
| [x] | U25 | Transcribir instrucciones del usuario y del PDF; requisitos sin perder detalle | — | S1 | Este archivo, `ENUNCIADO.md`, `INSTRUCCIONES_USUARIO.md` |
| [x] | U26 | `CLAUDE.md` que referencie otros .md (no todo en él) | — | S1 | `CLAUDE.md` |
| [x] | U27 | Al regenerar, la célula **copia la funcionalidad necesaria** | §6.3 paso 6 | S4 | Esc. 6 · `madre/copia.py` · `test_tumbar_una_regenera_un_clon_que_copia_sus_genes` · humo S5 E6 (`M1-N2·r1` con SUM 2.0, no 1.0) |
| [x] | U28 | La autorrecuperación **no necesita input del usuario** | §6.3 | S4 | Esc. 6 · humo S4 y S5 E6–E7 (nadie toca nada tras tumbar) |
| [x] | U29 | La autorrecuperación se **muestra fácilmente** en el video | §6.6 | S3–S4 | Esc. 6, 7 · gestor: pestaña Regeneración, animación naciendo/recién nacida, píldora de estado · capturas S5 E6–E7 |
| [x] | U30 | **Un gestor por nodo**, pero que **el usuario lo levante** (no arranca solo) | §0.1, §4.1, §10.1 | S3–S4 | Panel: botón **Gestor** por nodo (`G-N1`…`G-N4`); la configuración no abre gestores (`test_panel`) |
| [x] | U31 | Huella, evento y Min. ACK con las **definiciones del PDF** | §5.1 | S2 | — |
| [x] | U32 | Entrega final **súper completa** y **bonita visualmente, simple pero clean** | §15, §15.1 | Todas (S4 repaso) | Capturas S4 y S5 (gestor, GUI, panel, nodo) · `comun/estilo.py` en todas las ventanas |
| [x] | U33 | Plan aprobado → proceder con la sesión 1 | — | S1 | Mensaje 7 |

## Lenguaje, entregables, originalidad (PDF §1–§3)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | L1 | Cualquier lenguaje | §0.1 | — | Python |
| [x] | L2 | Java da puntos extra (se renuncia) | §0.1 | — | Se menciona en el reporte |
| [x] | E1 | Reporte técnico: diseño, protocolos heredados y nuevos | §14 | S6 | `REPORTE_TECNICO.md` + `.docx` (S6) |
| [ ] | E2 | Video con audio con diferentes escenarios | §11 | S7 | `GUION_VIDEO.md` listo (8 escenarios + "sin unidad central"); **falta grabarlo** (usuario) |
| [ ] | E3 | Liga al código: células cliente y servidor, nodos, **microservicios** y **gestor** | §2 | S6 | Repo nuevo en GitHub; **falta publicarlo** (usuario) |
| [x] | O1 | Originalidad (sin copia entre proyectos) | — | S6 | Reporte §16 |

## Base del segundo parcial (PDF §4)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | B1 | +, −, ×, ÷ | §3 (genes) | S1 | Esc. 0–1 · humo S5 (7+5, 6×7, 9−4) · `test_cuatro_operaciones…` |
| [x] | B2 | Tres programas base: cliente, servidor (madre) y nodo | §1 | S1 | `interfaz/`, `madre/`, `nodo/` |
| [x] | B3 | 4 nodos en malla completa | heredado | — | Esc. 0 · `test_malla` · captura S5 E0 (malla del diagrama) |
| [x] | B4 | 4 GUIs | §10.1 | S4 | Esc. 0 · panel (configuración mínima) · humo S5 |
| [x] | B5 | 4 células servidor por operación | §10.1, §10.2 | S3–S4 | Esc. 0 (tras "Distribuir" o modo con servicios) · humo S5 E0 |
| [x] | B6 | Por nodo: 1 GUI y una célula de cada operación | §10.1 | S4 | Esc. 0 · humo S5 E0 (una de cada operación por nodo) |
| [x] | B7 | Conexión entre nodos | heredado | — | Ventana del nodo (vecinos) · captura S5 E0 |
| [x] | B8 | Conexión célula–nodo | heredado (+ `MADRE`, `GESTOR`) | S1, S3 | Ventana del nodo (células) · captura S5 E0 |
| [x] | B9 | Comunicación por Código de Contenido | §7 | S1–S3 | Bitácoras · ventana del nodo (tráfico por código) |
| [x] | B10 | Broadcast sin ciclado | heredado | — | Sonda, FWD/DUP (captura S5 E0 del nodo) · `test_malla` |
| [x] | B11 | No limitado a 4 nodos ni número fijo de células | heredado, §6.2 | — | Esc. 8 · humo S5 E8 (Nodo 5 + madre nueva) |
| [x] | B12 | Sin unidad central / nodo maestro / componente único | §1, §4.1 | Todas | Esc. "sin unidad central" · humo S5 final |

## Foliado (PDF §5.1)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | F1 | Folio que correlaciona eventos, ACK y respuestas | §5.1, §5.2 | S2 | Esc. 1 · `test_foliado`, `test_cuatro_operaciones…` · humo S5 E1 |
| [x] | F2 | La GUI reconoce sus respuestas | §5.3 | S2 | Esc. 1–2 · `test_ajenos_se_ignoran`, `test_sello_alterado…`, `test_rafagas_simultaneas…` · humo S5 E2 |
| [x] | F3 | Células deciden con folio + Código de Contenido | §5.3 | S2 | Bitácoras `IGNORA`, `DROP huella inválida` · `test_huella_invalida_no_se_acusa`, `test_fin_cierra…` |
| [x] | F4 | **Huella**: origen / trayectoria lógica | §5.1 | S2 | Esc. 1 (rastro REQ → 4 ACK → RES → FIN) · `test_foliado` · humo S5 E1 |
| [x] | F5 | ACK de recepción/participación | §5.1 | S2 | Esc. 1 · humo S5 E1 (4 ACK) |
| [x] | F6 | Min. # de ACK para aceptar un evento | §5.1 | S2 | Esc. 1, 3 · `test_madre_muda…` (4/5 → FALLIDA) · humo S5 E3 (4/2) |
| [x] | F7 | Tolerancia si no responden todas las esperadas | §5.1 (ausentes) | S2 | Esc. 3 · `test_madre_muda_sale_en_ausentes…`, `test_esperados_ausentes_y_fases` · humo S5 E3 (ausente `SUM-N1m`) |
| [x] | F8 | Evento: inicio, confirmación, procesamiento y finalización | §5.1 (`X_FIN`) | S2 | Esc. 1 (fases) · `test_esperados_ausentes_y_fases`, `test_fin_cierra…` · humo S5 E1 (`FINALIZADO`) |

## Microservicios dinámicos (PDF §5.2)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | M1 | Existen físicamente en disco | §3.1, §3.2 | S1 | Carpetas `microservicios/` y `datos/celulas/*/genes/` · humo S5 E4 |
| [x] | M2 | Se cargan en memoria en ejecución | §3.3 | S1 | Esc. 4 (`GEN_CARGADO`) · humo S5 E4 |
| [x] | M3 | Programa base sin la lógica de +, −, ×, ÷ | §3 (`calculo.py` desaparece) | S1 | Código de `madre/` |
| [x] | M4 | Genes cambian en operación mediante el gestor | §4.3 | S3 | Esc. 5 · `test_c_sustituir…`, `test_g_sustituir_en_todas` · humo S5 E5 (0.1+0.2: 0.30000000000000004 → 0.3) |
| [x] | M5 | Reporte explica localizar, validar, cargar, activar y descargar | §3.3 | S6 | Reporte §6.4 |

## Autorrecuperación (PDF §5.3)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | A1 | Detectar baja de disponibilidad por falla/desconexión | §6.3 paso 1 | S4 | Esc. 6 · `Regeneracion._detectar` · `TestRegla` · humo S5 E6 (`CAIDA`) |
| [x] | A2 | Las células deciden cuándo generar otra instancia | §6.3 pasos 2–4 | S4 | Esc. 6 · `Regeneracion._turno` (HRW + `CLON_AVISO`) · `test_si_el_clonador_no_actua…` · humo S5 E6 |
| [x] | A3 | La nueva recupera/carga los genes necesarios | §6.3 paso 6 | S4 | Esc. 6 · `madre/copia.py` (`GEN_PIDE`; banco si nadie entrega) · humo S5 E6 |
| [x] | A4 | Sin controlador central | §6.1, §6.3 | S4 | Esc. 6 con gestor cerrado · `TestRegeneracionEnVivo` sin gestor · humo S5 final |
| [x] | A5 | Se detiene al alcanzar el nivel requerido | §6.2, §6.3 paso 8 | S4 | Esc. 7 · `NIVEL_OK` en todas las madres · `test_una_perdida…_y_alto` · humo S5 E6–E7 |
| [x] | A6 | Impide la generación ilimitada (cáncer) | §6.4 | S4 | Esc. 7 · `TestRegla` (tope duro, telómeros, cupo, reintentos) · humo S5 (10 avisos = 10 reemplazos, 0 de más) |
| [x] | A7 | Tolerancia: una falla local no pierde todo el servicio | §6.5 | S4 | Esc. 7 (tres `SUM`) · `test_tres_sum_vuelven_uno_por_uno` · humo S5 E7 |

## Gestor de servicios (PDF §5.4)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | G1 | Células pueden arrancar sin microservicios | §3.4, §10.1 | S1 | Esc. 0 (modo vacío), 4 · humo S5 E0, E4, E8 |
| [x] | G2 | Alta de un servicio en una célula | §4.3 | S3 | Esc. 4 · `test_e_alta…` · humo S5 E4 |
| [x] | G3 | Baja de un servicio | §4.3 | S3 | Esc. 5 · `test_d_baja_deja_de_acusar` · humo S5 E5 (M1-N4 vacía, ya no acusa) |
| [x] | G4 | Modificar o sustituir un servicio | §3.3, §4.3 | S3 | Esc. 5 · `test_c_sustituir_y_rechazar_manipulado` · humo S5 E5 (2.0 en todas; 9.9 rechazado) |
| [x] | G5 | Conoce/consulta la topología para decidir | §4.4 | S3 | Esc. 4 (clic en el diagrama) · `TOPO_REQ` (`test_h_…`) · humo S5 E4 (M5-N2 vacía) |
| [x] | G6 | Topología: nodos disponibles, células conectadas, servicios activos por célula | §4.4 | S3 | Esc. 8 · `TestTopologia`, `test_j_nodo_nuevo…` · humo S5 E8 |
| [x] | G7 | El sistema no depende de que el gestor siga activo | §4.1 | S3 | Esc. "sin unidad central" · `test_z_sin_gestor…` · humo S5 final |
| [x] | G8 | Alta/baja/modificación se reflejan en la carga dinámica de la célula | §3.3, §4.3 | S3 | Esc. 4–5 (bitácora de la madre: `GEN_ESCRITO/VALIDADO/CARGADO/ACTIVO`) · humo S5 E4 |

## Principios (PDF §7)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | P1 | Sin unidad central indispensable | §1 | Todas | Esc. final · humo S5 final |
| [x] | P2 | Sin nodo maestro | heredado | — | Tumbar un nodo (failover) · `test_nodo_tumbado_failover_y_el_servicio_sigue` |
| [x] | P3 | Nodos y células flexibles; 4 es el mínimo de demo | heredado, §6.2 | — | Esc. 8 · humo S5 E8 |
| [x] | P4 | Protocolos funcionan con altas, bajas, fallas y nuevas instancias | §3–§6 | S5 | Esc. 4–8 · humo S5 (30/30) |
| [x] | P5 | La pérdida de una célula no es punto único de falla | §6.5 | S4 | Esc. 6 · cualquier madre regenera a cualquiera (humo S5: clonadores de varios nodos) |
| [x] | P6 | Recuperación gradual y controlada, sin crecimiento ilimitado | §6.3, §6.4 | S4 | Esc. 7 · `TestRegla` · humo S5 E7 |
| [x] | P7 | Control de foliado, ACK, topología y recuperación distribuido | §5, §4.4, §6.1 | S2–S4 | Reporte §10 |

## Esquema (PDF §8)

| | ID | Requisito | Plan | Sesión | Evidencia |
|---|---|---|---|---|---|
| [x] | C1 | Estructura de la Figura 1 (4 nodos, 1 GUI + 4 células por nodo, 20 células) | §1 | S4 | Diagrama del gestor (capturas S4 y S5 E0) |

## Evidencia mínima del video (PDF §9)

Verificado en vivo (humo S5); en el video, la tabla del principio de `GUION_VIDEO.md` dice en qué escena se ve cada una.

| | ID | Evidencia | Escenario |
|---|---|---|---|
| [x] | V1 | 4 nodos como Campo de Datos | 0 |
| [x] | V2 | GUIs y células servidor conectadas | 0 |
| [x] | V3 | Conexión y broadcast heredados | 0 |
| [x] | V4 | Solicitudes con Código de Contenido y folio | 1 |
| [x] | V5 | Huella, ACK, Min. # de ACK y eventos visibles | 1, 3 |
| [x] | V6 | Cada GUI solo con sus respuestas | 1, 2 |
| [x] | V7 | Microservicio de disco a memoria en ejecución | 4 |
| [x] | V8 | Alta, baja y modificación desde el gestor | 4, 5 |
| [x] | V9 | Topología para elegir células destino | 4, 8 |
| [x] | V10 | Detección de la falla de una célula | 6 |
| [x] | V11 | Clonación automática | 6 |
| [x] | V12 | Alto de la clonación al nivel requerido | 7 |
| [x] | V13 | Sin dependencia de unidad central | final |

## Escenarios del video (PDF §10)

Verificados en vivo (humo S5, 30/30); en el video son las escenas 3 a 11 de `GUION_VIDEO.md` (S7).

| | ID | Escenario | Plan §11 |
|---|---|---|---|
| [x] | S1 | Operación normal con foliado; otra GUI no la muestra | 1 |
| [x] | S2 | Solicitudes simultáneas desde 2+ GUIs | 2 |
| [x] | S3 | Min. # de ACK con una célula que no responde; se identifica la ausencia | 3 |
| [x] | S4 | Célula sin servicio → instalar desde el gestor → carga de disco a memoria | 4 |
| [x] | S5 | Baja (deja de atender el código) y sustitución por versión nueva | 5 |
| [x] | S6 | Detener una célula → detección → célula nueva con genes | 6 |
| [x] | S7 | La clonación se detiene al recuperar el número requerido | 7 |
| [x] | S8 | Agregar/retirar célula o nodo; el gestor actualiza la topología y decide | 8 |

## Contenido del reporte (PDF §11)

| | ID | Sección | Plan §14 |
|---|---|---|---|
| [x] | D1 | Arquitectura final | II · reporte §3 |
| [x] | D2 | Topología de la demo | II · reporte §3.2 |
| [x] | D3 | Protocolo de conexión heredado | II · reporte §4.1 |
| [x] | D4 | Comunicación y prevención de ciclos | II · reporte §4.2 |
| [x] | D5 | Formato de mensajes y Códigos de Contenido | II · reporte §4.3–4.4 |
| [x] | D6 | Diseño del foliado | II · reporte §5 |
| [x] | D7 | Definición de huella, ACK, Min. # de ACK y evento | II · reporte §5.1 |
| [x] | D8 | Tolerancia a fallas | II · reporte §9 |
| [x] | D9 | Genes activos y carga dinámica | II · reporte §6 |
| [x] | D10 | Gestor de Servicios y representación de la topología | II · reporte §7 |
| [x] | D11 | Protocolo de autorrecuperación | II · reporte §8 |
| [x] | D12 | Reglas para clonar y detener la clonación | II · reporte §8.4 |
| [x] | D13 | Evidencias de pruebas y escenarios | III · reporte §11–12 |
| [x] | D14 | Limitaciones y decisiones de diseño | III · reporte §14 |
