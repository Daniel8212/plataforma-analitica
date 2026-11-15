# Manual de usuario

Abrir http://127.0.0.1:5173 con los servicios locales iniciados. Introducir la clave
de demostración suministrada por el autor; solo permanece en memoria hasta Salir
o cerrar/recargar la página. Los datos son la muestra de Microsoft de 2013–2016.
Importes sin impuestos y sin código de moneda confirmado; no son ventas actuales.

| Sección | Uso |
|---|---|
| Resumen | Cinco KPIs: ventas, unidades, facturas, ticket y variación; tendencias y desgloses |
| Detalle de ventas | Líneas de factura que respaldan el filtro, con paginación |
| Pronóstico | Modelo activo, evaluación, baseline, cuatro semanas previstas y corte |
| Asistente | Preguntas globales controladas y métricas verificadas por período |
| Alertas | Comparación semanal, eventos, estados, entrega y evaluaciones |
| Operación y calidad | Ejecuciones, conteos, fallas, watermark y cuarentena |

En Resumen/Detalle elegir Desde/Hasta, producto y categoría de cliente, y Aplicar
filtros. El inicio muestra los últimos 90 días del dataset. Todo el histórico amplía
el período; Restablecer devuelve los filtros iniciales. Pulsar un producto/categoría
del resumen navega a sus líneas. Las facturas distintas y ratios no se suman entre
grupos que se superponen. El período comparado tiene igual cantidad de días y se
muestran fechas exactas; sin referencia válida el porcentaje aparece sin dato.

El gráfico de Pronóstico separa observado de previsto. Las primeras predicciones
corresponden a mayo/junio **2016**, no al calendario actual. Revisar MAE/sMAPE y el
baseline: el modelo seleccionado no superó al baseline de última semana en MAE de
prueba. No usar estas proyecciones como garantía ni atribuirles causas comerciales.

En Asistente escribir un mes/año o fechas ISO. Ejemplos: «Ventas de marzo de 2016»,
«Compara ventas del 2016-03-01 al 2016-05-31», «Ventas por categoría en mayo de 2016».
Las cifras y períodos de la tabla son el respaldo; la frase es una interpretación
generada. Si se bloquea una explicación, siguen disponibles las métricas. «Ventas
de 2030» reconoce falta de cobertura. Las referencias relativas se anclan al último
dato, no al día actual. Las preguntas son independientes, sin memoria de conversación.

En Alertas la regla observa una caída mayor al 15 % entre dos semanas completas.
Una evaluación CLEAR es un resultado válido sin disparo. La demo positiva se marca
SIMULACIÓN; sus importes evaluados son sintéticos y no se añaden al dashboard.
El panel confirma entrega al renderizar. Marcar atendida o Descartar conserva el
historial; no modifica facturas. RESOLVED deriva de una reevaluación del mismo período.

Operación distingue rechazados de la última carga del historial de cuarentena.
Una falla anterior no implica que la carga vigente falló. Pulsar un conteo de rechazos
abre su detalle cuando existe. En un entorno nuevo puede no haber rechazos.
Las reparaciones y cargas se realizan desde los scripts operativos, no desde la UI.

Actualizar vuelve a consultar. Sin datos se muestra ausencia; error de conexión no
equivale a ventas cero. Reintentar después de revisar servicios con el operador.
Las marcas de eventos se muestran en Tegucigalpa (UTC−6); las fechas de negocio
no cambian de día por conversión de zona horaria.
