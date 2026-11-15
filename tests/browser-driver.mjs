import {spawn} from 'node:child_process';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
export const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));

export async function withBrowser(task) {
  const profile=path.join(process.cwd(),'data',`dashboard-browser-${Date.now()}`);
  await mkdir(profile,{recursive:true});
  const browser=spawn(process.env.CHROME_BIN || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',[
    '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
    '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'
  ],{windowsHide:true,stdio:'ignore'});
  let socket,call;
  try {
    let port;
    for(let i=0;i<100;i++) {try {port=(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await delay(100);}}
    if(!port) throw new Error('Chrome no inició con el perfil aislado');
    const pages=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket=new WebSocket(pages.find(row=>row.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
    const pending=new Map(),errors=[];
    let id=0;
    socket.onmessage=({data})=>{
      const message=JSON.parse(data),job=pending.get(message.id);
      if(job){pending.delete(message.id);message.error?job.reject(new Error(message.error.message)):job.resolve(message.result);}
      if(message.method==='Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
    };
    call=(method,params={})=>new Promise((resolve,reject)=>{
      const command=++id;pending.set(command,{resolve,reject});socket.send(JSON.stringify({id:command,method,params}));
      setTimeout(()=>{if(pending.delete(command))reject(new Error(`Timeout: ${method}`));},20000).unref();
    });
    const evaluate=async expression=>{
      const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
      if(result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || 'Error de evaluación de prueba');
      return result.result.value;
    };
    const wait=async(expression,label)=>{
      for(let i=0;i<200;i++){if(await evaluate(expression))return;await delay(100);}
      throw new Error(`No se cumplió: ${label}`);
    };
    const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
    const setValue=async(selector,value)=>{
      await evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});const setter=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value').set;setter.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));})()`);
      await delay(50);
    };
    const screenshot=async(name,full=true)=>{
      await delay(250);
      const params={format:'png',captureBeyondViewport:true};
      if(full){const metrics=await call('Page.getLayoutMetrics');params.clip={x:0,y:0,width:metrics.cssContentSize.width,height:metrics.cssContentSize.height,scale:1};}
      const result=await call('Page.captureScreenshot',params);
      await writeFile(path.join(process.cwd(),'documentation/evidence',name),Buffer.from(result.data,'base64'));
    };
    await call('Runtime.enable');await call('Page.enable');
    return await task({call,evaluate,wait,click,setValue,screenshot,errors});
  } finally {
    try {if(call)await call('Browser.close');}catch{}
    socket?.close();browser.kill();
  }
}
