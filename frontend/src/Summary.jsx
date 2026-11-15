import React from 'react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {number, money, compact, businessDate, shortDate} from './format.js';
import Empty from './EmptyState.jsx';
const tooltipStyle = {background: '#142237', border: '1px solid #334357', borderRadius: 10, color: '#eef3f9', fontSize: 12};

export default function Summary({data, grain, setGrain, drill}) {
  const k = data.kpis;
  const series = data.trends.map(row => ({...row, sales: Number(row.sales)}));
  const products = data.products.map(row => ({...row, sales: Number(row.sales), short: row.label.length > 23 ? row.label.slice(0, 23) + '…' : row.label}));
  const categories = data.categories.map(row => ({...row, sales: Number(row.sales)}));
  const cards = [
    ['Ventas sin impuestos', money(k.sales), k.is_comparable ? `Anterior: ${money(k.previous.sales)}` : 'Referencia fuera de cobertura', 'sales'],
    ['Unidades facturadas', number(k.units), 'Cantidad vendida en el período', 'units'],
    ['Facturas', number(k.invoice_count), `${number(k.line_count)} líneas de factura`, 'invoices'],
    ['Ticket promedio', k.average_ticket === null ? '—' : money(k.average_ticket), 'Ventas ÷ facturas distintas', 'ticket'],
    ['Variación del período', k.variation_pct === null ? '—' : `${Number(k.variation_pct) > 0 ? '+' : ''}${number(k.variation_pct, 2)}%`, k.variation_pct === null ? 'Sin referencia comparable' : 'Frente al período anterior', 'variation'],
  ];
  return <>
    <div className="kpi-grid" data-testid="kpi-grid">{cards.map(([label, value, caption, id], i) => <article className={`kpi-card ${i === 0 ? 'primary-kpi' : ''}`} key={id} data-kpi={id}>
      <div className="kpi-label"><span>{label}</span><span aria-hidden="true">{['↗', '▦', '▤', '÷', '⇄'][i]}</span></div>
      <strong className={id === 'variation' && k.variation_pct !== null ? Number(k.variation_pct) < 0 ? 'negative' : 'positive' : ''}>{value}</strong><p>{caption}</p>
    </article>)}</div>
    {k.invoice_count === 0 ? <Empty/> : <>
      <div className="charts-grid">
        <section className="panel trend-panel"><div className="panel-heading"><div><p className="eyebrow">EVOLUCIÓN HISTÓRICA</p><h2>Ventas a través del tiempo</h2></div><div className="segmented" aria-label="Agrupación temporal"><button aria-pressed={grain === 'week'} onClick={() => setGrain('week')}>Semanal</button><button aria-pressed={grain === 'month'} onClick={() => setGrain('month')}>Mensual</button></div></div>
          <div className="chart" aria-label="Tendencia de ventas sin impuestos"><ResponsiveContainer width="100%" height="100%"><AreaChart data={series} margin={{left: 0, right: 12, top: 12, bottom: 0}}>
            <defs><linearGradient id="sales-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5eead4" stopOpacity={0.26}/><stop offset="100%" stopColor="#5eead4" stopOpacity={0}/></linearGradient></defs>
            <CartesianGrid vertical={false} stroke="#253348" strokeDasharray="3 5"/><XAxis dataKey="bucket" tickFormatter={shortDate} tick={{fill: '#8798af', fontSize: 11}} axisLine={false} tickLine={false} minTickGap={30}/><YAxis tickFormatter={compact} tick={{fill: '#8798af', fontSize: 11}} axisLine={false} tickLine={false} width={55}/>
            <Tooltip contentStyle={tooltipStyle} labelFormatter={value => businessDate(value) + (series.find(row => row.bucket === value)?.partial ? ' · Período parcial' : '')} formatter={value => [money(value), 'Ventas']}/><Area isAnimationActive={false} type="monotone" dataKey="sales" stroke="#5eead4" strokeWidth={2.5} fill="url(#sales-fill)"/>
          </AreaChart></ResponsiveContainer></div><p className="chart-note">Importes sin impuestos. Los intervalos de los extremos pueden ser parciales.</p>
        </section>
        <section className="panel"><div className="panel-heading"><div><p className="eyebrow">CONTRIBUCIÓN</p><h2>Productos destacados</h2></div><span className="subtle">Top {products.length}</span></div>
          <div className="chart compact-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={products} layout="vertical" margin={{left: 0, right: 10}}><XAxis type="number" hide/><YAxis dataKey="short" type="category" width={150} tick={{fill: '#b6c4d5', fontSize: 10}} axisLine={false} tickLine={false}/><Tooltip contentStyle={tooltipStyle} formatter={value => [money(value), 'Ventas']}/><Bar isAnimationActive={false} dataKey="sales" fill="#6ea8ff" radius={[0, 4, 4, 0]} barSize={14}/></BarChart></ResponsiveContainer></div>
          <div className="drill-list">{data.products.slice(0, 3).map(row => <button key={row.id} data-product-drill={row.id} onClick={() => drill('product', row.id)} title={row.label}><span>{row.label}</span><span aria-hidden="true">→</span></button>)}</div><p className="chart-note">Selecciona un producto para consultar sus líneas.</p>
        </section>
      </div>
      <div className="bottom-grid">
        <section className="panel"><div className="panel-heading"><div><p className="eyebrow">REFERENCIA EXPLÍCITA</p><h2>Comparación entre períodos</h2></div></div>
          <div className="period-comparison"><div><span className="period-dot current"/>Actual<strong>{money(k.sales)}</strong><small>{businessDate(k.period.start)} — {businessDate(k.period.end)}</small></div><div><span className="period-dot previous"/>Anterior<strong>{k.is_comparable ? money(k.previous.sales) : 'No comparable'}</strong><small>{businessDate(k.previous.start)} — {businessDate(k.previous.end)}</small></div></div>
          {k.comparison_reason ? <p className="notice">{k.comparison_reason}</p> : <div className="comparison-result"><span className={Number(k.variation_pct) < 0 ? 'negative' : 'positive'}>{Number(k.variation_pct) >= 0 ? '↗' : '↘'} {number(k.variation_pct, 2)}%</span><p>Mismo número de días, con los mismos filtros dimensionales.</p></div>}
        </section>
        <section className="panel"><div className="panel-heading"><div><p className="eyebrow">CLIENTES</p><h2>Ventas por categoría</h2></div></div>
          <div className="category-list">{categories.map((row, index) => <button key={row.id} data-category-drill={row.id} onClick={() => drill('category', row.id)}><span className="category-rank">{String(index + 1).padStart(2, '0')}</span><span className="category-info"><span>{row.label}</span><span className="category-track"><span style={{width: `${categories[0].sales > 0 ? row.sales / categories[0].sales * 100 : 0}%`}}/></span></span><strong>{money(row.sales)}</strong><span aria-hidden="true">→</span></button>)}</div>
        </section>
      </div>
    </>}
    <details className="definitions"><summary>Definiciones de los indicadores y límites del análisis</summary><div><p>Ventas = cantidad × precio facturado = importe extendido − impuesto. Unidades = suma de cantidades. Facturas = documentos distintos dentro del filtro; no sumar subtotales por producto. Ticket = ventas ÷ facturas. Variación = (ventas actuales ÷ anteriores − 1) × 100.</p><p>La referencia usa el mismo número de días inmediatamente anteriores. No se calcula variación cuando falta cobertura o la base es cero. No se observan notas de crédito en la muestra. La clasificación del cliente conserva la versión observada al ingresar el hecho; no reconstruye su categoría original de 2013–2016.</p></div></details>
  </>;
}
