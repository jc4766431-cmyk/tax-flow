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
    internal,
    invites,
    invoices,
    messages,
    notifications,
    razorpay_webhook,
    reports,
    tasks,
    users,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(internal.router)
api_router.include_router(razorpay_webhook.router)
api_router.include_router(firms.router)
api_router.include_router(clients.router)
api_router.include_router(filings.router)
api_router.include_router(dashboard.router)
api_router.include_router(documents.router)
api_router.include_router(tasks.router)
api_router.include_router(whatsapp.router)
api_router.include_router(billing.router)
api_router.include_router(invoices.router)
api_router.include_router(invites.router)
api_router.include_router(users.router)
api_router.include_router(notifications.router)
api_router.include_router(messages.router)
api_router.include_router(automation.router)
api_router.include_router(reports.router)
