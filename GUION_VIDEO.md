# Guion del video de la Calculadora ADS

Duración objetivo: unos 16 minutos, en 15 escenas. Cada escena dice qué hacer (clics, teclas y
comandos) y qué decir. El texto de "Di esto" es una guía y lo puedes decir con tus palabras.

Haz las escenas en este orden, porque cada una deja el sistema como lo necesita la siguiente.

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
#    (los comandos de las escenas 6 y 7 leen todo lo que hay en logs/)
if (Test-Path logs) { Rename-Item logs "logs_reporte_$(Get-Date -Format yyyyMMdd_HHmm)" }
```

En **otra** terminal, en la misma carpeta, corre las pruebas (~85 s) y déjala abierta. Es la que se
muestra en la escena 14.

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
Nodo 1 y maximízala solo para los comandos de las escenas 6 y 7.

**No cierres con la X la ventana de un nodo**, porque eso detiene el nodo. La caída de un nodo se
hace en la escena 10, desde el panel.

---

## Escena 1. Presentación (0:30)

**Haz esto.** Muestra el `README.md` del repositorio.

**Di esto.**

> Hola, soy `<tu nombre>`. Este es el proyecto del segundo parcial de Cómputo Distribuido. Es la
> calculadora del primer parcial, pasada a una arquitectura de sistemas autónomos descentralizados,
> o ADS. En el primer parcial todo pasaba por un middleware, y ese middleware era un punto único de
> falla. Aquí ya no hay middleware ni servidor central. Hay un Campo de Datos formado por nodos en
> malla, y las células se comunican solo por broadcast, con Códigos de Contenido. Está hecho en
> Python, solo con la librería estándar, así que no hay nada que instalar.

---

## Escena 2. La arquitectura (0:45)

**Haz esto.** Muestra el diagrama del `README.md` (sección "Qué hace") o el de la sección 3.2 del
reporte.

**Di esto.**

> Esta es la arquitectura que pide el enunciado. Cuatro nodos forman el Campo de Datos en malla
> completa, así que cada nodo está conectado con los otros tres. A cada nodo se conectan cinco
> células, una GUI y un servidor de cada operación. Son veinte células en total. Los nodos solo
> aceptan conexiones, retransmiten por broadcast y evitan los ciclos. Nunca abren el contenido de un
> mensaje. Cada célula decide qué le interesa por el Código de Contenido. Por ejemplo, una célula de
> suma solo procesa `SUM_REQ` e ignora todo lo demás. Cada nodo, célula, mensaje y operación tiene
> un identificador SHA-256 que genera él mismo. Nadie asigna identificadores, porque no hay un
> componente central.

---

## Escena 3. Levantar el sistema (1:00)

**Haz esto.**

1. En la terminal, corre `py -m panel`.
2. En el panel, haz clic en **"Levantar configuración mínima"**.
3. Espera las 8 ventanas. Primero salen los 4 nodos y, un segundo después, las 4 GUIs.
4. Trae el panel al frente. Señala la matriz de 4 × 6 con "● 1" en cada casilla y la columna
   "comando" de la lista de procesos.

**Di esto.**

> Para la demostración uso este panel. Aclaro que el panel no es parte del sistema, y así lo dice su
> rótulo. Solo lanza procesos del sistema operativo, y cada uno se podría lanzar a mano con el
> comando que aparece en la lista. Por ejemplo, el Nodo 2 es `py -m nodo --puerto 5002` con una
> semilla. Un servidor es `py -m servidor --servicio SUM` conectado a su nodo. Es el mismo programa
> para las cuatro operaciones y se configura con `--servicio`. Son 24 procesos independientes, 4
> nodos y 20 células. Los servidores no tienen ventana, y su bitácora se ve aquí abajo al
> seleccionarlos.

---

## Escena 4. La malla y el control de conexiones (1:15)

**Haz esto.**

1. Trae al frente la ventana del **Nodo 2**.
2. Señala el encabezado ("Nodo 2 · <hash> · escucha 127.0.0.1:5002"), la tabla **"Vecinos: 3"** y la
   tabla **"Células: 5 (1 GUI + 4 servidores)"**.
3. Trae el panel y señala la parte `--semillas` del comando de los nodos 3 y 4.

**Di esto.**

> Esta es la ventana del Nodo 2, y aquí se ve lo que pide el protocolo de conexión. A la izquierda
> están sus vecinos, los otros tres nodos, así que la malla está completa. A la derecha están sus
> células, una GUI y cuatro servidores, cada uno con su tipo, servicio y hash. Esas dos tablas son
> el control de conexiones activas. El nodo sabe quién es quién porque toda conexión empieza con un
> mensaje `HOLA` que dice qué entidad es. El nodo contesta `BIENVENIDA` con la lista de nodos que
> conoce, y cada vez que conoce uno nuevo se lo avisa a los demás con `PARES`. Así se descubren por
> gossip. En el panel se ve que a cada nodo le di como semilla un solo nodo, elegido al azar. Nadie
> tiene la lista completa, y aun así la malla se completó sola en una fracción de segundo. Si dos
> nodos se marcan al mismo tiempo, quedan dos conexiones entre ellos. Una regla basada solo en los
> hashes hace que los dos se queden con la misma, sin hablarlo.

---

## Escena 5. Una operación de punta a punta, 7 + 5 (2:15)

Es la escena más importante, porque aquí se ven los 10 pasos del §12. No la apresures.

**Haz esto.**

1. Trae al frente la **GUI-1** y, con el mouse, haz clic en `7` `+` `5` `=`.
2. Señala el display (`12`) y la línea de estado ("titular SUM-N… · acuses 4/2 · ~510 ms").
3. Señala la línea nueva de **"Mis operaciones"** y **anota el `op`** del final (8 caracteres). Lo
   usas en la escena 7.
4. Señala en el **mini log de protocolo** la `SOLICITUD`, los cuatro `ACUSE`, el `QUÓRUM 2/2` y el
   `RESULTADO` con "solicitud … ↔ respuesta …".
5. Trae al frente el **Nodo 2** y marca **"pausar"** en la tabla de tráfico. Señala la fila `FWD
   SUM_REQ` (ruta `N1→N2`), las dos `DUP SUM_REQ` y la fila `FWD SUM_RES`. Desmarca "pausar".
6. En el panel, selecciona en la lista el servidor que respondió (el que dice la GUI, por ejemplo
   `SUM-N4`). Señala en su bitácora `RX`, `ACUSE`, `COLA`, `TITULAR · rank 0 de 4` y `RES`.

**Di esto.**

> Hago una suma desde la GUI-1, siete más cinco. El resultado es 12, y abajo está el recorrido
> completo. La GUI generó una solicitud con un identificador único y el código `SUM_REQ`, y la mandó
> a su nodo, el Nodo 1. El Nodo 1 la difundió a los otros tres nodos y a sus células. En el Nodo 2
> se ve que la recibió del Nodo 1, con la ruta N1 a N2. Ese campo `ruta` es el recorrido observable
> del mensaje. Después le llegaron dos copias más, del Nodo 3 y del Nodo 4. Son `DUP`, porque ya la
> había procesado, y no las retransmite. Las otras 19 células recibieron la solicitud una sola vez
> cada una, pero solo las cuatro de suma la procesaron. Las cuatro acusaron de inmediato, que son
> estos cuatro `ACUSE` en la GUI. Con dos acuses la GUI ya tiene quórum. Aunque las cuatro tienen la
> operación, respondió una sola, la titular. Esta es su bitácora. Recibió, acusó, encoló y, al medio
> segundo, supo que era la titular, en el lugar 0 de 4. Respondió con `SUM_RES`, un mensaje nuevo
> con su propio identificador, que lleva el identificador de la solicitud original y el resultado.
> La respuesta también viajó por broadcast. Las cuatro GUIs la recibieron, pero solo la GUI-1 la
> reconoció como suya, por el identificador de la operación. En esta línea se ve la asociación entre
> la solicitud y la respuesta. Son identificadores distintos, y la GUI sabe que van juntos. La
> operación tarda medio segundo, y casi todo es espera a propósito. Es el tiempo que usan las
> células para ponerse de acuerdo sobre quién responde, sin un coordinador.

---

## Escena 6. Las cuatro operaciones, una desde cada GUI (1:00)

**Haz esto.**

1. Con el mouse, haz una operación en cada GUI (trae cada una al frente).

   | GUI | Clics | Resultado |
   |---|---|---|
   | GUI-2 | `1` `0` `−` `4` `=` | `6` |
   | GUI-3 | `6` `×` `7` `=` | `42` |
   | GUI-4 | `7` `÷` `2` `=` | `3.5` |
   | GUI-4 | `1` `÷` `0` `=` | `ERROR` y, en rojo, "división entre cero" |

2. Maximiza la terminal y corre este comando. Muestra las solicitudes de las otras GUIs que la GUI-1
   ignoró ("SUB_REQ de GUI-2 (…): no es para una GUI").

   ```powershell
   Select-String '\[IGNORA\] (SUB|MUL|DIV)_REQ' logs\GUI-1-*.log | ForEach-Object Line
   ```

**Di esto.**

> Ahora las cuatro operaciones, cada una desde una GUI distinta. Resta en la GUI-2, seis.
> Multiplicación en la GUI-3, cuarenta y dos. División en la GUI-4, tres punto cinco. Y una división
> entre cero. El sistema no se cae. La célula de división responde con un error, y ese error es una
> respuesta válida que viaja igual que un resultado. La titular la decide el hash en cada operación,
> así que el trabajo se reparte entre los nodos sin que nadie lo asigne. Las GUIs tampoco se
> mezclan. En "Mis operaciones" cada GUI tiene solo las suyas. Las solicitudes de las demás sí les
> llegan, porque todo es broadcast, pero las ignoran por código. Aquí está la bitácora de la GUI-1,
> que ignoró la resta de la GUI-2, la multiplicación de la GUI-3 y las divisiones de la GUI-4.

---

## Escena 7. Una sola respuesta por solicitud (1:00)

Esta escena incluye la diferencia con la clase sobre quién responde (reporte, sección 20).

**Haz esto.**

1. En la terminal, pon el `op` que anotaste en la escena 5 y corre:

   ```powershell
   $op = 'xxxxxxxx'   # el "op" de 7 + 5 que muestra la GUI-1
   Select-String "op $op" logs\SUM-*.log |
     Where-Object Line -match '\[(TITULAR|RESPALDO|LIBERADO|RETIRADA|RES)\]' |
     ForEach-Object { '{0,-8} {1}' -f ($_.Filename -replace '-[0-9a-f]{8}\.log$',''), $_.Line }
   ```

   Se ven las cuatro células de suma, una `TITULAR` con su `RES`, tres `RESPALDO` (rank 1, 2 y 3,
   con relevo a los 1.5, 3.0 y 4.5 s) y tres `LIBERADO`. Si un respaldo sale como `RETIRADA` en
   lugar de `RESPALDO` y `LIBERADO`, también es correcto. Solo vio la respuesta antes de terminar su
   elección.

2. Cuenta las respuestas por operación:

   ```powershell
   Select-String '\[RES\]' logs\*-N*.log |
     ForEach-Object { ($_.Line -split ' op ')[1].Substring(0,8) } |
     Group-Object | Select-Object Count, Name
   ```

   Sale una tabla con **Count = 1** en cada operación hecha hasta ahora.

**Di esto.**

> El enunciado pide evitar que una misma solicitud produzca varias respuestas, y así se logra. Cada
> célula de suma calcula el mismo ranking entre las células que acusaron, con un hash de su
> identificador y el de la operación. Todas llegan a la misma conclusión sin mandar ningún mensaje
> extra. Una es la titular y responde. Las demás quedan como respaldos escalonados, cada una con un
> plazo distinto, y cuando ven la respuesta de la titular quedan liberadas. Y este es el conteo.
> Cada operación que hice tiene exactamente una respuesta en todo el sistema. Aquí me aparto un poco
> de lo que vimos en clase. En clase se planteó que respondieran todas las células y que la GUI
> tomara la primera. El enunciado pide evitar las respuestas no deseadas, no solo filtrarlas, y por
> eso decidí que responda una sola. La redundancia se mantiene en los respaldos, que responden si la
> titular falla, y la deduplicación en la GUI que vimos en clase sigue ahí como última capa.

---

## Escena 8. Titular lenta, relevo y respuesta suprimida (1:45)

**Haz esto.**

1. En el panel, escribe `4000` en **"retardo ms de los servidores (▶)"** y haz clic en **▶** de la
   columna `+`, fila **Nodo 3**. Aparece `SUM-N3b` en la lista de procesos. Selecciónalo para ver su
   bitácora.
2. **Regresa el retardo a `0`** enseguida, para que el siguiente ▶ no salga lento.
3. En la **GUI-3**, haz sumas sencillas (`1 + 1`, `2 + 2`, `3 + 3`…) hasta que una tarde **~2 s** y
   el estado diga **"relevo 1 SUM-…"**. Es al azar. Con 5 células de suma, la lenta sale titular 1
   de cada 5 veces en promedio.
4. En la bitácora de `SUM-N3b` (en el panel), señala `[TITULAR] … rank 0 de 5` y, unos 4 s después,
   `[SUPRIMIDA] … no envío mi respuesta (titular)`.
5. Haz clic en **■** de la columna `+`, fila Nodo 3. Tumba la más reciente, que es `SUM-N3b`, y así
   las siguientes sumas ya no tardan de más.

**Di esto.**

> ¿Qué pasa si la titular se cuelga? Voy a levantar una quinta célula de suma, pero lenta, que tarda
> cuatro segundos en calcular. Las GUIs la ven al instante, y la suma pasa a cinco vivas. Hago sumas
> hasta que el hash la elija titular... Ahí está. Esta tardó dos segundos, y no respondió la titular
> sino el relevo 1. El primer respaldo esperó su plazo, vio que nadie había respondido y respondió
> él. Lo interesante viene después. La titular lenta sí terminó de calcular, a los cuatro segundos y
> medio. Pero antes de publicar volvió a revisar, vio que la operación ya estaba resuelta y suprimió
> su respuesta. Así hubo una sola respuesta, aunque la titular seguía viva. Si la titular se cae en
> lugar de colgarse, pasa lo mismo y responde el relevo. Ese caso está cubierto en las pruebas
> automatizadas.

---

## Escena 9. Prevención de ciclos con la sonda (1:45)

**Haz esto.**

1. Trae al frente el **Nodo 2** y pon la terminal sobre el Nodo 1. Señala en el encabezado del Nodo
   2 los contadores "duplicados descartados" e "ids en el registro temporal".
2. Corre este comando y señala en el Nodo 2 la fila `FWD SONDA_PRUEBA` con destino "0 nodo(s)" y la
   fila `TTL`.

   ```powershell
   py -m sonda --nodo 127.0.0.1:5002 --ttl 1
   ```

3. Corre este y señala en el Nodo 2 un `FWD` y dos `DUP` "de SONDA" con el mismo id.

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

> Una malla completa está llena de ciclos. Sin defensas, un solo mensaje daría vueltas para siempre.
> Hay cuatro defensas, y para mostrarlas por separado uso una sonda. Es una herramienta que se
> conecta a un nodo, inyecta un mensaje de prueba que ninguna célula procesa y termina. La primera
> defensa es el TTL. Mando un mensaje con TTL de 1 al Nodo 2. Lo procesó y lo entregó a sus células,
> pero no lo reenvió a ningún nodo, porque el TTL se agotó ahí. La segunda es el registro de
> identificadores. Mando la misma copia tres veces. El Nodo 2 procesó la primera y descartó las
> otras dos como duplicadas, así que nunca salieron de ese nodo. El registro es temporal. Cada id se
> recuerda 60 segundos, y este contador muestra cuántos hay ahora. Y no solo lo detecta el nodo que
> lo vio entrar. Tomo el identificador de un mensaje que ya circuló y lo reinyecto por el Nodo 3. El
> Nodo 3 también lo reconoce y lo descarta. Las otras dos defensas actúan en cada mensaje. Un nodo
> nunca devuelve un mensaje por donde llegó ni lo manda a un nodo que ya está en la ruta, y cada
> célula tiene su propio registro de vistos.

---

## Escena 10. Se cae un nodo y sus células hacen failover (1:15)

**Haz esto.**

1. Deja a la vista la **GUI-1** y el **Nodo 2**.
2. En el panel, haz clic en **■** de la columna **Nodo**, fila **Nodo 1**. La ventana del Nodo 1
   desaparece.
3. Señala la línea de arriba de la GUI-1. Pasa a ámbar ("se perdió Nodo 1; buscando otro nodo…") y
   en unos 3 s a verde ("failover → Nodo 2").
4. Señala en el Nodo 2 **"Vecinos: 2"** y **"Células: 10 (2 GUI + 8 servidores)"**.
5. En la GUI-1, haz clic en `9` `×` `9` `=`. Debe dar `81`.

**Di esto.**

> Ahora tumbo un nodo completo, el Nodo 1. El panel lo mata sin avisarle a nadie, así que es una
> caída real. Sus cinco células se quedaron sin nodo. La GUI-1 detectó la caída, buscó otro nodo en
> la lista que recibió al conectarse y en unos tres segundos se pasó sola al Nodo 2. Los cuatro
> servidores del Nodo 1 hicieron lo mismo. El Nodo 2 ahora tiene dos vecinos y diez células, y la
> GUI-1 sigue funcionando. Nueve por nueve, ochenta y uno. El failover es más rápido que la
> caducidad de los latidos, así que ninguna GUI llegó a dar por muertos a esos servidores. Por eso
> ningún nodo es un punto único de falla. Un detalle. La matriz del panel cuenta las células por el
> nodo con el que se lanzaron. Dónde están conectadas ahora se ve en la ventana de cada nodo.

---

## Escena 11. Disponibilidad por latidos (1:15)

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

*Opcional (20 s).* Antes del paso 4, baja "mín. acuses" de División a `1` en la GUI-2. El operador
se habilita con una sola viva. Después regrésalo a `2`.

**Di esto.**

> Cada célula servidor publica un latido cada dos segundos, por broadcast como todo lo demás. Con
> eso, cada GUI sabe en todo momento cuántas células de cada operación están vivas. Tumbo tres de
> las cuatro células de división. Seis segundos después, que son tres latidos sin noticias, las GUIs
> las dan por muertas. Queda una viva y el mínimo de acuses es dos, así que la GUI deshabilita la
> división y lo anota en su mini log. Si intento dividir, me avisa que no está disponible en lugar
> de mandar una solicitud que no podría completarse. Levanto una célula de división nueva... En
> cuanto manda su primer latido, la división se habilita otra vez, y la GUI dice qué célula llegó.
> Ocho entre dos, cuatro. Esta es la otra diferencia con lo que vimos en clase. En clase la
> disponibilidad se conocía solo por los acuses. Yo agregué latidos para que la GUI sepa, antes de
> pedir, si una célula aparece o desaparece. Con solo acuses se enteraría hasta que una operación
> fallara. Los acuses se conservan y también cuentan como señal de vida.

---

## Escena 12. Un quinto nodo en vivo (0:45)

**Haz esto.**

1. En el panel, haz clic en **▶** de la columna **Nodo**, fila **Nodo 1**. El Nodo 1 regresa con 3
   vecinos y 0 células, porque las suyas ya viven en el Nodo 2.
2. Haz clic en **"+ Nodo"**. Aparece la fila Nodo 5 en la matriz y su ventana sale encima del Nodo 1.
   Señala **"Vecinos: 4"** y, en el panel, su `--semillas` con un solo nodo.
3. En la GUI-3, haz clic en `2` `+` `2` `=`. Señala en la tabla de tráfico del Nodo 5 un `FWD
   SUM_REQ` y tres `DUP`.

**Di esto.**

> El enunciado pide que el protocolo no dependa del número de nodos ni de células. Primero regreso
> el Nodo 1, que vuelve solo a la malla con sus tres vecinos. Ahora agrego un quinto nodo, con el
> mismo programa y una sola semilla. En menos de una décima de segundo ya está conectado con los
> otros cuatro. No cambié código ni configuración, y no reinicié a nadie. Hago una suma, y el quinto
> nodo ya participa. La procesó una vez y descartó las tres copias que le llegaron de los otros
> nodos. Con las células pasa lo mismo. La de suma lenta y la de división nueva que levanté se
> integraron sin avisarle a nadie.

---

## Escena 13. El panel tampoco es punto de falla (0:30)

**Haz esto.**

1. Cierra el panel con su **X**. Cuando pregunte "¿Detener también todos los procesos?", contesta
   **No**.
2. En la GUI-4, haz clic en `3` `×` `3` `=`. Debe dar `9`.

**Di esto.**

> Por último, cierro el panel y le digo que no detenga los procesos. Las ventanas siguen ahí y el
> sistema sigue funcionando. Tres por tres, nueve. El panel solo lanzaba procesos, y el sistema
> nunca dependió de él.

---

## Escena 14. Pruebas automatizadas (0:30)

**Haz esto.** Trae al frente la segunda terminal, la de las pruebas (`Ran 106 tests in …s` y `OK`).

**Di esto.**

> El proyecto tiene 106 pruebas automatizadas. Hay pruebas unitarias de cada módulo común y pruebas
> de integración que levantan el sistema completo dentro del proceso, con una célula espía que
> cuenta cuántas respuestas hay por operación. Las pruebas encontraron tres errores reales, que
> están documentados en el reporte. El más interesante era que, si un reintento llegaba a un
> servidor antes que la solicitud original por caminos distintos de la malla, salía una segunda
> respuesta. Se corrigió y quedó cubierto con su prueba.

---

## Escena 15. Cierre (0:45)

**Haz esto.** Deja a la vista las ventanas del sistema o el diagrama del README.

**Di esto.**

> Para cerrar, estos son los tres puntos principales del diseño. Primero, no hay componente central.
> Los nodos se encuentran por gossip con una sola semilla, la difusión no usa tablas de ruteo y la
> titular de cada operación se elige sin coordinador. Segundo, cada solicitud recibe una sola
> respuesta, con respaldos escalonados por si la titular falla y varias capas más para los casos de
> borde. Tercero, nada es indispensable. Se cayó un nodo, se cayeron servidores, se cerró el panel y
> el sistema siguió funcionando. Los límites conocidos están en el reporte. Los enlaces medio
> abiertos no se detectan, no hay autenticación de quien se conecta, y el foliado y las células que
> levantan células quedan para la entrega final. Gracias.

---

## Si algo falla en vivo

No cortes la grabación. Explica lo que pasó y corrígelo en cámara.

| Qué pasó | Qué decir | Qué hacer |
|---|---|---|
| En la escena 8, la lenta no sale titular tras varias sumas | "Es al azar. El hash la elige una de cada cinco veces" | Sigue sumando. Revisa en el panel que `SUM-N3b` esté `vivo` |
| Después de la escena 8, algunas sumas tardan ~2 s | "Es la célula lenta, y la está relevando un respaldo" | ■ en `+`, fila Nodo 3 (tumba `SUM-N3b`) |
| `DIV-N2b` salió lenta (escena 11) | Nada | El retardo no estaba en 0. ■ en `÷`, fila Nodo 2, pon 0 y ▶ otra vez |
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
| 1 | Presentación | `<mm:ss>` |
| 2 | La arquitectura | `<mm:ss>` |
| 3 | Levantar el sistema | `<mm:ss>` |
| 4 | La malla y el control de conexiones | `<mm:ss>` |
| 5 | Una operación de punta a punta | `<mm:ss>` |
| 6 | Las cuatro operaciones | `<mm:ss>` |
| 7 | Una sola respuesta por solicitud | `<mm:ss>` |
| 8 | Titular lenta, relevo y respuesta suprimida | `<mm:ss>` |
| 9 | Prevención de ciclos con la sonda | `<mm:ss>` |
| 10 | Failover | `<mm:ss>` |
| 11 | Disponibilidad por latidos | `<mm:ss>` |
| 12 | Un quinto nodo | `<mm:ss>` |
| 13 | El panel tampoco es punto de falla | `<mm:ss>` |
| 14 | Pruebas automatizadas | `<mm:ss>` |
| 15 | Cierre | `<mm:ss>` |

#### Matriz del reporte

Son las filas de la matriz de trazabilidad (§2 del reporte) que se demuestran en el video, en el
mismo orden.

| § | Requisito | Escena | Minuto |
|---|---|---|---|
| 1 | Cualquier lenguaje | 1 | |
| 4 | Suma, resta, multiplicación y división vía Campo de Datos, broadcast y código | 6 | |
| 5 | Célula cliente (GUI): captura, genera la solicitud, recibe la respuesta | 5 | |
| 5 | Célula servidor configurable por servicio | 3 | |
| 5 | Nodo: forma la malla, acepta conexiones, retransmite por broadcast | 4 | |
| 6 | 4 nodos en malla completa | 4 | |
| 6 | 5 células por nodo (20 en total) | 4 | |
| 6 | Sin límite de nodos ni de células; sin cambiar el código | 12 | |
| 7 | Toda solicitud y respuesta lleva Código de Contenido | 5 | |
| 7 | La respuesta es un mensaje nuevo con el id de la solicitud original y el resultado | 5 | |
| 9 | Broadcast por el Campo de Datos | 5 | |
| 9 | Evitar múltiples respuestas no deseadas (estrategia documentada) | 7 | |
| 9 | Respuestas difundidas con su código de respuesta | 5 | |
| 10.1 | Conectar los nodos en malla | 4 | |
| 10.1 | Conectar GUIs y servidores a cada nodo | 4 | |
| 10.1 | Identificar el tipo de entidad y controlar las conexiones activas | 4 | |
| 10.1 | Independiente del número de instancias | 12 | |
| 10.2 | Broadcast entre nodos y células | 5 | |
| 10.2 | Transporta los códigos de solicitud y de respuesta | 5 | |
| 10.2 | Impide la circulación indefinida | 9 | |
| 10.2 | Detecta mensajes ya recibidos | 9 | |
| 10.2 | Asocia la respuesta con su solicitud | 5 | |
| 11 | Registro **temporal** de ids procesados | 9 | |
| 11 | No retransmitir un id repetido | 9 | |
| 11 | La respuesta tiene id propio y conserva el de la solicitud | 5 | |
| 11 | Estrategia contra respuestas duplicadas con varios servidores | 8 | |
| 12 | Flujo general de 10 pasos | 5 | |
| 14 | Nodos 1 a 4 ejecutándose en malla completa | 4 | |
| 14 | Una GUI y un servidor de cada operación por nodo | 4 | |
| 14 | Solicitudes y respuestas con Código de Contenido | 5 | |
| 14 | Asociación correcta solicitud ↔ respuesta | 5 | |
| 14 | Prevención de ciclos y de mensajes duplicados | 9 | |
| 14 | Ejecución correcta de las 4 operaciones | 6 | |
| 15 | Sin nodo central ni punto único de falla | 10 | |
| 15 | Recorrido de los mensajes observable | 5 | |

### Antes de subirlo

- [ ] El audio se escucha durante todo el video, no solo al principio.
- [ ] Las 15 escenas tienen su minuto y `py docs/llenar_minutos.py` corrió sin errores.
- [ ] El texto de las ventanas se lee al ver el video en pantalla completa.
- [ ] No se ve información personal, contraseñas ni ventanas ajenas.
- [ ] El video está subido con acceso para cualquiera con el enlace (YouTube como *no listado*, o
  Drive), y la liga abre en una ventana de incógnito.
- [ ] La liga del video ya está en la portada del reporte (`<LIGA AL VIDEO>`) y el `.docx` se
  regeneró.
