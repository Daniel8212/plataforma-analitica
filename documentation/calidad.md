# Catálogo inicial de calidad y transformación

Catálogo para toda la entrega. Implementación actual: claves únicas, nulos/rangos, integridad,
importes, trim, calendario, SCD observado, cuarentena, linaje y reconciliación están implementados
y probados; detalle en incremental-y-scd.md. Q10 implementado en el perfilado ML mediante IQR
semanal y de cantidad/precio/importe por línea; límites y ejemplos en evidence/ml-training.json.
Las observaciones señaladas se conservaron; no se imputaron causas ni se borraron valores.
Cada ejecución registra conteos antes/después y rechazo por regla. Un outlier no se elimina
por ser atípico; precio cero puede ser válido y cantidades negativas requieren contexto de crédito.

| ID | Control / transformación | Tratamiento aplicado | Evidencia |
|---|---|---|---|
| Q01 | Clave natural de línea no nula y única en extracción | Duplicado inesperado: fallar lote, sin elegir sobreviviente arbitrario | Conteo total vs distinct |
| Q02 | Factura, producto, cliente y fecha resolubles | FK desconocida: cuarentena o miembro desconocido según causa documentada | Anti-joins y rechazo |
| Q03 | Cantidad/precio/impuesto/importe convertibles a decimal exacto | No truncar; errores a cuarentena | Tipo fuente y sumas |
| Q04 | Coherencia del importe extendido con base e impuesto | Cantidad × precio + impuesto = extendido; diferencias a cuarentena | Conteo y diferencia monetaria |
| Q05 | Semántica de notas de crédito y devoluciones | Conservar original; no cambiar signo dos veces | Distribución por IsCreditNote y signo |
| Q06 | Fechas válidas y relaciones temporales coherentes | Conservar fecha de negocio; auditoría UTC separada | Mínimos, máximos y nulos |
| Q07 | Nombres/códigos con espacios y formatos | Trim documentado en clean; raw sin modificación | Comparación de valores modificados |
| Q08 | Nulos por campo y causa | No imputar medidas con cero; desconocidos diferenciados | Perfil de completitud |
| Q09 | Join de grupos de producto potencialmente muchos-a-muchos | No expandir hechos; elegir atributo con cardinalidad comprobada o puente separado | Conteos y sumas antes/después |
| Q10 | Outliers de cantidad/precio/ventas | Marcar/investigar, sin eliminación automática | Percentiles y ejemplos con clave |
| Q11 | Claves sustitutas y miembros desconocidos | Resolver antes del hecho, FK y restricción de grano | Duplicados y huérfanos en DW |
| Q12 | Historia de atributos | Tipo 2 donde se justifique; no inventar vigencias previas a observación | Intervalos sin solapamientos |
| Q13 | Enriquecimiento de calendario y medidas | Derivación determinista, unidades y moneda explícitas | Pruebas de fecha y fórmulas |
| Q14 | Reconciliación fuente/raw/clean/DW | Igualdad exacta o diferencia justificada por rechazo | Consulta independiente y audit |
| Q15 | Linaje y recuperación | execution_id, fuente, clave y estado; no publicar carga parcial | Ejecución fallida y reintento |

Métricas: completitud (no nulos/total), unicidad (claves distintas/total),
validez (válidos/total), consistencia (reglas cruzadas satisfechas/total),
integridad (huérfanos) y oportunidad (evento → disponibilidad, distinguiendo dataset histórico
de latencia técnica de carga). Registrar numeradores/denominadores y no solo porcentajes.

Aceptación final: deployment.acceptance calcula numeradores/denominadores de
completitud de precio, unicidad de clave, consistencia de importes y aceptación en
clean, junto con huérfanos, linaje y duración de carga. Resultados ejecutados en
evidence/day4-rebuild/persistence-after.json y evidence/day4-main-preserved.json.
En la reconstrucción: 228.265/228.265 completos, únicos, consistentes y aceptados;
cero huérfanos y cero hechos sin carga exitosa. La antigüedad del dataset se registra
aparte de la duración técnica; no se presenta como incumplimiento de un SLA actual.
