from datetime import date

from pydantic import BaseModel


class MonthlyFilingsPoint(BaseModel):
    month: str  # "2026-01"
    count: int


class StaffProductivityRow(BaseModel):
    accountant_id: str
    accountant_name: str
    filings_completed: int


class TurnaroundStats(BaseModel):
    avg_days: float | None
    sample_size: int


class ReportsSummary(BaseModel):
    period_start: date
    period_end: date
    monthly_filings: list[MonthlyFilingsPoint]
    revenue: float  # sum of paid Invoice.total_amount in the period, see HANDOFF §5
    staff_productivity: list[StaffProductivityRow]
    turnaround: TurnaroundStats
    completion_rate: float  # completed / total filings in period, 0-1
