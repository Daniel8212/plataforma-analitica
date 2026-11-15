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
Copy-Item .env.example .env
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

Los comandos de ETL, API, frontend y pruebas se añadirán conforme sean implementados y ejecutados.
No se declara todavía el cierre del día 1.
