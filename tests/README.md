# Pruebas

Resultados reales y plan: `documentation/pruebas.md`.
Pruebas de integración requieren SQL Server local y bootstrap; se ejecutan desde raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Incremental usa bases únicas WWI_Test_* y SalesAnalytics_Test_* con tres facturas copiadas del
ejemplo; cambios/fallas solo allí y todas esas ejecuciones marcadas IsSimulated. La fuente
principal no se modifica. Las bases de prueba quedan disponibles para inspección.

Con FastAPI/Vite activos y Chrome instalado:

```powershell
node tests/dashboard-smoke.mjs
```

El navegador usa perfil separado bajo data/; nunca tu perfil habitual. Valida acceso, KPIs,
filtros, drill-down, paginación, operación, rechazos, móvil y una falla de consulta visual
**simulada y declarada**, seguida de recuperación real. No se envían claves fuera de localhost.
browser-smoke.mjs conserva el recorrido histórico de la primera pantalla; la prueba vigente es dashboard-smoke.mjs.

La suite completa requiere también entrenamiento ML publicado; el modelo se genera
con `python -m machine_learning.train`. Pytest no necesita un servidor Ollama activo:
los controles unitarios usan dobles explícitos, y las llamadas reales se registran
separadamente con `python -m generative_ai.evaluate` (Ollama sí debe estar activo).
Pronóstico, chat y alertas tienen pruebas de navegador dedicadas en forecast-browser.mjs,
chat-browser.mjs y alerts-browser.mjs. El último requiere la demo explícitamente simulada.

Lote corto reproducible: `python -m deployment.demo_lot`, siete casos de cambios,
cuarentena, rollback y alertas. Usa TEST_EVIDENCE_DIR para separar sus reportes y
no sobrescribir evidencias históricas; las bases Test quedan disponibles para inspección.
