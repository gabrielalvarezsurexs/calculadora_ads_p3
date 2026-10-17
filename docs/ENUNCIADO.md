# Enunciado del Proyecto del Segundo Parcial

Transcripción fiel de `Instrucciones_Proyecto_Segundo_Parcial_ADS (1).pdf` (Cómputo Distribuido,
6 de octubre de 2026). Si hay duda, manda el PDF.

---

## Adecuación de la calculadora del primer parcial a una arquitectura ADS

**Objetivo general.** Transformar la calculadora del primer parcial para operar bajo una
arquitectura ADS, usando un Campo de Datos de cuatro nodos en malla completa, células GUI y células
servidor distribuidas, comunicación por broadcast y Códigos de Contenido para solicitudes y
respuestas.

## 1. Lenguaje de programación

- El proyecto puede desarrollarse en cualquier lenguaje de programación.
- Si el proyecto se realiza en JAVA, se otorgarán puntos extras. La cantidad de puntos adicionales
  será la indicada por el profesor.

## 2. Entregables obligatorios

| Entregable | Contenido requerido |
|---|---|
| **Reporte técnico** | Documento que explique técnicamente el diseño y construcción del sistema, incluyendo la arquitectura ADS, topología, protocolos, broadcast, Códigos de Contenido, prevención de ciclos y decisiones de implementación. |
| **Video con audio** | Demostración del funcionamiento de los cuatro nodos, las células conectadas, el broadcast, la atención de solicitudes y la recepción de respuestas. |
| **Liga al código fuente** | Enlace accesible al código fuente completo de los programas: célula cliente, célula servidor y nodo del Campo de Datos. |

## 3. Regla de originalidad académica

**IMPORTANTE:** No se permite la copia total o parcial entre proyectos. En caso de detectarse copia,
se anulará la calificación del proyecto y el caso será reportado al coordinador de la carrera
correspondiente.

## 4. Arquitectura del proyecto

**La arquitectura cliente/servidor de tres capas del primer parcial se sustituye por una
arquitectura ADS.** La calculadora conservará las operaciones de suma, resta, multiplicación y
división, pero el acceso a los servicios se realizará mediante el Campo de Datos, broadcast y Código
de Contenido.

## 5. Programas que deben desarrollarse

- **Célula cliente (GUI).** Programa que contiene la interfaz gráfica de la calculadora, captura los
  operandos y la operación, genera la solicitud y recibe la respuesta.
- **Célula servidor.** Programa capaz de configurarse para atender un servicio específico: suma,
  resta, multiplicación o división.
- **Nodo del Campo de Datos.** Programa encargado de formar la malla de comunicación, aceptar
  conexiones de células y nodos, y retransmitir mensajes mediante broadcast.

## 6. Configuración obligatoria del sistema

- El Campo de Datos estará formado por cuatro nodos: Nodo 1, Nodo 2, Nodo 3 y Nodo 4.
- Los cuatro nodos deberán formar una malla completa; cada nodo estará conectado directamente con
  los otros tres nodos.
- Existirán cuatro células cliente GUI: una conectada a cada nodo.
- Existirán cuatro células servidor de Suma (+): una conectada a cada nodo.
- Existirán cuatro células servidor de Resta (-): una conectada a cada nodo.
- Existirán cuatro células servidor de Multiplicación (x): una conectada a cada nodo.
- Existirán cuatro células servidor de División (/): una conectada a cada nodo.

**En consecuencia, cada nodo del Campo de Datos deberá tener conectadas cinco células:** 1 GUI, 1
servidor de suma, 1 servidor de resta, 1 servidor de multiplicación y 1 servidor de división. En
total, el sistema tendrá 20 células: 4 GUI y 16 células servidor.

Las cantidades anteriores corresponden a la configuración mínima exigida para la demostración del
proyecto. La solución no deberá estar limitada a cuatro nodos ni a cuatro instancias de cada tipo de
célula.

El protocolo de conexión deberá ser flexible y escalable: el mismo programa de nodo deberá poder
utilizarse para crear cualquier número de instancias, y los programas de células deberán poder
ejecutarse también en cualquier número de instancias sin requerir cambios en el código fuente.

## 7. Códigos de Contenido

**Toda solicitud y toda respuesta deberán incluir un Código de Contenido.** Este código permite
identificar tanto el servicio solicitado como el tipo de mensaje que circula por el Campo de Datos.

| Operación | Código solicitud | Código respuesta | Descripción |
|---|---|---|---|
| Suma | **SUM_REQ** | **SUM_RES** | Solicitud y respuesta de una suma. |
| Resta | **SUB_REQ** | **SUB_RES** | Solicitud y respuesta de una resta. |
| Multiplicación | **MUL_REQ** | **MUL_RES** | Solicitud y respuesta de una multiplicación. |
| División | **DIV_REQ** | **DIV_RES** | Solicitud y respuesta de una división. |

**Requisito de diseño para las respuestas:** cuando una célula servidor procese una solicitud,
deberá generar un nuevo mensaje con el Código de Contenido de respuesta correspondiente. La
respuesta deberá incluir, como mínimo, el identificador de la solicitud original y el resultado
calculado.

## 8. Estructura mínima sugerida de los mensajes

- Identificador único del mensaje.
- Identificador de la solicitud original, en el caso de una respuesta.
- Código de Contenido.
- Operandos requeridos para la operación, en el caso de una solicitud.
- Resultado, en el caso de una respuesta.
- Identificador de la célula que originó el mensaje.
- Cualquier dato adicional necesario para el control del broadcast y la prevención de ciclos.

## 9. Comunicación por broadcast

- La comunicación entre las células se realizará por broadcast a través del Campo de Datos.
- Una solicitud generada por cualquier GUI deberá difundirse por la malla.
- Debido a que existe una célula servidor de cada operación conectada a cada nodo, varias células
  servidor del mismo tipo pueden recibir una solicitud.
- El diseño deberá definir claramente cómo se evita que una misma solicitud produzca múltiples
  respuestas no deseadas. La estrategia seleccionada deberá documentarse en el reporte.
- Las respuestas también deberán difundirse utilizando su Código de Contenido de respuesta.

## 10. Protocolos requeridos

### 10.1 Protocolo de conexión

- Debe permitir conectar los cuatro nodos para formar la malla completa.
- Debe permitir conectar células GUI y células servidor a cada nodo.
- Debe identificar el tipo de entidad conectada y mantener control de las conexiones activas.
- El protocolo deberá ser independiente del número de instancias: aunque la demostración requiera
  cuatro nodos, deberá permitir conectar cualquier cantidad de nodos al Campo de Datos.
- De la misma forma, deberá permitir conectar cualquier cantidad de células GUI o células servidor,
  sin depender de valores fijos codificados en el programa.

### 10.2 Protocolo de comunicación

- Debe implementar el broadcast de mensajes entre nodos y células.
- Debe transportar los Códigos de Contenido de solicitud y de respuesta.
- Debe impedir que los mensajes circulen indefinidamente dentro de la malla.
- Debe detectar mensajes previamente recibidos mediante un identificador único u otro mecanismo
  equivalente.
- Debe permitir asociar una respuesta con la solicitud que la originó.

## 11. Prevención de ciclos y duplicados

- Cada mensaje deberá contar con un identificador único.
- Cada nodo deberá registrar temporalmente los identificadores ya procesados.
- Si un nodo recibe nuevamente un mensaje con el mismo identificador, no deberá retransmitirlo.
- La respuesta deberá generar un identificador de mensaje propio, pero conservar una referencia al
  identificador de la solicitud original.
- El equipo deberá documentar la estrategia utilizada para evitar respuestas duplicadas cuando
  existan varios servidores del mismo servicio.

## 12. Flujo general de una operación

1. El usuario selecciona una operación e introduce los operandos en una célula GUI.
2. La GUI genera una solicitud con identificador único y Código de Contenido de solicitud.
3. La GUI envía la solicitud al nodo al que está conectada.
4. El nodo realiza broadcast hacia los otros nodos de la malla y hacia sus células conectadas.
5. Los nodos descartan cualquier copia de un mensaje que ya haya sido procesado.
6. Las células servidor revisan el Código de Contenido y determinan si corresponde a su servicio.
7. La célula servidor que deba atender la solicitud ejecuta la operación.
8. El servidor genera una respuesta con un nuevo identificador de mensaje, el identificador de la
   solicitud original, el resultado y el Código de Contenido de respuesta correspondiente.
9. La respuesta se distribuye por broadcast a través del Campo de Datos.
10. Las células GUI reciben la respuesta y la GUI correspondiente muestra el resultado.

## 13. Esquema conceptual de la solución

**Cada uno de los cuatro nodos tendrá conectadas las mismas cinco células:** GUI, Suma (+), Resta
(-), Multiplicación (x) y División (/). Los cuatro nodos forman una malla completa.

Figura 1 del PDF, "Arquitectura ADS - Configuración del Segundo Parcial". Muestra 4 nodos en malla
completa (Nodo 1 y Nodo 2 arriba, Nodo 3 y Nodo 4 abajo, con las 6 conexiones entre ellos). Cada
nodo conecta 1 GUI y 4 células servidor (+, -, x, /). Total: 4 GUI + 16 células servidor = 20
células conectadas al Campo de Datos.

## 14. Evidencia mínima en la demostración

- Nodo 1, Nodo 2, Nodo 3 y Nodo 4 ejecutándose y conectados en malla completa.
- Una célula GUI conectada a cada nodo.
- Una célula servidor de suma conectada a cada nodo.
- Una célula servidor de resta conectada a cada nodo.
- Una célula servidor de multiplicación conectada a cada nodo.
- Una célula servidor de división conectada a cada nodo.
- Generación y propagación de solicitudes con Código de Contenido.
- Generación y propagación de respuestas con Código de Contenido de respuesta.
- Asociación correcta entre solicitud y respuesta.
- Prevención de ciclos y mensajes duplicados.
- Ejecución correcta de suma, resta, multiplicación y división.

## 15. Consideraciones técnicas

**Principio obligatorio de descentralización:** ninguna función esencial del sistema deberá depender
de una unidad central, nodo maestro, servidor coordinador o componente único. La conexión, el
descubrimiento, la propagación de mensajes, el enrutamiento y la atención de solicitudes deberán
diseñarse de forma distribuida.

- El sistema deberá funcionar sin depender de un nodo central.
- El formato de los mensajes y los Códigos de Contenido deberá estar documentado.
- La demostración deberá permitir observar el recorrido de los mensajes mediante consola, bitácora o
  registro de eventos.
- La arquitectura deberá evitar cualquier punto único de fallo; ninguna instancia individual deberá
  ser indispensable para el funcionamiento global del sistema.
