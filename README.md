# Plataforma de analítica de ventas

Proyecto académico local: WideWorldImporters OLTP → raw → clean → DW SQL Server →
FastAPI → React. ML, asistente generativo y alertas se incorporan tras validar el flujo base.
Estado real y siguientes pasos: [registro de avance](documentation/avance.md).
Requisitos de la guía: [matriz y plan](documentation/requisitos-y-plan.md).

## Preparación (PowerShell, desde la raíz)

Herramientas verificadas: Python 3.12.6, Git 2.46.0, Docker 29.9.3, Compose 5.7.0,
Node 25.7.0, npm 11.10.1, ODBC Driver 17 para SQL Server. No se requiere activar venv.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --timeout 180 -r requirements.lock.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Completar secretos locales fuertes y distintos en .env. Nunca versionarlos.
New-Item -ItemType Directory -Force data/backups
.\deployment\download-source.ps1
docker compose --env-file .env -f deployment/compose.yaml up -d
docker compose --env-file .env -f deployment/compose.yaml ps
.\.venv\Scripts\python.exe -m deployment.restore
.\.venv\Scripts\python.exe -m deployment.profile
```

No copiar `.env.example` sobre un `.env` existente. En este entorno ya se generaron
secretos aleatorios locales. El restore rehúsa sobrescribir una base existente.
El backup corresponde al **OLTP**, no WideWorldImportersDW. La descarga parcial no es válida.

## Inicio, parada y persistencia

```powershell
docker compose --env-file .env -f deployment/compose.yaml up -d
docker compose --env-file .env -f deployment/compose.yaml stop
docker compose --env-file .env -f deployment/compose.yaml start
docker compose --env-file .env -f deployment/compose.yaml logs --tail 60 sqlserver
```

SQL Server está en `127.0.0.1:14333`, volumen `plataforma-analitica_sqlserver_data`.
Límite contenedor 6 GB; SQL Server 4096 MB. Detener conserva datos. No ejecutar `down -v`
para reiniciar: elimina la persistencia. La fuente y DW serán bases separadas en la misma
instancia para reducir recursos. `sa` se reserva a preparación; ETL y API usarán cuentas distintas.
No publicar servicios ni secretos; GitHub y Vercel aún no configurados.

## Fuentes oficiales

- [Backup e instalación OLTP](https://learn.microsoft.com/sql/samples/wide-world-importers-oltp-install-configure)
- [Contenedores SQL Server](https://learn.microsoft.com/sql/linux/quickstart-install-connect-docker)
- [Memoria SQL Server en Linux](https://learn.microsoft.com/sql/linux/configure/performance-best-practices-sql-server-memory)

## Carga y aplicación — estado actual

```powershell
.\.venv\Scripts\python.exe -m deployment.bootstrap --grant-source-territories
.\.venv\Scripts\python.exe -m etl.run_initial
.\.venv\Scripts\python.exe -m deployment.catalog_warehouse
.\.venv\Scripts\python.exe -m deployment.validate_initial
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# Otra terminal, desde raíz:
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

**Bloqueo conocido de la muestra:** WideWorldImporters aplica RLS a clientes. El extractor
no ve clientes hasta pertenecer a sus nueve roles territoriales. El usuario autorizó esta
ampliación para la muestra local y se aplicó con el flag explícito mostrado arriba.
Los roles no tienen permisos SQL propios; se usan como banderas RLS. La política sigue activa
y ETL conserva SELECT sobre las cinco tablas. Sin esos roles la carga falla por cobertura,
conservando raw. No desactivar RLS ni usar sa como extractor.

La clave demo se consulta localmente en `.env`; no colocar su valor en comandos, URLs ni capturas.
El navegador solo la mantiene en memoria. La API usa analytics_reader sobre dw.vSalesKpi;
sa se limita a bootstrap/restauración y el extractor tiene cuenta separada.

```powershell
# Desde raíz: tres pruebas ejecutadas y aprobadas:
.\.venv\Scripts\python.exe -m pytest tests/test_initial_integration.py -q
# Con API y Vite activos: prueba Chrome ejecutada y aprobada:
node tests/browser-smoke.mjs
```

La prueba de navegador requiere Chrome instalado, API en 8000 y Vite en 5173.
Usa perfil propio bajo data/ y no modifica el perfil habitual.
Primer flujo cerrado: 228.265 líneas y 172.261.341,20 sin impuestos coinciden en las cuatro
capas y en pantalla. Son datos de ejemplo oficiales de Microsoft (2013–2016), no ventas
de una empresa real ni cifras hardcodeadas. Repetir la carga sin cambios inserta cero hechos.
Incremental, watermark atómico, bajas lógicas y SCD2 observado están implementados;
detalle y límites en [incremental-y-scd.md](documentation/incremental-y-scd.md).
Dashboard completo, ML, GenAI y alertas siguen pendientes.

## Cargas posteriores y recuperación

```powershell
.\.venv\Scripts\python.exe -m deployment.bootstrap
.\.venv\Scripts\python.exe -m etl.run_incremental
# Si se detecta un cambio fuera de la ventana de 48 horas:
.\.venv\Scripts\python.exe -m etl.run_incremental --full
# Pruebas de cambios simulados SOLO en bases Test separadas:
.\.venv\Scripts\python.exe -m pytest tests/test_incremental_integration.py -q
```

Orden SQL administrativo: 001_schema.sql → 004_incremental.sql (bootstrap lo aplica).
Ejecución: extraer delta → 006_validate_batch.sql → 005_publish.sql → reconciliar →
confirmar DW, auditoría y watermark. 002_transform.sql queda como referencia del primer flujo.
`etl.run_initial` ahora usa el mismo motor en modo completo, sin duplicar lógica de carga.
No se conceden nuevos roles RLS al ejecutar bootstrap sin el flag territorial.

Para detener la aplicación: Ctrl+C en ambas terminales. SQL Server puede permanecer activo
o detenerse con Compose; los datos permanecen en el volumen. La reconstrucción desde cero
y la restauración del entorno completo se volverán a validar en la etapa final.
