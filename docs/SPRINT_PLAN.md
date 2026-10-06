# Plan de trabajo del MVP

Calendario propuesto: sprint 1 del 5 al 16 de octubre de 2026, sprint 2 del 19 al 30 de octubre y piloto presencial el lunes 2 de noviembre de 2026. Se trabaja sobre `main` con ramas de vida menor a un día, PR pequeños y revisión cruzada obligatoria.

## Sprint 1 — Identidad, padrón y cuotas

| Día | Integrante 1 — Backend/DevOps | Integrante 2 — Frontend/UX/Integración | Dependencia o hito |
|---|---|---|---|
| 1 | Compose, PostgreSQL, Alembic y configuración por entorno | Vite, Tailwind, shell mobile-first y estados comunes | Entorno reproducible |
| 2 | Role, User, Building, JWT corto y refresh | Login, sesión e interceptor 401/403 | OpenAPI de autenticación publicado |
| 3 | Invitaciones, recuperación y rate limit | Alta por invitación y recuperación | SMTP/Mailpit disponible |
| 4 | Unit, UnitResident y autorización por edificio | Listado y formulario de unidades | Usuarios y edificio sembrados |
| 5 | Importación CSV con errores por fila | UI de carga y reporte de errores | **Congelación parcial del contrato OpenAPI** |
| 6 | FeeConcept y MaintenanceFee | Tipos/hook generados y MSW actualizado | Modelos estables |
| 7 | Generación fija/coeficiente, unicidad y auditoría | Estado de cuenta responsive | Contrato de cuotas estable |
| 8 | Consulta con protección IDOR y saldo derivado | Estados vacío/carga/error y badges | Prueba de aislamiento aprobada |
| 9 | PDF de estado de cuenta y reportes base | Descarga PDF y pruebas de accesibilidad | Historia HU01 completa |
| 10 | Migración desde cero, hardening y demo | Regresión móvil y guion de demo | Release `pilot-s1` |

Definición de hecho de HU01: un residente autenticado solo puede consultar unidades vigentes vinculadas a él; ve importe, pagos aprobados, saldo derivado y estado; descarga el PDF; existen pruebas de IDOR y estados de interfaz.

## Sprint 2 — Reporte y conciliación

| Día | Integrante 1 — Backend/DevOps | Integrante 2 — Frontend/UX/Integración | Dependencia o hito |
|---|---|---|---|
| 1 | PaymentReport, Allocation, AuditLog, Receipt y storage | Modal RHF/Zod y selección multicuota | Esquema de pagos migrado |
| 2 | Validación magic bytes, hash y duplicados | Captura móvil, compresión y previsualización | Política de archivos acordada |
| 3 | Idempotency-Key y validación de saldo reservado | Multipart, feedback y reintento seguro | HU02 integrada |
| 4 | Bandeja filtrable y streaming autorizado | Tabla admin, filtros y contador | Datos MSW realistas |
| 5 | Revisión transaccional con `FOR UPDATE` | Visor PDF/imagen con zoom | **Contrato OpenAPI final del piloto** |
| 6 | Aprobación, recálculo único y recibo correlativo | Aprobar/observar con confirmaciones | Conciliación extremo a extremo |
| 7 | Observación, reenvío y emails | Motivo visible al residente | HU03 completa |
| 8 | Reportes de morosidad, resumen y CSV | Resumen financiero y refinamiento móvil | Métricas verificables |
| 9 | Pruebas concurrentes, backups, Caddy y logs JSON | Pruebas de integración y accesibilidad | Checklist de seguridad |
| 10 | Ensayo con copia de producción y soporte | Prueba de aceptación con administrador | Release `pilot-mvp` |

Definición de hecho de HU02: archivo válido de hasta 5 MB, hash y nombre seguro; monto parcial o multicuota no supera el saldo libre; doble envío es idempotente; el saldo no disminuye mientras está en revisión.

Definición de hecho de HU03: solo un administrador del mismo edificio revisa; aprobación concurrente aplica una vez; la auditoría conserva estado anterior/nuevo y monto; observar exige motivo; el recibo correlativo se genera al aprobar y se notifica al residente.

## Ritmo de coordinación

- Sincronización diaria de 15 minutos y revisión del tablero después del almuerzo.
- PR máximo recomendado: 300 líneas netas o un día de trabajo.
- Quien modifica un contrato actualiza OpenAPI, tipos generados, MSW y ejemplo HTTP en el mismo PR.
- No se fusiona si fallan migración desde cero, pytest, Ruff, mypy, ESLint, TypeScript o build.
- El 30 de octubre se congela funcionalidad; el fin de semana queda reservado para preparar datos y respaldo, no para añadir alcance.
