# Manual de operación

Ejecutar desde la raíz en Windows PowerShell. Configuración privada en `.env`;
usar `.env.example` como plantilla únicamente si no existe. Nunca copiarla encima
de una configuración local. Las contraseñas deben ser distintas y robustas;
bootstrap crea logins que no existen, no rota contraseñas de logins existentes.

## Componentes y permisos

| Componente | Dirección local | Persistencia / cuenta |
|---|---|---|
| SQL principal | 127.0.0.1:14333 | volumen Compose; fuente WideWorldImporters y DW SalesAnalytics |
| API | 127.0.0.1:8000 | analytics_reader, doce vistas aprobadas |
| Eventos | dentro de API | analytics_events: insertar chat y EXEC de dos procedimientos de alertas |
| ETL / ML / alertas | proceso Python | etl_loader; carga analítica y SELECT sobre cinco tablas de origen |
| Frontend | 127.0.0.1:5173 | Vite, proxy /api a 8000; clave solo en memoria del navegador |
| Ollama | 127.0.0.1:11434 | modelos/runtimes ignorados bajo data/ |
| SQL de reconstrucción | 127.0.0.1:14334 | volumen y proyecto distintos; se deja detenido al finalizar |

`sa` solo en restore/bootstrap/readiness. Las cuentas del backend no son administradoras.
Puertos limitados a loopback; no se ha desplegado Internet. La clave de demostración
no sustituye autenticación multiusuario ni un sistema de permisos para producción.

## Instalación nueva

1. Verificar Docker, Python 3.12, Node 22.12 o el entorno previamente comprobado,
   Git y Microsoft ODBC Driver 17. Instalar dependencias fijadas con el README.
2. Completar todas las variables de .env.example. APP_PASSWORD es necesaria además
   de las cuentas ETL y API. SQL_HOST debe ser 127.0.0.1 y SQL_PORT 14333.
3. Descargar el **OLTP Full** oficial mediante deployment/download-source.ps1.
   Preparar `data/backups/WideWorldImporters-Full.bak`, completo y verificable.
4. Ejecutar, en este orden:

```powershell
docker compose --env-file .env -f deployment/compose.yaml up -d --wait
.\.venv\Scripts\python.exe -m deployment.wait_ready
.\.venv\Scripts\python.exe -m deployment.restore
.\.venv\Scripts\python.exe -m deployment.bootstrap --grant-source-territories
.\.venv\Scripts\python.exe -m deployment.wait_ready --databases
.\.venv\Scripts\python.exe -m etl.run_initial
.\.venv\Scripts\python.exe -m deployment.validate_initial
.\.venv\Scripts\python.exe -m machine_learning.train
.\.venv\Scripts\python.exe -m deployment.acceptance
```

El flag territorial corresponde a los nueve roles de la **muestra local** autorizados
por el usuario. La política RLS permanece activa; no usar este flag sobre otra fuente
sin revisar su política. `restore` rechaza sobrescribir una base existente y no usa REPLACE.
En una instalación existente saltar restore, ejecutar bootstrap sin flag territorial
y usar la rutina de inicio siguiente. La carga completa no elimina raw previo.

Preparar Ollama/modelo una sola vez siguiendo generative-ai/GENAI.md. Para el
frontend, `npm.cmd ci` dentro de frontend/. No reinstalar dependencias en cada inicio.

## Inicio cotidiano y parada

```powershell
docker compose --env-file .env -f deployment/compose.yaml up -d --wait
.\.venv\Scripts\python.exe -m deployment.wait_ready --databases
.\.venv\Scripts\python.exe -m notifications.retry
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

En otra terminal: `Set-Location frontend`, `npm.cmd run dev -- --strictPort`.
En una tercera desde raíz: `.\deployment\start-ollama.ps1`.
Abrir localhost:5173 e introducir DEMO_API_KEY sin mostrar el .env en pantalla.
`/api/health` confirma proceso vivo; `wait_ready --databases` confirma recuperación
y acceso SQL. Docker healthy por sí solo no asegura que WWI terminó de recuperarse.

Parar API, Vite y Ollama con Ctrl+C en sus terminales; después:

```powershell
docker compose --env-file .env -f deployment/compose.yaml stop
# Reinicio posterior: up -d --wait y wait_ready --databases.
```

El volumen conserva las bases. No usar `down -v` para reiniciar. La prueba final
recreó el contenedor de aceptación conservando el mismo volumen y verificó igualdad
de hechos, auditoría, watermark, versión del modelo y predicciones antes/después.

## Cargas, monitoreo y recuperación

```powershell
.\.venv\Scripts\python.exe -m etl.run_incremental
# Solo cuando se diagnostica un cambio anterior a la ventana:
.\.venv\Scripts\python.exe -m etl.run_incremental --full
# Si falló únicamente la notificación después de confirmar la carga:
.\.venv\Scripts\python.exe -m notifications.retry
```

Cada carga usa bloqueo exclusivo, auditoría por ejecución, originales durables,
cuarentena y publicación atómica. Una carga fallida no confirma DW/watermark.
Corregir la causa y repetir la carga; no editar manualmente el watermark ni borrar raw.
Si el error indica reconciliación fuera de ventana, usar --full después de revisar
la fuente. Si la carga ya está SUCCEEDED y falla notify.Task, reintentar la tarea;
no se necesita repetir ETL. Detalle: incremental-y-scd.md y notifications/README.md.

La operación es batch bajo demanda; una evaluación automática sigue cada carga
exitosa. No hay scheduler, correo ni tiempo real. Monitorear Operación y calidad,
Alertas y sus intentos/diagnósticos. Los logs y tiempos se registran en UTC; la
interfaz muestra eventos en Tegucigalpa. Fechas de facturas son fechas de negocio.

| Síntoma | Diagnóstico y acción |
|---|---|
| 14333 no responde | Revisar Docker Desktop, compose ps y logs; esperar bases ONLINE |
| Clientes invisibles | Revisar roles territoriales autorizados; no desactivar RLS |
| Login falla | Revisar variable local y login existente; bootstrap no rota contraseñas |
| HTTP 401 | Revisar clave demo; no pegarla en URL ni guardarla en Git |
| Chat 503 | Iniciar Ollama/modelo, esperar otra generación; no hay API alternativa automática |
| Chat 429 | Esperar la ventana de un minuto; límite doce preguntas/IP |
| Snapshot antiguo | Revisar corte del dataset 2016; no interpretarlo como venta actual |
| Pronóstico requiere actualización | Reentrenar después de publicar cambios o una semana nueva |
| Alerta pendiente de entrega | Abrir panel; actualizar/reintentar el acuse después de corregir API |

## Restauración y reconstrucción de aceptación

La fuente se recupera desde el backup OLTP oficial en una instancia/base vacía.
El DW puede reconstruirse con bootstrap, carga completa y entrenamiento. Esa
reconstrucción regenera el snapshot y modelo, **no** conserva la historia observada
SCD2 ni auditoría anterior. El volumen existente sí conserva esa historia.
No se afirma haber implementado backup operativo completo del DW ni recuperación
ante pérdida física del disco; conservar el volumen no reemplaza una política de backup.

Procedimiento aislado repetible, con suficiente espacio libre (la prueba usó ~81 GB libres):

```powershell
.\.venv\Scripts\python.exe -m deployment.prepare_rebuild
$rebuildInfo = Get-Content data/rebuild-latest.json -Raw | ConvertFrom-Json
docker compose --env-file .env -f deployment/compose.yaml stop
Set-Location -LiteralPath $rebuildInfo.checkout
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
docker compose -p $rebuildInfo.project --env-file .env -f deployment/compose.rebuild.yaml up -d --wait
# Repetir instalación nueva desde restore; SQL_PORT ya está ajustado a 14334 en esta copia.
```

prepare_rebuild copia los archivos Git y archivos nuevos no ignorados, un .env local
ignorado y el backup, nunca .git/.venv/node_modules/volumen/modelos. Crea un directorio
nuevo y no sobrescribe otro. Instalar frontend con npm ci y entrenar antes de la suite.
Se reutilizaron cachés de paquetes, backup oficial y Ollama descargado; el venv,
node_modules y volumen SQL fueron nuevos. Es una prueba en el mismo Windows, no
una certificación de todos los sistemas. Al terminar, detener este Compose y volver
al original con sus comandos y readiness. No borrar automáticamente bases o volúmenes.
