from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, fees, payments, residents, units
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de gestión y cobranza recurrente para condominios pequeños.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(residents.router, prefix=settings.api_prefix)
app.include_router(units.router, prefix=settings.api_prefix)
app.include_router(fees.router, prefix=settings.api_prefix)
app.include_router(payments.router, prefix=settings.api_prefix)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}

