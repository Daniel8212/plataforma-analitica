# Revisión final de entrega

Validación del 15 de noviembre de 2026, en el mismo Windows 11. Se creó una copia
del código con .venv y node_modules nuevos, puerto SQL 14334 y un volumen nuevo.
Se restauró el backup OLTP oficial verificado, sin reutilizar las bases principales.
Las cachés de paquetes, el archivo de backup y Ollama/modelo descargados se reutilizaron.

| Comprobación ejecutada | Resultado |
|---|---|
| Instalación Python desde lockfile; pip check | Correcta, sin conflictos |
| npm ci y build con Node 22.12/npm 10.9 | Correctos; auditoría npm reportó cero vulnerabilidades en esa ejecución |
| Restore, bootstrap y RLS autorizada de muestra | Bases ONLINE y extracción con cuenta ETL |
| Carga inicial | 228.265 líneas, 70.510 facturas, 8.950.628 unidades |
| Reconciliación fuente/raw/clean/DW | 172.261.341,20 sin impuestos, igualdad exacta |
| Incremental sin cambios | Cero inserciones/actualizaciones; sin duplicados |
| Suite sobre dependencias y SQL nuevos | 75 pruebas aprobadas; advertencia httpx/Starlette no bloqueante |
| Reentrenamiento desde DW nuevo | Ridge α=100 y métricas reproducidas; cuatro predicciones persistidas |
| GenAI real | 14 preguntas; 9 llamadas, 7 explicaciones aceptadas, 2 bloqueadas; falta de cobertura reconocida |
| Navegador | Dashboard, detalle, operación, pronóstico, chat y alertas; escritorio/móvil, sin excepciones JS |
| Persistencia | Contenedor de prueba recreado; datos, watermark, modelo y conteos operativos conservados |
| Protección de restore | Segunda restauración rechazada porque la fuente ya existía |

Hallazgos corregidos: detección automática de Tailwind variaba al copiar sin .git;
se limitó a frontend/src, conforme a la [documentación oficial](https://tailwindcss.com/docs/detecting-classes-in-source-files).
El healthcheck master precedía a la recuperación de WWI; wait_ready --databases
comprueba bases ONLINE y conexiones técnicas. La prueba visual de cuarentena asumía
rechazos históricos; ahora valida también su ausencia en una instalación limpia.

Evidencias detalladas: evidence/day4-rebuild/. El modelo reconstruido tiene una
versión nueva, pero reproduce importes previstos y métricas del modelo anterior.
El modelo principal y sus bases permanecieron intactos durante esta prueba.
La regla real detectó una caída 5,4520 %, inferior al umbral. El positivo del 35 %
en el panel está marcado SIMULACIÓN, sin cambiar ventas de OLTP/DW.

## Pendientes de entrega externos al código

- Las exportaciones PNG incorporadas por el usuario se conservan junto con fuentes
  editables independientes en diagramas/. delivery-check.json verifica sus enlaces.
  Regenerar ERD y modelo con las correcciones explicadas en revision-diagramas.md;
  las imágenes iniciales se conservan y sus diferencias quedan aclaradas en texto.
- Grabar el video y realizar la demo final. El guion no equivale a un video grabado.
- Revisar y hacer push desde la cuenta del usuario; no se publica automáticamente.

No se afirma haber probado otro equipo, reinstalado Windows ni recuperado una pérdida
física del disco. La solución es local y académica. El pronóstico corresponde al corte
de mayo 2016; no es una proyección de ventas actuales. La documentación distingue
funcionalidad verificada, limitaciones y trabajo manual pendiente.
