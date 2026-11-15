export const number = (value, digits = 0) => new Intl.NumberFormat('es-HN', {minimumFractionDigits: digits, maximumFractionDigits: digits}).format(Number(value));
export const money = value => number(value, 2);
export const compact = value => new Intl.NumberFormat('es-HN', {notation: 'compact', maximumFractionDigits: 1}).format(Number(value));
export const businessDate = value => value ? new Intl.DateTimeFormat('es-HN', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'}).format(new Date(`${value}T00:00:00Z`)) : 'Sin cobertura';
export const timestamp = value => value ? new Intl.DateTimeFormat('es-HN', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Tegucigalpa'}).format(new Date(value)) : 'Sin carga exitosa';
export const shortDate = value => new Intl.DateTimeFormat('es-HN', {day: 'numeric', month: 'short', timeZone: 'UTC'}).format(new Date(`${value}T00:00:00Z`));
