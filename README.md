# Plataforma de analítica de ventas

WideWorldImporters OLTP → raw → clean → Data Warehouse SQL Server → FastAPI → React.
Incluye dashboard histórico, pronóstico semanal, asistente local y alertas.
Los datos son la muestra oficial de Microsoft de **2013–2016**, no ventas actuales.

## Qué instrucciones seguir

| Tu situación | Sección |
|---|---|
| El proyecto ya está instalado en este equipo y quieres abrirlo | [Arranque habitual](#arranque-habitual-proyecto-ya-instalado) |
| Quieres ejecutar una carga o mostrar una alerta durante la demo | [Acciones de demostración](#acciones-de-demostración-opcionales) |
| Quieres cerrar la aplicación | [Parada](#parada) |
| Acabas de clonar el repositorio en un entorno nuevo | [Primera instalación](#primera-instalación) |
| Necesitas validar o reparar algo | [Pruebas y mantenimiento](#pruebas-y-mantenimiento) |

**No ejecutes el README completo cada vez.** Para usar la instalación actual basta
con el arranque habitual y abrir el navegador. No necesitas restaurar datos,
reinstalar dependencias, entrenar el modelo ni ejecutar pruebas en cada inicio.

## Arranque habitual: proyecto ya instalado

Abre Docker Desktop y espera a que esté operativo. Abre la carpeta
`plataforma-analitica` en VS Code. Crea **tres terminales PowerShell**, inicialmente
situadas en esa carpeta: la raíz contiene este README, `.env` y `deployment/`.

Cada terminal mantiene un servicio activo. Déjalas abiertas mientras usas la
aplicación; es normal que no vuelva a aparecer el indicador para escribir comandos.

### Terminal 1 — SQL Server y API

Desde la raíz, ejecuta las líneas en orden. Continúa cuando cada comando termine
sin errores. Si `wait_ready` falla, revisa el diagnóstico antes de iniciar la API.

```powershell
docker compose --env-file .env -f deployment/compose.yaml up -d --wait
.\.venv\Scripts\python.exe -m deployment.wait_ready --databases
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

SQL Server queda ejecutándose en Docker; la terminal permanece ocupada por la API.
El mensaje `Uvicorn running on http://127.0.0.1:8000` confirma que la API inició.

### Terminal 2 — interfaz web

En una terminal nueva, desde la raíz:

```powershell
Set-Location frontend
npm.cmd run dev -- --strictPort
```

El mensaje con `http://127.0.0.1:5173/` indica que la interfaz está disponible.
Esta terminal queda situada en `frontend`; las otras siguen en la raíz.

### Terminal 3 — asistente de IA

En una terminal nueva, desde la raíz:

```powershell
.\deployment\start-ollama.ps1
```

Mantén Ollama abierto para consultar el asistente. Si solo necesitas dashboard,
detalle, pronóstico y alertas, puedes omitir esta terminal. Sin Ollama el chat informa
indisponibilidad; no cambia automáticamente a una API externa de pago.

### Abrir la plataforma

Abre **http://127.0.0.1:5173** e introduce el valor de `DEMO_API_KEY` de tu `.env`
local. La clave solo permanece en memoria durante la sesión del navegador.
No la pegues en URLs, comandos, capturas ni archivos versionados.

Ya puedes navegar por Resumen, Detalle de ventas, Pronóstico, Asistente, Alertas y
Operación y calidad. Los datos y las predicciones previamente guardados están
disponibles sin ejecutar otra carga. Swagger está en http://127.0.0.1:8000/docs.

## Acciones de demostración: opcionales

La aplicación completa funciona con las tres terminales anteriores. Para lanzar
comandos mientras esos servicios siguen activos, abre una **cuarta terminal** en la
raíz. Esta terminal es de trabajo temporal, no un cuarto servicio permanente.
Ejecuta únicamente la acción que quieras mostrar.

| Acción | Comando desde la raíz |
|---|---|
| Actualizar el DW desde la fuente y evaluar la regla de alerta | `.\.venv\Scripts\python.exe -m etl.run_incremental` |
| Comparar fuente, raw, clean y DW mediante SQL independiente | `.\.venv\Scripts\python.exe -m deployment.validate_initial` |
| Mostrar una alerta positiva identificada como simulación | `.\.venv\Scripts\python.exe -m notifications.demo --simulate` |
| Probar cambios, cuarentena y recuperación en bases Test aisladas | `.\.venv\Scripts\python.exe -m deployment.demo_lot` |

Después de una carga o alerta, pulsa **Actualizar** en la sección correspondiente
de la aplicación. Si la fuente no cambió, el incremental inserta y actualiza cero
hechos. La carga exitosa evalúa automáticamente la última semana completa frente a
la anterior; el umbral es una caída **mayor al 15 %**.

La muestra tiene una caída real del 5,4520 % en esa comparación: no dispara alerta.
El comando `notifications.demo --simulate` crea o reutiliza un evento sintético del
35 %, marcado **SIMULACIÓN**, sin cambiar las ventas de la fuente ni del DW.

Recorrido completo: [demo.md](documentation/demo.md). El
[guion del video](documentation/guion-video.md) indica qué mostrar en cinco minutos.

## Parada

1. Pulsa **Ctrl+C** en las terminales de API, frontend y Ollama.
2. En la terminal 1, que sigue en la raíz, detén SQL si también quieres liberarlo:

```powershell
docker compose --env-file .env -f deployment/compose.yaml stop
```

El volumen conserva las bases. Para volver a abrir el proyecto, repite el arranque
habitual. **No uses `down -v` para reiniciar:** elimina la persistencia.

## Primera instalación

**Solo para un entorno nuevo.** En el equipo ya preparado, utiliza el arranque habitual.

Entorno de reconstrucción verificado: Windows 11, PowerShell 5.1, Python 3.12.6,
Git 2.46.0, Docker 29.9.3, Compose 5.7.0, Node 22.12.0, npm 10.9.0 y Microsoft ODBC
Driver 17 para SQL Server. También se probó Node 25.7/npm 11.10.1. Equipo con 16 GB
de RAM; la primera descarga requiere Internet y espacio para SQL, dependencias y modelo.

Instala previamente esas herramientas y comprueba Docker Desktop. Desde la raíz:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --timeout 180 -r requirements.lock.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

**Antes de continuar**, completa los secretos locales de `.env`, incluidos
`MSSQL_SA_PASSWORD`, `ETL_PASSWORD`, `API_PASSWORD`, `APP_PASSWORD` y `DEMO_API_KEY`.
Usa contraseñas fuertes y distintas. No sobrescribas un `.env` existente.

Después, para preparar la fuente y la base analítica nuevas, ejecuta cada línea y
verifica que termine correctamente antes de continuar:

```powershell
New-Item -ItemType Directory -Force data/backups
.\deployment\download-source.ps1
docker compose --env-file .env -f deployment/compose.yaml up -d --wait
.\.venv\Scripts\python.exe -m deployment.wait_ready
.\.venv\Scripts\python.exe -m deployment.restore
.\.venv\Scripts\python.exe -m deployment.bootstrap --grant-source-territories
.\.venv\Scripts\python.exe -m deployment.wait_ready --databases
.\.venv\Scripts\python.exe -m etl.run_initial
.\.venv\Scripts\python.exe -m deployment.validate_initial
.\.venv\Scripts\python.exe -m machine_learning.train
npm.cmd --prefix frontend ci
```

El restore usa **WideWorldImporters OLTP**, no su DW preconstruido, y rechaza
sobrescribir una base existente. El flag territorial incorpora al extractor a nueve
roles de la muestra local autorizados para leer los clientes bajo RLS; mantiene la
política activa y SELECT sobre cinco tablas. No aplicarlo a otra fuente sin revisar
su política. Los scripts no usan `sa` como cuenta de ETL ni de consulta de la aplicación.

Para instalar Ollama y descargar el modelo por primera vez, sigue
[GENAI.md](generative-ai/GENAI.md). Después vuelve a **Arranque habitual**.
El orden completo, permisos y reconstrucción aislada están en el
[manual de operación](documentation/operacion.md).

## Pruebas y mantenimiento

Estas acciones son independientes del arranque y se ejecutan desde la raíz en una
terminal libre. La suite requiere bases preparadas y modelo entrenado.

| Necesidad | Comando |
|---|---|
| Suite automatizada | `.\.venv\Scripts\python.exe -m pytest -q` |
| Reintentar tareas de alertas pendientes o fallidas | `.\.venv\Scripts\python.exe -m notifications.retry` |
| Reentrenar tras cambios de datos o una semana completa nueva | `.\.venv\Scripts\python.exe -m machine_learning.train` |
| Carga completa, si se diagnostican cambios fuera de la ventana incremental | `.\.venv\Scripts\python.exe -m etl.run_incremental --full` |
| Ver logs recientes de SQL | `docker compose --env-file .env -f deployment/compose.yaml logs --tail 60 sqlserver` |

Para pruebas de navegador, consulta [tests/README.md](tests/README.md): necesitan
Chrome y los servicios correspondientes activos. Python tiene versiones fijadas en
`requirements.lock.txt`; frontend usa `frontend/package-lock.json`.

## Resultados, límites y documentación

La reconstrucción en el mismo equipo, con dependencias y volumen SQL nuevos,
reconcilió 228.265 líneas y 172.261.341,20 sin impuestos. Pasaron 75 pruebas y los
recorridos de navegador. No equivale a una prueba en otro sistema operativo.

El pronóstico usa 177 semanas completas y cuatro semanas de horizonte, con corte
en mayo de **2016**. MAE de prueba: 113.773,87; sMAPE: 10,99 %. El baseline de última
semana tuvo un MAE ligeramente menor. No se afirma superioridad ni predicción actual.
Ollama/Qwen2.5 1.5B funciona localmente; herramientas controladas proporcionan cifras
al asistente y se bloquean explicaciones que no superan la verificación.

- [Manual de usuario](documentation/manual-usuario.md): uso de las seis secciones.
- [Manual de operación](documentation/operacion.md): variables, puertos, permisos y recuperación.
- [Índice técnico](documentation/indice-entrega.md): requisitos, diagramas y diccionarios.
- [Revisión final](documentation/revision-final.md): evidencias y pendientes reales.
- [Registro de avance](documentation/avance.md): historial del proyecto.
- [Machine Learning](machine-learning/ML.md), [GenAI](generative-ai/GENAI.md) y [alertas](notifications/README.md).

SQL principal: `127.0.0.1:14333`, volumen `plataforma-analitica_sqlserver_data`;
contenedor limitado a 6 GB y SQL a 4096 MB. La solución sigue siendo local, con batch
bajo demanda. Vercel y correo no están configurados. No subir `.env`, `data/`, backups,
modelos binarios, perfiles del navegador ni credenciales al
[repositorio GitHub](https://github.com/Daniel8212/plataforma-analitica).

Fuentes oficiales: [instalación OLTP de Microsoft](https://learn.microsoft.com/sql/samples/wide-world-importers-oltp-install-configure),
[SQL Server en Docker](https://learn.microsoft.com/sql/linux/quickstart-install-connect-docker)
y [memoria de SQL Server en Linux](https://learn.microsoft.com/sql/linux/configure/performance-best-practices-sql-server-memory).
