# Calculadora ADS — Tercer Parcial (notas internas)

Evolución del sistema ADS del segundo parcial: Campo de Datos (nodos en malla) + GUIs + **células
madre** vacías que jalan microservicios (genes) de disco, un **gestor de microservicios** con base
de datos que inyecta genes por el Campo de Datos y dibuja la topología, **foliado** y
**regeneración** automática, gradual y sin cáncer. **No hay orquestador.**

## Dónde está cada cosa (leer según haga falta; aquí solo va lo indispensable)

| Documento | Para qué |
|---|---|
| [ROADMAP.md](ROADMAP.md) | **Empezar aquí:** estado actual, siguiente paso, casillas por sesión, registro |
| [docs/INSTRUCCIONES_USUARIO.md](docs/INSTRUCCIONES_USUARIO.md) | Lo que pidió el usuario, **literal**. Manda sobre el plan |
| [docs/ENUNCIADO.md](docs/ENUNCIADO.md) | El PDF del tercer parcial, literal, con IDs por requisito |
| [docs/REQUISITOS.md](docs/REQUISITOS.md) | Lista de verificación: requisito → sección del plan → sesión → evidencia |
| [docs/PLAN.md](docs/PLAN.md) | Diseño completo: arquitectura, madres y genes, gestor, foliado, regeneración, mensajes, constantes, escenarios, pruebas, reporte, calidad |
| [docs/parcial2/](docs/parcial2/) | Lo entregado en el segundo parcial (plan, reporte, guion, resumen). Referencia del diseño heredado |

## Reglas de trabajo (no reabrir)
- Plan **aprobado** (2026-11-17, mensaje 7). Cambios de diseño de fondo se consultan antes con
  el usuario. Instrucciones nuevas se anexan literal a `docs/INSTRUCCIONES_USUARIO.md` y se
  reflejan en `PLAN.md` y `REQUISITOS.md`.
- **Un gestor por nodo**, que el usuario levanta (el panel no los abre solo).
- Entrega final **súper completa y visualmente clean**: todas las ventanas usan `comun/tema.py`
  (PLAN §15.1).
- Fases en orden estricto: 0 → A código → B pruebas → C fixes → D reporte → E guion.
- **Python 3.14, solo librería estándar** en el sistema; **uv** para el entorno. Sin Java.
- **No hay orquestador**: las células deciden solas; gestor y panel son herramientas.
- Regeneración **automática** (sin input del usuario), **gradual**, reemplazo **1 a 1**, ocho
  límites anti-cáncer; el clon **copia** los genes de la célula perdida.
- Video **fácil de grabar**; código **deslumbrante** (PLAN §15). Reporte **≤ 30 páginas**.
- El PDF manda sobre lo visto en clase; las diferencias se mencionan breve y respetuosamente.
- Commits solo cuando el usuario lo pida. El repo del segundo parcial (`../calculadora_ads/`) no
  se toca.

## Reglas de código (heredadas)
1. Ningún `nucleo.py` importa Tkinter; eventos por `queue.Queue` + `after(100)`.
2. Constantes como `config.X` al usarlas, nunca `from comun.config import X` (las pruebas las
   parchan).
3. Estado compartido entre hilos protegido por el lock del objeto dueño.
4. Ningún hilo de red muere por excepción: se registra `ERROR` y se sigue.
5. Al arrancar: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.
6. Nodos "bobos": nunca leen el `cuerpo`. Todo dato por broadcast; cada célula filtra por código.

## Cómo correr (desde esta carpeta)
```
uv sync                                   # una vez: crea .venv con ruff
uv run python -m unittest discover -s tests -t .
uv run ruff check .
uv run python -m panel                    # demo
```
Comandos de cada programa: `README.md` y PLAN §3.4 (madre). **Estado del código:** S1 hecha:
`servidor/` ya no existe (lo sustituye `madre/`), `comun/huella.py` es `comun/hashes.py`, banco
`microservicios/` firmado con `herramientas/firmar.py`. S2 hecha: foliado en `comun/foliado.py`
(rondas por `(código, folio, intento)`, `X_FIN`; detalles en PLAN §5.5). S3 hecha: `gestor/`
(BD, topología, diagrama, ventana), `NODO_LAT` en el nodo, `TOPO_REQ` en la célula base, órdenes
y pedidos de genes en la madre (`madre/ordenes.py`, `madre/pedidos.py`, `comun/pedidos.py`),
piezas Tk en `comun/estilo.py`; detalles en PLAN §4.6. S4 hecha: regeneración
(`madre/regeneracion.py` decide, `madre/lanzador.py` lanza procesos desacoplados + `run/`,
`madre/copia.py` = el reemplazo copia sus genes), línea de tiempo y animación en el gestor, GUI
con tarjeta de evento, panel con dos modos y botón Gestor por nodo, repaso visual; detalles en
PLAN §6.7. S5 hecha: los 8 escenarios en vivo (30/30), fixes (ver registro del `ROADMAP.md`),
`docs/REQUISITOS.md` marcado, capturas para el reporte en `docs/capturas/`. Cerrar ventanas
con `estilo.cerrar(raiz)` (cancela los `after` pendientes). S6 hecha: `REPORTE_TECNICO.md` →
`uv run python docs/md_a_docx.py` → `.docx` de **30 páginas exactas** (cualquier texto nuevo se
compensa; revisar con Word, notas del `ROADMAP.md`), `README.md`, `ENTREGA.md`. S7 hecha:
`GUION_VIDEO.md` (11 escenas; si cambia una etiqueta de ventana, actualizar el guion) y
Auditoría final hecha (registro del `ROADMAP.md`): el clonador cancela a su hijo vencido (`cancelar=` en `Madre`/`Regeneracion`; `lanzar_proceso` devuelve el registro); un enlace duplicado se cierra con `drenar=True` (sigue
leyendo hasta el fin de datos del par). Sin minutos (mensaje 19): la columna "Escena" del §2 del reporte remite a las escenas del guion;
si se reordenan escenas, actualizarla. En pruebas,
`Sistema(regenerar=True)` para que las madres clonen (en proceso).
Para humo con procesos reales, redirigir su stdout a archivo (un pipe sin leer los bloquea).
Capturas de ventanas Tk: **nunca asomarlas** (el usuario las minimiza); al fondo + `PrintWindow`
modo 2, y las del mismo proceso desde su hilo de Tk: notas "Capturas (S5)" del `ROADMAP.md`.
Un humo con madres reales deja reemplazos vivos: terminarlos con `madre.lanzador.registrados()`.

## Entorno del usuario
- Windows 11, pantalla 1463×914 lógicos (2560×1600 al 175 %). Para operar/capturar ventanas sin
  quitarle el foco: notas del `ROADMAP.md`.
- Revisar `.docx`: Word por COM (`Documents.Open` + `SaveAs2(pdf, 17)`) y la API
  `Windows.Data.Pdf`; no hay pandoc ni LibreOffice.
