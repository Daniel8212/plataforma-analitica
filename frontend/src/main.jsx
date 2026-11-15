import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [key, setKey] = useState('');
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  async function load(event) {
    event.preventDefault();
    setStatus('loading'); setError(''); setResult(null);
    try {
      const response = await fetch('/api/kpis', {headers: {'X-API-Key': key}});
      if (!response.ok) throw new Error(response.status === 401 ? 'Clave de acceso incorrecta.' : 'No se pudo consultar el Data Warehouse. Revisa la API y la última carga.');
      setResult(await response.json()); setStatus('ready');
    } catch (err) { setError(err.message); setStatus('error'); }
  }
  return <main className="mx-auto max-w-6xl px-6 py-12">
    <header className="mb-10 flex flex-wrap items-start justify-between gap-4">
      <div><p className="eyebrow">WIDE WORLD IMPORTERS / ANALÍTICA</p><h1 className="mt-3 text-4xl font-semibold tracking-tight">Ventas facturadas</h1><p className="mt-3 text-slate-400">Del registro operacional a una métrica verificable.</p></div>
      <span className="rounded-full border border-teal-800 px-4 py-2 text-sm text-teal-300">Entorno local</span>
    </header>
    <section className="panel mb-8" aria-label="Acceso a datos">
      <form onSubmit={load} className="flex flex-wrap items-end gap-4">
        <label className="flex min-w-64 flex-1 flex-col gap-2 text-sm text-slate-300">Clave de acceso de la demo<input required type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)} className="rounded-lg border border-slate-600 bg-slate-950 p-3 text-white"/></label>
        <button disabled={status === 'loading'} className="rounded-lg bg-teal-300 px-6 py-3 font-semibold text-slate-950 disabled:opacity-50">{status === 'loading' ? 'Consultando…' : 'Consultar DW'}</button>
      </form>
    </section>
    <div aria-live="polite">
      {status === 'idle' && <p className="panel text-slate-300">Ingresa la clave local para consultar los datos. No se muestran cifras de ejemplo.</p>}
      {status === 'loading' && <p className="panel">Consultando la última carga validada…</p>}
      {error && <p role="alert" className="panel border-red-800 text-red-300">{error}</p>}
      {result && (result.invoice_count === 0 ? <p className="panel">No hay datos para el período consultado.</p> : <>
        <article className="panel"><p className="eyebrow">VENTAS SIN IMPUESTOS</p><p className="my-5 text-5xl font-semibold tabular-nums">{new Intl.NumberFormat('es-HN', {maximumFractionDigits: 2, minimumFractionDigits: 2}).format(Number(result.sales))}</p><p className="text-sm text-slate-400">Importe en moneda de origen · {result.first_date} — {result.last_date}</p></article>
        <p className="mt-5 text-sm text-slate-400">Última carga exitosa: {result.loaded_at ? new Intl.DateTimeFormat('es-HN', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Tegucigalpa'}).format(new Date(result.loaded_at)) + ' (Tegucigalpa, UTC−6)' : 'No disponible'} · Ejecución: {result.execution_id ?? 'No disponible'}</p>
      </>)}
    </div>
    <footer className="mt-12 border-t border-slate-800 pt-5 text-sm text-slate-500">Datos de ejemplo de Microsoft · Proyecto académico · Vista inicial del flujo de ventas</footer>
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
