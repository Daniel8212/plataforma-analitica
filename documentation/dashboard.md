# Dashboard y manual de uso

## Inicio local

Desde raíz PowerShell, SQL Server saludable y una carga confirmada:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Otra terminal:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

Abrir http://127.0.0.1:5173. Consultar la clave local DEMO_API_KEY en el editor de `.env` e
introducirla en el formulario; no copiarla a URLs, capturas ni repositorio. Se conserva en memoria
de la sesión y se descarta al salir. No se usa sa desde la API ni desde el navegador.
Detener con Ctrl+C en ambas terminales. La base conserva datos en su volumen Docker.

## Resumen

La pantalla abre los últimos 90 días **de la muestra cargada**, actualmente 2016-03-03–2016-05-31.
Son datos de ejemplo Microsoft, no ventas actuales ni datos productivos de una empresa real.
Cambiar Desde/Hasta, producto y categoría de cliente; pulsar Aplicar filtros. Atajos permiten
volver a 90 días, consultar todo el histórico o restablecer las dimensiones y fechas iniciales.

Cinco indicadores: ventas sin impuestos, unidades facturadas, facturas distintas, ticket medio
y variación frente al período anterior de igual duración. Se muestran las fechas exactas de
referencia; si no hay cobertura o ventas de base, aparece sin referencia comparable.
Importes sin código de moneda disponible: no se inventa un símbolo USD/HNL.

Gráficos semanales/mensuales y contribución por producto. El tooltip identifica intervalos
parciales; no interpretar el extremo parcial como una caída de semana completa. Seleccionar
un producto destacado o una categoría lleva al detalle y mantiene los filtros correspondientes.

La clasificación de cliente corresponde a la versión observada cuando el hecho ingresó, no a
una reconstrucción de su categoría en 2013–2016. Las definiciones de los KPIs están desplegables
en la propia pantalla.

## Detalle

Tabla por línea de factura: fecha/documento, cliente, categoría observada, producto, cantidad,
precio, venta sin impuestos e impuesto. Páginas de 20 filas con orden estable por fecha,
factura y línea. Los filtros siguen disponibles. No sumar ticket ni conteos distintos entre
productos para reconstruir totales; usar los KPIs del conjunto filtrado.

## Operación y calidad

Hasta 12 ejecuciones con inicio, estado, modo, conteos, duración y diagnóstico sanitizado.
El watermark representa únicamente el último progreso confirmado. Los rechazos de la última
carga exitosa se distinguen del historial de rechazos, que incluye fallas anteriores.
Pulsar un conteo de rechazos para revisar regla, fuente, clave y detalle paginado.
No se expone el JSON original ni se permite ejecutar/reparar cargas desde la cuenta de lectura.
Usar el manual incremental-y-scd.md para reintentos.

## Estados y recuperación de consulta

- Carga: indicador visible, sin mezclar tarjetas anteriores con filtros nuevos.
- Sin datos: mensaje explícito; no se inventa un gráfico para períodos fuera de cobertura.
- Error: diagnóstico de consulta genérico y botón Reintentar. No se transforma una falla en ventas cero.
- Actualizar: vuelve a consultar datos y catálogos; última carga en hora de Tegucigalpa, auditoría UTC.
- Salir: elimina la clave de la sesión. No se persiste en localStorage.

## Validación ejecutada

SQL independiente para KPIs con fechas/producto/categoría combinados; pruebas de acceso y límites,
referencias ausentes, paginación y consistencia de series. Chrome verificó el recorrido completo,
capturas de resumen/filtros/detalle/operación/ausencia de datos y diseño móvil.
La prueba visual de error intercepta **solo fetch local** con un retraso y respuesta 503 simulados;
se declara en dashboard-browser.json y en el nombre de la captura. SQL Server no se detiene.
Las modificaciones operacionales simuladas usan bases Test separadas y bandera IsSimulated.

Los gráficos se cargan de forma diferida; build de Vite genera entrada y módulo de gráficos
separados. Latencias HTTP puntuales en evidence/api-measurements.json; no equivalen a un SLA.
La reconstrucción desde un equipo limpio se validará en la etapa final de entrega.
