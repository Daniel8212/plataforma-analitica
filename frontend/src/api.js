export function query(filters, extra = {}) {
  return new URLSearchParams(Object.entries({...filters, ...extra}).filter(([, value]) => value !== '' && value != null)).toString();
}
export async function request(path, key, signal, init = {}) {
  const timeout = AbortSignal.timeout(path.split('?')[0] === 'chat' ? 90000 : 20000);
  const response = await fetch(`/api/${path}`, {...init, cache: 'no-store', headers: {...init.headers, 'X-API-Key': key}, signal: signal ? AbortSignal.any([signal, timeout]) : timeout});
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(response.status === 401 ? 'La clave de acceso no es válida.' : typeof payload.detail === 'string' ? payload.detail : 'No fue posible consultar los datos. Revisa los filtros e inténtalo otra vez.');
  return payload;
}
