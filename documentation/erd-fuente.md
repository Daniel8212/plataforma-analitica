# ERD de fuente — relaciones del catálogo real

![alt text](<ERD -  DIAGRAM.png>)

La exportación PNG conserva el dibujo inicial. La fuente editable corregida está en
[diagramas/erd-fuente.mmd](diagramas/erd-fuente.mmd): las ocho FK mostradas son NOT NULL,
por lo que cada hijo tiene exactamente un padre (`||`), y un padre puede tener cero
o muchos hijos (`o{`). La opcionalidad del extremo padre del PNG inicial no representa
el catálogo físico. Véase [revisión de diagramas](revision-diagramas.md).
Se muestran las tablas del alcance inspeccionado; relaciones externas quedan en source-profile.json.
