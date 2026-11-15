# ERD de fuente — relaciones del catálogo real

```mermaid
erDiagram
  Sales_Customers |o--o{ Sales_Customers : BillToCustomerID
  Sales_CustomerCategories |o--o{ Sales_Customers : CustomerCategoryID
  Sales_Invoices |o--o{ Sales_InvoiceLines : InvoiceID
  Warehouse_StockItems |o--o{ Sales_InvoiceLines : StockItemID
  Sales_Customers |o--o{ Sales_Invoices : BillToCustomerID
  Sales_Customers |o--o{ Sales_Invoices : CustomerID
  Warehouse_StockGroups |o--o{ Warehouse_StockItemStockGroups : StockGroupID
  Warehouse_StockItems |o--o{ Warehouse_StockItemStockGroups : StockItemID
```

El marcador 0/1 representa opcionalidad conservadora; consultar nullable y FK en el diccionario.
Se muestran las tablas del alcance inspeccionado; relaciones externas quedan en source-profile.json.
