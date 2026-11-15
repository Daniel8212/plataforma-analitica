# Demo reproducible

Ambiente principal iniciado según operacion.md. Entrar a la aplicación sin grabar
la clave ni el .env. Dataset oficial de muestra; toda alteración de prueba se identifica.

## Lote de cambios, calidad y recuperación

```powershell
.\.venv\Scripts\python.exe -m deployment.demo_lot
```

Copia registros seleccionados del OLTP a dos pares de bases Test nuevas con sufijo
único. Aplica corrección, registro tardío y repetición sin duplicación; valores inválidos
y reparación de cuarentena; fallas después de raw, publicación y antes de commit,
con recuperación; alerta verdadera/falsa y falla de evaluador/acuse con reintento.
Cada ejecución se marca simulada. No modifica las bases principales. Conserva las
bases para inspección; no elimina bases ni archivos existentes. Reportes por lote en
data/demo-<UTC>/ (manifest, JUnit, incremental-tests.json y alert-tests.json).

Para la explicación, abrir el manifiesto del lote recién ejecutado y los IDs de
sus bases/ejecuciones. Mostrar que watermark y hechos no se publican cuando falla,
y que una tarea de alerta fallida no revierte una carga que ya confirmó.
El lote puede tardar decenas de segundos; ejecutarlo antes del segmento breve del video.

## Recorrido visible de la aplicación

1. Ejecutar `.\.venv\Scripts\python.exe -m etl.run_incremental`: carga real de la
   muestra, reconciliada; sin cambios debe insertar/actualizar cero hechos.
2. Ejecutar `.\.venv\Scripts\python.exe -m deployment.acceptance`: mostrar igualdad
   fuente/DW y métricas con numerador/denominador. La reconciliación inicial entre
   cuatro capas se consulta con deployment.validate_initial.
3. Resumen: período 2016-03-01–2016-05-31, producto y categoría; aplicar, comparar
   y navegar a detalle. Quitar filtros y volver al histórico para explicar totales.
4. Pronóstico: señalar versión, corte 2016-05-29, cuatro semanas, MAE y baseline.
5. Asistente con Ollama activo: preguntar ventas de marzo 2016, contrastar
   **4.645.254,00** y período. Preguntar ventas de 2030: reconoce falta de datos.
6. Ejecutar `.\.venv\Scripts\python.exe -m notifications.demo --simulate`.
   Abrir Alertas y Actualizar. Mostrar SIMULACIÓN, caída sintética 35 %, referencia
   real y estado/entrega. La evaluación operacional CLEAR del 5,4520 % se distingue.
7. Atender o descartar el evento de prueba y actualizar. Repetir generación no duplica
   la alerta de la misma regla/semana; se conserva la decisión del operador.

La demo positiva no agrega ni cambia ventas en la fuente o DW. Si ya existe una
alerta de la misma semana, se reutiliza por deduplicación; no se promete un UUID
nuevo. Un nuevo incremental permite una evaluación nueva con otra carga origen.
No borrar eventos para fingir una primera ejecución.
