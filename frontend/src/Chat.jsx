import React,{useState,useEffect,useRef} from 'react';
import {request} from './api.js';
import {money,number,businessDate,timestamp} from './format.js';

function value(fact){
 if(fact.unit==='formula')return fact.value;
 if(fact.unit==='porcentaje')return number(fact.value,2)+'%';
 if(fact.unit==='unidades'||fact.unit==='facturas')return number(fact.value);
 return money(fact.value);
}

export default function Chat({apiKey}){
 const [question,setQuestion]=useState('');
 const [messages,setMessages]=useState([]);
 const [pending,setPending]=useState(false);
 const [error,setError]=useState('');
 const controller=useRef(null);
 useEffect(()=>()=>controller.current?.abort(),[]);
 async function send(text=question){
  const input=text.trim();if(!input||pending)return;
  setMessages(old=>[...old,{role:'user',text:input}]);setQuestion('');setError('');setPending(true);
  controller.current=new AbortController();
  try{
   const result=await request('chat',apiKey,controller.current.signal,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:input})});
   setMessages(old=>[...old,{role:'assistant',result}]);
  }catch(err){if(!controller.current.signal.aborted)setError(err.name==='TimeoutError'?'El modelo local tardó demasiado. Reintenta una pregunta breve.':err.message);}
  finally{setPending(false);}
 }
 const examples=['¿Cuáles fueron las ventas de marzo de 2016?','Compara ventas del 2016-03-01 al 2016-05-31','¿Qué productos tuvieron más ventas en mayo de 2016?','¿Qué pronóstico hay para las próximas semanas?'];
 return <section className="panel chat-panel" data-testid="chat-panel">
  <div className="panel-heading"><div><p className="eyebrow">PREGUNTA CON RESPALDO</p><h2>Asistente analítico</h2></div><span className="status-badge running">Ollama local · Qwen2.5 1.5B</span></div>
  <p className="chat-scope">Consultas globales sobre la muestra 2013–2016. Las referencias relativas usan la última fecha cargada. Las cifras y períodos proceden de herramientas controladas; el modelo redacta la interpretación.</p>
  {!messages.length&&<div className="chat-examples">{examples.map(text=><button key={text} disabled={pending} onClick={()=>send(text)}>{text}<span aria-hidden="true">↗</span></button>)}</div>}
  <div className="chat-messages" aria-live="polite">{messages.map((message,index)=>message.role==='user'?<div className="chat-question" key={index}><span className="eyebrow">TU PREGUNTA</span><p>{message.text}</p></div>:<article className="chat-response" key={index} data-chat-response={message.result.status}><div className="chat-response-head"><span className="eyebrow">{message.result.generated?'INTERPRETACIÓN GENERADA':message.result.status==='grounded_fallback'?'EXPLICACIÓN BLOQUEADA':'ALCANCE DE LOS DATOS'}</span><span>{message.result.duration_ms/1000} s</span></div><p>{message.result.answer}</p>
   {message.result.forecast_as_of&&<p className="notice">Predicción, no venta observada. Corte del modelo: {businessDate(message.result.forecast_as_of)}.</p>}
   {message.result.reference_period&&<p className="chat-context">Referencia comparable: {businessDate(message.result.reference_period.start)} — {businessDate(message.result.reference_period.end)}.</p>}
   {!!message.result.facts.length&&<div className="table-scroll chat-facts"><table><thead><tr><th>Respaldo consultado</th><th>Período</th><th className="numeric">Resultado</th></tr></thead><tbody>{message.result.facts.map(fact=><tr key={fact.id}><td>{fact.label}<small>{fact.unit==='prediccion_moneda_origen'?'Predicción versionada':'Data Warehouse'}</small></td><td>{fact.period?`${businessDate(fact.period.start)} — ${businessDate(fact.period.end)}`:'Definición documentada'}</td><td className="numeric emphasis">{value(fact)}</td></tr>)}</tbody></table></div>}
   <div className="chat-provenance"><span>Datos actualizados: {timestamp(message.result.dataset.loaded_at)} · Tegucigalpa</span><code title={message.result.dataset.execution_id||''}>Carga: {message.result.dataset.execution_id?.slice(0,8)||'Sin carga'}…</code></div>
   {message.result.generated&&<p className="chart-note">La interpretación no establece causas. Las cifras de la tabla se consultaron sin delegar cálculos ni SQL al modelo.</p>}
  </article>)}</div>
  {pending&&<div className="loading" role="status"><span className="spinner"/>Consultando datos y generando una respuesta local…</div>}
  {error&&<div className="error-box" role="alert">{error}</div>}
  <form className="chat-form" id="chat-form" onSubmit={event=>{event.preventDefault();send();}}><label htmlFor="chat-question">Tu pregunta<textarea id="chat-question" rows={3} maxLength={500} disabled={pending} value={question} onChange={event=>setQuestion(event.target.value)} placeholder="Ejemplo: ¿Ventas del último trimestre completo?"/></label><div><span>{question.length}/500 · Máximo doce preguntas por minuto</span><button type="submit" className="action primary" disabled={pending||question.trim().length<3}>{pending?'Consultando…':'Consultar →'}</button></div></form>
 </section>;
}
