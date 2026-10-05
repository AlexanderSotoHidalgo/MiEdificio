# MiEdificio MVP

MVP de gestión y cobranza recurrente para condominios pequeños. Es un monorepo deliberadamente simple para un equipo de dos personas: API FastAPI, SPA React y PostgreSQL, sin microservicios ni infraestructura innecesaria.

## Arquitectura

```text
React + TanStack Query
        │ HTTPS / JWT
        ▼
FastAPI ───────► volumen /data/uploads (comprobantes)
        │
        ▼
PostgreSQL (datos, restricciones y auditoría)
```

- `frontend/`: React, Vite, TypeScript, Tailwind y Axios.
- `backend/app/api/routes/`: rutas separadas por dominio (`auth`, `residents`, `units`, `fees`, `payments`).
- `backend/app/models/`: modelo relacional SQLAlchemy.
- `backend/alembic/`: migraciones versionadas.
- `docker-compose.yml`: PostgreSQL, API, SPA/Nginx, red y volúmenes persistentes.

Para el MVP se eligió un volumen Docker para comprobantes. La base guarda solamente un nombre interno aleatorio; migrar a MinIO después requiere sustituir el adaptador de almacenamiento en `payments.py`, sin cambiar el contrato HTTP ni el modelo funcional.

## Inicio rápido

Requisitos: Docker Desktop con el motor Linux activo y Docker Compose v2.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Servicios:

- Aplicación: http://localhost:8080
- API y OpenAPI: http://localhost:8000/docs
- Salud: http://localhost:8000/health

Con `SEED_DEMO_DATA=true` se crean datos idempotentes:

| Perfil | Correo | Contraseña |
|---|---|---|
| Residente | `residente@miedificio.pe` | `Residente123!` |
| Administrador | `admin@miedificio.pe` | `Admin123!` |

Estas credenciales son exclusivamente locales. Antes de desplegar, cambie `JWT_SECRET`, desactive `SEED_DEMO_DATA` y gestione secretos fuera del repositorio.

Para detener sin perder datos:

```powershell
docker compose down
```

`docker compose down -v` elimina también base y comprobantes; úselo solo para reiniciar deliberadamente el ambiente local.

## Flujo funcional

1. El administrador crea residentes y unidades, y vincula cada unidad a un residente.
2. Genera las cuotas de un período en lote. `uq_fee_unit_period` impide duplicar una cuota aun con peticiones concurrentes.
3. El residente consulta únicamente cuotas cuyas unidades le pertenecen.
4. Reporta un pago con PDF/JPG/PNG/WEBP. El archivo se limita a 8 MB, se valida por firma y se almacena con UUID.
5. La cuota cambia a `Pago en revisión`; el saldo todavía no cambia.
6. El administrador aprueba u observa. La revisión bloquea las filas del pago y de la cuota (`SELECT … FOR UPDATE`), registra una auditoría y confirma todo en una sola transacción.
7. Repetir la misma aprobación devuelve una respuesta idempotente; una decisión distinta devuelve `409` y nunca aplica el importe dos veces.

Estados:

```text
Cuota: Pendiente ──reporte──► Pago en revisión ──aprobación total──► Pagada
                                  │                      └─parcial──► Pendiente
                                  └────observación─────────────────► Pendiente

Pago:  Pendiente ──► Aprobado | Observado
```

El motivo de observación es obligatorio y reaparece en `GET /fees/my-account` para el residente.

## Endpoints del MVP

Todos salvo login requieren `Authorization: Bearer <token>`.

| Método y ruta | Rol | Propósito |
|---|---|---|
| `POST /api/v1/auth/login` | Público | Obtener JWT con formulario OAuth2 (`username`, `password`). |
| `GET /api/v1/auth/me` | Ambos | Sesión actual. |
| `POST /api/v1/residents` | Administrador | Crear residente. |
| `GET /api/v1/residents` | Administrador | Listar residentes. |
| `POST /api/v1/units` | Administrador | Crear/vincular unidad. |
| `GET /api/v1/units` | Administrador | Listar unidades. |
| `POST /api/v1/fees/batch` | Administrador | Crear cuotas para todas las unidades, omitiendo duplicadas. |
| `GET /api/v1/fees/my-account` | Residente | Estado de cuenta limitado a sus unidades. |
| `POST /api/v1/payments/report` | Residente | Reportar pago con `multipart/form-data`. |
| `GET /api/v1/payments/pending` | Administrador | Bandeja por verificar. |
| `GET /api/v1/payments/{id}/receipt` | Dueño/Admin | Visualizar comprobante protegido. |
| `POST /api/v1/payments/{id}/review` | Administrador | Aprobar u observar atómicamente. |

Ejemplo de revisión:

```json
{ "action": "approve" }
```

```json
{ "action": "observe", "reason": "El monto no coincide con la operación bancaria." }
```

## Decisiones y controles importantes

- Importes con `Numeric(12,2)` / `Decimal`; nunca `float`.
- Contraseñas con Argon2 y JWT con expiración configurable.
- RBAC centralizado en dependencias FastAPI; no se confía en el rol del frontend.
- Propiedad de unidad comprobada dentro de la consulta SQL de cuotas y reportes.
- Restricciones `CHECK`, claves foráneas y unicidad resguardan invariantes aunque se omita la API.
- El comprobante no usa el nombre proporcionado por el usuario como ruta y no se expone como archivo estático público.
- Aprobación con bloqueo de fila, transacción, rollback e historial inmutable con administrador y fecha/hora.
- CORS explícito por entorno. Para producción, use TLS, antivirus/escaneo de objetos, rate limiting y almacenamiento privado tipo S3/MinIO.

## Verificación

Frontend:

```powershell
Set-Location frontend
npm install
npm run typecheck
npm run build
npm audit --audit-level=high
```

Contenedores/API:

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs backend
Invoke-RestMethod http://localhost:8000/health
```

La migración y los datos demo se ejecutan automáticamente antes de Uvicorn. Un smoke test manual completo consiste en: iniciar como residente, reportar el pago de la cuota demo, cerrar sesión, iniciar como administrador, abrir el comprobante y aprobarlo; al volver al residente, la cuota debe figurar `Pagada` y saldo `S/ 0.00`.

## Plan exacto para dos sprints

Cada sprint dura 10 días hábiles. Ambos integrantes revisan los PR del otro; límite recomendado: un día de trabajo por PR.

### Sprint 1 — Identidad, padrón y cuotas

Objetivo demostrable: el residente inicia sesión y consulta cuotas reales de sus unidades.

| Días | Integrante 1 — Backend / DevOps / Docker | Integrante 2 — Frontend / UX / API |
|---|---|---|
| 1 | Compose, PostgreSQL, FastAPI, Alembic, `.env.example`. | Vite/TypeScript/Tailwind, tokens visuales y shell responsive. |
| 2–3 | Tablas Role, User y Unit; seed; Argon2/JWT y dependencias RBAC. | Login, persistencia de sesión, interceptor JWT, manejo uniforme de errores. |
| 4–5 | CRUD mínimo de residentes/unidades y validaciones de propiedad. | Tipos API, navegación por rol y estados loading/empty/error. |
| 6–7 | MaintenanceFee, unicidad unidad/período y `POST /fees/batch`. | Estado de cuenta: tabla responsive, totales y badges. |
| 8 | `GET /fees/my-account` con prueba de aislamiento entre residentes. | Integración del estado de cuenta y refinamiento móvil/accesibilidad. |
| 9 | Pruebas de permisos, migración desde cero y revisión de índices. | Pruebas de componentes y correcciones de integración. |
| 10 | Demo, correcciones críticas y documentación operativa. | Demo, correcciones UX y guion de validación con usuario. |

Criterio de salida: un usuario A nunca obtiene cuotas del usuario B; generar dos veces el período no duplica registros; el entorno se levanta con un comando.

### Sprint 2 — Reporte y conciliación

Objetivo demostrable: el pago viaja desde el residente hasta una conciliación auditable.

| Días | Integrante 1 — Backend / DevOps / Docker | Integrante 2 — Frontend / UX / API |
|---|---|---|
| 1–2 | PaymentReport/AuditLog, volumen persistente y política de archivos. | Modal de reporte, selección de cuota y validaciones de formulario/archivo. |
| 3–4 | `POST /payments/report`, control de propiedad, tamaño, firma y nombre seguro. | Integración multipart, progreso/feedback e invalidación de caché. |
| 5–6 | Bandeja pendiente, descarga autorizada y serialización de comprobantes. | Tabla administrativa, filtros y visualizador protegido del comprobante. |
| 7 | Revisión transaccional con bloqueos, rollback, auditoría e idempotencia. | Acciones aprobar/observar, confirmación y motivo obligatorio. |
| 8 | Pruebas de concurrencia, doble clic, pago parcial y observación. | Pruebas del flujo, estado actualizado y motivo visible al residente. |
| 9 | Hardening: límites, tipos MIME, CORS, logs y backup de volúmenes. | Accesibilidad, responsive, mensajes y regresión entre roles. |
| 10 | Smoke test desde base vacía, checklist de release y soporte de demo. | Prueba de aceptación, grabación/demo y registro de métricas de validación. |

Criterio de salida: aprobar dos veces no duplica el pago; observar exige y muestra motivo; ningún comprobante es accesible sin ser administrador o propietario; el flujo crítico se completa sin tocar la base manualmente.

## Próxima iteración recomendada

Medir durante la validación: porcentaje de reportes aprobados sin contacto adicional, tiempo medio hasta conciliación y causas de observación. No añadir notificaciones, pasarela de pagos ni contabilidad avanzada hasta confirmar que este flujo reduce el trabajo manual del administrador.
