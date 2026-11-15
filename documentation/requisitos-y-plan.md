# Requisitos y plan de cuatro días

Fuente: guía v1.0, noviembre 2026, 15 páginas; leída completa el 14/11/2026.
Las instrucciones del usuario gobiernan el trabajo; la guía es la referencia académica,
no una autorización para publicar ni para transmitir información a terceros.

## Obligatorios de la guía

| Área | Mínimo verificable | Páginas | Evidencia prevista |
|---|---|---|---|
| Fuente | Inventario, ERD, diccionario, perfilado y preguntas | 4 | Exportaciones del catálogo y perfiles |
| ETL | Inicial e incremental; originales, limpieza, nulos, duplicados, estandarización, tipos, integridad, outliers, reglas, enriquecimiento, integración, históricos, cuarentena y linaje | 5–6 | Código, catálogo de reglas, pruebas y conteos |
| Fiabilidad | Watermark confirmado tras éxito, actualizaciones, tardíos, política de eliminaciones, idempotencia y recuperación | 6,12 | Lotes controlados, auditoría, reconciliación |
| DW | SQL Server, grano explícito, hechos, dimensiones, claves sustitutas/naturales, fecha, desconocidos y SCD justificada | 6–7 | DDL, diagrama editable, diccionario, SQL independiente |
| BI | Backend, acceso demo, 4–6 KPIs, fecha y dos dimensiones, tendencias, comparaciones, detalle, navegación, actualización y estados | 7–8 | Aplicación real, consultas independientes y latencia |
| ML | Python, DW, variables reproducibles, train/valid/test, baseline, evaluación, artefacto/versiones, predicciones persistidas y visibles | 8–9 | Experimentos y métricas de prueba independiente |
| GenAI | Datos autorizados, entradas y frecuencia limitadas, consultas controladas, respaldo y actualización, privacidad, trazabilidad | 9–10 | 10 preguntas, al menos 2 sin respaldo |
| Alertas | Un flujo completo, contenido y estado, disparo/no disparo, deduplicación, reintentos, generación y entrega registradas | 10 | Panel y pruebas, simulaciones identificadas |
| Operación | Mínimo privilegio, secretos externos, monitoreo y recuperación reproducible | 10–11 | Roles, reporte operativo y manual |
| Entrega | Código Git, documentación técnica completa, pruebas E2E, demo y video de 5 minutos | 11–14 | README probado, diagramas editables y guion |

## Recomendaciones y ejemplos, no obligaciones

- WideWorldImporters, herramientas y stack (pp. 4–5,15): permiten equivalentes. Aquí se mantiene el stack acordado.
- Estrella y un proceso principal (pp. 4,6): recomendaciones adoptadas por simplicidad.
- FactSales y atributos de ejemplo (p.7): no copiar campos sin comprobar fuente.
- Pronóstico, clasificación, clustering y anomalías (p.8): alternativas; el pronóstico semanal se confirma tras perfilado.
- Caída del 15% (p.10): ejemplo; el umbral será configurable y documentado.
- Airflow, mensajería, WebSockets, MLflow y canales externos: opcionales; quedan fuera inicialmente.
- Ocho fases y rúbrica ponderada (pp.11,13): sugeridas, no ocho semanas obligatorias.

## Contraste con el cronograma del usuario

No hay incompatibilidad sustancial. Los cuatro días comprimen las fases sin eliminar sus resultados.
El plan del usuario exige Tipo 2 en una dimensión; la guía exige estrategia SCD justificada,
sin imponer Tipo 2 específicamente. Implementaremos Tipo 2 donde haya valor comprobable.
La guía añade detalles que deben hacerse explícitos: outliers, latencia de consultas,
privacidad de logs GenAI, límites de frecuencia/tamaño, métricas de calidad/oportunidad,
registro de generación **y entrega** de alertas y conclusión breve del video.
Local reproducible satisface el despliegue del entorno; no se exige alojamiento público ni Vercel.
Cinco KPIs cumplen el rango de 4–6. El panel web basta como canal de alerta.
No denominar tiempo real al batch; frecuencia inicial bajo demanda y alerta tras éxito.

## Plan y puertas de aceptación

1. Día 1: entorno → fuente oficial → perfilado → modelo → carga inicial → KPI real visible y reconciliado.
2. Día 2: incremental, SCD, idempotencia y recuperación → API/dashboard completo y permisos.
3. Día 3: ML evaluado → proveedor generativo probado → chat respaldado → alertas verificadas.
4. Día 4: E2E y reconstrucción → documentación final → lote de demo y guion/video.

La documentación y evidencias se producen en cada paso. No avanzar declarando una puerta
superada sin ejecución. Si hay bloqueo, conservar requisitos y diagnosticar antes de sustituir fuente.
