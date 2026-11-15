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

## Pendientes de aceptación

1. SQL Server saludable y versión/edición registradas; backup oficial descargado y restore verificado.
2. Perfilado, grano y relaciones confirmados; prueba de multiplicación de joins.
3. Inicial: conteos e importes fuente/raw/clean/DW; rechazos explicados.
4. Endpoint protegido con KPI real y pantalla conectada; valores comparados con SQL independiente.
5. Incremental, idempotencia, tardíos, actualizaciones, SCD, cuarentena y recuperación.
6. KPIs/filtros combinados, período vacío, errores y latencia.
7. ML sin fuga temporal, baseline y prueba independiente.
8. GenAI: 10 casos, 2 sin respaldo, preguntas ambiguas/fuera de alcance y límites.
9. Alertas: disparo, no disparo, deduplicación, reintentos y entrega web.
10. Reconstrucción por README, E2E y lote de demo identificable.

No hay pruebas funcionales aprobadas todavía.
