# Evidencias de reconstrucción

Prueba aislada ejecutada el 15/11/2026 en copia bajo data/rebuild-20261115T205729Z,
SQL 14334 y volumen nuevo. `summary.json` identifica versiones y alcance.

- Restore oficial, carga inicial e incremental: restore.json, independent-validation.json
  y los dos reportes incremental-*.json.
- Dependencias y pruebas: Python nuevo coincide exactamente con requirements.lock.txt;
  npm ci/build aprobados; pytest-day4-rebuild.xml contiene 75 casos.
- ML reentrenado: ml-training.json y ml-weekly-series.csv; algoritmo, métricas y
  predicciones reproducidos. Las rutas data/models de ese reporte son relativas a
  la **copia de aceptación**, no al directorio de ejecución principal.
- GenAI: genai-evaluation.json, 14 preguntas reales y explicaciones bloqueadas.
- Calidad/recuperación: incremental-tests.json, alert-tests.json y JUnit; datos
  modificados únicamente en bases Test aisladas.
- Navegador: dashboard-browser.json, forecast-browser.json, chat-browser.json,
  alerts-browser.json y capturas. Los nombres day2-*/day3-* provienen de los scripts
  reutilizados; en esta carpeta corresponden a la reconstrucción final.
- Persistencia: persistence-before.json, persistence-after.json y persistence.json,
  tras recrear el contenedor con el mismo volumen y verificar readiness.

No se incluyeron .env, modelos binarios, backups ni runtimes. Se reutilizaron cachés
y el backup/modelo previamente descargados; no se afirma una instalación en otro
equipo. La instancia de aceptación se deja detenida y su volumen se conserva.
