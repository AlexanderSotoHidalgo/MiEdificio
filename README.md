# MiEdificio

MVP de gestión y cobranza recurrente para condominios peruanos de 20 a 150 unidades. Es un monolito modular: FastAPI, React, PostgreSQL y almacenamiento local o MinIO, sin microservicios ni procesos distribuidos.

## Inicio rápido

Requisitos: Docker Desktop con Compose v2.

```powershell
Copy-Item .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev up --build --wait
```

- Aplicación: http://localhost:5173
- OpenAPI: http://localhost:8000/docs
- Mailpit: http://localhost:8025
- Salud: http://localhost:8000/health/ready

Datos demo:

| Perfil | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@miedificio.pe` | `Admin123!` |
| Residente | `residente@miedificio.pe` | `Residente123!` |

El seed crea un edificio, 20 unidades, cinco residentes, cuatro conceptos, tres periodos y pagos aprobados, en revisión y observados. Es idempotente.

La migración `0001_initial` reemplaza el esquema del prototipo previo. Si ya se ejecutó aquella versión local de `0001_initial`, respalde los datos y reinicie una sola vez los volúmenes de desarrollo:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev down --volumes
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev up --build --wait
```

No use `--volumes` en un entorno con información que deba conservarse.

## Arquitectura

```text
React/Vite ── HTTPS/JWT ── FastAPI ── PostgreSQL
                              │
                              ├── StorageBackend ── Local / MinIO
                              └── SMTP ──────────── Mailpit / proveedor
```

Los módulos backend se encuentran en `backend/app/modules`: `auth`, `buildings`, `units`, `fees`, `payments`, `reports`, `notifications` y `storage`. Las rutas solo traducen HTTP; reglas, bloqueos y transacciones viven en servicios de dominio.

El frontend está organizado por `features`: autenticación, estado de cuenta, reporte de pagos y conciliación. `src/api/generated` se regenera desde OpenAPI y MSW permite trabajar sin backend.

## Flujo funcional

1. El administrador invita residentes y registra o importa unidades.
2. Genera cuotas por monto fijo o coeficiente. La clave `(unit_id, period, concept_id)` evita duplicados.
3. El residente solo consulta cuotas de unidades vinculadas vigentes.
4. Reporta un pago parcial o multicuota con `Idempotency-Key` y comprobante privado.
5. El saldo permanece igual mientras el reporte está en revisión; el monto queda reservado para impedir sobrerreportes.
6. El administrador visualiza el comprobante mediante un endpoint autenticado y aprueba u observa.
7. La aprobación bloquea reporte y cuotas, aplica asignaciones una sola vez, registra auditoría y emite un recibo correlativo PDF.

El saldo nunca se almacena: `importe - SUM(asignaciones de reportes aprobados)`.

## API principal

| Método y ruta | Acceso | Propósito |
|---|---|---|
| `POST /api/v1/auth/login` | Público | Access token corto y refresh token rotativo |
| `POST /api/v1/auth/invitations` | Administrador | Invitación de un solo uso |
| `POST /api/v1/auth/password/forgot` | Público | Recuperación sin enumerar usuarios |
| `POST /api/v1/units/import` | Administrador | CSV con errores por fila |
| `POST /api/v1/fees/batch` | Administrador | Generación idempotente por lote |
| `GET /api/v1/fees/my-account` | Residente | Estado de cuenta protegido contra IDOR |
| `POST /api/v1/payments/report` | Residente | Reporte multipart parcial/multicuota |
| `GET /api/v1/payments` | Administrador | Bandeja con filtros |
| `GET /api/v1/payments/{id}/receipt` | Titular/Admin | Streaming privado del comprobante |
| `POST /api/v1/payments/{id}/review` | Administrador | Conciliación transaccional |
| `GET /api/v1/reports/my-account.pdf` | Residente | Estado de cuenta PDF |
| `GET /api/v1/reports/delinquency.csv` | Administrador | Exportación de morosidad |

## Calidad

Backend dentro del contenedor:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev exec backend python -m pytest -q
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev exec backend ruff check app tests
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev exec backend mypy app
```

Frontend:

```powershell
Set-Location frontend
npm ci
npm run lint
npm run typecheck
npm run build
```

Para regenerar el contrato con la API ejecutándose:

```powershell
Set-Location frontend
npm run generate:api
```

## Producción

Configure contraseñas aleatorias, `JWT_SECRET`, dominio, CORS y SMTP en `.env`. Desactive el seed:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod up -d --build
```

Caddy publica 80/443 y gestiona TLS. PostgreSQL, FastAPI y Nginx no exponen puertos al host. Las migraciones se ejecutan una vez al iniciar el contenedor backend; el MVP de producción utiliza una sola réplica.

Administrador inicial sin datos demo:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod exec backend python -m app.cli create-admin
```

## Operación y documentación

- Backup manual: `./scripts/backup.ps1` o `./scripts/backup.sh`.
- [Plan de dos sprints](docs/SPRINT_PLAN.md)
- [Roadmap post-piloto](docs/ROADMAP.md)
- Términos y política de privacidad: `frontend/public`.

Los comprobantes jamás se sirven desde `/uploads`; siempre pasan por autorización de edificio, rol y propietario.
