# Enunciado — Proyecto del Tercer Parcial (transcripción literal)

Fuente: `Instrucciones_Proyecto_Tercer_Parcial_ADS_v4.pdf` (raíz del repo). Texto copiado tal cual,
sección por sección, para que no se pierda nada. Los identificadores entre corchetes (`[F3]`, …)
son los de `docs/REQUISITOS.md`. El PDF manda.

---

**Cómputo Distribuido — PROYECTO DEL TERCER PARCIAL**
**Fecha: 13 de noviembre de 2026**
**Evolución de la calculadora distribuida bajo arquitectura ADS**

> **Objetivo general.** Evolucionar el sistema ADS desarrollado en el segundo parcial
> incorporando mecanismos de foliado, carga dinámica de microservicios, autorrecuperación y
> administración distribuida de servicios, manteniendo el funcionamiento sin dependencia de una
> unidad central.

## 1. Lenguaje de programación

- El proyecto puede desarrollarse en cualquier lenguaje de programación. `[L1]`
- Si el proyecto se realiza en JAVA, se otorgarán puntos extras. La cantidad de puntos adicionales
  será la indicada por el profesor. `[L2]`

## 2. Entregables obligatorios

| Entregable | Contenido requerido |
|---|---|
| Reporte técnico `[E1]` | Documento que explique técnicamente el diseño y construcción del sistema, incluyendo los protocolos heredados del segundo parcial y los nuevos mecanismos de foliado, carga dinámica, autorrecuperación y gestión de servicios. |
| Video con audio `[E2]` | Demostración mediante diferentes escenarios que evidencien el cumplimiento de los protocolos y funcionalidades solicitados para el tercer parcial. |
| Liga al código fuente `[E3]` | Enlace accesible al código fuente completo del sistema, incluyendo células cliente, células servidor, nodos del Campo de Datos, microservicios y gestor de servicios. |

## 3. Regla de originalidad académica

> **IMPORTANTE:** No se permite la copia total o parcial entre proyectos. En caso de detectarse
> copia, se anulará la calificación del proyecto y el caso será reportado al coordinador de la
> carrera correspondiente. `[O1]`

## 4. Base obligatoria proveniente del Segundo Parcial

**El proyecto del tercer parcial es una evolución del sistema del segundo parcial.** Por lo tanto,
al iniciar esta entrega el sistema ya debe contar, como mínimo, con los siguientes elementos:

- Calculadora capaz de resolver suma, resta, multiplicación y división. `[B1]`
- Tres programas base: célula cliente, célula servidor y nodo del Campo de Datos. `[B2]`
- Campo de Datos con cuatro nodos en malla completa para la configuración de demostración. `[B3]`
- Cuatro células cliente GUI. `[B4]`
- Cuatro células servidor por cada operación: suma, resta, multiplicación y división. `[B5]`
- En cada nodo de demostración: una GUI y una célula servidor de cada operación. `[B6]`
- Protocolo de conexión entre nodos para formar el Campo de Datos. `[B7]`
- Protocolo de conexión entre células y nodos. `[B8]`
- Protocolo de comunicación entre células basado en Código de Contenido. `[B9]`
- Comunicación por broadcast evitando el ciclado de mensajes. `[B10]`
- Diseño flexible: el software no debe estar limitado a cuatro nodos ni a una cantidad fija de
  células. `[B11]`
- Diseño distribuido sin dependencia de una unidad central, nodo maestro o componente único.
  `[B12]`

## 5. Nuevos requisitos del Tercer Parcial

### 5.1 Protocolo de foliado

**Objetivo:** garantizar que cada célula realice únicamente la funcionalidad que le corresponde y
que cada interfaz GUI muestre solamente la información asociada a las operaciones que ella
solicitó.

- Cada solicitud deberá manejar un folio o identificador que permita correlacionar eventos, ACK y
  respuestas. `[F1]`
- La GUI deberá poder reconocer qué respuestas pertenecen a sus propias solicitudes. `[F2]`
- Las células deberán utilizar la información del folio junto con el Código de Contenido para
  decidir qué mensajes deben atender o ignorar. `[F3]`
- El protocolo deberá incorporar el concepto de huella para identificar el origen o trayectoria
  lógica de una solicitud. `[F4]`
- Deberán utilizarse ACK para confirmar la recepción o participación de las células involucradas.
  `[F5]`
- Se deberá definir un mínimo número de ACK (Min. # de ACK) necesario para considerar válido o
  aceptado un evento. `[F6]`
- El mecanismo deberá contemplar tolerancia a fallas cuando no todas las células esperadas
  respondan. `[F7]`
- Se deberá definir claramente qué se considera un evento y cómo se identifica su inicio,
  confirmación, procesamiento y finalización. `[F8]`

### 5.2 Carga dinámica de microservicios

**Objetivo:** hacer que la funcionalidad de una célula viva en sus genes activos y no esté
incorporada permanentemente en el programa base.

- Los microservicios deberán existir físicamente en disco. `[M1]`
- Una célula deberá cargar en memoria el microservicio requerido al momento de ejecución. `[M2]`
- El programa base de la célula deberá poder funcionar sin tener compilada de manera fija la
  lógica de suma, resta, multiplicación o división. `[M3]`
- Los servicios activos de una célula deberán poder cambiar durante la operación del sistema
  mediante el Gestor de Servicios. `[M4]`
- El reporte deberá explicar el mecanismo utilizado para localizar, validar, cargar, activar y
  descargar un microservicio. `[M5]`

### 5.3 Protocolo de autorrecuperación

**Objetivo:** permitir que el sistema detecte la pérdida o falla de células y recupere
automáticamente la capacidad de servicio mediante clonación controlada.

- El sistema deberá detectar cuando la disponibilidad de un servicio disminuya por falla o
  desconexión de una célula. `[A1]`
- Las células o componentes distribuidos deberán determinar cuándo es necesario generar una nueva
  instancia. `[A2]`
- La nueva célula deberá recuperar o cargar los genes activos necesarios para reemplazar la
  capacidad perdida. `[A3]`
- La autorrecuperación deberá realizarse sin depender de un controlador central. `[A4]`
- La clonación deberá detenerse al alcanzar el nivel requerido de disponibilidad. `[A5]`
- El diseño deberá impedir la generación ilimitada de células. Este control representa el
  mecanismo para evitar el 'cáncer' del sistema. `[A6]`
- El mecanismo de recuperación deberá contemplar tolerancia a fallas y evitar que una falla local
  provoque la pérdida completa del servicio. `[A7]`

### 5.4 Gestor de servicios

**Objetivo:** proporcionar una interfaz administrativa para modificar de forma dinámica los genes
activos de las células.

- Inicialmente, las células deberán poder arrancar sin microservicios instalados o activos. `[G1]`
- Desde el Gestor de Servicios se deberá poder dar de alta un servicio en una célula. `[G2]`
- Se deberá poder dar de baja un servicio. `[G3]`
- Se deberá poder modificar o sustituir un servicio existente. `[G4]`
- El gestor deberá conocer o consultar la topología actual del sistema para decidir en qué células
  instalar, retirar o actualizar servicios. `[G5]`
- La topología deberá incluir, como mínimo, nodos disponibles, células conectadas y servicios
  activos en cada célula. `[G6]`
- El gestor es una herramienta de administración; el funcionamiento normal del sistema no deberá
  depender de que el gestor permanezca activo. `[G7]`
- La alta, baja o modificación de servicios deberá reflejarse en la carga dinámica de
  microservicios de la célula seleccionada. `[G8]`

## 6. Relación entre los mecanismos del Tercer Parcial

| Mecanismo | Responsabilidad principal | Relación con el sistema |
|---|---|---|
| Foliado | Correlacionar solicitudes, eventos, ACK y respuestas. | Evita que una GUI muestre resultados ajenos y permite validar la atención de una operación. |
| Microservicios dinámicos | Convertir la funcionalidad en genes activos cargables. | Permite cambiar la capacidad de una célula sin alterar su programa base. |
| Autorrecuperación | Restablecer automáticamente la capacidad perdida. | Clona células cuando es necesario y detiene la clonación al recuperar la disponibilidad requerida. |
| Gestor de servicios | Administrar los genes activos de las células. | Usa la topología para decidir dónde dar de alta, baja o modificar servicios. |

## 7. Principios de diseño obligatorios

- No debe existir una unidad central indispensable para la operación del sistema. `[P1]`
- No debe existir un nodo maestro cuya falla detenga el Campo de Datos. `[P2]`
- La cantidad de nodos y células debe ser flexible y configurable; las cuatro instancias
  corresponden a la configuración mínima de demostración. `[P3]`
- Los protocolos deben funcionar aun cuando existan altas, bajas, fallas o nuevas instancias.
  `[P4]`
- La pérdida de una célula no debe convertirse en un punto único de falla. `[P5]`
- La recuperación debe ser gradual y controlada, evitando crecimiento ilimitado. `[P6]`
- La información de control necesaria para foliado, ACK, topología y recuperación debe integrarse
  de forma distribuida. `[P7]`

## 8. Esquema conceptual del proyecto

A continuación se presenta el mismo esquema base utilizado en el documento del Segundo Parcial,
mostrando los nodos del Campo de Datos y las células conectadas a cada nodo. Este diagrama sirve
como referencia estructural para la presente entrega.

*Figura 1. Esquema conceptual base del sistema ADS.* Título: "Arquitectura ADS — Configuración del
Segundo Parcial". Subtítulo: "4 nodos en malla completa; cada nodo conecta 1 GUI y 4 células
servidor (+, -, x, /)". Nodo 1, Nodo 2, Nodo 3 y Nodo 4 unidos todos con todos (6 enlaces). A cada
nodo se conectan: GUI, Suma (+), Resta (-), Multiplicación (x), División (/). Pie: "Total: 4 GUI +
16 células servidor = 20 células conectadas al Campo de Datos". `[C1]`

## 9. Evidencia mínima que debe observarse en la demostración

- Los cuatro nodos de demostración ejecutándose y comunicándose como Campo de Datos. `[V1]`
- Células GUI y células servidor conectadas a los nodos. `[V2]`
- Funcionamiento del protocolo de conexión y del broadcast heredados del segundo parcial. `[V3]`
- Solicitudes identificadas mediante Código de Contenido y folio. `[V4]`
- Uso visible o verificable de huella, ACK, Min. # de ACK y eventos. `[V5]`
- Cada GUI mostrando únicamente las respuestas correspondientes a sus propias solicitudes. `[V6]`
- Carga de un microservicio desde disco hacia memoria durante la ejecución. `[V7]`
- Alta, baja y modificación de servicios mediante el Gestor de Servicios. `[V8]`
- Consulta o visualización de la topología para seleccionar las células destino. `[V9]`
- Detección de la falla de una célula. `[V10]`
- Clonación automática para recuperar la capacidad del servicio. `[V11]`
- Detención de la clonación al alcanzar el nivel requerido de disponibilidad. `[V12]`
- Ausencia de dependencia de una unidad central para mantener el funcionamiento normal. `[V13]`

## 10. Escenarios propuestos para el video

**El video no deberá limitarse a mostrar una sola operación correcta.** Se recomienda demostrar
varios escenarios que prueben explícitamente los requisitos del tercer parcial.

- **Escenario 1 — Operación normal con foliado.** Generar una operación desde una GUI, mostrar su
  folio, huella, Código de Contenido, ACK recibidos y la respuesta final. Verificar que otra GUI
  no muestre ese resultado. `[S1]`
- **Escenario 2 — Solicitudes simultáneas.** Ejecutar operaciones desde dos o más GUI al mismo
  tiempo. Mostrar que cada interfaz recibe únicamente las respuestas asociadas a sus propios
  folios. `[S2]`
- **Escenario 3 — Min. # de ACK y tolerancia a fallas.** Provocar que una de las células que
  normalmente enviaría ACK no responda. Demostrar que el evento puede continuar cuando se alcanza
  el mínimo configurado y que el sistema identifica la ausencia. `[S3]`
- **Escenario 4 — Carga dinámica de microservicios.** Iniciar una célula sin un servicio activo,
  instalar el microservicio desde el Gestor de Servicios, cargarlo desde disco a memoria y
  demostrar que la célula adquiere la nueva funcionalidad sin modificar su programa base. `[S4]`
- **Escenario 5 — Baja y modificación de un servicio.** Retirar un microservicio de una célula y
  demostrar que deja de atender ese Código de Contenido. Después instalar o sustituir una nueva
  versión y verificar el cambio. `[S5]`
- **Escenario 6 — Falla y autorrecuperación.** Detener intencionalmente una célula que proporciona
  un servicio. Mostrar cómo el sistema detecta la pérdida de disponibilidad y genera una nueva
  célula con los genes activos necesarios. `[S6]`
- **Escenario 7 — Prevención del 'cáncer'.** Mostrar que, después de recuperar el número requerido
  de células para un servicio, el proceso de clonación se detiene y no continúa creando
  instancias innecesarias. `[S7]`
- **Escenario 8 — Cambio de topología.** Agregar o retirar una célula o nodo durante la ejecución.
  Mostrar que el Gestor de Servicios actualiza o consulta la topología y puede tomar decisiones
  con la nueva configuración. `[S8]`

## 11. Contenido mínimo sugerido del reporte técnico

- Descripción de la arquitectura final. `[D1]`
- Topología utilizada en la demostración. `[D2]`
- Protocolo de conexión heredado del segundo parcial. `[D3]`
- Protocolo de comunicación y prevención de ciclos. `[D4]`
- Formato de mensajes y Códigos de Contenido. `[D5]`
- Diseño del protocolo de foliado. `[D6]`
- Definición de huella, ACK, Min. # de ACK y evento. `[D7]`
- Estrategia de tolerancia a fallas. `[D8]`
- Diseño de genes activos y carga dinámica de microservicios. `[D9]`
- Diseño del Gestor de Servicios y representación de la topología. `[D10]`
- Diseño del protocolo de autorrecuperación. `[D11]`
- Reglas para decidir cuándo clonar y cuándo detener la clonación. `[D12]`
- Evidencias de pruebas y escenarios ejecutados. `[D13]`
- Limitaciones conocidas y decisiones de diseño. `[D14]`
