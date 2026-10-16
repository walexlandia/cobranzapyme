from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.access_logging import AuthenticatedAccessLogMiddleware
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
    payability,
    payments,
    pilot,
    payers,
    workflows,
)


app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(AuthenticatedAccessLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(access_logs.router)
app.include_router(auth.router)
app.include_router(client_portal.router)
app.include_router(clients.router)
app.include_router(invoices.router)
app.include_router(imports.router)
app.include_router(contracts.router)
app.include_router(workflows.router)
app.include_router(payers.router)
app.include_router(payability.router)
app.include_router(payments.router)
app.include_router(pilot.router)
app.include_router(communications.router)
app.include_router(exceptions.router)

