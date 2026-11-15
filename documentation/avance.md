# Registro de avance

## 2026-11-14 — Día 1 completado

- Carpeta inicial vacía, sin Git ni archivos que preservar. Repositorio local inicializado en main; sin remoto ni publicación.
- Guía leída completa; requisitos contrastados en `requisitos-y-plan.md`.
- Windows/PowerShell; Git 2.46.0; Python 3.12.6; Node 25.7.0; npm 11.10.1;
  Docker CLI/motor 29.9.3; Compose 5.7.0. ODBC Driver 17 registrado.
- Ollama no encontrado en PATH. Sin suponer GPU ni memoria libre: CIM fue denegado por aislamiento.
- Docker responde fuera del aislamiento. No había contenedores; volúmenes preexistentes no se modifican.
- `.venv` local, configuración sin secretos versionados, Compose limitado a localhost y volumen dedicado.
- Descargas de backup OLTP oficial, imagen SQL Server y dependencias completadas.
- Frontend React/Vite/Tailwind/Recharts instalado; pantalla inicial compilada con éxito.
  Integrado con endpoint y datos de ejemplo oficiales. El build requirió salir del aislamiento por acceso de esbuild.
- Python: SQLAlchemy 2.0.57, pyodbc 5.5.0, Pandas 2.3.3, FastAPI 0.163.0 instalados.
  `pip check` sin dependencias rotas. Versiones exactas en requirements.lock.txt.
  Vite respondió HTTP 200 en localhost; prueba visual Chrome y captura ejecutadas.
- API inicial con clave demo: salud=200 y acceso sin clave/clave incorrecta=401 verificados.
  Consulta válida integrada con dw.vSalesKpi y validada contra SQL independiente.
- SQL Server iniciado, healthcheck healthy y conexión Python/ODBC verificada.
  SQL Server 2022 Developer CU28 16.0.4325.4, Ubuntu 22.04.5.
  Imagen fijada por digest en Compose; motor Linux con 7,4 GiB y 16 CPUs visibles.

## Próximo punto de continuidad

El usuario autorizó iniciar día 2 el 2026-11-15. Repositorio publicado por el usuario en
https://github.com/Daniel8212/plataforma-analitica; los dos primeros commits coinciden con origin/main.
Incremental/SCD/recuperación implementados; cerrar sus pruebas y tercer commit, luego completar API/dashboard.

### Fuente confirmada

- Backup oficial descargado: 127.111.168 bytes; SHA256 registrado en evidence/backup-sha256.txt.
- Se corrigió cierre prematuro de cursor ODBC de RESTORE; el script consume todos los resultados,
  verifica el backup y exige estado ONLINE. Restauración final y perfilado ejecutados con éxito.
- 70.510 facturas, 228.265 líneas únicas, cobertura 2013-01-01–2016-05-31, sin notas de crédito.
- Base sin impuestos 172.261.341,20; impuestos 25.782.098,25; total 198.043.439,45.
- Fórmula cantidad × precio + impuesto validada sin discrepancias; cero líneas huérfanas de factura.
- ERD y diccionario generados del catálogo real. Grano/fórmulas definidos en modelo-ventas.md.

### Historial Git acordado: máximo ocho commits

1. Infraestructura, requisitos e inspección de fuente.
2. Carga inicial y primer KPI integrado.
3. Incremental, SCD y recuperación.
4. Dashboard y API completos.
5. Modelo predictivo y evaluación.
6. Asistente generativo verificado.
7. Alertas integradas y pruebas.
8. Validación final, manuales y entrega.

Mensajes describen cambios sin mencionar días. Ajustar agrupación si cambia el alcance,
sin superar ocho commits ni reescribir historial publicado sin autorización.

### Primer commit y diagnóstico RLS resuelto

- Commit `990395f`: infraestructura, guía e inspección de fuente.
- DDL analítico y cuentas técnicas creadas; API lee vista aprobada y no puede consultar raw.
- Primer lote conservó raw, pero la política RLS de WWI ocultó todos los clientes al extractor.
  Todas las líneas quedaron rechazadas, sin hechos cargados. Se corrigió la clasificación a FAILED
  y se añadió control de dimensiones vacías/cobertura. Evidencia inicial conserva el diagnóstico.
- La política usa nueve roles territoriales existentes sin permisos SQL propios.
  Propuesta concreta: agregar etl_loader a esos nueve roles para leer todos los clientes de muestra,
  conservando RLS activa y SELECT sobre cinco tablas. No usar db_owner ni desactivar seguridad.
- La revisión automática rechazó la ampliación persistente por requerir autorización explícita.
  El usuario autorizó expresamente el acceso y se aplicaron los nueve roles existentes.
  Bootstrap exige el flag explícito `--grant-source-territories`; RLS permanece activa.
  No se concedió db_owner ni permisos propios adicionales de los roles (no los tienen).
- Prueba de permisos del lector: 1 passed (vista permitida, raw denegado con SQL 229).
- Segundo lote con acceso sin cambios: FAILED por SOURCE_VISIBILITY_OR_EMPTY_DIMENSION,
  validando el control nuevo; raw conservado y DW vacío. Los cambios RLS se aplicaron solo tras autorización.

### Cierre del primer flujo

- Carga `f2da2c18-02a6-4ba2-8345-1c833cb2b633`: 228.265 hechos insertados, cero rechazos.
- Repetición `6da8442c-94d2-4d9c-98e9-06718342df80`: cero hechos nuevos, mismos conteos/importes.
- Reconciliación independiente: cuatro capas con 228.265 líneas, 70.510 facturas,
  172.261.341,20 sin impuestos y 8.950.628 unidades. Consulta KPI con conexión: 95,48 ms
  en una medición local, no un benchmark.
- Pytest: 3 passed, una advertencia de deprecación httpx/Starlette; no impide la ejecución.
- Chrome: acceso al KPI, importe renderizado igual a API, captura final registrada.
- API identifica UTC; React muestra actualización en America/Tegucigalpa.
- Diccionarios de fuente y capas analíticas, ERD, estrella, reglas y contratos guardados.
- Código de esta etapa se guarda en el segundo commit; quedan seis commits del máximo acordado.

## Pendientes posteriores

Completar únicamente día 2 en esta etapa; no adelantar ML/GenAI/alertas del día 3.
Video debe grabarse con ejecución real; solo se prepara guion automáticamente.

## 2026-11-15 — Día 2 en curso

- Árbol inicialmente limpio y main sincronizada con GitHub (dos commits).
- Docker healthy; se inspeccionaron capacidades temporales y marcas de edición sin modificar OLTP.
- Migración aditiva 004: watermark/auditoría, estado lógico de hechos e intervalos SCD2 observados.
- Incremental de medidas con solapamiento 48 h, claves nuevas y cambios de cabecera; dimensiones pequeñas completas.
- Publicación, SCD y watermark en una transacción. Raw y validación sobreviven a fallas de publicación.
- Política de bajas: conservar hecho DELETED y excluirlo de métricas; invalidaciones QUARANTINED recuperables.
- Tipo 2 de cliente conserva clasificación observada; producto Tipo 1. No se inventa historia comercial.
- Reconciliación exhaustiva por filas en ambas direcciones detecta cambios fuera de ventana y exige --full.
- Dos incrementales principales sin cambios conservaron 228.265 hechos y 172.261.341,20;
  el primero extrajo 530 líneas solapadas y el siguiente 0 líneas. Fuente principal intacta.
- Pruebas en bases Test aisladas, con IsSimulated=1: actualizaciones, tardíos, SCD2, cuarentena,
  bajas/reaparición, tres puntos de falla y reparación completa. Evidencia en incremental-tests.json.
- Pruebas originales: 3 passed tras la migración. Suite incremental: 11 passed, incluida protección
  contra watermark futuro. Reportes JUnit y ejecuciones simuladas registrados. Pendiente API/dashboard.
