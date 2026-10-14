# Especificación de Arquitectura — P6 Toolkit Core 1.0

Estado del documento: diseño de 14 módulos (M13 y M14 añadidos en v0.2.1); implementación incremental en curso.

## 1. Visión

- Python es el **motor independiente**; Streamlit es solamente la interfaz.
- La fuente XER es **inmutable**; se conserva SHA-256 y tabla/campo original.
- Un `ProjectSnapshot` representa **una versión** y un único proyecto; el XER puede contener múltiples proyectos.
- El análisis numérico diferencia: valores exportados de P6, resultados del motor propio, reglas diagnósticas e hipótesis.
- Los valores `*_hr_cnt` mantienen unidades **horas** hasta disponer de un calendario validado.
- Las comparaciones por `Activity ID` se declaran provisionales; casos renombrados/recodificados requieren resolución de identidad.
- No se equipara automáticamente el grafo de actividades con el grafo de eventos Start/Finish.

### Data Date (v0.2.2)

El mapa XER de Oracle describe `PROJECT.last_recalc_date` solo como *Last Recalc Date*; la librería abierta
xerparser usa `max(last_recalc_date, plan_start_date)` como Data Date. Ante fuentes en conflicto el Toolkit
**sugiere** ese valor y exige **confirmación del usuario** por versión. Ningún módulo usa una Data Date no confirmada.

## 2. Capas y contratos

```text
APP (Streamlit: app.py → ui/registry.py → ui/modules/mNN_*.py; CLI: python -m p6toolkit)
  └── application services (orquestación, reportes, validación)
      ├── analytics (salud, DCMA-14, tendencias, caminos, restricciones)
      ├── engines (calendar, graph, event-constraint, temporal)
      └── core/data (parser XER, snapshot, versionado, identidad, auditoría)
```

### Contrato del parser

`parse_xer_bytes(data: bytes, filename: str) -> XERDocument`

- Entrada: bytes sin modificaciones.
- Salida: tablas originales (`PROJECT`, `TASK`, `TASKPRED`, `PROJWBS`, `CALENDAR`, etc.), huella digital, codificación, advertencias.
- Error: XER inválido, campos truncados, tabla repetida, estructura corrupta.
- La codificación se prueba en orden UTF-8, CP1252, Latin-1; se reporta la elegida.
- Los datos `CALENDAR.clndr_data` se preservan sin interpretación prematura.

### Contrato de snapshots

`build_snapshot(doc: XERDocument, project_id: str | None) -> ProjectSnapshot`

- Establece correspondencia interna de `TASK.task_id` y `TASKPRED.pred_task_id`.
- Agrupa atributos normalizados de actividad, relaciones internas, calendarios referenciados, links externos y alertas.
- No infiere un calendario estadounidense a partir de su nombre.
- No presume que `PROJECT.last_recalc_date` sea equivalente a `Data Date`: este campo es *Last Recalc Date* según el mapeo de Oracle; se expone provisionalmente como fecha de referencia no verificada.
- Los códigos de proyecto pueden diferir entre BL y UP (ej. DC7-BL / DC7-UP05-CURR). La versión 0.1 exige confirmación explícita para compararlos. Futura capa: `ProjectIdentityMap` configurable con proyecto lógico, versión y tabla de resolución de Activity ID.

### Contrato de resultados analíticos (objetivo 1.0)

Cada `AnalysisResult` deberá exponer:

```text
analysis_id, module_id, algorithm_version, status,
source_hashes[], project_code, data_date, inputs,
metrics{}, evidence[], diagnostics[], assumptions[], errors[]
```

`status`: PASS / WARNING / BLOCKED / NOT_EVALUABLE. Nunca se atribuirá PASS a una comprobación no implementada.

## 3. Interfaces de los cuatro motores

| Motor | Protocolo objetivo | Alcance y restricciones |
|---|---|---|
| XER Data Engine | `parse_xer_bytes`, `build_snapshot`, `compare_snapshots` | Importación, correspondencia, datos tabulares |
| Calendar Engine | `working_intervals(calendar_id, window)`, `work_hours(start,end)` | Jornada semanal, excepciones, turnos, DST con zona horaria |
| Graph Engine | `build_graph(snapshot)`, `inspect_network(snapshot)`, `scc()` | Topología y anomalías; no genera fechas |
| Temporal Engine | `build_event_constraints()`, `check_feasibility()`, `calculate_dates()` | Eventos S/F y lags; restricciones y varios calendarios requieren validación explícita |

### Representación del motor temporal

Se representará cada actividad con eventos `S_i` y `F_i`. Ejemplos para lag horario fijo `L`:

- FS: `S_j >= F_i + L`
- SS: `S_j >= S_i + L`
- FF: `F_j >= F_i + L`
- SF: `F_j >= S_i + L`
- Duración (sin calendario): `F_i = S_i + D_i`.

Estas desigualdades describen un modelo temporal simplificado. En P6 real, turnos, calendarios de las actividades/lag, excepciones, restricciones, avance y configuración del programador impiden trasladar indiscriminadamente estas ecuaciones a horas de reloj. SCC cíclica **no prueba** automáticamente inviabilidad de las restricciones temporales. La validación de factibilidad deberá ser separada del análisis topológico.

## 4. Registro de los 14 módulos

| ID | Módulo | Función de servicio prevista | Entrada | Resultado | Dependencias | Estado v0.1 |
|---|---|---|---|---|---|---|
| M01 | XER Explorer | `explore_xer()` | XER | Tablas/actividades/códigos | Data | Parcial funcional |
| M02 | XER Comparator | `compare_snapshots()` | 2 snapshots | Altas/bajas/campos/relaciones | Identidad | Parcial funcional |
| M03 | Calendar Analyzer | `analyze_calendars()` | CALENDAR + TASK | Jornadas/horas/excepciones | Calendar Engine | Pendiente (metadata base) |
| M04 | Network Integrity Analyzer | `inspect_network()` | TASK + TASKPRED | SCC/conectividad/extremos | Graph Engine | Parcial funcional |
| M05 | Logic Analyzer | `analyze_logic()` | Relación S/F y calendarios | Reglas, redundancia, temporalidad | Temporal Engine | Pendiente |
| M06 | Schedule Health Index | `score_schedule()` | M01,M03,M04,M05,M11,M12 | Diagnóstico + aptitud | Quality Gates | Pendiente |
| M07 | Critical Path Analyzer | `analyze_paths()` | Fechas, calendario, grafo, configuración | Caminos / discrepancias P6 | Temporal Engine | Pendiente |
| M08 | Float Erosion Tracker | `build_float_history()` | UP consecutivas | Delta TF (horas) | Identity/Update | Parcial descriptivo |
| M09 | Update-to-Update Analyzer | `analyze_updates()` | BL, UP01..UPn | Cambios y tendencia | Compare/History | Pendiente (comparación par) |
| M10 | Schedule Dashboard | `render_dashboard()` | Resultados de módulos | UI/Excel/HTML | App | Prototipo parcial |
| M11 | DCMA-14 Checker | `check_dcma14()` | Red, fechas, duraciones, avance | 14 métricas y N/A por indicador | Calendarios / lógica | Pendiente |
| M12 | Constraints Analyzer | `analyze_constraints()` | TASK restricciones | Inventario, causalidad, impactos | Temporal Engine | Pendiente |
| M13 | P6 Relationship Converter | `convert_workbook()`, `to_import_workbook()` | Excel de layout P6 (hoja `data`) | Libro TASK + TASKPRED + Validation | Ninguna (no usa XER) | Operativo (v0.2.1) |
| M14 | Progress Validator | `validate_progress(snapshot, data_date)` | TASK + TASKPRED + Data Date confirmada | Chequeos P01–P10 con población elegible | Data Date confirmada por el usuario | Operativo descriptivo (v0.2.1) |

## 5. Semántica de los diagnósticos

**Data validation:** integridad de claves, rangos y formatos. **Structural network validation:** conectividad, SCC, extremos legítimos, arcos desconocidos y enlaces externos. **Temporal validation:** factibilidad de restricciones de inicio/fin con calendarios, lags y estados. **Constructability validation:** revisión experta de la secuencia real, no inferible únicamente del grafo. Estos cuatro planos se reportan separados.

### Quality Gates

- G0: Archivo legible y sin pérdidas silenciosas de datos.
- G1: Identidades y referencias suficientes para comparar.
- G2: Red construible; anomalías estructurales documentadas.
- G3: Calendarios interpretados para el subconjunto de funciones temporales activado.
- G4: Secuencia de versiones/Data Dates verificadas (distintas de Last Recalc Date).
- G5: Float homogéneo en unidades y parámetros para inferencias históricas.

Si falla G3 no se bloquea M01 ni M02: se bloquean solo los cálculos que requieren reconstrucción de fechas.

### DCMA-14

Debe instrumentarse como **checker separado** del Schedule Health Index. Cada prueba define población elegible, exclusiones, numerador, denominador, umbral, unidad, dato faltante, versión metodológica y trazabilidad. No se declarará el checklist completo hasta auditar cada punto con muestras con y sin recursos/costos; varias pruebas requieren información que puede no estar en un XER limitado.

### Constraints Analyzer

Primero se implementará inventario de tipos y fechas de restricciones. La **influencia causal** sobre float/camino necesitará escenarios contrafactuales validados contra P6. El simple conteo no constituye medición de impacto.

## 6. Ensayos de aceptación por módulo

| ID | Ensayo indispensable |
|---|---|
| M01 | Recuento fiel por tabla; Unicode/CP1252; multi-proyecto; XER malformado sin parseo silencioso |
| M02 | Renumeración interna TASK sin cambios falsos; relaciones y campos cambiados; Activity ID cambiado -> advertencia |
| M03 | Calendarios 8/10/12/24 h; turnos parciales, excepciones, cambios de año y DST |
| M04 | Componentes, extremos legítimos, SCC incluidas FS/SS/FF/SF y autolazos |
| M05 | Matriz FS/SS/FF/SF con lag +/-; diferencias entre inconsistencia y redundancia |
| M06 | Error bloqueante no compensado por score; reglas N/A excluidas sin inflar puntaje |
| M07 | Caminos de redes sintéticas, P6 varios calendarios; discrepancias explicadas |
| M08 | TF 20/17/14/11 (unidades coherentes); missing/duplicated Data Date; cambios de lógica advertidos |
| M09 | BL/UP01/UP02/UPn; orden por Data Date verificado; ventanas de hitos |
| M10 | Filtros reproducibles, vista por actividad y reporte con procedencia |
| M11 | 14 pruebas por separado; denominadores, umbrales, exclusiones y N/A documentados |
| M12 | Conteo de restricciones y contraste P6 con escenarios de impacto |
| M13 | Export real: conteos por tipo, cruce Predecessor/Successor Details, filas de desborde, IDs inexistentes; salida importable en P6 |
| M14 | Fechas reales vs Data Date, estado vs fechas, hitos con una sola fecha real, OOS por FS/SS/FF/SF, lag negativo y solape del mismo día |

## 7. Desarrollo y versiones

1. **0.1**: parser, snapshots, comparación, topología y float exportado, UI exploratoria. Entrega actual.
2. **0.2**: calendario documentado, WBS/códigos, gestión de identidad y fechas de datos.
3. **0.3**: grafo S/F, lógica, restricciones, calidad y DCMA-14 completo.
4. **0.4**: caminos, tendencias históricas y contraste cruzado P6.
5. **1.0**: integración total de 14 módulos, regresión con NIH/DC7 (cuando se aporten XER), documentación y empaquetado.

La numeración expresa *etapas*, no fechas ni compromisos de duración.

## 8. Referencias metodológicas

- Oracle P6 Professional 26 — Multiple Float Paths: https://docs.oracle.com/cd/G48902_01/client_help/en_US/analyzing_the_schedule_using_multiple_critical_float_paths.htm
- Oracle scheduling parameters: https://docs.oracle.com/cd/E75420_01/p6help/en/6067.htm

El formato XER deberá contrastarse con archivos reales del entorno que se utilizará. Una muestra sintética solo verifica las reglas implementadas, no garantiza compatibilidad con cualquier exportación de P6.

- Oracle XER Data Map — `last_recalc_date` identificado como Last Recalc Date: https://docs.oracle.com/cd/F74771_01/English/Mapping_and_Schema/xer_import_export_data_map_project/97885.htm
