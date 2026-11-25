# ENTREGA — Tercer Parcial

Hoja de control antes de entregar: los tres entregables que pide el enunciado (§2) y lo que falta
hacer a mano.

## Los 3 entregables

| Entregable | Estado | Dónde / qué falta |
|---|---|---|
| **Reporte técnico** | **Final** (PDF, 29 páginas) | [Reporte_Tecnico_Calculadora_ADS.pdf](Reporte_Tecnico_Calculadora_ADS.pdf). Solo falta la liga del video en la portada. `REPORTE_TECNICO.md` y el `.docx` son la versión extendida de trabajo |
| **Video con audio** | Guion listo, **falta grabar** | [GUION_VIDEO.md](GUION_VIDEO.md): 11 escenas, ~12 min (los ocho escenarios + arranque + "sin unidad central") |
| **Liga al código fuente** | Publicado en GitHub (`calculadora_ads_p3`) | Falta subir lo último: commit + push, y la etiqueta `parcial-2` |

## Lo que falta que hagas tú

1. **Subir la etiqueta del punto de partida** (`git push origin parcial-2`): la sección 16 del
   reporte la menciona y aún no está en GitHub. Haz también commit + push del PDF final.
2. **Grabar el video** siguiendo [GUION_VIDEO.md](GUION_VIDEO.md). Antes, haz su sección "Antes de
   grabar" (procesos, bitácoras, pruebas y checklist). **Prueba el micrófono**: el enunciado pide
   video *con audio*. Graba la pantalla completa (OBS o Recortes).
   Graba las escenas en el orden del guion: la columna "Escena" de la matriz del reporte (§2)
   remite a ellas.
3. **Subir el video** con acceso "cualquiera con el enlace" y comprobar la liga en incógnito.
4. **Poner la liga en la portada** (donde dice "AGREGAR LIGA DEL VIDEO"), volver a exportar el
   PDF y reemplazar `Reporte_Tecnico_Calculadora_ADS.pdf` en el repo con el mismo nombre.
   **No** regeneres el `.docx` encima: el PDF es tu versión editada y el `.md` es más largo.
5. **Entregar las tres ligas**: reporte, video y repositorio.

## Checklist final

- [ ] La portada del PDF ya tiene la liga del video.
- [ ] El video se escucha de principio a fin y su liga abre en incógnito.
- [ ] El repositorio en GitHub es visible para el profesor y tiene el último commit, con el
      PDF final, `microservicios/` y las capturas, y la etiqueta `parcial-2`.
- [ ] (Opcional) En el repo publicado, `uv run python -m unittest discover -s tests -t .` sigue
      en verde.

## Cumplimiento del enunciado

La matriz completa, con archivo y función de cada requisito, está en el §2 del reporte; la lista
de verificación con su evidencia, en [docs/REQUISITOS.md](docs/REQUISITOS.md).

| § | Requisito | Estado |
|---|---|---|
| 1 | Cualquier lenguaje | Python 3.14 con librería estándar y uv (se renuncia a los puntos de Java) |
| 2 | Reporte, video con audio y liga al código | Reporte final (PDF) y repo en GitHub; falta grabar el video |
| 3 | Originalidad | Código propio; la base es el segundo parcial del mismo autor (§16 del reporte) |
| 4 | Base del segundo parcial (B1–B12) | Cumple; nodo y célula base heredados, `servidor/` sustituido por `madre/` |
| 5.1 | Foliado (F1–F8) | Cumple: folio, huella (sello + rastro), ACK, mínimo de ACK, evento de 4 fases con `X_FIN` |
| 5.2 | Microservicios dinámicos (M1–M5) | Cumple: genes en disco, `importlib`, programa base sin aritmética, cambio desde el gestor |
| 5.3 | Autorrecuperación (A1–A7) | Cumple: detección, HRW sin coordinador, copia de genes, `NIVEL_OK`, ocho límites |
| 5.4 | Gestor de servicios (G1–G8) | Cumple: BD SQLite, diagrama de topología, alta/baja/sustituir, no es orquestador |
| 7 | Principios (P1–P7) | Cumple |
| 9–10 | Evidencias y escenarios | Verificados en vivo (30/30); se muestran en el video |
| 11 | Contenido del reporte (D1–D14) | Cubierto; ver §2.2 del reporte |

Estado técnico: **217 pruebas en verde tres veces seguidas** (~192 s cada corrida, tras la auditoría final), `ruff`
limpio, y los ocho escenarios más "sin unidad central" verificados con procesos reales: 0 `ERROR`,
0 `Traceback`, 0 respuestas duplicadas, 10 avisos de clonación = 10 reemplazos.
