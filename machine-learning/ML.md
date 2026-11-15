# Pronóstico semanal de ventas

Problema: estimar cuatro semanas de ventas globales sin impuestos para planificación orientativa.
Fuente exclusiva de entrenamiento: dw.vSalesRead. Muestra sintética Microsoft, no operación actual.

La extracción encontró 179 buckets y conservó 177 semanas completas, de 2013-01-07 a 2016-05-23.
Se excluyen 2012-12-31 y 2016-05-30 por cobertura parcial. No se imputaron semanas faltantes (0).
No hay valores semanales negativos ni no finitos. Corte: domingo 2016-05-29; la muestra llega a
2016-05-31, pero esos dos días no entran en entrenamiento. Primera predicción: semana 2016-05-30.
Es una semana completa pronosticada desde el corte anterior, no una cifra para el año actual.

## Variables y separación

Lags 1/2/4/13/52; medias anteriores de 4/13 semanas; desviación anterior de 4; tendencia temporal
y seno/coseno del calendario conocido. No se usa cantidad futura, precio futuro ni el objetivo
actual. StandardScaler se ajusta solo en entrenamiento durante selección.

| Conjunto de objetivos | Período | Filas |
|---|---|---|
| Entrenamiento | 2014-01-06–2015-06-08 | 75 |
| Validación | 2015-06-15–2015-11-30 | 25 |
| Prueba | 2015-12-07–2016-05-23 | 25 |

La primera anualidad aporta el historial necesario para lags; no es un conjunto de prueba.
Se evalúan bloques cronológicos de origen móvil con hasta cuatro predicciones recursivas.
Cada origen conoce solo semanas anteriores; dentro del bloque usa predicciones propias.

Candidatos: última semana y estacional anual como baselines; Ridge α=1/10/100 con escalado y
Random Forest (150 árboles, profundidad 4, hoja mínima 4, semilla 42, un proceso).
Selección: menor MAE en validación. Reajuste train+validation, prueba congelada y, únicamente
después de reportarla, reajuste de despliegue con todas las semanas completas.
Se conservan tanto el estimador evaluado como el reajustado, y la serie CSV que los reproduce.

## Resultados ejecutados

Ridge α=100 fue seleccionado por validación (MAE 82.832,50). Prueba:

| Alternativa | MAE | RMSE | sMAPE |
|---|---|---|---|
| Ridge α=100 | 113.773,87 | 146.406,10 | 10,99 % |
| Última semana | 112.844,55 | 146.908,34 | 10,68 % |
| Estacional anual | 157.939,58 | 203.492,76 | 15,13 % |

El baseline de última semana obtuvo MAE ligeramente mejor en prueba. No se cambió la selección
usando ese resultado ni se afirma superioridad universal del modelo. No hay precisión mínima
garantizada ni intervalos de confianza. El error está en moneda de origen sin código disponible.

## Calidad Q10 y límites

IQR de semanas completas señaló 2016-05-02 (1.353.330,25). IQR de líneas: 13.907 cantidades,
24.184 precios y 20.012 importes señalados (pueden superponerse). El reporte guarda límites y
ejemplos verificables por producto/línea. Los productos de precio alto y cantidades grandes
siguen sujetos a las validaciones aritméticas existentes; no se eliminan automáticamente ni
se atribuye su comportamiento a promociones, clima o causas no disponibles.

Limitaciones: pocas observaciones, generador sintético y una separación temporal; sin variables
externas ni intervalos. Recortar a cero predicciones negativas respeta el objetivo no negativo
del alcance sin notas de crédito; no se imputa ni altera ninguna venta observada.

## Reproducibilidad y servicio

Paquete importable `machine_learning/` (underscore por sintaxis Python); documentación en
`machine-learning/`. Desde raíz PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m deployment.bootstrap
.\.venv\Scripts\python.exe -m machine_learning.train
.\.venv\Scripts\python.exe -m pytest tests/test_forecasting.py -q
```

ml.ModelRun conserva versión, fechas, parámetros, métricas, hash de datos/código/artefacto,
ejecución fuente y reporte. ml.Prediction conserva origen, objetivo, horizonte, generación y tipo.
Publicación de versión/predicciones atómica; artefactos confiables locales en data/models/.
El backend solo lee vistas aprobadas: no ejecuta pickles ni acepta artefactos de usuarios.
GET /api/forecast exige clave de demo y entrega resultados persistidos, métricas y advertencia
si cambian hechos después de la carga entrenada. La vista React distingue histórico de predicción.
Reentrenar tras cambios materiales o una nueva semana completa; ejecución manual reproducible,
no se configuró una frecuencia automática que los datos estáticos no requieren.

Evidencia: documentation/evidence/ml-training.json, ml-weekly-series.csv y pytest-ml.xml.
