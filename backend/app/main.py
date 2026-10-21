from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.access_logging import AuthenticatedAccessLogMiddleware
from app.security_headers import SecurityHeadersMiddleware
from app.routers import (
    access_logs,
    auth,
    client_portal,
    clients,
    communications,
    contracts,
    exceptions,
    health,
    imports,
    invoices,
    metrics,
    payability,
    payments,
    pilot,
    payers,
    workflows,
)


app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(AuthenticatedAccessLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health.router)
app.include_router(access_logs.router)
app.include_router(auth.router)
app.include_router(client_portal.router)
app.include_router(clients.router)
app.include_router(invoices.router)
app.include_router(metrics.router)
app.include_router(imports.router)
app.include_router(contracts.router)
app.include_router(workflows.router)
app.include_router(payers.router)
app.include_router(payability.router)
app.include_router(payments.router)
app.include_router(pilot.router)
app.include_router(communications.router)
app.include_router(exceptions.router)

