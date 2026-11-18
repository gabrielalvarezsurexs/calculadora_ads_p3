# Guion del video de la Calculadora ADS (Tercer Parcial)

Duración objetivo: unos 12 minutos, en 11 escenas. Cada escena dice qué hacer (clics y comandos),
qué se ve y qué decir. El texto de "Di esto" es una guía; dilo con tus palabras.

Haz las escenas **en este orden**: cada una deja el sistema como lo necesita la siguiente (por
ejemplo, la escena 9 tumba los reemplazos que nacieron en la 8). Lo que se describe en "Qué se ve"
salió así en la verificación en vivo del 17 de noviembre; los hashes, los nombres de las titulares
y los milisegundos cambian en cada corrida.

**Qué pide el enunciado y dónde se ve** (`docs/ENUNCIADO.md`, §9 y §10):

| Escenario (§10) | Evidencia (§9) | Escena |
|---|---|---|
| — Arranque y base heredada | V1 nodos · V2 células conectadas · V3 conexión y broadcast | 2 y 3 |
| S1 Operación normal con foliado | V4 código y folio · V5 huella, ACK, mínimo, evento · V6 | 3 |
| S2 Solicitudes simultáneas | V6 cada GUI solo lo suyo | 4 |
| S3 Mínimo de ACK y tolerancia | V5 | 5 |
| S4 Carga dinámica | V7 disco → memoria · V8 alta · V9 topología para elegir | 6 |
| S5 Baja y modificación | V8 baja y cambio | 7 |
| S6 Falla y autorrecuperación | V10 detección · V11 clonación | 8 |
| S7 Prevención del cáncer | V12 alto de la clonación | 9 |
| S8 Cambio de topología | V9 | 10 |
| — Sin unidad central | V13 | 11 |

---

## Antes de grabar

En una terminal de PowerShell, en la carpeta del proyecto:

```powershell
cd c:\SCHOOL\COMPUTO_DISTRIBUIDO\calculadora_ads_p3

# 1. Que no quede nada corriendo de antes. Debe imprimir 0
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object CommandLine -match ' -m (nodo|madre|interfaz|gestor|panel|sonda)( |$)' |
  Measure-Object | ForEach-Object Count

# 2. Bitácoras viejas a un lado (la escena 11 cuenta lo que hay en logs\*.log)
New-Item -ItemType Directory -Force logs\anteriores | Out-Null
Move-Item logs\*.log logs\anteriores\ -ErrorAction SilentlyContinue

# 3. Las pruebas (~3 min). Corre esto ANTES de abrir el panel y deja la terminal abierta:
#    es la que se muestra al final de la escena 11
uv run python -m unittest discover -s tests -t .
```

Cuando terminen las pruebas (`Ran 201 tests` y `OK`), abre **otra** terminal en la misma carpeta;
esa es la de la demo.

Checklist:

- [ ] **Prueba de audio.** Graba 10 segundos y escúchalos: el enunciado pide video *con audio*.
- [ ] Grabador de **pantalla completa**: OBS Studio ("Captura de pantalla" + micrófono) o la
  Herramienta Recortes en modo grabar con el micrófono activado. La Xbox Game Bar no sirve:
  graba una sola ventana.
- [ ] No molestar activado (`Win` + `N`); correo, mensajería y todo lo ajeno al proyecto, cerrado.
- [ ] Las terminales con letra grande (`Ctrl` + `+`).
- [ ] La lupa de Windows a la mano (`Win` + `+` acerca, `Win` + `Esc` la cierra): las bitácoras
  y la tabla de tráfico tienen letra chica.
- [ ] Este guion en el celular o en otra pantalla, no en la que grabas.

**Dónde quedan las ventanas.** El panel sale arriba al centro; los cuatro nodos, en una cuadrícula
de 2 × 2 a la izquierda; las cuatro GUIs, en cascada a la derecha; el gestor ocupa casi toda la
pantalla. Se enciman: para traer una al frente, clic en su barra de título o en la barra de
tareas. Lo normal es dejar el **gestor de fondo** y traer encima la GUI o el panel que toque.

**No cierres con la X la ventana de un nodo ni la de una madre**: eso es una caída. Las fallas se
hacen desde el panel, en las escenas 8, 9 y 11.

**Si vas largo de tiempo**, omite la sustitución rechazada (`SUM 9.9`) de la escena 7. Lo demás
cubre lo que pide el enunciado.

---

## Escena 1. Qué cambió y con qué está hecho (0:40)

**Haz esto.** Muestra el `README.md` (la tabla de las cuatro cosas nuevas).

**Di esto.**

> Hola, soy `<tu nombre>`. Este es el tercer parcial: la calculadora ADS del segundo parcial con
> cuatro cosas nuevas. Las células servidor ahora son células madre vacías que cargan su lógica,
> los genes, desde disco mientras corren. Un gestor con base de datos dibuja la topología y manda
> esos genes por el Campo de Datos. Cada operación lleva folio y huella. Y si una célula muere,
> las demás la regeneran solas, sin orquestador. Todo en Python con la librería estándar.

---

## Escena 2. Arranque: nodos, madres vacías y el gestor (1:30)

**Haz esto.**

1. En la terminal de la demo, corre `uv run python -m panel` y haz clic en **"Configuración
   mínima — vacía"**. Salen primero los 4 nodos y, un segundo después, las 4 GUIs.
2. En el panel, señala la fila de cada nodo: **"vivo"**, **"GUI 1"** y cuatro fichas grises
   **"M1 · vacía" … "M4 · vacía"**. Baja a **Procesos** y señala la columna **comando**: hay
   tres programas, `-m nodo`, `-m madre` (sin genes) y `-m interfaz`.
3. Trae al frente una **GUI**: los operadores están grises y en **Disponibilidad** las cuatro
   operaciones dicen **"vivas 0"** con **✗**.
4. Trae al frente el **Nodo 2**: **"Vecinos · 3"** (Nodos 1, 3 y 4) y **"Células · 5 (1 GUI + 4
   madres)"**.
5. En el panel, clic en **"Gestor"** de la fila **Nodo 1**. Se abre **G-N1**. Señala en el
   diagrama los 4 nodos con sus 6 enlaces, las 16 madres punteadas ("vacía") y las 4 GUIs; en el
   **Catálogo**, los 6 genes de la BD con **SUM 9.9** marcado con **✘**.
6. Clic en **"Distribuir una de cada operación por nodo"**. En menos de un segundo las 16 madres
   se pintan del color de su gen, la pestaña **Órdenes** se llena con 16 altas `ok` y arriba del
   diagrama queda **"SUM 4 · SUB 4 · MUL 4 · DIV 4"**. En el panel, las fichas pasan a
   **"M1 · SUM"**, **"M2 · SUB"**, **"M3 · MUL"** y **"M4 · DIV"**, cada una de su color.

**Di esto.**

> El panel solo lanza los mismos comandos que escribiría a mano; está fuera del sistema. Arranco
> en modo vacío: cuatro nodos en malla y, en cada uno, una GUI y cuatro madres sin ningún gen.
> Por eso la calculadora no puede hacer nada todavía. El Nodo 2 tiene tres vecinos y cinco
> células: la conexión es la del segundo parcial. Abro el gestor del Nodo 1: es una célula más y
> arma este diagrama solo con los latidos. Su base de datos tiene seis genes; la SUM 9.9 sale con
> una cruz porque está manipulada a propósito. Con un clic, una madre de cada operación por nodo:
> dieciséis órdenes por el Campo de Datos, y queda el esquema del enunciado.

---

## Escena 3. Una operación con folio, de punta a punta (1:30)

**Haz esto.**

1. Trae al frente la **GUI-1** y haz clic en `7` `+` `5` `=`. El display dice `12` y debajo
   sale `F-…-0001 · titular M1-N… · SUM@1.0 · ~510 ms`.
2. En la pestaña **Evento**, recorre de arriba abajo: el **folio** `F-…-0001` con la píldora
   **"resuelta"**, las cuatro fases en verde (**1. inicio · 2. confirmado · 3. procesado ·
   4. finalizado**), el **sello**, **ACK 4/2** con los nombres, **esperados** (las 4 madres SUM),
   **ausentes: ninguno**, **respondió** y el **rastro** `GUI-1 REQ → 4×ACK → M1-N… RES → GUI-1 FIN`.
3. Clic en la pestaña **Protocolo**: `EVENTO_INICIO … SUM_REQ 7 + 5 · sello … · esperadas 4`,
   cuatro `ACUSE`, `CONFIRMADO`, `RESULTADO … solicitud … ↔ respuesta …` y `FIN`.
4. Trae al frente la **GUI-2**: su display no cambió y abajo **"ajenas ignoradas"** subió.
5. Trae al frente el **Nodo 2**, marca **"pausar"** en **Tráfico** y señala `FWD SUM_REQ` (ruta
   `N1→N2`) y las filas `DUP` (copias que llegaron por otro camino y no se reenvían). Desmarca
   "pausar".
6. En el panel, clic en la ficha de la madre que respondió (la que dice la GUI, por ejemplo
   **"M1 · SUM"** de Nodo 1). En su **bitácora en vivo** señala `RX SUM_REQ … sello … ✓`,
   `ACUSE`, `TITULAR … rank 0 de 4`, `RES … solicitud … ↔ respuesta …` y el `RX SUM_FIN`.

**Di esto.**

> Siete más cinco: doce. Esta tarjeta es el evento. El folio amarra solicitud, acuses, respuesta
> y cierre. La huella es un sello, un hash del origen, el folio y la operación, más un rastro de
> quién tocó el evento. Pasó por sus cuatro fases: inicio, confirmado al llegar al mínimo de dos
> acuses, procesado con la respuesta, y finalizado con SUM_FIN. La GUI-2 recibió lo mismo por
> broadcast, pero el folio no es suyo y lo ignora. En el Nodo 2, las copias repetidas se descartan
> como duplicadas: no hay ciclos. Y la madre titular validó el sello, acusó y respondió una sola
> vez; las de resta ni la tomaron, porque deciden por Código de Contenido y folio.

---

## Escena 4. Solicitudes simultáneas (0:40)

**Haz esto.**

1. Acomoda la **GUI-1** y la **GUI-2** para que se vean las dos (en cascada se ve el borde de
   cada una; basta con clic en su barra de título).
2. Clic en **"Ráfaga ×8"** de la GUI-1 e, inmediatamente, en **"Ráfaga ×8"** de la GUI-2.
3. En cada una, clic en la pestaña **Mis eventos**: 8 folios propios (de las cuatro operaciones)
   que pasan de "en vuelo" a **"resuelta"** en medio segundo. Los folios de GUI-1 empiezan con un
   hash y los de GUI-2 con otro.

**Di esto.**

> Ahora dieciséis operaciones casi a la vez: ocho desde cada GUI, de las cuatro operaciones, todas
> en vuelo al mismo tiempo. Cada GUI recibe por broadcast las respuestas de todas, pero cada una
> se queda solo con las de sus folios: aquí están sus ocho, todas resueltas, y ninguna de la otra.

---

## Escena 5. Mínimo de ACK y una célula que no acusa (0:50)

**Haz esto.**

1. En el panel, clic en **"+ Muda (SUM)"** de la fila **Nodo 1**. Aparece la ficha roja
   **"SUMm · muda"** (la madre `SUM-N1m`). Es una madre que late, así que cuenta como esperada, pero nunca acusa.
2. En la **GUI-1**, señala en **Disponibilidad** el campo **"mín. ACK"** de la suma (2) y luego
   haz clic en `2` `+` `2` `=`.
3. Pestaña **Evento**: **ACK 4/2**, **esperados** con 5 madres (incluida `SUM-N1m`),
   **ausentes: SUM-N1m** y el evento **finalizado** con `4`. En **Protocolo**: `AUSENTES …
   SUM-N1m no acusaron · ACK 4/2 de 5 esperada(s) → el evento sigue (tolerancia)`.

**Di esto.**

> Agrego una célula de suma muda: late, así que la GUI la espera, pero nunca manda su acuse.
> El mínimo de acuses es configurable por operación, aquí mismo, y está en dos. Dos más dos:
> esperaba cinco acuses, llegaron cuatro, y como pasa del mínimo el evento sigue y termina. Pero
> el sistema sí identifica la ausencia: la GUI dice exactamente quién no acusó.

---

## Escena 6. Carga dinámica: una madre vacía aprende a multiplicar (1:10)

**Haz esto.**

1. En el panel, clic en **"+ Madre"** de la fila **Nodo 2**. Sale **"M5 · vacía"**.
2. Trae al frente el **gestor**. En unos 2 s aparece **M5-N2** punteada junto al Nodo 2. Haz clic
   en ella: en **Célula destino** sale **M5-N2** sin genes.
3. En el **Catálogo**, clic en **MUL 1.0** y luego en **"Inyectar (alta)"**. Abajo dice que la
   orden quedó `ok` y la ruta `datos/celulas/M5-N2-…/genes/MUL/1.0/`. M5-N2 se pinta de naranja.
4. En el panel, clic en la ficha **"M5 · MUL"**. En su bitácora señala, en orden:
   `GEN_ESCRITO … → datos\celulas\…`, `GEN_VALIDADO … sha256 … coincide`,
   `GEN_CARGADO … en memoria con importlib` y `GEN_ACTIVO … ahora atiendo MUL_REQ`.
5. En la **GUI-1**, `6` `×` `7` `=` → `42`. En **Evento**: **esperados** con 5 madres MUL,
   incluida **M5-N2**, y **ACK 5/2**.

**Di esto.**

> Agrego una madre vacía al Nodo 2: el mismo programa base, sin aritmética. Aparece sola en el
> gestor. La elijo en el diagrama, elijo la multiplicación e inyecto. La madre escribe el gen en
> su propio disco, lo valida contra su sha256, lo carga en memoria con importlib y lo activa. Sin
> reiniciar nada ya multiplica: seis por siete, cuarenta y dos, y M5-N2 está entre las que
> acusaron.

---

## Escena 7. Baja y cambio de versión (1:20)

**Haz esto.**

1. En el **gestor**, clic en **M1-N4** (la SUM del Nodo 4) y en **"Baja del gen"**. M1-N4 queda
   punteada (vacía).
2. En la **GUI-1**, `0` `.` `1` `+` `0` `.` `2` `=` → **`0.30000000000000004`**. En **Evento**,
   **esperados** ya no incluye a M1-N4; **respondió … SUM@1.0**.
3. En el gestor, **Catálogo** → clic en **SUM 2.0** → **"Sustituir en todas las que lo tengan"**.
   En **Órdenes** salen 4 cambios `ok` (`SUM@1.0 → SUM@2.0`), también el de la muda.
4. En la **GUI-1**, otra vez `0.1 + 0.2 =` → **`0.3`**, y **respondió … SUM@2.0**.
5. En el gestor, clic en **M1-N1**, en el catálogo clic en **SUM 9.9** (✘) y en **"Sustituir
   versión"**. Abajo sale en rojo: **rechazada — validar: sha256 no coincide … ; sigue activo
   SUM@2.0**.

**Di esto.**

> Doy de baja la suma en la madre del Nodo 4: deja de atender SUM_REQ y la GUI ya no la espera.
> Cero punto uno más cero punto dos con la versión 1.0, en punto flotante: 0.30000000000000004.
> Sustituyo la versión en todas por la 2.0, que suma en decimal exacto; el cambio es atómico.
> Mismo cálculo: cero punto tres. Y si intento instalar la 9.9, la madre la rechaza porque no
> coincide con su firma, y se queda con la 2.0. La madre decide; el gestor solo pide.

---

## Escena 8. Falla y autorrecuperación (1:10)

**Haz esto.**

1. Deja el **gestor** a la vista y, encima, solo el panel. En el panel, clic en **"Tumbar SUM de
   Nodo 2"**. Dice **"Tumbé M1-N2. Ahora no toques nada…"**. **No toques nada.**
2. En el gestor (se abre sola la pestaña **Regeneración**), a los ~6 s: **M1-N2** en rojo con
   **✕** y la línea **caída**. Unos 2 s después: **clonador** (`M3-N… (rango 0) regenera a M1-N2 →
   M1-N2·r1 en Nodo 2; copiará SUM 2.0`), **conectada** (el contorno azul "naciendo"), **gen**
   (`M1-N… entrega SUM@2.0 …`), **listo** y **nivel ok**. En el diagrama nace **M1-N2·r1** con la
   insignia **r1**.
3. Mientras se regenera, en la **GUI-3**, `3` `+` `4` `=` → `7`.
4. En el panel aparece la ficha **"M1·r1 · SUM"** en Nodo 2.

**Di esto.**

> Mato una célula de suma sin avisarle a nadie, y no toco nada más. A los seis segundos todas las
> madres la dan por perdida: se fue sin despedirse. Ninguna manda: todas calculan el mismo
> ranking y la primera es la clonadora; avisa para que nadie más clone y lanza el reemplazo. El
> reemplazo nace vacío y pide por el Campo de Datos los genes de la perdida: la SUM 2.0, no la
> 1.0. Mientras, la suma nunca dejó de funcionar: tres más cuatro, siete. Nivel recuperado.

---

## Escena 9. Prevención del cáncer: se detiene sola (1:20)

**Haz esto.**

1. Señala la pestaña **Regeneración** y la píldora de arriba **"regeneración: nivel ok · sin
   clonar"**. Espera unos 10 s en silencio o hablando: **no aparece nada nuevo**. En el panel
   sigue habiendo un solo reemplazo.
2. En el panel, clic en **"Tumbar 3 SUM"** (tumba una SUM de los Nodos 1, 2 y 3, incluido el
   reemplazo `M1-N2·r1`). **No toques nada.**
3. En la **GUI-1**, el botón `+` se pone gris unos segundos y **Protocolo** dice
   `DESHABILITADA SUM deshabilitada: 1 viva(s) < 2 mínima(s)`: solo queda la muda. Cuando nace
   el primer reemplazo, `HABILITADA`.
4. En el gestor, a los ~6 s: tres **caídas** juntas. Después, **uno por uno**: clonador →
   conectada → gen → listo → **en espera** (`gradual: falta(n) …; va una a la vez`), otra vez, y
   al tercero **nivel ok**. Nacen **M1-N1·r1**, **M1-N2·r2** y **M1-N3·r1**.
5. La GUI-1 vuelve a habilitar la suma. Señala que hay exactamente las mismas SUM que antes.

**Di esto.**

> Recuperado el nivel, la clonación se detiene: diez segundos y nada más. Ahora tumbo tres sumas
> a la vez, incluido el reemplazo. Las madres no las clonan juntas: va una a la vez, con pausa, y
> cada pérdida tiene un solo reemplazo. Son ocho límites contra el cáncer, entre ellos topes por
> gen y en total, y telómeros: este es r2, clon de un clon. Al volver a las tres sumas que había,
> nivel OK y se detiene.

---

## Escena 10. Cambio de topología: un quinto nodo (0:50)

**Haz esto.**

1. En el panel, clic en **"+ Nodo"** (arriba). Sale la ventana del **Nodo 5** con **"Vecinos ·
   4"**, y en el panel una fila nueva **Nodo 5**. En **Procesos**, su comando tiene una sola
   `--semillas`.
2. En el **gestor**, el diagrama se redibuja con **5 nodos** y los enlaces del nuevo.
3. En el panel, clic en **"+ Madre"** de la fila **Nodo 5**. En el gestor aparece **M1-N5**
   vacía. Clic en ella → catálogo **DIV 1.0** → **"Inyectar (alta)"**.
4. En la **GUI-4**, `7` `÷` `2` `=` → `3.5`. En **Evento**, **esperados** con 5 madres DIV,
   incluida **M1-N5**.

**Di esto.**

> Agrego un quinto nodo con una sola semilla: por gossip tiene cuatro vecinos en un momento, sin
> reiniciar a nadie. El gestor lo dibuja porque le llegó su latido. Le pongo una madre, la elijo
> en la topología nueva y le inyecto la división. Siete entre dos, tres punto cinco.

---

## Escena 11. Sin unidad central y cierre (1:20)

**Haz esto.**

1. Cierra el **gestor** con su **X**.
2. En el panel, clic en la ficha **"M4 · DIV"** de la fila **Nodo 3** y luego en **"Tumbar
   seleccionado"**.
3. Cierra el **panel** con su **X**. A "¿Detener también todos los procesos?" contesta **No**.
4. Trae al frente la **GUI-4**. En **Disponibilidad**, **División** baja de **vivas 5** a
   **vivas 4** (~6 s) y unos 2 s después vuelve a **vivas 5**.
5. En la **GUI-2**, `9` `−` `4` `=` → `5`; en la **GUI-4**, `8` `÷` `2` `=` → `4`. En el
   **Evento** de la GUI-4, **esperados** incluye a **M4-N3·r1**, el reemplazo que nació sin
   gestor ni panel.
6. En la terminal de la demo, maximizada, corre esto. Sale **1** en "respuestas por folio" para
   todos los folios del video:

   ```powershell
   Select-String '\[RES\] \w+_RES \w+ (F-\w{8}-\d{4})' logs\*.log |
     ForEach-Object { $_.Matches[0].Groups[1].Value } | Group-Object | Group-Object Count |
     Select-Object @{n='respuestas por folio';e={$_.Name}}, @{n='folios';e={$_.Count}}
   ```

7. Trae al frente la terminal de las pruebas: `Ran 201 tests in …s` y `OK`.

**Di esto.**

> Por último, nada central. Cierro el gestor, tumbo una madre de división y cierro el panel sin
> detener nada. Solo quedan nodos, madres y GUIs, y aun así la pérdida se regenera sola: la
> división volvió a cinco. Nueve menos cuatro, cinco; ocho entre dos, cuatro. Este conteo, de las
> bitácoras de todas las madres, dice que cada folio recibió exactamente una respuesta. Y las 201
> pruebas automatizadas están en verde. En resumen: genes que se cargan y copian en caliente,
> folio y huella en cada operación, un sistema que se cura solo sin crecer de más, y ninguna pieza
> indispensable. Gracias.

---

## Si algo falla en vivo

No cortes la grabación. Explica lo que pasó y corrígelo en cámara.

| Qué pasó | Qué decir | Qué hacer |
|---|---|---|
| Al abrir el gestor, el diagrama sale vacío o incompleto | "Arma la topología con los latidos; en dos segundos están todos" | Espera, o clic en **"Consultar topología (TOPO_REQ)"** |
| "Distribuir" dice que no hay nada que distribuir | "Ya tienen sus genes" | Nada: sigue con la escena 3 |
| Una GUI dice `REINTENTO` o `FALLIDA` | "No llegó el mínimo de acuses a tiempo; la GUI reintenta sola con el mismo folio" | Repite la operación |
| Un operador sigue gris tras "Distribuir" | "Espera el primer latido de su madre" | Espera 2 s |
| En la escena 8 o 9 tarda más de 15 s en aparecer el clonador | "Primero tiene que dar por muerta a la célula y esperar su turno" | Espera; no toques nada |
| En el panel, un nodo sale `terminado (1)` | "El puerto está ocupado por un proceso de antes" | Cierra todo, corre la limpieza de abajo y vuelve a empezar |
| Cerraste por error la ventana de un nodo o de una madre | "Esto es justo una caída real" | Si fue una madre, deja que se regenere; si fue un nodo, ▶ en su fila del panel |
| Una ventana tapa lo que quieres mostrar | Nada | Clic en la barra de tareas, o la lupa (`Win` + `+`) |

---

## Después de grabar

### Limpieza

Con el panel cerrado, los procesos siguen vivos (también los reemplazos). Para detenerlos todos:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object CommandLine -match ' -m (nodo|madre|interfaz|gestor|panel|sonda)( |$)' |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Remove-Item run\*.json -ErrorAction SilentlyContinue
```

### Minutos

Mira el video completo y anota en "Minutos por escena" el minuto en que empieza cada escena. Si una
evidencia aparece bastante después del inicio de su escena, escribe su minuto en la columna
"Minuto" de "Matriz del reporte"; si no, déjala vacía y se usa el de la escena.

Después corre:

```powershell
uv run python docs/llenar_minutos.py --revisar   # muestra qué minuto va en cada fila, sin escribir
uv run python docs/llenar_minutos.py             # lo escribe en la columna "Video" del §2 del reporte
uv run python docs/md_a_docx.py                  # regenera el .docx
```

El script revisa que las filas de "Matriz del reporte" coincidan con las de la matriz del reporte
(mismo ID y mismo requisito, en el mismo orden) y no escribe nada si falta un minuto. Lo puedes
volver a correr si corriges alguno.

#### Minutos por escena

| Escena | Título | Minuto |
|---|---|---|
| 1 | Qué cambió y con qué está hecho | `<mm:ss>` |
| 2 | Arranque: nodos, madres vacías y el gestor | `<mm:ss>` |
| 3 | Una operación con folio, de punta a punta | `<mm:ss>` |
| 4 | Solicitudes simultáneas | `<mm:ss>` |
| 5 | Mínimo de ACK y una célula que no acusa | `<mm:ss>` |
| 6 | Carga dinámica | `<mm:ss>` |
| 7 | Baja y cambio de versión | `<mm:ss>` |
| 8 | Falla y autorrecuperación | `<mm:ss>` |
| 9 | Prevención del cáncer | `<mm:ss>` |
| 10 | Cambio de topología | `<mm:ss>` |
| 11 | Sin unidad central y cierre | `<mm:ss>` |

#### Matriz del reporte

Son las filas de la matriz de trazabilidad (§2 del reporte) que se demuestran en el video, en el
mismo orden.

| ID | Requisito | Escena | Minuto |
|---|---|---|---|
| B1 | Suma, resta, multiplicación y división | 4 | |
| B2 | Tres programas base | 2 | |
| B3 | 4 nodos en malla completa | 2 | |
| B4 | Cuatro GUIs | 2 | |
| B5 | Cuatro células por operación | 2 | |
| B6 | Por nodo: una GUI y una célula de cada operación | 2 | |
| B7 | Conexión entre nodos | 2 | |
| B8 | Conexión entre células y nodos | 2 | |
| B9 | Comunicación por Código de Contenido | 3 | |
| B10 | Broadcast sin ciclado | 3 | |
| B11 | Sin límite de nodos ni de células | 10 | |
| B12 | Sin unidad central ni nodo maestro | 11 | |
| F1 | Folio que correlaciona eventos, ACK y respuestas | 3 | |
| F2 | La GUI reconoce sus respuestas | 3 | |
| F3 | Folio + Código de Contenido para atender o ignorar | 3 | |
| F4 | Huella (origen y trayectoria lógica) | 3 | |
| F5 | ACK de recepción y participación | 3 | |
| F6 | Mínimo de ACK | 5 | |
| F7 | Tolerancia si no responden todas | 5 | |
| F8 | Evento: inicio, confirmación, procesamiento y finalización | 3 | |
| M1 | Microservicios en disco | 6 | |
| M2 | Carga en memoria durante la ejecución | 6 | |
| M3 | Programa base sin la lógica de las operaciones | 6 | |
| M4 | Los genes cambian en operación mediante el gestor | 7 | |
| A1 | Detectar la baja de disponibilidad | 8 | |
| A2 | Las células deciden cuándo generar otra instancia | 8 | |
| A3 | La nueva célula recupera sus genes | 8 | |
| A4 | Sin controlador central | 8 | |
| A5 | Detener la clonación al nivel requerido | 9 | |
| A6 | Impedir la generación ilimitada (cáncer) | 9 | |
| A7 | Una falla local no pierde el servicio | 8 | |
| G1 | Arrancar sin microservicios | 2 | |
| G2 | Alta de un servicio | 6 | |
| G3 | Baja de un servicio | 7 | |
| G4 | Modificar o sustituir un servicio | 7 | |
| G5 | Usar la topología para decidir | 6 | |
| G6 | Topología con nodos, células y servicios activos | 2 | |
| G7 | No depender del gestor | 11 | |
| G8 | Alta, baja y cambio se reflejan en la carga dinámica | 7 | |
| P1 | Sin unidad central indispensable | 11 | |
| P3 | Nodos y células flexibles | 10 | |
| P4 | Protocolos con altas, bajas, fallas y nuevas instancias | 10 | |
| P5 | La pérdida de una célula no es punto único de falla | 8 | |
| P6 | Recuperación gradual y controlada | 9 | |
| C1 | Esquema de la Figura 1 del enunciado | 2 | |

### Antes de subirlo

- [ ] El audio se escucha durante todo el video, no solo al principio.
- [ ] Las 11 escenas tienen su minuto y `uv run python docs/llenar_minutos.py` corrió sin errores.
- [ ] El texto de las ventanas se lee al ver el video en pantalla completa.
- [ ] No se ve información personal, contraseñas ni ventanas ajenas.
- [ ] El video está subido con acceso para cualquiera con el enlace (YouTube como *no listado*, o
  Drive), y la liga abre en una ventana de incógnito.
- [ ] La liga del video ya está en la portada del reporte (`<LIGA AL VIDEO>`) y el `.docx` se
  regeneró (sigue en 30 páginas o menos).
