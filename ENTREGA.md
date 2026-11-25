# ENTREGA — Tercer Parcial

Hoja de control antes de entregar: los tres entregables que pide el enunciado (§2) y lo que falta
hacer a mano.

## Los 3 entregables

| Entregable | Estado | Dónde / qué falta |
|---|---|---|
| **Reporte técnico** | Escrito (30 páginas en Word) | [REPORTE_TECNICO.md](REPORTE_TECNICO.md) y `Reporte_Tecnico_Calculadora_ADS.docx`. Falta llenar la portada y regenerar el `.docx` |
| **Video con audio** | Guion listo, **falta grabar** | [GUION_VIDEO.md](GUION_VIDEO.md): 11 escenas, ~12 min (los ocho escenarios + arranque + "sin unidad central") |
| **Liga al código fuente** | Publicado en GitHub (`calculadora_ads_p3`) | Falta subir lo último: commit + push, y la etiqueta `parcial-2` |

## Lo que falta que hagas tú

1. **Llenar la portada del reporte.** [REPORTE_TECNICO.md](REPORTE_TECNICO.md) tiene 5
   marcadores: `<NOMBRE COMPLETO>`, `<MATRÍCULA>`, `<GRUPO>`, `<LIGA AL REPOSITORIO>` y
   `<LIGA AL VIDEO>`.
2. **Subir lo último al repositorio.** El repo ya está en GitHub, pero la auditoría y los
   arreglos finales aún no están en commits: pídeme el commit cuando quieras, o hazlo tú, y haz
   push. Sube también la etiqueta del punto de partida (`git push origin parcial-2`), que el §16
   del reporte menciona. El `.gitignore` ya excluye `logs/`, `datos/`, `run/`, `__pycache__/` y
   `.venv/`.
3. **Grabar el video** siguiendo [GUION_VIDEO.md](GUION_VIDEO.md). Antes, haz su sección "Antes de
   grabar" (procesos, bitácoras, pruebas y checklist). **Prueba el micrófono**: el enunciado pide
   video *con audio*. Graba la pantalla completa (OBS o Recortes).
   Graba las escenas en el orden del guion: la columna "Escena" de la matriz del reporte (§2)
   remite a ellas.
4. **Subir el video** con acceso "cualquiera con el enlace" y comprobar la liga en incógnito.
5. **Regenerar el `.docx`** cuando ya no le muevas al reporte:
   `uv run python docs/md_a_docx.py`. Ábrelo en Word y revisa portada, matriz y que siga en
   30 páginas o menos.
6. **Entregar las tres ligas**: reporte, video y repositorio.

## Checklist final

- [ ] La portada del reporte no tiene ningún `<…>` pendiente.
- [ ] `Reporte_Tecnico_Calculadora_ADS.docx` se regeneró después de lo anterior y tiene ≤ 30 páginas.
- [ ] El video se escucha de principio a fin y su liga abre en incógnito.
- [ ] El repositorio en GitHub es visible para el profesor y tiene el último commit, con el
      `.docx`, `microservicios/` y las capturas.
- [ ] (Opcional) En el repo publicado, `uv run python -m unittest discover -s tests -t .` sigue
      en verde.

## Cumplimiento del enunciado

La matriz completa, con archivo y función de cada requisito, está en el §2 del reporte; la lista
de verificación con su evidencia, en [docs/REQUISITOS.md](docs/REQUISITOS.md).

| § | Requisito | Estado |
|---|---|---|
| 1 | Cualquier lenguaje | Python 3.14 con librería estándar y uv (se renuncia a los puntos de Java) |
| 2 | Reporte, video con audio y liga al código | Reporte escrito y guion listo; video y liga los haces tú |
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
