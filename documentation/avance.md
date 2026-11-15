# Registro de avance

## 2026-11-14 — Día 1 en curso

- Carpeta inicial vacía, sin Git ni archivos que preservar. Repositorio local inicializado en main; sin remoto ni publicación.
- Guía leída completa; requisitos contrastados en `requisitos-y-plan.md`.
- Windows/PowerShell; Git 2.46.0; Python 3.12.6; Node 25.7.0; npm 11.10.1;
  Docker CLI/motor 29.9.3; Compose 5.7.0. ODBC Driver 17 registrado.
- Ollama no encontrado en PATH. Sin suponer GPU ni memoria libre: CIM fue denegado por aislamiento.
- Docker responde fuera del aislamiento. No había contenedores; volúmenes preexistentes no se modifican.
- `.venv` local, configuración sin secretos versionados, Compose limitado a localhost y volumen dedicado.
- En curso: descargar backup OLTP oficial, imagen SQL Server e instalar dependencias.
- Frontend React/Vite/Tailwind/Recharts instalado; pantalla inicial compilada con éxito.
  Todavía sin endpoint ni datos. El build requirió salir del aislamiento por acceso de esbuild.
- Python: SQLAlchemy 2.0.57, pyodbc 5.5.0, Pandas 2.3.3, FastAPI 0.163.0 instalados.
  `pip check` sin dependencias rotas. Versiones exactas en requirements.lock.txt.
  Vite respondió HTTP 200 en localhost; sin prueba visual de navegador todavía.
- API inicial con clave demo: salud=200 y acceso sin clave/clave incorrecta=401 verificados.
  La consulta válida depende de vista analítica aún no creada. No hay KPI real validado.
- SQL Server iniciado, healthcheck healthy y conexión Python/ODBC verificada.
  SQL Server 2022 Developer CU28 16.0.4325.4, Ubuntu 22.04.5.
  Imagen fijada por digest en Compose; motor Linux con 7,4 GiB y 16 CPUs visibles.

## Próximo punto de continuidad

Confirmar final de descargas; iniciar y verificar SQL Server. Restaurar sin REPLACE;
inventariar y perfilar fuente **antes** de fijar fórmulas/DDL analítico.
Después: carga raw/clean/DW con auditoría/cuarentena, reconciliación, endpoint y pantalla React.
Día 1 NO cerrado hasta probar el recorrido completo.

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

## Pendientes posteriores

Días 2–4 según cronograma del usuario y matriz de requisitos. GitHub requiere autorización
para crear/publicar remoto. Video debe grabarse con ejecución real; solo se prepara guion automáticamente.
