# Guion del video de la Calculadora ADS

Duración objetivo: entre 10 y 11 minutos, en 10 escenas. Cada escena dice qué hacer (clics, teclas y
comandos) y qué decir. El texto de "Di esto" es una guía y lo puedes decir con tus palabras.

Haz las escenas en este orden, porque cada una deja el sistema como lo necesita la siguiente.

**Qué pide el enunciado y dónde se ve** (`docs/ENUNCIADO.md`, §2 y §14):

| Evidencia | Escena |
|---|---|
| Los 4 nodos en malla completa | 2 |
| Una GUI y un servidor de cada operación en cada nodo | 2 |
| Solicitudes y respuestas con su Código de Contenido, y su propagación | 3 |
| Asociación correcta entre solicitud y respuesta | 3 |
| Prevención de ciclos y mensajes duplicados | 3 y 7 |
| Suma, resta, multiplicación y división correctas | 3 y 4 |
| Recorrido de los mensajes observable (§15) | 3 |
| Una sola respuesta por solicitud (§9 y §11) | 5 y 6 |
| Sin punto único de falla (§15) | 8, 9 y 10 |
| Cualquier número de nodos y células (§6 y §10.1) | 10 |

---

## Antes de grabar

En una terminal de PowerShell:

```powershell
cd c:\SCHOOL\COMPUTO_DISTRIBUIDO\calculadora_ads

# 1. Revisa que no quede nada corriendo. Debe imprimir 0
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='py.exe'" |
  Where-Object CommandLine -match ' -m (nodo|servidor|interfaz|panel)( |$)' |
  Measure-Object | ForEach-Object Count

# 2. Guarda las bitácoras viejas para grabar con logs/ vacía
#    (el comando de la escena 5 lee todo lo que hay en logs/)
if (Test-Path logs) { Rename-Item logs "logs_reporte_$(Get-Date -Format yyyyMMdd_HHmm)" }
```

En **otra** terminal, en la misma carpeta, corre las pruebas (~85 s) y déjala abierta. Es la que se
muestra en la escena 10.

```powershell
py -m unittest discover -s tests -t .
```

Checklist:

- [ ] **Prueba de audio.** Graba 10 segundos y escúchalos. El enunciado pide video con audio.
- [ ] Grabador de **pantalla completa**, ya sea OBS Studio ("Captura de pantalla" + micrófono) o la
  Herramienta Recortes en modo grabar con el micrófono activado. No uses la Xbox Game Bar, porque
  graba una sola ventana.
- [ ] No molestar activado (`Win` + `N`).
- [ ] Correo, mensajería y todo lo ajeno al proyecto, cerrado.
- [ ] Las terminales con letra grande (`Ctrl` + `+`).
- [ ] La lupa de Windows a la mano (`Win` + `+` acerca, `Win` + `Esc` la cierra), para el mini log y
  la tabla de tráfico, que tienen letra chica.
- [ ] Este guion en el celular o en otra pantalla, no en la que grabas.

**Dónde quedan las ventanas.** El panel las acomoda solo. Los cuatro nodos quedan en una cuadrícula
de 2 × 2 (Nodo 1 arriba a la izquierda, Nodo 4 abajo a la derecha), las cuatro GUIs quedan en
cascada encima de los Nodos 2 y 4, y el panel queda arriba al centro. Todas se enciman, así que para
traer una al frente haz clic en su barra de título o en la barra de tareas. Pon la terminal sobre el
Nodo 1 y maximízala solo para el comando de la escena 5.

**No cierres con la X la ventana de un nodo**, porque eso detiene el nodo. La caída de un nodo se
hace en la escena 8, desde el panel.

**Si vas largo de tiempo**, en la escena 7 omite la sonda con `--id` y en la escena 10 omite el
quinto nodo. Lo demás cubre lo que pide el enunciado.

---

## Escena 1. Qué cambió y con qué está hecho (1:00)

**Haz esto.** Muestra el diagrama de la sección "Qué hace" del `README.md`.

**Di esto.**

> Hola, soy `<tu nombre>`. Este es el segundo parcial de Cómputo Distribuido. Es la calculadora del
> primer parcial pasada a una arquitectura ADS. En el primer parcial todo pasaba por un middleware,
> y si se caía, se caía todo. Aquí no hay nada central. Cuatro nodos forman el Campo de Datos en
> malla completa, y a cada nodo se conectan cinco células, una GUI y un servidor por operación. Las
> células no se hablan directamente. Publican mensajes sin destinatario, con un Código de Contenido
> como `SUM_REQ`, y cada una toma solo los que le tocan. Los nodos retransmiten por broadcast y
> evitan ciclos, pero nunca abren el contenido. Lo decidí así para que, si aparece un servicio
> nuevo, los nodos no tengan que cambiar. Todo está en Python con la librería estándar, así que no
> hay nada que instalar. Usé sockets TCP con mensajes JSON, uno por línea, hilos para atender varias
> conexiones a la vez, Tkinter para las ventanas y SHA-256 para los identificadores. Cada nodo,
> célula y mensaje genera el suyo, así que nadie tiene que asignarlos.

---

## Escena 2. Los cuatro nodos y sus células (1:15)

**Haz esto.**

1. En la terminal, corre `py -m panel` y haz clic en **"Levantar configuración mínima"**. Empieza a
   hablar mientras salen las 8 ventanas (primero los 4 nodos y, un segundo después, las 4 GUIs).
2. En el panel, señala la matriz de 4 × 6 con "● 1" en cada casilla y la columna "comando" de la
   lista de procesos.
3. Trae al frente el **Nodo 2**. Señala la tabla **"Vecinos: 3"** (Nodo 1, 3 y 4) y recorre con el
   mouse la tabla **"Células: 5 (1 GUI + 4 servidores)"** (GUI-2, SUM-N2, SUB-N2, MUL-N2 y DIV-N2).
4. Trae al frente, uno por uno, los **Nodos 1, 3 y 4** (clic en la barra de tareas) y señala en cada
   uno "Vecinos: 3" y "Células: 5".

**Di esto.**

> Uso este panel solo para la demostración. No es parte del sistema. Lanza procesos que se podrían
> lanzar a mano con el comando que aparece en esta lista. El servidor es el mismo programa para las
> cuatro operaciones y se configura con `--servicio`. Son 24 procesos, 4 nodos y 20 células. Esta
> es la ventana del Nodo 2. Tiene tres vecinos, los otros tres nodos, y cinco células, la GUI y un
> servidor de suma, resta, multiplicación y división. Lo mismo en el Nodo 1, el 3 y el 4, así que la
> malla está completa. Esas dos tablas son el control de conexiones activas. Cada conexión empieza
> con un `HOLA` que dice qué entidad es. A cada nodo le di una sola semilla al azar, y el resto lo
> descubrió solo, por gossip. Así ningún nodo es especial, y agregar uno no obliga a configurar a
> los demás.

---

## Escena 3. Una operación de punta a punta, 7 + 5 (1:45)

Es la escena más importante, porque aquí se ven los 10 pasos del §12. No la apresures.

**Haz esto.**

1. Trae al frente la **GUI-1** y, con el mouse, haz clic en `7` `+` `5` `=`. Señala el display
   (`12`) y la línea de estado ("titular SUM-N… · acuses 4/2 · ~510 ms").
2. Señala en el **mini log de protocolo** la `SOLICITUD`, los cuatro `ACUSE`, el `QUÓRUM 2/2` y el
   `RESULTADO` con "solicitud … ↔ respuesta …".
3. Trae al frente el **Nodo 2** y marca **"pausar"** en la tabla de tráfico. Señala la fila `FWD
   SUM_REQ` (ruta `N1→N2`), las dos `DUP SUM_REQ` y la fila `FWD SUM_RES`. Desmarca "pausar".
4. En el panel, selecciona en la lista el servidor que respondió (el que dice la GUI, por ejemplo
   `SUM-N4`). Señala en su bitácora `RX`, `ACUSE`, `COLA`, `TITULAR · rank 0 de 4` y `RES`.

**Di esto.**

> Siete más cinco desde la GUI-1. Da doce, y aquí abajo está el recorrido. La GUI generó una
> solicitud con un id único y el código `SUM_REQ`, y la mandó al Nodo 1. El Nodo 1 la difundió a
> los otros tres nodos y a sus células. En el Nodo 2 se ve que llegó del Nodo 1, con la ruta N1 a
> N2. Ese campo es el recorrido observable del mensaje. Las dos copias que llegaron después, del
> Nodo 3 y del Nodo 4, son `DUP` y no se retransmiten. Las cuatro células de suma acusaron de
> inmediato, que son estos cuatro acuses, y con dos ya hay quórum. Acusan al recibir y no al
> terminar, para que una célula lenta no parezca muerta. Las demás células la ignoraron
> por código. Respondió una sola, la titular. En su bitácora se ve que recibió, acusó, encoló y al
> medio segundo supo que era la titular. Respondió con `SUM_RES`, un mensaje nuevo con su propio id,
> que lleva el id de la solicitud original y el resultado. La respuesta también viajó por broadcast,
> y solo la GUI-1 la tomó, porque el id de la operación es suyo. Esta línea muestra la asociación
> entre la solicitud y la respuesta. El medio segundo que tarda es la espera para que las células se
> pongan de acuerdo sin un coordinador.

---

## Escena 4. Las cuatro operaciones (0:40)

**Haz esto.** Con el mouse, haz una operación en cada GUI (trae cada una al frente).

| GUI | Clics | Resultado |
|---|---|---|
| GUI-2 | `1` `0` `−` `4` `=` | `6` |
| GUI-3 | `6` `×` `7` `=` | `42` |
| GUI-4 | `7` `÷` `2` `=` | `3.5` |
| GUI-4 | `1` `÷` `0` `=` | `ERROR` y, en rojo, "división entre cero" |

**Di esto.**

> Ahora las otras operaciones, cada una desde otra GUI. Resta, seis. Multiplicación, cuarenta y
> dos. División, tres punto cinco. Y una división entre cero. El sistema no se cae. El servidor
> responde con un error, que viaja igual que un resultado. Cada GUI muestra solo sus operaciones,
> aunque por broadcast le llegan las de todas.

---

## Escena 5. Una sola respuesta por solicitud (0:45)

Esta escena incluye la diferencia con la clase sobre quién responde (reporte, sección 20).

**Haz esto.** Maximiza la terminal y corre este comando. Sale una tabla con **Count = 1** en cada
operación hecha hasta ahora.

```powershell
Select-String '\[RES\]' logs\*-N*.log |
  ForEach-Object { ($_.Line -split ' op ')[1].Substring(0,8) } |
  Group-Object | Select-Object Count, Name
```

**Di esto.**

> Aquí cuento las respuestas en las bitácoras de todos los servidores. Cada operación tiene
> exactamente una. Las células que acusaron calculan el mismo ranking con un hash y llegan a la
> misma titular sin mandar mensajes extra. Las demás quedan como respaldos escalonados, por si la
> titular falla. Aquí me aparto un poco de lo que vimos en clase, donde respondían todas y la GUI
> tomaba la primera. El enunciado pide evitar las respuestas no deseadas, por eso responde una sola.
> La deduplicación en la GUI se conserva como última capa.

---

## Escena 6. Titular lenta, relevo y respuesta suprimida (1:00)

**Haz esto.**

1. En el panel, escribe `4000` en **"retardo ms de los servidores (▶)"** y haz clic en **▶** de la
   columna `+`, fila **Nodo 3**. Aparece `SUM-N3b` en la lista de procesos. Selecciónalo para ver su
   bitácora.
2. **Regresa el retardo a `0`** enseguida, para que el siguiente ▶ no salga lento.
3. En la **GUI-3**, haz sumas sencillas (`1 + 1`, `2 + 2`, `3 + 3`…) hasta que una tarde **~2 s** y
   el estado diga **"relevo 1 SUM-…"**. Es al azar, y sale 1 de cada 5 veces en promedio.
4. En la bitácora de `SUM-N3b`, señala `[TITULAR] … rank 0 de 5` y, unos 4 s después,
   `[SUPRIMIDA] … no envío mi respuesta (titular)`.
5. Haz clic en **■** de la columna `+`, fila Nodo 3, para tumbar `SUM-N3b`.

**Di esto.**

> ¿Y si la titular se cuelga? Levanto una quinta célula de suma que tarda cuatro segundos en
> calcular. Hago sumas hasta que el hash la elija titular... Ahí está. Tardó dos segundos y respondió
> el relevo 1, que esperó su plazo y vio que nadie había respondido. La titular lenta terminó
> después, pero antes de publicar volvió a revisar, vio que la operación ya estaba resuelta y
> suprimió su respuesta. Hubo una sola respuesta, aunque la titular seguía viva. Si en lugar de
> colgarse se cae, pasa lo mismo, y ese caso está en las pruebas automatizadas.

---

## Escena 7. Prevención de ciclos con la sonda (1:00)

**Haz esto.**

1. Trae al frente el **Nodo 2** y pon la terminal sobre el Nodo 1, sin maximizar.
2. Corre este comando y señala en el Nodo 2 la fila `FWD SONDA_PRUEBA` con destino "0 nodo(s)" y la
   fila `TTL`.

   ```powershell
   py -m sonda --nodo 127.0.0.1:5002 --ttl 1
   ```

3. Corre este y señala en el Nodo 2 un `FWD` y dos `DUP` "de SONDA" con el mismo id, y el contador
   "ids en el registro temporal".

   ```powershell
   py -m sonda --nodo 127.0.0.1:5002 --repetir 3
   ```

4. Corre estos dos seguidos (el segundo antes de que pasen 60 s). Trae al frente el **Nodo 3** y
   señala la última fila, `DUP SONDA_PRUEBA … de SONDA`.

   ```powershell
   $id = (py -m sonda --nodo 127.0.0.1:5002 | Select-String '^id=').Line.Substring(3)
   py -m sonda --nodo 127.0.0.1:5003 --id $id
   ```

**Di esto.**

> Una malla completa está llena de ciclos. Para mostrar las defensas uso una sonda, que inyecta un
> mensaje de prueba que ninguna célula procesa. Con TTL de 1, el Nodo 2 lo entrega a sus células
> pero no lo reenvía a ningún nodo. Si mando la misma copia tres veces, procesa una y descarta dos
> como duplicadas, y esas nunca salen del nodo. El registro de ids es temporal y guarda cada uno 60
> segundos. Si reinyecto por el Nodo 3 un id que ya circuló, el Nodo 3 también lo descarta. Además,
> ningún nodo devuelve un mensaje por donde llegó, y cada célula tiene su propio registro.

---

## Escena 8. Se cae un nodo y sus células hacen failover (1:00)

**Haz esto.**

1. Deja a la vista la **GUI-1** y el **Nodo 2**.
2. En el panel, haz clic en **■** de la columna **Nodo**, fila **Nodo 1**. La ventana del Nodo 1
   desaparece.
3. Señala la línea de arriba de la GUI-1. Pasa a ámbar ("se perdió Nodo 1; buscando otro nodo…") y
   en unos 3 s a verde ("failover → Nodo 2").
4. Señala en el Nodo 2 **"Vecinos: 2"** y **"Células: 10 (2 GUI + 8 servidores)"**.
5. En la GUI-1, haz clic en `9` `×` `9` `=`. Debe dar `81`.

**Di esto.**

> Ahora tumbo el Nodo 1 sin avisarle a nadie, como una caída real. Sus cinco células se quedan sin
> nodo. La GUI-1 lo detecta, busca otro nodo en la lista que recibió al conectarse y en unos tres
> segundos se pasa al Nodo 2. Sus servidores hacen lo mismo. El Nodo 2 ahora tiene dos vecinos y
> diez células. Nueve por nueve, ochenta y uno. Ningún nodo es indispensable.

---

## Escena 9. Disponibilidad por latidos (1:00)

Esta escena incluye la diferencia con la clase sobre la disponibilidad (reporte, sección 20).

**Haz esto.**

1. En el panel, haz clic en **■** de la columna `÷` en las filas **Nodo 1, Nodo 2 y Nodo 3**. Queda
   una sola célula de división (`DIV-N4`).
2. Trae al frente la **GUI-2** y espera unos 6 s. En "Disponibilidad (latidos)", la fila de División
   pasa a "vivas: 1" con **✗** rojo, el botón `÷` queda gris y el mini log dice `DESHABILITADA`.
3. En la GUI-2, teclea `8` y luego `/` en el teclado. La línea de estado dice en rojo "DIV no
   disponible".
4. Revisa que el retardo del panel esté en `0` y haz clic en **▶** de la columna `÷`, fila **Nodo
   2**. Nace `DIV-N2b`, y la GUI-2 muestra al instante `HABILITADA … 2/2 (nueva: DIV-N2b · …)`.
5. El `8` sigue en el display de la GUI-2. Haz clic en `÷` `2` `=`. Debe dar `4`.

**Di esto.**

> Cada servidor manda un latido cada dos segundos. Tumbo tres de las cuatro células de división. A
> los seis segundos las GUIs las dan por muertas. Queda una y el mínimo de acuses es dos, así que la
> división se deshabilita. Si intento dividir, me avisa en lugar de mandar una solicitud que no se
> completaría. Levanto una célula nueva... y con su primer latido se habilita otra vez. Ocho entre
> dos, cuatro. Esta es la otra diferencia con la clase, donde la disponibilidad se conocía solo por
> los acuses. Con latidos la GUI lo sabe antes de pedir. Los acuses se conservan y también cuentan
> como señal de vida.

---

## Escena 10. Escalar, cerrar el panel y cierre (1:15)

**Haz esto.**

1. En el panel, haz clic en **▶** de la columna **Nodo**, fila **Nodo 1**. El Nodo 1 regresa con 3
   vecinos.
2. Haz clic en **"+ Nodo"**. Su ventana sale encima del Nodo 1. Señala **"Vecinos: 4"** y, en el
   panel, su `--semillas` con un solo nodo.
3. En la GUI-3, haz clic en `2` `+` `2` `=`. Señala en el tráfico del Nodo 5 un `FWD SUM_REQ` y tres
   `DUP`.
4. Cierra el panel con su **X**. Cuando pregunte "¿Detener también todos los procesos?", contesta
   **No**. En la GUI-4, haz clic en `3` `×` `3` `=`. Debe dar `9`.
5. Trae al frente la terminal de las pruebas (`Ran 106 tests in …s` y `OK`).

**Di esto.**

> El protocolo no depende del número de nodos. Regreso el Nodo 1, que vuelve solo a la malla, y
> agrego un quinto nodo con una sola semilla. Al instante tiene cuatro vecinos, sin cambiar código
> ni reiniciar a nadie. Dos más dos, y el Nodo 5 ya la procesa y descarta tres copias. Ahora cierro
> el panel sin detener los procesos. Tres por tres, nueve. El sistema nunca dependió de él. Por
> último, el proyecto tiene 106 pruebas automatizadas que levantan el sistema completo, y que
> encontraron tres errores reales documentados en el reporte. En resumen, no hay componente
> central, cada solicitud recibe una sola respuesta y nada es indispensable. Gracias.

---

## Si algo falla en vivo

No cortes la grabación. Explica lo que pasó y corrígelo en cámara.

| Qué pasó | Qué decir | Qué hacer |
|---|---|---|
| En la escena 6, la lenta no sale titular tras varias sumas | "Es al azar. El hash la elige una de cada cinco veces" | Sigue sumando. Revisa en el panel que `SUM-N3b` esté `vivo` |
| Después de la escena 6, algunas sumas tardan ~2 s | "Es la célula lenta, y la está relevando un respaldo" | ■ en `+`, fila Nodo 3 (tumba `SUM-N3b`) |
| `DIV-N2b` salió lenta (escena 9) | Nada | El retardo no estaba en 0. ■ en `÷`, fila Nodo 2, pon 0 y ▶ otra vez |
| Una GUI dice `REINTENTO` o `FALLIDA` | "No llegó el quórum a tiempo. La GUI reintenta sola con el mismo id de operación" | Repite la operación |
| En el panel, un nodo sale `terminado (1)` | "El puerto está ocupado por un proceso que quedó de antes" | Cierra todo, corre la limpieza de abajo y vuelve a levantar |
| Cerraste por error la ventana de un nodo | "Esto es justo una caída real", y explica el failover | ▶ en la columna Nodo de esa fila |
| Una ventana tapa lo que quieres mostrar | Nada | Clic en la barra de tareas, o la lupa (`Win` + `+`) para acercar |

---

## Después de grabar

### Limpieza

Con el panel cerrado, los procesos siguen vivos. Para detenerlos todos:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='py.exe'" |
  Where-Object CommandLine -match ' -m (nodo|servidor|interfaz|panel)( |$)' |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

### Minutos

Mira el video completo y anota en "Minutos por escena" el minuto en que empieza cada escena. Si una
evidencia aparece bastante después del inicio de su escena, escribe su minuto en la columna "Minuto"
de "Matriz del reporte". Si no, déjala vacía y se usa el de la escena.

Después corre:

```powershell
py docs/llenar_minutos.py --revisar   # muestra qué minuto va en cada fila, sin escribir
py docs/llenar_minutos.py             # lo escribe en la columna "Video" del §2 del reporte
py docs/md_a_docx.py                  # regenera el .docx
```

El script revisa que las filas de "Matriz del reporte" coincidan con las de la matriz del reporte
(mismo § y mismo requisito, en el mismo orden) y no escribe nada si falta un minuto. Lo puedes
volver a correr si corriges alguno.

#### Minutos por escena

| Escena | Título | Minuto |
|---|---|---|
| 1 | Qué cambió y con qué está hecho | `<mm:ss>` |
| 2 | Los cuatro nodos y sus células | `<mm:ss>` |
| 3 | Una operación de punta a punta | `<mm:ss>` |
| 4 | Las cuatro operaciones | `<mm:ss>` |
| 5 | Una sola respuesta por solicitud | `<mm:ss>` |
| 6 | Titular lenta, relevo y respuesta suprimida | `<mm:ss>` |
| 7 | Prevención de ciclos con la sonda | `<mm:ss>` |
| 8 | Failover | `<mm:ss>` |
| 9 | Disponibilidad por latidos | `<mm:ss>` |
| 10 | Escalar, cerrar el panel y cierre | `<mm:ss>` |

#### Matriz del reporte

Son las filas de la matriz de trazabilidad (§2 del reporte) que se demuestran en el video, en el
mismo orden.

| § | Requisito | Escena | Minuto |
|---|---|---|---|
| 1 | Cualquier lenguaje | 1 | |
| 4 | Suma, resta, multiplicación y división vía Campo de Datos, broadcast y código | 4 | |
| 5 | Célula cliente (GUI): captura, genera la solicitud, recibe la respuesta | 3 | |
| 5 | Célula servidor configurable por servicio | 2 | |
| 5 | Nodo: forma la malla, acepta conexiones, retransmite por broadcast | 2 | |
| 6 | 4 nodos en malla completa | 2 | |
| 6 | 5 células por nodo (20 en total) | 2 | |
| 6 | Sin límite de nodos ni de células; sin cambiar el código | 10 | |
| 7 | Toda solicitud y respuesta lleva Código de Contenido | 3 | |
| 7 | La respuesta es un mensaje nuevo con el id de la solicitud original y el resultado | 3 | |
| 9 | Broadcast por el Campo de Datos | 3 | |
| 9 | Evitar múltiples respuestas no deseadas (estrategia documentada) | 5 | |
| 9 | Respuestas difundidas con su código de respuesta | 3 | |
| 10.1 | Conectar los nodos en malla | 2 | |
| 10.1 | Conectar GUIs y servidores a cada nodo | 2 | |
| 10.1 | Identificar el tipo de entidad y controlar las conexiones activas | 2 | |
| 10.1 | Independiente del número de instancias | 10 | |
| 10.2 | Broadcast entre nodos y células | 3 | |
| 10.2 | Transporta los códigos de solicitud y de respuesta | 3 | |
| 10.2 | Impide la circulación indefinida | 7 | |
| 10.2 | Detecta mensajes ya recibidos | 7 | |
| 10.2 | Asocia la respuesta con su solicitud | 3 | |
| 11 | Registro **temporal** de ids procesados | 7 | |
| 11 | No retransmitir un id repetido | 7 | |
| 11 | La respuesta tiene id propio y conserva el de la solicitud | 3 | |
| 11 | Estrategia contra respuestas duplicadas con varios servidores | 6 | |
| 12 | Flujo general de 10 pasos | 3 | |
| 14 | Nodos 1 a 4 ejecutándose en malla completa | 2 | |
| 14 | Una GUI y un servidor de cada operación por nodo | 2 | |
| 14 | Solicitudes y respuestas con Código de Contenido | 3 | |
| 14 | Asociación correcta solicitud ↔ respuesta | 3 | |
| 14 | Prevención de ciclos y de mensajes duplicados | 7 | |
| 14 | Ejecución correcta de las 4 operaciones | 4 | |
| 15 | Sin nodo central ni punto único de falla | 8 | |
| 15 | Recorrido de los mensajes observable | 3 | |

### Antes de subirlo

- [ ] El audio se escucha durante todo el video, no solo al principio.
- [ ] Las 10 escenas tienen su minuto y `py docs/llenar_minutos.py` corrió sin errores.
- [ ] El texto de las ventanas se lee al ver el video en pantalla completa.
- [ ] No se ve información personal, contraseñas ni ventanas ajenas.
- [ ] El video está subido con acceso para cualquiera con el enlace (YouTube como *no listado*, o
  Drive), y la liga abre en una ventana de incógnito.
- [ ] La liga del video ya está en la portada del reporte (`<LIGA AL VIDEO>`) y el `.docx` se
  regeneró.
