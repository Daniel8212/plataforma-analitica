import React, { useEffect, useState, lazy, Suspense } from 'react';
import {number, money, businessDate, timestamp} from './format.js';
import Empty from './EmptyState.jsx';
import {request, query} from './api.js';
const Forecast = lazy(() => import('./Forecast.jsx'));
const Alerts = lazy(() => import('./Alerts.jsx'));
const Chat = lazy(() => import('./Chat.jsx'));
const Summary = lazy(() => import('./Summary.jsx'));



const defaults = meta => {
  if (!meta.last_date) return {start: '', end: '', product_id: '', category_id: ''};
  const start = new Date(`${meta.last_date}T00:00:00Z`);
  start.setUTCDate(start.getUTCDate() - 89);
  return {start: start.toISOString().slice(0, 10), end: meta.last_date, product_id: '', category_id: ''};
};

function Mark() {
  return <svg viewBox="0 0 32 32" width="31" height="31" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#163b3b"/><path d="M9 23V16M16 23V9M23 23V13" stroke="#5eead4" strokeWidth="3" strokeLinecap="round"/></svg>;
}
function Loading({label = 'Consultando indicadores…'}) { return <div role="status" className="loading"><span className="spinner"/>{label}</div>; }
function Failure({message, retry}) { return <div className="error-box" role="alert"><div><strong>No pudimos completar la consulta</strong><p>{message}</p></div><button className="action secondary" onClick={retry}>Reintentar</button></div>; }



function Detail({data, page, setPage}) {
  if (!data.total) return <Empty/>;
  return <section className="panel detail-panel" data-testid="detail-panel"><div className="panel-heading"><div><p className="eyebrow">DEL RESUMEN A LA OPERACIÓN</p><h2>Líneas de factura</h2></div><span className="subtle">{number(data.total)} líneas</span></div>
    <div className="table-scroll"><table><thead><tr><th>Fecha / factura</th><th>Cliente</th><th>Producto</th><th className="numeric">Unidades</th><th className="numeric">Precio</th><th className="numeric">Ventas sin impuesto</th><th className="numeric">Impuesto</th></tr></thead><tbody>{data.items.map(row => <tr key={row.InvoiceLineID}><td>{businessDate(row.InvoiceDate)}<small>Factura #{row.InvoiceID} · Línea {row.InvoiceLineID}</small></td><td>{row.CustomerName}<small>{row.CustomerCategory}</small></td><td className="product-cell">{row.ProductName}</td><td className="numeric">{number(row.Quantity)}</td><td className="numeric">{money(row.UnitPrice)}</td><td className="numeric emphasis">{money(row.SalesAmount)}</td><td className="numeric">{money(row.TaxAmount)}</td></tr>)}</tbody></table></div>
    <div className="pagination"><span>{number((page - 1) * data.page_size + 1)}–{number(Math.min(page * data.page_size, data.total))} de {number(data.total)}</span><div><button className="action secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>← Anterior</button><span>Página {page}</span><button className="action secondary" disabled={page * data.page_size >= data.total} data-action="next-page" onClick={() => setPage(page + 1)}>Siguiente →</button></div></div>
  </section>;
}

function Operations({data, inspect, rejects, rejectStatus, rejectError, rejectPage, setRejectPage, rejectRun}) {
  const success = data.runs.find(row => row.Status === 'SUCCEEDED');
  return <div data-testid="operations-panel">
    <div className="operations-summary"><article className="panel"><span className="eyebrow">ÚLTIMA CARGA EXITOSA</span><strong>{timestamp(data.latest_success.loaded_at)}</strong><p>Hora de Tegucigalpa · UTC−6</p></article><article className="panel"><span className="eyebrow">RECHAZADOS EN ESA CARGA</span><strong>{number(success?.RowsRejected ?? 0)}</strong><p>{number(success?.RowsInserted ?? 0)} hechos nuevos · {number(success?.RowsUpdated ?? 0)} corregidos</p></article><article className="panel"><span className="eyebrow">FALLAS EN LAS ÚLTIMAS {data.runs.length}</span><strong>{data.runs.filter(row => row.Status === 'FAILED').length}</strong><p>El historial conserva fallas y recuperaciones.</p></article></div>
    <section className="panel"><div className="panel-heading"><div><p className="eyebrow">TRAZABILIDAD DE CARGAS</p><h2>Ejecuciones recientes</h2></div><span className="subtle">Hasta 12 ejecuciones</span></div><div className="table-scroll"><table><thead><tr><th>Inicio / ejecución</th><th>Estado</th><th>Modo</th><th className="numeric">Leídos</th><th className="numeric">Insertados</th><th className="numeric">Actualizados</th><th className="numeric">Rechazados</th><th className="numeric">Duración</th></tr></thead><tbody>{data.runs.map(row => <tr key={row.ExecutionID}><td>{timestamp(row.StartTime)}<small className="run-id" title={row.ExecutionID}>{row.ExecutionID.slice(0, 8)}… {row.IsSimulated && '· SIMULACIÓN'}</small>{row.ErrorDetail && <details className="run-error"><summary>Ver diagnóstico</summary><p>{row.ErrorDetail}</p></details>}</td><td><span className={`status-badge ${row.Status.toLowerCase()}`}>{row.Status === 'SUCCEEDED' ? 'Exitosa' : row.Status === 'FAILED' ? 'Fallida' : 'En curso'}</span></td><td>{row.LoadMode === 'incremental' ? 'Incremental' : 'Completa'}</td><td className="numeric">{number(row.RowsRead)}</td><td className="numeric">{number(row.RowsInserted)}</td><td className="numeric">{number(row.RowsUpdated)}</td><td className="numeric">{row.RowsRejected ? <button className="text-action" onClick={() => inspect(row.ExecutionID)}>{number(row.RowsRejected)} ↗</button> : '0'}</td><td className="numeric">{number(row.DurationSeconds, 2)} s</td></tr>)}</tbody></table></div></section>
    <div className="bottom-grid operations-bottom"><section className="panel"><div className="panel-heading"><div><p className="eyebrow">PROGRESO CONFIRMADO</p><h2>Watermark persistido</h2></div></div>{data.watermarks.length ? data.watermarks.map(row => <div className="watermark" key={row.PipelineName}><span>{row.PipelineName}</span><strong>{timestamp(row.WatermarkValue)}</strong><p>Solo avanza al confirmar una publicación exitosa.</p><code>{row.ExecutionID}</code></div>) : <p className="subtle">Sin incremental confirmado.</p>}</section><section className="panel"><div className="panel-heading"><div><p className="eyebrow">CONTROL DE CALIDAD</p><h2>Historial de rechazos</h2></div></div>{data.rejections.length ? <div className="rejection-summary">{data.rejections.map(row => <button key={`${row.ExecutionID}-${row.RuleID}`} onClick={() => inspect(row.ExecutionID)}><span><code>{row.RuleID}</code><small>{row.ExecutionID.slice(0, 8)}…</small></span><strong>{number(row.count)} →</strong></button>)}</div> : <p className="subtle">No hay rechazos registrados.</p>}<p className="chart-note">Incluye cargas fallidas anteriores. No representa el rechazo de la última carga.</p></section></div>
    {rejectRun && <section className="panel rejection-detail" data-testid="rejection-detail"><div className="panel-heading"><div><p className="eyebrow">DETALLE DE CUARENTENA</p><h2>Registros rechazados</h2><p className="subtle run-id">{rejectRun}</p></div></div>{rejectStatus === 'loading' && <Loading label="Consultando rechazos…"/>}{rejectError && <p role="alert" className="negative">{rejectError}</p>}{rejectStatus === 'ready' && rejects && <><div className="table-scroll"><table><thead><tr><th>Fecha</th><th>Origen / clave</th><th>Regla</th><th>Detalle</th></tr></thead><tbody>{rejects.items.map(row => <tr key={row.QuarantineID}><td>{timestamp(row.RecordedAt)}</td><td>{row.SourceObject}<small>Clave: {row.SourceKey}</small></td><td><code>{row.RuleID}</code></td><td>{row.Detail}</td></tr>)}</tbody></table></div><div className="pagination"><span>{number(rejects.total)} registros · Página {rejectPage}</span><div><button className="action secondary" disabled={rejectPage === 1} onClick={() => setRejectPage(rejectPage - 1)}>← Anterior</button><button className="action secondary" disabled={rejectPage * rejects.page_size >= rejects.total} onClick={() => setRejectPage(rejectPage + 1)}>Siguiente →</button></div></div></>}</section>}
  </div>;
}

export default function App() {
  const [key, setKey] = useState('');
  const [connected, setConnected] = useState(false);
  const [loginStatus, setLoginStatus] = useState('idle');
  const [loginError, setLoginError] = useState('');
  const [meta, setMeta] = useState(null);
  const [tab, setTab] = useState('summary');
  const [draft, setDraft] = useState({start: '', end: '', product_id: '', category_id: ''});
  const [applied, setApplied] = useState(null);
  const [grain, setGrain] = useState('week');
  const [revision, setRevision] = useState(0);
  const [dashboard, setDashboard] = useState(null);
  const [dashboardStatus, setDashboardStatus] = useState('idle');
  const [dashboardError, setDashboardError] = useState('');
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState(null);
  const [detailStatus, setDetailStatus] = useState('idle');
  const [detailError, setDetailError] = useState('');
  const [operations, setOperations] = useState(null);
  const [opsStatus, setOpsStatus] = useState('idle');
  const [opsError, setOpsError] = useState('');
  const [rejectRun, setRejectRun] = useState('');
  const [rejectPage, setRejectPage] = useState(1);
  const [rejects, setRejects] = useState(null);
  const [rejectStatus, setRejectStatus] = useState('idle');
  const [rejectError, setRejectError] = useState('');
  async function login(event) {
    event.preventDefault(); setLoginStatus('loading'); setLoginError('');
    try { const payload = await request('filters', key); setMeta(payload); const initial = defaults(payload); setDraft(initial); setApplied(initial); setConnected(true); setLoginStatus('ready'); }
    catch (error) { setLoginError(error.message); setLoginStatus('error'); }
  }
  useEffect(() => {
    if (!connected || !applied) return;
    const controller = new AbortController();
    setDashboardStatus('loading'); setDashboard(null); setDashboardError('');
    request(`dashboard?${query(applied, {grain})}`, key, controller.signal).then(data => {setDashboard(data); setDashboardStatus('ready');}).catch(error => {if (!controller.signal.aborted) {setDashboardError(error.name === 'TimeoutError' ? 'La consulta tardó demasiado. Inténtalo otra vez.' : error.message); setDashboardStatus('error');}});
    return () => controller.abort();
  }, [connected, applied, grain, revision, key]);
  useEffect(() => {
    if (!connected || !applied || tab !== 'detail') return;
    const controller = new AbortController(); setDetailStatus('loading'); setDetail(null); setDetailError('');
    request(`detail?${query(applied, {page, page_size: 20})}`, key, controller.signal).then(data => {setDetail(data); setDetailStatus('ready');}).catch(error => {if (!controller.signal.aborted) {setDetailError(error.message); setDetailStatus('error');}});
    return () => controller.abort();
  }, [connected, applied, tab, page, revision, key]);
  useEffect(() => {
    if (!connected || tab !== 'operations') return;
    const controller = new AbortController(); setOpsStatus('loading'); setOpsError('');
    request('operations', key, controller.signal).then(data => {setOperations(data); setOpsStatus('ready');}).catch(error => {if (!controller.signal.aborted) {setOpsError(error.message); setOpsStatus('error');}});
    return () => controller.abort();
  }, [connected, tab, revision, key]);
  useEffect(() => {
    if (!connected || tab !== 'operations' || !rejectRun) return;
    const controller = new AbortController(); setRejectStatus('loading'); setRejectError('');
    request(`rejections?${query({execution_id: rejectRun, page: rejectPage, page_size: 10})}`, key, controller.signal).then(data => {setRejects(data); setRejectStatus('ready');}).catch(error => {if (!controller.signal.aborted) {setRejectError(error.message); setRejectStatus('error');}});
    return () => controller.abort();
  }, [connected, tab, rejectRun, rejectPage, revision, key]);
  const retry = () => { setRevision(value => value + 1); if (connected) request('filters', key).then(setMeta).catch(() => {}); };
  function apply(next) { setDraft(next); setApplied({...next}); setPage(1); }
  function drill(dimension, id) { apply({...applied, [dimension === 'product' ? 'product_id' : 'category_id']: String(id)}); setTab('detail'); }
  const latest = (tab === 'operations' ? operations?.latest_success : dashboard?.kpis) ?? meta;
  const nav = [['summary', '◴', 'Resumen'], ['detail', '▤', 'Detalle de ventas'], ['forecast', '↝', 'Pronóstico'], ['chat', '◇', 'Asistente'], ['alerts', '!', 'Alertas'], ['operations', '⌁', 'Operación y calidad']];
  const heading = {alerts: ['ALERTAS AUTOMATICAS','Detecta cambios y revisa su respaldo.','Semanas completas, referencia comparable y seguimiento persistido.'], chat: ['ASISTENTE LOCAL','Pregunta con datos a la vista.','Interpretaciones generadas con medidas y periodos verificables.'], summary: ['VENTAS FACTURADAS','Una vista clara de tus ventas.','Explora resultados históricos respaldados por facturas de la muestra.'], detail: ['VENTAS FACTURADAS','Cada línea cuenta.','Consulta las líneas que respaldan el conjunto filtrado.'], forecast: ['MODELO PREDICTIVO','Una mirada a las próximas semanas.','Predicciones versionadas y evaluación cronológica sobre la muestra histórica.'], operations: ['CONFIABILIDAD DEL DATO','Del origen al indicador.','Consulta ejecuciones, rechazos y progreso confirmado de las cargas.']}[tab];
  return <div className={`app-shell text-slate-100 ${connected ? '' : 'signed-out'}`}>
    <aside className="sidebar"><div className="brand"><Mark/><div><strong>Ventas</strong><span>ANALÍTICA INTELIGENTE</span></div></div>{connected && <nav aria-label="Navegación principal">{nav.map(([id, icon, label]) => <button key={id} data-tab={id} aria-current={tab === id ? 'page' : undefined} onClick={() => setTab(id)}><span aria-hidden="true">{icon}</span>{label}{tab === id && <i/>}</button>)}</nav>}<div className="sidebar-foot"><span className="source-dot"/>Muestra de Microsoft<p>Wide World Importers<br/>Histórico 2013–2016</p><span className="local-label">Entorno local</span></div></aside>
    <main className="workspace"><header className="topbar"><div className="breadcrumbs">Analítica de ventas <span>/</span> {connected ? nav.find(row => row[0] === tab)[2] : 'Acceso'}</div>{connected && <div className="topbar-actions"><span className="connection"><i/>Sesión activa</span><button className="text-action" onClick={() => {setConnected(false); setKey(''); setDashboard(null); setDetail(null); setOperations(null);}}>Salir</button></div>}</header>
      {!connected ? <div className="login-layout"><div className="login-intro"><span className="eyebrow">INFORMACIÓN PARA DECIDIR</span><h1>Tus ventas,<br/><span>en perspectiva.</span></h1><p>Explora el histórico, compara períodos y sigue cada indicador hasta sus líneas de factura.</p><div className="login-features"><span>◴ Histórico</span><span>⇄ Comparaciones</span><span>⌁ Trazabilidad</span></div><p className="sample-note">Datos de ejemplo oficiales de Microsoft. No corresponden a operaciones actuales de una empresa real.</p></div><section className="panel login-panel"><p className="eyebrow">ACCESO A LA DEMOSTRACIÓN</p><h2>Consulta tus indicadores</h2><p className="subtle">Ingresa la clave local para abrir la plataforma.</p><form id="access-form" onSubmit={login}><label htmlFor="demo-key">Clave de acceso</label><input id="demo-key" type="password" required autoComplete="off" value={key} onChange={event => setKey(event.target.value)}/><button type="submit" className="action primary" disabled={loginStatus === 'loading'}>{loginStatus === 'loading' ? 'Conectando…' : 'Entrar a la plataforma →'}</button></form>{loginError && <p role="alert" className="negative login-error">{loginError}</p>}<span className="privacy-note">La clave se mantiene solo en memoria durante esta sesión.</span></section></div> : <>
        <section className="page-heading"><div><p className="eyebrow">{heading[0]}</p><h1>{heading[1]}</h1><p>{heading[2]}</p></div><button className="action secondary" data-action="refresh" onClick={retry}>↻ Actualizar</button></section>
        <div className="freshness"><span className="freshness-dot"/><span>Última carga: <strong>{timestamp(latest?.loaded_at)}</strong> · Tegucigalpa, UTC−6</span><span className="coverage">Cobertura: {businessDate(meta?.first_date)} — {businessDate(meta?.last_date)}</span></div>
        {['summary','detail'].includes(tab) && <section className="filter-panel" aria-label="Filtros de ventas"><form id="filter-form" onSubmit={event => {event.preventDefault(); apply(draft);}}><label htmlFor="date-start">Desde<input id="date-start" type="date" required min="1900-01-01" max="2099-12-31" value={draft.start} onChange={event => setDraft({...draft, start: event.target.value})}/></label><label htmlFor="date-end">Hasta<input id="date-end" type="date" required min={draft.start || '1900-01-01'} max="2099-12-31" value={draft.end} onChange={event => setDraft({...draft, end: event.target.value})}/></label><label htmlFor="product-id">Producto<select id="product-id" value={draft.product_id} onChange={event => setDraft({...draft, product_id: event.target.value})}><option value="">Todos los productos</option>{meta.products.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label><label htmlFor="category-id">Categoría de cliente<select id="category-id" value={draft.category_id} onChange={event => setDraft({...draft, category_id: event.target.value})}><option value="">Todas las categorías</option>{meta.categories.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label><button type="submit" className="action primary">Aplicar filtros</button></form><div className="filter-shortcuts"><span>Período:</span><button onClick={() => apply({...applied, ...defaults(meta)})}>Últimos 90 días</button><button onClick={() => apply({...applied, start: meta.first_date, end: meta.last_date})}>Todo el histórico</button><button className="reset-filter" data-action="reset-filters" onClick={() => apply(defaults(meta))}>Restablecer filtros</button></div></section>}
        {tab === 'summary' && <div data-testid="summary-panel">{dashboardStatus === 'loading' && <Loading/>}{dashboardError && <Failure message={dashboardError} retry={retry}/>} {dashboardStatus === 'ready' && dashboard && <Suspense fallback={<Loading label="Cargando visualizaciones..."/>}><Summary data={dashboard} grain={grain} setGrain={setGrain} drill={drill}/></Suspense>}</div>}
        {tab === 'detail' && <>{detailStatus === 'loading' && <Loading label="Consultando líneas de factura…"/>}{detailError && <Failure message={detailError} retry={retry}/>} {detailStatus === 'ready' && detail && <Detail data={detail} page={page} setPage={setPage}/>}</>}
        {tab === 'forecast' && <Suspense fallback={<Loading label="Cargando pronóstico…"/>}><Forecast apiKey={key} revision={revision}/></Suspense>}
        {tab === 'alerts' && <Suspense fallback={<Loading label="Consultando alertas..."/>}><Alerts apiKey={key} revision={revision}/></Suspense>}
        {tab === 'chat' && <Suspense fallback={<Loading label="Cargando asistente…"/>}><Chat apiKey={key}/></Suspense>}
        {tab === 'operations' && <>{opsStatus === 'loading' && <Loading label="Consultando ejecuciones y calidad…"/>}{opsError && <Failure message={opsError} retry={retry}/>} {opsStatus === 'ready' && operations && <Operations data={operations} inspect={id => {setRejectRun(id); setRejectPage(1);}} rejects={rejects} rejectStatus={rejectStatus} rejectError={rejectError} rejectPage={rejectPage} setRejectPage={setRejectPage} rejectRun={rejectRun}/>}</>}
        <footer className="app-footer"><span>Wide World Importers · Datos de ejemplo de Microsoft · Proyecto académico</span><span>Importes sin impuestos · Moneda de origen sin código disponible</span></footer>
      </>}
    </main>
  </div>;
}
