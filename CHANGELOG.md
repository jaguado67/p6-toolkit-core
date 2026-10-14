# Changelog

## 0.2.2 — Workbench hardening

- Interfaz y mensajes del motor en inglés; pruebas que comparaban textos actualizadas.
- Login con usuario y contraseña (`auth.py`: PBKDF2-SHA256, 600.000 iteraciones, sal aleatoria, comparación
  en tiempo constante; `ui/auth.py`). `py -m p6toolkit hash-password`. Modo local advertido; `P6TOOLKIT_REQUIRE_AUTH=1`
  bloquea un servidor sin usuarios.
- Data Date: confirmación por versión en la barra lateral; `data_date_candidates()` y `suggested_data_date()`
  (last_recalc_date, nunca anterior a plan_start_date); `check_version_order()`; DCMA 09 evaluado con Data Date
  confirmada. `ProjectSnapshot.project` conserva la fila PROJECT original.
- Exportación .xlsx en todas las tablas (`export.py`: limpia caracteres de control, valida el nombre de hoja y el
  límite de filas de Excel).
- `app.py` dividido en `ui/` (shell, contexto, helpers comunes, autenticación, Data Date) y un archivo por módulo en
  `ui/modules/` con registro ordenado. Verificado contra una traza de referencia: mismas 418 llamadas de interfaz
  en 19 escenarios.
- Regresión con archivos reales: `tests/regression/record_golden.py` + `tests/test_regression.py`; datos ignorados por git.
- 43 pruebas.

## 0.2.1 — Converter & Progress

- **M13 P6 Relationship Converter** (`converter.py`): Excel exportado de un layout P6 (hoja `data`) →
  libro de importación con `TASK`, `TASKPRED` y `Validation`. No requiere XER. Validado contra el export
  real QTS CDR1-DC7 (6.684 actividades, 12.271 relaciones; salida idéntica celda por celda a la verificada
  manualmente).
- **M14 Progress Validator** (`progress.py`): fechas reales posteriores a la Data Date, fechas pronosticadas
  anteriores a la Data Date, estado incoherente con fechas reales, AF < AS, completadas con duración
  remanente y progreso fuera de secuencia por tipo de relación. La Data Date la confirma el usuario.
  Solapes del mismo día se separan (P10) porque sin hora no son decidibles.
- La navegación ya no exige un XER para las herramientas que no lo usan.
- `__init__`: `__all__` incluía solo parte de la API pública; ahora exporta diagnósticos, convertidor y validador.
- Nueva dependencia: `openpyxl`.
- 32 pruebas (20 previas + 12 nuevas).

## 0.2.0 — Diagnostic Workbench

- UI reconstruida: navegación de 12 módulos, overview, filtros y visuales de red/estado.
- Nuevo motor `diagnostics.py`: auditorías de relaciones, restricciones, perfiles y precheck DCMA-14.
- Exportación CSV por herramienta; historial de Float con confirmación de orden.
- Eliminadas las largas listas JSON de componentes y extremos de red.
- Vista de WBS basada en rutas del PROJWBS cuando la tabla está disponible.
- 20 pruebas automatizadas aprobadas.
- **No implementa todavía** motor temporal P6, scoring SHI, DCMA formal ni simulación de caminos críticos.

## 0.1.0 — Foundation

- XER parser, snapshots, comparación de pares, estructura de red y Float histórico descriptivo.
- 14 pruebas iniciales.
