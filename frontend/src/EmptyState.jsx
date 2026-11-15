import React from 'react';
export default function Empty() { return <div className="empty-state" data-testid="empty-state"><span aria-hidden="true">∅</span><h3>No hay datos para estos filtros</h3><p>No hay ventas cargadas que coincidan con el período y las dimensiones seleccionadas.</p></div>; }
