// Prueba real en Chrome instalado, perfil separado; no requiere paquetes adicionales.
import { spawn } from 'node:child_process';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const root = process.cwd();
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const profile = path.join(root, 'data', `browser-smoke-${Date.now()}`);
await mkdir(profile, {recursive: true});
const browser = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'
], {windowsHide: true, stdio: 'ignore'});
let socket;
try {
  let port;
  for (let i=0; i<100; i++) {
    try { port = (await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; break; }
    catch { await delay(100); }
  }
  if (!port) throw new Error('Chrome no abrió DevTools en el perfil de prueba');
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = pages.find(item => item.type === 'page');
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {socket.onopen=resolve; socket.onerror=reject;});
  let id=0;
  const pending = new Map();
  socket.onmessage = ({data}) => {
    const msg=JSON.parse(data); const job=pending.get(msg.id);
    if (job) {pending.delete(msg.id); msg.error ? job.reject(new Error(msg.error.message)) : job.resolve(msg.result);}
  };
  const call = (method, params={}) => new Promise((resolve,reject) => {
    const commandId=++id; pending.set(commandId,{resolve,reject});
    socket.send(JSON.stringify({id:commandId,method,params}));
    setTimeout(() => {if (pending.delete(commandId)) reject(new Error(`Timeout en ${method}`));},15000).unref();
  });
  const evaluate = async expression => (await call('Runtime.evaluate', {expression,returnByValue:true})).result.value;
  await call('Emulation.setDeviceMetricsOverride', {width:1280,height:850,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:'http://127.0.0.1:5173/'});
  for (let i=0;i<100;i++) {if (await evaluate('!!document.querySelector("input")')) break; await delay(100);}
  const env=await readFile(path.join(root,'.env'),'utf8');
  const key=env.match(/^DEMO_API_KEY=(.+)$/m)?.[1].trim();
  if (!key) throw new Error('Falta clave demo local');
  await evaluate('document.querySelector("input").focus()');
  await call('Input.insertText',{text:key});
  await evaluate('document.querySelector("button").click()');
  let text;
  for (let i=0;i<150;i++) {
    text=await evaluate('document.querySelector("article")?.innerText ?? null');
    if (text) break;
    const error=await evaluate('document.querySelector("[role=alert]")?.innerText ?? null');
    if (error) throw new Error(error);
    await delay(100);
  }
  if (!text) throw new Error('No apareció un KPI real');
  const response=await fetch('http://127.0.0.1:5173/api/kpis',{headers:{'X-API-Key':key}});
  if (!response.ok) throw new Error(`API vía proxy: ${response.status}`);
  const kpi=await response.json();
  const formatted=new Intl.NumberFormat('es-HN',{maximumFractionDigits:2,minimumFractionDigits:2}).format(Number(kpi.sales));
  if (!text.includes(formatted)) throw new Error('El importe renderizado no coincide con API');
  const evidence=path.join(root,'documentation','evidence');
  await mkdir(evidence,{recursive:true});
  const screenshot=await call('Page.captureScreenshot',{format:'png'});
  await writeFile(path.join(evidence,'day1-dashboard.png'),Buffer.from(screenshot.data,'base64'));
  await writeFile(path.join(evidence,'browser-smoke.json'),JSON.stringify({status:'passed',url:'http://127.0.0.1:5173/',kpi,rendered_text:text},null,2));
  console.log('KPI visible y coincidente con API. Captura guardada.');
} finally {
  socket?.close();
  browser.kill();
}
