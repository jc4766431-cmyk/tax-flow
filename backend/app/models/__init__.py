"""
Import every model module here so that Base.metadata is fully populated
for Alembic autogenerate and for mapper configuration at app startup.
"""
from app.models.user import Firm, User, UserRole  # noqa: F401
from app.models.client import Client  # noqa: F401
from app.models.document import (  # noqa: F401
    CHECKLIST_CATEGORIES,
    ChecklistItem,
    Document,
    DocumentCategory,
    DocumentStatus,
)
from app.models.filing import (  # noqa: F401
    FilingRequest,
    FilingStage,
    FilingStageEvent,
    FilingType,
)
from app.models.workflow import (  # noqa: F401
    AuditLog,
    Message,
    Notification,
    NotificationType,
    Reminder,
    ReminderChannel,
    Task,
    TaskStatus,
)
from app.models.whatsapp import (  # noqa: F401
    WhatsAppInboundMessage,
    WhatsAppMessageType,
    WhatsAppProcessingStatus,
)
from app.models.billing import (  # noqa: F401
    BillingPeriod,
    Plan,
    PlanTier,
    Subscription,
    SubscriptionStatus,
)
from app.models.invoice import Invoice, InvoiceStatus  # noqa: F401
from app.models.system_state import SystemState  # noqa: F401
