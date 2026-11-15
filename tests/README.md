# Pruebas

Resultados reales y plan: `documentation/pruebas.md`.
Pruebas de integración requieren SQL Server local y bootstrap; se ejecutan desde raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_initial_integration.py tests/test_incremental_integration.py tests/test_dashboard_api.py -q
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
