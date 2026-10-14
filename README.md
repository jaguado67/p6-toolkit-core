# P6 Toolkit — Core 1.0 · Workbench v0.2.2

**Versión técnica en desarrollo.** El alcance pasa a **14 herramientas** (v0.2.1 añade M13 P6 Relationship Converter y M14 Progress Validator); no significa que las catorce estén completas. Es una ampliación práctica del primer prototipo con navegación analítica, nuevas auditorías de datos y diagnósticos explorables.

## Qué cambió en v0.2.2

- **Interfaz en inglés** (pantallas, mensajes del motor y exportes). La documentación sigue en español.
- **Acceso con usuario y contraseña** (ver *Control de acceso*). Sin configuración, la app funciona en modo local y lo advierte en pantalla.
- **Data Date confirmada en la barra lateral**, una vez por versión. La usan Progress Validator (M14), el punto 09 de DCMA-14 (M11) y el orden de versiones en Float Erosion (M08), que además avisa si hay Data Dates faltantes, repetidas o fuera de orden.
- **Exportación a Excel (.xlsx)** junto al CSV en todas las tablas.
- **Un archivo por módulo** en `ui/modules/` (ver *Cómo agregar un módulo*). `app.py` queda como un shell de ~100 líneas.
- **Regresión con archivos reales** en `tests/regression/` (los datos de clientes quedan fuera del repositorio).

## Qué cambió en v0.2.1

- **P6 Relationship Converter (M13):** cargue el Excel exportado de un layout de P6 (hoja `data` con *Predecessor Details* / *Successor Details*) y descargue el libro `TASK` + `TASKPRED` + `Validation` para *Archivo › Importar › Hoja de cálculo*. No necesita XER.
- **Progress Validator (M14):** con una Data Date confirmada por el usuario, revisa fechas reales y pronosticadas, coherencia de estados y progreso fuera de secuencia. Cada chequeo informa su población elegible.

## Qué cambió respecto a v0.1.0

- Dashboard integrado con KPIs, actividad por estado, distribución de relaciones y una tabla de hallazgos con sus fuentes.
- Explorador de actividades con filtros por estado, WBS jerárquica, calendario, ID/nombre y exportación.
- Diagnóstico de red con tabla resumen por componente, actividades aisladas/extremos y **visualización de subred alrededor de una actividad** (evita descargar miles de registros JSON).
- Logic Analyzer funcional para **tipos FS/SS/FF/SF, lags positivos/negativos, posibles duplicados exactos y relaciones múltiples**.
- Constraints Analyzer: inventario de restricciones primarias y secundarias presentes en `TASK`, con fechas sin informar y exportación.
- Pantalla DCMA-14 de **cobertura exploratoria**: enumera los 14 puntos, presenta señales disponibles y separa explícitamente lo que no está evaluado; **no es un resultado de cumplimiento formal**.
- Schedule Health: perfil de observaciones con evidencias; sin índice 0–100 arbitrario.
- Critical Path: distribución y clasificación del Total Float tal como lo exporta P6; **no se atribuye a nuestro motor el cálculo de caminos críticos**.
- Float History: requiere mínimo dos versiones para mostrar una tendencia y exige confirmar explícitamente el orden de las actualizaciones; con una sola versión muestra solo distribución actual.
- Comparison / Update-to-Update: filtros por campo, tabulados de cambios y exportación CSV.
- Metadatos XER y calendario disponibles sin pretender calcular las excepciones hasta validar `clndr_data`.

## Instalación en Windows (PowerShell)

Descomprima la carpeta y abra PowerShell dentro de `p6-toolkit-core`.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[ui,dev]"
py -m pytest -q
py -m streamlit run app.py
```

Si ya tenía instalada una versión anterior, conserve el entorno virtual y reinstale (v0.2.1 añadió `openpyxl`):

```powershell
py -m pip install -e ".[ui,dev]"
py -m streamlit run app.py
```

En PowerShell, si se restringe la activación del entorno, puede invocar directamente `.\.venv\Scripts\python.exe` o habilitar la activación de entornos de forma controlada.

## Control de acceso (usuario y contraseña)

1. Cree el hash de cada contraseña (mínimo 10 caracteres): `py -m p6toolkit hash-password`
2. Copie `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y pegue los hashes. Nunca comparta ni suba ese archivo (está en `.gitignore`).
3. Para quitar el acceso a alguien sin borrarlo, agregue `disabled = true` a su usuario.
4. En un servidor compartido defina la variable de entorno `P6TOOLKIT_REQUIRE_AUTH=1`: si falta la configuración, la app se bloquea en lugar de quedar abierta.

Límites conocidos: el bloqueo tras 5 intentos fallidos es por sesión (otra pestaña reinicia el contador) y no hay recuperación de contraseña; el administrador genera un hash nuevo. En Streamlit Community Cloud los secretos se cargan en *Settings › Secrets* de la app.

## Cómo agregar un módulo

1. Cree `ui/modules/m15_nombre.py` con `SPEC = ModuleSpec("15", "Tool name", "Maturity", needs_xer=True)` y `def render(ctx): ...`.
2. Agréguelo a `NAV_ORDER` en `ui/registry.py`. La navegación y la tabla de alcance se actualizan solas.
3. Ponga la lógica en `src/p6toolkit/` (sin Streamlit) y sus pruebas en `tests/`.

## Cómo probar

1. Active en la barra lateral **Use demo project** para cargar una baseline y un update sintéticos.
2. Inspeccione **Schedule Dashboard**, **Network Integrity Analyzer** y **Logic Analyzer**.
3. Abra **XER Comparator** para comparar las dos versiones.
4. En **Float Erosion Tracker**, seleccione el orden cronológico y confírmelo antes de generar una tendencia.
5. Cargue un XER real de Primavera P6 y valide los resultados contra los datos de P6.

## Validación

- Ejecutar `py -m pytest -q`: **43 pruebas** de parsers, snapshots, comparaciones, red, historial, restricciones, lógica, DCMA preliminar, convertidor, validador de avance, exportación Excel, contraseñas y regresión con archivos reales.
- `app.py` se ejecutó completo (14 páginas, demo y export real de 6.684 actividades, y los flujos de inicio de sesión) contra un Streamlit simulado; la interfaz visual sigue requiriendo verificación en el equipo del usuario.

## Pendiente antes del Core 1.0 estable

- Parser y motor completo de calendarios, turnos, excepciones y lags.
- Análisis temporal de eventos inicio/fin y driving relationships comparable a P6.
- DCMA-14 formal con definiciones, umbrales, exclusiones y fechas confiables.
- Schedule Health Index validado mediante evidencia, criterios de bloqueo y calibración de pesos.
- Reconstrucción de caminos críticos, multipath y diagnóstico del efecto causal de restricciones.
- Comparación longitudinal robusta cuando cambia Activity ID y cuando hay relaciones externas.
- Prueba de desempeño y resultados cruzados en grandes XER reales (por ejemplo proyectos de 6.000+ actividades).

### Principios

- **No modificar** archivos XER de entrada.
- **No confundir** `PROJECT.last_recalc_date` con la Data Date confirmada.
- **No convertir** indiscriminadamente horas a días laborables.
- **No confundir** ciclos estructurales con una demostración de inviabilidad temporal.
- **No presentar** inventarios DCMA como cumplimiento ni Float negativo como camino crítico.

## Arquitectura

`src/p6toolkit/xer.py` → `snapshot.py` → `network.py`, `compare.py`, `history.py`, `diagnostics.py` y `progress.py` → `ui/modules/*` → `app.py`. `converter.py` es independiente del XER (Excel → Excel); `export.py` y `auth.py` son utilidades sin Streamlit. Los motores son reutilizables sin Streamlit.

Leer también `docs/arquitectura.md` y `CHANGELOG.md`.

## Deployment on Streamlit Community Cloud

The repository-ready distribution includes `requirements.txt` (installs the local package as well as UI dependencies). See [DEPLOYMENT.md](DEPLOYMENT.md) for publishing, entrypoint, secrets, and privacy guidance. Never upload `.streamlit/secrets.toml` or real customer schedule files to GitHub.
