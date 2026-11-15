# Revisión del día 3

Alcance autorizado: ML, asistente local y alertas integrados. El día 4 no se inició.

## Comprobaciones para revisar

- [x] ML consume DW, usa 177 semanas completas y excluye dos intervalos parciales.
- [x] Variables con pasado disponible, partición cronológica y evaluación recursiva a cuatro pasos.
- [x] Baselines y modelo entrenado; selección por validación, prueba independiente.
- [x] Artefactos, hashes, parámetros, fechas, versión y predicciones persistidos.
- [x] Pronóstico visible en React, identificado y separado del histórico.
- [x] Ollama CPU probado; proveedor único sin API de pago ni datos enviados al exterior.
- [x] POST /api/chat protegido, herramientas limitadas y SQL parametrizado.
- [x] Cifras/períodos/carga consultados por código; explicaciones incompatibles bloqueadas.
- [x] 14 preguntas registradas, tres sin respaldo, aclaración e intento de SQL.
- [x] Alertas tras carga exitosa, snapshot transaccional, deduplicación y reintentos.
- [x] Registro de valores, referencia, umbral, origen, severidad, estado y entrega.
- [x] Disparo/no disparo, falla de carga/evaluador/acuse y recuperación probados.
- [x] Eventos sintéticos identificados; fuente principal y hechos sin alteraciones simuladas.
- [x] Pronóstico, chat y alertas accesibles en aplicación local, escritorio y móvil.

## Evidencia y límites

Suite final: **75 passed**, una advertencia no bloqueante httpx/Starlette.
Compilación Vite aprobada. Comandos comprobados desde la raíz del repositorio:
`.\.venv\Scripts\python.exe -m pytest -q` para la suite y
`.\.venv\Scripts\python.exe -m tests.verify_day3` para el reporte de lectura.

| Componente | Evidencia principal | Resultado / límite |
|---|---|---|
| ML | evidence/ml-training.json, pytest-ml.xml | Ridge α=100; MAE prueba 113.773,87; baseline última semana ligeramente mejor |
| Calidad | ml-training.json | IQR por línea y semana; sin eliminar ventas válidas |
| GenAI | genai-evaluation.json, genai-review.md | 9 llamadas reales: 7 explicaciones aceptadas, 2 bloqueadas con métricas visibles |
| API/UI chat | chat-browser.json, capturas day3-chat | Consulta soportada y falta de cobertura desde React |
| Regla real | incremental-15dc90de-e5a0-4764-8940-4f34f58ac729.json | Caída 5,4520 %, CLEAR; importes DW reconciliados |
| Alertas | alert-tests.json, pytest-day3.xml | Bases Test aisladas: disparo, recuperación, permisos y entrega |
| Demo positiva | alert-demo.json, alerts-browser.json | Caída 35 % sintética, sin modificar ventas; etiqueta SIMULACIÓN |

Todos los archivos de evidencia están en `documentation/evidence/`. Las capturas
de prueba usan el historial 2013–2016; no representan pronósticos actuales de 2026.
Modelos y runtimes binarios permanecen ignorados en data/ y se regeneran/descargan
con los comandos documentados. El asistente pequeño no garantiza exactitud libre;
las métricas se sirven por herramientas y las explicaciones se filtran.

## Recorrido de revisión local

1. Iniciar SQL con Compose y API con el comando del README; iniciar Vite.
2. Iniciar Ollama con deployment/start-ollama.ps1 (modelo descargado).
3. Entrar con DEMO_API_KEY local; abrir Pronóstico y revisar métricas, versión y corte.
4. Asistente: preguntar ventas de marzo de 2016; verificar 4.645.254,00.
5. Preguntar ventas de 2030; debe reconocer falta de cobertura sin inventar cifras.
6. Ejecutar incremental; ver evaluación CLEAR y tarea exitosa en Alertas.
7. Ver demo SIMULACIÓN, referencia, estado y entrega; se puede atender o descartar.
8. Inspeccionar reportes de recuperación sin ejecutar fallas sobre la fuente principal.

La reconstrucción completa desde cero, revisión global de entrega y grabación del
video corresponden al día 4 y requieren autorización para iniciarlo. No se ha
publicado la aplicación ni se ha hecho push durante esta etapa.
