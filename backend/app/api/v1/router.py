from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    automation,
    billing,
    clients,
    dashboard,
    documents,
    filings,
    firms,
    invoices,
    messages,
    notifications,
    reports,
    tasks,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(firms.router)
api_router.include_router(clients.router)
api_router.include_router(filings.router)
api_router.include_router(dashboard.router)
api_router.include_router(documents.router)
api_router.include_router(tasks.router)
api_router.include_router(whatsapp.router)
api_router.include_router(billing.router)
api_router.include_router(invoices.router)
api_router.include_router(notifications.router)
api_router.include_router(messages.router)
api_router.include_router(automation.router)
api_router.include_router(reports.router)
