# Plan y resultados de pruebas

## Ejecutadas — 2026-11-14

| Comprobación | Resultado real | Límite |
|---|---|---|
| Lectura PDF | 15 páginas extraídas y revisadas | Se requirió salida UTF-8 |
| Docker info | Motor 29.9.3 respondió fuera del aislamiento | No prueba SQL Server |
| Inventario Docker | Sin contenedores preexistentes | Volúmenes existentes preservados |
| Compose config --quiet | Código de salida 0 | No prueba arranque ni memoria disponible |
| compileall etl/deployment/backend | Código de salida 0 | Sintaxis, no conexión ni lógica ETL |
| git check-ignore | .env, .venv y backup excluidos | Revisar staged antes de cada commit |
| npm install | Finalizó con código 0; package-lock.json generado | Sin pruebas de navegador |
| npm run build | Vite 7.3.8 compiló 28 módulos, código 0 | Requirió acceso fuera del aislamiento por esbuild; no valida datos |
| HTTP frontend | GET http://127.0.0.1:5173/ respondió 200 | No sustituye prueba visual ni E2E |
| pip install / pip check | Instalación código 0 y sin dependencias rotas | No prueba conectividad SQL |
| pyodbc.drivers() | Confirma ODBC Driver 17 for SQL Server | Driver 18 no requerido para esta demo local |
| API TestClient | /api/health=200; /api/kpis sin clave=401 y clave incorrecta=401 | No prueba DW ni consulta válida; deprecación informativa httpx/Starlette |
| SQL Server | Contenedor healthy y SELECT @@VERSION desde Python/ODBC exitoso | Restauración y datos aún pendientes |
| Restauración OLTP | VERIFYONLY ejecutado y estado ONLINE confirmado | Primer intento interrumpido por cursor, corregido y repetido |
| Perfilado | 228.265 líneas únicas; 0 huérfanos de factura; 0 diferencias de fórmula monetaria | Reconciliación DW aún pendiente |

## Plan de aceptación

1. Completado: SQL Server saludable y versión/edición registradas; backup descargado y restore verificado.
2. Completado: perfilado, grano y relaciones confirmados; relación muchos-a-muchos excluida del hecho.
3. Completado: inicial con conteos/importes fuente/raw/clean/DW; rechazos iniciales explicados.
4. Completado: endpoint protegido, KPI en pantalla y SQL independiente coincidente.
5. Incremental, idempotencia, tardíos, actualizaciones, SCD, cuarentena y recuperación.
6. KPIs/filtros combinados, período vacío, errores y latencia.
7. ML sin fuga temporal, baseline y prueba independiente.
8. GenAI: 10 casos, 2 sin respaldo, preguntas ambiguas/fuera de alcance y límites.
9. Alertas: disparo, no disparo, deduplicación, reintentos y entrega web.
10. Reconstrucción por README, E2E y lote de demo identificable.

## Diagnóstico y pruebas de acceso/cobertura

- Primer lote `1f183aff-19d8-4b77-8d69-c4fc2011bc2c`: 228.265 líneas a cuarentena Q02_CUSTOMER.
  RLS ocultó los 663 clientes al extractor; DW quedó vacío. Se corrigió estado de SUCCEEDED a FAILED,
  conservando en JSON el estado inicialmente reportado y la explicación de la reclasificación.
- Se añadió comprobación de dimensiones no vacías y rechazo total antes de publicar datos.
- Lote `039f7a39-7cdb-44aa-a095-bc74500a0e27`: FAILED por SOURCE_VISIBILITY_OR_EMPTY_DIMENSION,
  comportamiento esperado con los permisos actuales; conserva raw, sin hechos publicados.
- `pytest tests/test_initial_integration.py::test_reader_has_only_approved_view -q`: **1 passed**.
  Se comprueba código SQL 229 al intentar leer raw con la cuenta API.
- Pendiente autorización de los nueve roles territoriales RLS (sin permisos propios).
  No se han ejecutado las pruebas positivas de reconciliación/API/navegador por falta de clientes visibles.

## Cierre tras autorización del usuario

- Acceso territorial autorizado expresamente; aplicados nueve roles existentes sin desactivar RLS.
- Carga aceptada: 228.265 líneas, 0 rechazos, 172.261.341,20 sin impuestos en fuente/raw/clean/DW.
- Repetición sin cambios: 0 hechos insertados, mismas filas e importe. No equivale a incremental probado.
- `pytest tests/test_initial_integration.py -q`: **3 passed**, una advertencia de deprecación
  httpx/Starlette; reporte JUnit en evidence/pytest-initial.xml.
- SQL independiente en database/003_validate.sql: las cuatro capas coinciden también en
  70.510 facturas y 8.950.628 unidades; evidence/independent-validation.json.
- Consulta de KPI incluyendo conexión: 95,48 ms en una medición local, no benchmark de rendimiento.
- Chrome: importe mostrado igual a API; captura y reporte en evidence/day1-dashboard.png
  y evidence/browser-smoke.json. Se revisó la captura, incluida fecha local Tegucigalpa.
- Frontend compila. API permite consulta con clave y rechaza acceso ausente/incorrecto.

Criterio de cierre del día 1 satisfecho con los datos de ejemplo oficiales de Microsoft.
No se iniciará día 2 sin indicación del usuario.

## Cierre del día 2 — autorizado el 2026-11-15

- Suite unificada: **42 passed**, una advertencia no bloqueante httpx/Starlette.
  Reporte actual: evidence/pytest-day2.xml. Los reportes anteriores preservan las etapas previas.
- Doce casos incrementales: cambios de línea/cabecera/cliente, tardíos, idempotencia, SCD2,
  tres fallas inyectadas con recuperación, cuarentena y reversión, baja/reaparición, corrección
  retrodatada, watermark futuro y duplicados idénticos sin supervivencia arbitraria.
- Veintisiete casos de API: SQL independiente para filtros combinados y comparación; tendencias,
  paginación, vacío, referencia ausente, entrada inválida, acceso y denegación de escritura.
- Doce comprobaciones Chrome: acceso incorrecto/correcto, KPI/API, dos dimensiones, drill-down,
  páginas, operación/rechazos, vacío/error/carga/reintento, móvil 360/390 px y tablas contenidas.
  Reporte evidence/dashboard-browser.json, cero excepciones JavaScript.
- La falla visual 503 se intercepta localmente y está expresamente identificada; los cambios
  operacionales/fallas de pipeline solo ocurren en bases Test con IsSimulated=1.
- Fuente principal intacta: 228.265 líneas y 172.261.341,20 sin impuestos, últimas ediciones de 2016;
  evidence/api-measurements.json. No se confundieron pruebas simuladas con datos operacionales reales.
- Build Vite aprobado con gráficos separados de la entrada; sin ampliar dependencias.
- Pendiente global: outliers estadísticos del catálogo y etapas 3/4, incluida reconstrucción limpia,
  ML, GenAI, alertas, validación final y video. No se declaran cumplidas todavía.

## Verificación de la tercera etapa

Los pendientes de ML, GenAI, alertas y outliers anteriores se completaron en esta
etapa. Suite completa y resultados: evidence/pytest-day3.xml. Las pruebas nuevas
incluyen siete de ML, catorce de GenAI y doce de notificaciones (además de las 42 previas).
Una advertencia de deprecación httpx/Starlette no impide la ejecución.

Navegador: reportes forecast-browser.json, chat-browser.json, alerts-browser.json,
y day3-regression-dashboard-browser.json en evidence/. Todos usan la aplicación
real y registran cero excepciones JavaScript; el error HTTP interceptado del dashboard
se identifica como simulación. Las capturas anteriores se conservan y las nuevas
regresiones del dashboard llevan prefijo day3-regression-.

Alertas: snapshot real con condición falsa; condición verdadera y recuperación
en bases Test aisladas, además de evento sintético visible marcado en el panel.
Se prueba rollback efectivo de un acuse de entrega, luego reintento idempotente.
Reactivación tras RESOLVED y descarte de snapshot antiguo tras uno posterior
impiden sobrescribir un resultado vigente. La caída total de conexión del evaluador
devuelve estado recuperable y no revierte ni cambia la carga ya confirmada.

Reconstrucción integral, validación global de entrega y video permanecen para el día 4.

## Validación de reconstrucción y entrega

La reconstrucción integral se ejecutó con volumen SQL, venv y node_modules nuevos
en el mismo equipo. Suite: **75 passed** en evidence/day4-rebuild/pytest-day4-rebuild.xml.
Lote adicional de demo: **7 passed**, con fallas/cambios solo en nuevas bases Test y
evidencia propia en data/demo-20261115T211447Z. Se conserva copia de su reporte de entrega.

La carga inicial y el incremental se ejecutaron en la fuente restaurada; se repitieron
entrenamiento, 14 preguntas GenAI, cuatro recorridos de navegador y recreación del
contenedor conservando volumen. Datos, linaje, watermark, modelo, predicciones y
conteos operativos iguales tras reinicio. Se detectó y corrigió readiness de las bases.

Documentación: revision-final.md, operacion.md y evidence/day4-rebuild/summary.json.
El video sigue pendiente; no se declara ejecutado ni aprobado por estas pruebas.
