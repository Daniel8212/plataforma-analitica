import React,{useState,useEffect} from 'react';
import {request} from './api.js';
import {money,number,businessDate,timestamp} from './format.js';

export default function Alerts({apiKey,revision}){
 const [data,setData]=useState(null),[error,setError]=useState(''),[refresh,setRefresh]=useState(0),[busy,setBusy]=useState(false);
 useEffect(()=>{
  const controller=new AbortController();setError('');
  request('alerts',apiKey,controller.signal).then(setData).catch(e=>{if(!controller.signal.aborted)setError(e.message);});
  return()=>controller.abort();
 },[apiKey,revision,refresh]);
 // Acknowledge only after React rendered the alert list. Failed acknowledgements remain pending.
 useEffect(()=>{
  if(!data)return;
  let active=true;
  Promise.all(data.items.filter(a=>a.DeliveryStatus==='PENDING').map(a=>request(`alerts/${a.AlertID}/seen`,apiKey,undefined,{method:'POST'})))
   .then(results=>{if(active&&results.length)setRefresh(n=>n+1);}).catch(()=>{if(active)setError('No se confirmó la entrega al panel. Pulsa Actualizar para reintentar.');});
  return()=>{active=false;};
 },[data,apiKey]);
 async function change(id,state){
  setBusy(true);setError('');
  try{await request(`alerts/${id}/state`,apiKey,undefined,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state})});setRefresh(n=>n+1);}
  catch(e){setError(e.message);}finally{setBusy(false);}
 }
 return <div data-testid="alerts-panel">
  <section className="panel"><p className="eyebrow">REGLA AUTOMÁTICA TRAS CARGA EXITOSA</p><h2>Caída semanal de ventas</h2>
   <p className="subtle">Más del 15 % frente a la semana completa anterior. Semanas de lunes a domingo, ancladas a la última fecha del DW; se excluyen semanas parciales. Importes sin impuestos.</p>
   {error&&<div className="error-box" role="alert">{error}<button className="action secondary" onClick={()=>setRefresh(n=>n+1)}>Reintentar</button></div>}
   {!data&&!error&&<p role="status">Consultando evaluaciones…</p>}
   {data&&!data.items.length&&<p className="notice">No hay alertas registradas. Consulta las evaluaciones: una condición falsa también queda documentada.</p>}
  </section>
  {data?.items.map(a=><article key={a.AlertID} className="panel alert-card" data-alert-id={a.AlertID}>
   <div className="panel-heading"><div><p className="eyebrow">{a.IsSimulated?'SIMULACIÓN EXPLÍCITA · NO SON VENTAS DEL DW':'EVENTO RESPALDADO POR EL DW'}</p><h2>Caída del {number(a.DropPercent,2)} %</h2></div><span className={`status-badge ${a.IsSimulated?'running':'failed'}`}>{a.IsSimulated?'SIMULACIÓN':a.Severity}</span></div>
   <div className="alert-values"><div><span>Semana evaluada</span><strong>{money(a.ObservedValue)}</strong><p>{businessDate(a.CurrentStart)} — {businessDate(a.CurrentEnd)}</p></div><div><span>Referencia comparable</span><strong>{money(a.ReferenceValue)}</strong><p>{businessDate(a.ReferenceStart)} — {businessDate(a.ReferenceEnd)}</p></div><div><span>Umbral / estado</span><strong>{number(a.ThresholdPercent)} % · {a.State}</strong><p>Entrega: {a.DeliveryStatus==='DELIVERED'?'confirmada en panel':'pendiente'}</p></div></div>
   {a.IsSimulated&&<p className="notice">Valor evaluado sintetizado para demostrar la regla. La fuente operacional y las ventas del DW no fueron modificadas.</p>}
   <p>{a.Explanation}</p><details><summary>Origen y trazabilidad</summary><p>Regla {a.RuleName} · {a.Origin}</p><p>Creada {timestamp(a.CreatedAt)} · última evaluación {timestamp(a.UpdatedAt)}</p><code>{a.AlertID}</code><p>Carga: <code>{a.SourceExecutionID}</code></p></details>
   <div className="alert-actions"><button className="action secondary" disabled={busy||a.State==='RESOLVED'||a.State==='ATTENDED'} onClick={()=>change(a.AlertID,'ATTENDED')}>Marcar atendida</button><button className="action secondary" disabled={busy||a.State==='RESOLVED'||a.State==='DISCARDED'} onClick={()=>change(a.AlertID,'DISCARDED')}>Descartar</button></div>
  </article>)}
  {!!data?.tasks.length&&<section className="panel"><div className="panel-heading"><div><p className="eyebrow">TRAZABILIDAD Y RECUPERACIÓN</p><h2>Evaluaciones recientes</h2></div></div><div className="table-scroll"><table><thead><tr><th>Fecha / carga</th><th>Regla</th><th>Procesamiento</th><th>Resultado</th><th>Intentos / diagnóstico</th></tr></thead><tbody>{data.tasks.map(t=><tr key={t.TaskID}><td>{timestamp(t.CreatedAt)}<small>{t.ExecutionID.slice(0,8)}{t.IsSimulated?' · SIMULACIÓN':''}</small></td><td>{t.RuleName}</td><td>{t.Status}</td><td>{t.Outcome||'Pendiente'}<small>{t.Explanation}</small></td><td>{t.Attempts}<small>{t.LastError}</small></td></tr>)}</tbody></table></div></section>}
 </div>;
}
