from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.db.session import get_db
from app.models.client import Client
from app.models.filing import FilingRequest, FilingStage, FilingStageEvent
from app.models.user import User, UserRole
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.report import (
    MonthlyFilingsPoint,
    ReportsSummary,
    StaffProductivityRow,
    TurnaroundStats,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _firm_scoped_filing_ids(db: Session, current_user: User):
    """Returns a scalar subquery of filing_request ids visible to current_user's firm,
    or None if the caller is a SUPER_ADMIN (unscoped)."""
    if current_user.role == UserRole.SUPER_ADMIN:
        return None
    return (
        select(FilingRequest.id)
        .join(Client, Client.id == FilingRequest.client_id)
        .where(Client.firm_id == current_user.firm_id)
    )


@router.get("/summary", response_model=ReportsSummary, dependencies=[Depends(require_staff)])
def reports_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
):
    """Aggregate analytics for the reports dashboard: monthly filings, staff
    productivity, average client turnaround time, completion rate, and
    revenue (sum of Invoice.total_amount for invoices paid in the period —
    see HANDOFF §5, previously hardcoded to 0 before the Invoice model
    existed)."""
    period_end = period_end or date.today()
    period_start = period_start or (period_end - timedelta(days=365))

    scoped_ids = _firm_scoped_filing_ids(db, current_user)
    revenue_firm_id = None if current_user.role == UserRole.SUPER_ADMIN else current_user.firm_id
    revenue = InvoiceRepository(db).sum_paid_between(revenue_firm_id, period_start, period_end)

    base_filter = [FilingRequest.created_at.between(period_start, period_end)]
    if scoped_ids is not None:
        base_filter.append(FilingRequest.id.in_(scoped_ids))

    # Monthly filings count
    month_expr = func.to_char(FilingRequest.created_at, "YYYY-MM")
    monthly_rows = db.execute(
        select(month_expr.label("month"), func.count().label("count"))
        .where(*base_filter)
        .group_by(month_expr)
        .order_by(month_expr)
    ).all()
    monthly_filings = [MonthlyFilingsPoint(month=r.month, count=r.count) for r in monthly_rows]

    # Staff productivity: filings completed per accountant in period
    staff_rows = db.execute(
        select(
            User.id, User.full_name, func.count(FilingRequest.id).label("completed")
        )
        .join(FilingRequest, FilingRequest.assigned_accountant_id == User.id)
        .where(FilingRequest.stage == FilingStage.COMPLETED, *base_filter)
        .group_by(User.id, User.full_name)
        .order_by(func.count(FilingRequest.id).desc())
    ).all()
    staff_productivity = [
        StaffProductivityRow(accountant_id=str(r.id), accountant_name=r.full_name, filings_completed=r.completed)
        for r in staff_rows
    ]

    # Turnaround: avg days between "requested" and "filed" stage events
    requested = FilingStageEvent.__table__.alias("requested_evt")
    filed = FilingStageEvent.__table__.alias("filed_evt")
    turnaround_query = (
        select(func.avg(func.extract("epoch", filed.c.created_at - requested.c.created_at) / 86400.0))
        .select_from(requested.join(filed, filed.c.filing_request_id == requested.c.filing_request_id))
        .where(
            requested.c.stage == FilingStage.REQUESTED,
            filed.c.stage == FilingStage.FILED,
        )
    )
    if scoped_ids is not None:
        turnaround_query = turnaround_query.where(requested.c.filing_request_id.in_(scoped_ids))
    avg_days = db.scalar(turnaround_query)

    sample_size = db.scalar(
        select(func.count())
        .select_from(requested.join(filed, filed.c.filing_request_id == requested.c.filing_request_id))
        .where(requested.c.stage == FilingStage.REQUESTED, filed.c.stage == FilingStage.FILED)
    ) or 0

    # Completion rate
    total = db.scalar(select(func.count()).select_from(FilingRequest).where(*base_filter)) or 0
    completed = db.scalar(
        select(func.count()).select_from(FilingRequest).where(
            FilingRequest.stage == FilingStage.COMPLETED, *base_filter
        )
    ) or 0
    completion_rate = (completed / total) if total else 0.0

    return ReportsSummary(
        period_start=period_start,
        period_end=period_end,
        monthly_filings=monthly_filings,
        revenue=revenue,
        staff_productivity=staff_productivity,
        turnaround=TurnaroundStats(avg_days=avg_days, sample_size=sample_size),
        completion_rate=completion_rate,
    )
